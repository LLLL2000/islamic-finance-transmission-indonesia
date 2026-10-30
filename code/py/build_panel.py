import sys; sys.path.append(r"C:/Users/consu/AppData/Local/Packages/PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0/LocalCache/local-packages/Python311/site-packages")
"""
build_panel.py -- harmonised sector x bank-type credit panel for the Indonesian dual-banking paper.

Builds every output from data/clean/ only (outputs of the ojk_sector and bi_credit builders):
    ojk_islamic_financing_by_sector.csv   OJK SPS Islamic financing and NPF by sector (old9 / new19)
    ojk_conversion_events.csv              conversion / merger / scan events
    bi_credit_by_sector_group.csv          BI SEKI I.4 credit by sector and bank group (old9 / kbli17)
For one validation check only (T7) it also reads, read-only and values only, the raw OJK SPI workbook
data/raw/ojk/SPI_2025_02.xlsx (placed there by another builder); the check is skipped if the file is absent.
Writes data/clean/:
    sector_crosswalk.csv                   source code -> harmonised sector, with validity windows and basis
    panel_sector_banktype.csv              long panel: date x panel (H9/H15) x sector x bank type
    sector_islamic_share.csv               Islamic share of commercial-bank credit by sector + pre-period averages
and prints one JSON block with every validation number quoted in notes/data_panel.md.

Run from the project root:  python -I code/py/build_panel.py   (all paths inside are absolute)
The script is deterministic: fixed sort orders, explicit rounding, no timestamps in outputs.
"""
import hashlib
import json

import numpy as np
import pandas as pd

ROOT = "C:/Users/consu/Documents/Universidad/Islamic_Finance_Project/wp_dual_banking"
CLEAN = ROOT + "/data/clean"
IN_OJK = CLEAN + "/ojk_islamic_financing_by_sector.csv"
IN_EVT = CLEAN + "/ojk_conversion_events.csv"
IN_BI = CLEAN + "/bi_credit_by_sector_group.csv"
OUT_XW = CLEAN + "/sector_crosswalk.csv"
OUT_PANEL = CLEAN + "/panel_sector_banktype.csv"
OUT_SHARE = CLEAN + "/sector_islamic_share.csv"
# Validation only (never used to build outputs): OJK SPI Feb-2025 edition, read-only, values only.
IN_SPI = ROOT + "/data/raw/ojk/SPI_2025_02.xlsx"

T = pd.Timestamp
GRID = pd.date_range("2009-01-01", "2025-06-01", freq="MS")
END = T("2025-06-01")
BANK_TYPES = ["ISL", "BUS", "UUS", "CONV", "TOTAL"]

# Thresholds (documented in notes/data_panel.md, section 5)
MATERIAL_REL = 0.01    # event footprint: |abnormal m/m change| >= 1% of the previous level ...
Z_THR = 3.0            # ... and >= 3 robust noise units of that series -> sector affected (merger/scan/follow-up months)
MIRROR_REL = 0.005     # SPS reclassification mirrored in SEKI: flag TOTAL if |abnormal ISL change| >= 0.5% of TOTAL
SPIKE = 0.10           # one-month spike: |dlog| >= 0.10 into t and out of t, opposite signs ...
SPIKE_OFFSET = 0.25    # ... and |dlog_t + dlog_t+1| <= 0.25 * max(|dlog_t|, |dlog_t+1|) (reversal of >= 75%)
REALLOC_MULT = 4.0     # informational: reallocation index above 4x its median over the panel span
BIG_JUMP = 0.10        # informational: |dlog| above 0.10 for CONV or TOTAL in a month whose change is otherwise ok

V = {}  # validation block


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def r(x, nd=4):
    """Round for the JSON block (None for NaN)."""
    if x is None:
        return None
    try:
        if pd.isna(x):
            return None
    except (TypeError, ValueError):
        pass
    return round(float(x), nd)


def ym(d):
    return pd.Timestamp(d).strftime("%Y-%m")


# ----------------------------------------------------------------------------------------------
# 1. Inputs
# ----------------------------------------------------------------------------------------------
ojk = pd.read_csv(IN_OJK, parse_dates=["date"])
evt = pd.read_csv(IN_EVT, parse_dates=["date"])
bi = pd.read_csv(IN_BI, parse_dates=["date"])
V["inputs"] = {p.split("/")[-1]: {"md5": md5(p), "rows": int(n)}
               for p, n in [(IN_OJK, len(ojk)), (IN_EVT, len(evt)), (IN_BI, len(bi))]}
assert not ojk.duplicated(["date", "classification", "bank_type", "sector_code"]).any()
assert not bi.duplicated(["date", "classification", "bank_group_code", "sector_code"]).any()


def sps_wide(cls, bt, value):
    d = ojk[(ojk.classification == cls) & (ojk.bank_type == bt)]
    return d.pivot(index="date", columns="sector_code", values=value).reindex(GRID)


SPS_FIN = {(c, b): sps_wide(c, b, "financing_rp_bn") for c, b in
           [("old9", "BUSUUS"), ("new19", "BUSUUS"), ("new19", "BUS"), ("new19", "UUS")]}
SPS_NPF = {(c, b): sps_wide(c, b, "npf_rp_bn") for c, b in SPS_FIN}
# rows carrying a builder note (corrections, provisional cells, year-end column, ...)
SPS_NOTE = {(c, b): ojk[(ojk.classification == c) & (ojk.bank_type == b)].assign(
    has=lambda x: (x["note"].notna() & (x["note"].astype(str).str.len() > 0)).astype(float)).pivot(
    index="date", columns="sector_code", values="has").reindex(GRID).fillna(0.0) > 0
    for c, b in SPS_FIN}

HH_ITEMS = ["HH_housing", "HH_flat_apartment", "HH_shophouse_office", "HH_vehicles", "HH_other"]
COMM_GROUPS = ["persero", "bpd", "bsn", "foreign_joint", "foreign_branch"]


def seki_commercial(cls):
    """Commercial-bank credit by sector = SEKI 'total' (banks + BPR) minus BPR."""
    d = bi[(bi.classification == cls) & bi.bank_group_code.isin(["total", "bpr"] + COMM_GROUPS)].copy()
    # BPR has no household breakdown: all BPR consumption is in HH_other and the other four HH items are 0
    # in every month, except 2024-01..05 when the source leaves them blank. Treat those blanks as 0.
    hh0 = (d.bank_group_code == "bpr") & d.sector_code.isin(HH_ITEMS[:4])
    assert d.loc[hh0 & d.credit_rp_bn.notna(), "credit_rp_bn"].abs().max() == 0.0
    n_fixed = int((hh0 & d.credit_rp_bn.isna()).sum())
    d.loc[hh0 & d.credit_rp_bn.isna(), "credit_rp_bn"] = 0.0
    w = d.pivot(index=["date", "sector_code"], columns="bank_group_code", values="credit_rp_bn")
    comm = w["total"] - w["bpr"]
    groups = [g for g in COMM_GROUPS if g in w.columns]
    gsum = w[groups].sum(axis=1, min_count=1)
    both = comm.notna() & gsum.notna()
    gap = float((comm[both] - gsum[both]).abs().max())
    wide = comm.unstack("sector_code").reindex(GRID)
    return wide, gap, n_fixed


SEKI = {}
V["seki_commercial"] = {}
for cls in ["old9", "kbli17"]:
    SEKI[cls], gap, nfix = seki_commercial(cls)
    secs = [c for c in SEKI[cls].columns if c not in ("TOTAL", "PROD_TOTAL", "NONPROD_TOTAL") and not c.startswith(("HH_", "MEMO"))]
    ok = SEKI[cls]["TOTAL"].notna()
    V["seki_commercial"][cls] = {
        "months": int(ok.sum()), "first": ym(SEKI[cls].index[ok][0]), "last_used": ym(SEKI[cls].index[ok][-1]),
        "max_gap_total_minus_bpr_vs_sum_commercial_groups_rp_bn": r(gap, 6),
        "bpr_hh_blank_cells_set_to_zero": nfix,
        "max_gap_sectors_vs_PROD_TOTAL_rp_bn": r((SEKI[cls][secs].sum(axis=1, min_count=len(secs)) - SEKI[cls]["PROD_TOTAL"]).abs().max(), 6),
        "max_gap_HH_items_vs_NONPROD_TOTAL_rp_bn": r((SEKI[cls][HH_ITEMS].sum(axis=1, min_count=5) - SEKI[cls]["NONPROD_TOTAL"]).abs().max(), 6),
        "max_gap_PROD_plus_NONPROD_vs_TOTAL_rp_bn": r((SEKI[cls]["PROD_TOTAL"] + SEKI[cls]["NONPROD_TOTAL"] - SEKI[cls]["TOTAL"]).abs().max(), 6),
    }

# ----------------------------------------------------------------------------------------------
# 2. Crosswalk (single source of truth; written to sector_crosswalk.csv)
# ----------------------------------------------------------------------------------------------
L = lambda a, z: [f"L{i:02d}" for i in range(a, z + 1)]
N_ALL = [f"N0{i}" for i in range(1, 7)]
K17_SVC = ["K_finance_insurance", "L_real_estate", "MN_business_services",
           "O_public_admin", "P_education", "Q_health_social", "RSU_other_services"]
SRC = {"sps_old9": ("OJK SPS", "old9"), "sps_new19": ("OJK SPS", "new19"),
       "seki_old9": ("BI SEKI I.4", "old9"), "seki_kbli17": ("BI SEKI I.4", "kbli17")}

# each mapping: source -> (codes, quality, basis)
PANELS = {
    "H9": {
        "windows": {"sps_old9": (T("2009-01-01"), T("2014-05-01")), "sps_new19": (T("2014-06-01"), END),
                    "seki_old9": (T("2009-01-01"), T("2017-06-01")), "seki_kbli17": (T("2017-07-01"), END)},
        "pre": (T("2009-01-01"), T("2011-12-01")), "pre_alt": (T("2015-03-01"), T("2016-08-01")),
        "sectors": [
            ("H9_AGR", "Agriculture, forestry and fishery", {
                "sps_old9": (["S01"], "exact", "S01 = L01+L02 exactly in all 12 overlap months 2014-06..2015-05 (ojk_sector V6)"),
                "sps_new19": (L(1, 2), "exact", "agriculture/hunting/forestry plus fishery = SEKI agriculture incl. fishery"),
                "seki_old9": (["old_A_agri"], "exact", "old SEKI 'Pertanian, Peternakan, Kehutanan & Perikanan'"),
                "seki_kbli17": (["A_agri"], "exact", "KBLI-2015 A; within 0.04% of old9 in all 13 overlap months")}),
            ("H9_MIN", "Mining and quarrying", {
                "sps_old9": (["S02"], "exact", "S02 = L03 exactly in the 12 overlap months"),
                "sps_new19": (["L03"], "exact", "mining and quarrying"),
                "seki_old9": (["old_B_mining"], "exact", "old SEKI mining and quarrying"),
                "seki_kbli17": (["B_mining"], "near-exact", "KBLI-2015 B; -0.6% to -0.9% vs old9 in the overlap")}),
            ("H9_MAN", "Manufacturing", {
                "sps_old9": (["S03"], "exact", "S03 = L04 exactly in the 12 overlap months"),
                "sps_new19": (["L04"], "exact", "manufacturing"),
                "seki_old9": (["old_C_manuf"], "exact", "old SEKI manufacturing"),
                "seki_kbli17": (["C_manuf"], "exact", "KBLI-2015 C; within 0.12% of old9 in the overlap")}),
            ("H9_UTL", "Electricity, gas and water", {
                "sps_old9": (["S04"], "exact", "S04 = L05 exactly in the 12 overlap months"),
                "sps_new19": (["L05"], "exact", "electricity, gas and water"),
                "seki_old9": (["old_DE_utilities"], "exact", "old SEKI electricity, gas and clean water"),
                "seki_kbli17": (["D_elec_gas", "E_water_waste"], "approximate", "KBLI-2015 D+E; +1.1% to +1.5% vs old9 (E adds sewerage/waste)")}),
            ("H9_CON", "Construction", {
                "sps_old9": (["S05"], "exact", "S05 = L06 exactly in the 12 overlap months"),
                "sps_new19": (["L06"], "exact", "construction"),
                "seki_old9": (["old_F_construction"], "exact", "old SEKI construction"),
                "seki_kbli17": (["F_construction"], "exact", "KBLI-2015 F; 0.00% vs old9 in the overlap")}),
            ("H9_TRD", "Trade, hotels and restaurants", {
                "sps_old9": (["S06"], "exact", "S06 = L07+L08 exactly in the 12 overlap months"),
                "sps_new19": (L(7, 8), "exact", "wholesale/retail trade plus accommodation and food"),
                "seki_old9": (["old_GI_trade_hotel_rest"], "exact", "old SEKI trade, hotels and restaurants"),
                "seki_kbli17": (["G_trade", "I_accom_food"], "approximate", "KBLI-2015 G+I; +1.4% to +1.5% vs old9")}),
            ("H9_TRN", "Transport, storage and communication", {
                "sps_old9": (["S07"], "exact", "S07 = L09 exactly in the 12 overlap months"),
                "sps_new19": (["L09"], "exact", "transport, warehousing and communication"),
                "seki_old9": (["old_HJ_transport_comm"], "exact", "old SEKI transport and communication"),
                "seki_kbli17": (["H_transport", "J_info_comm"], "approximate", "KBLI-2015 H+J; +8.5% to +9.3% vs old9 (J is broader)")}),
            ("H9_SHH", "Finance, real estate, business and social services, and households", {
                "sps_old9": (["S08", "S09", "S10"], "exact (aggregate)",
                             "S08 includes household house/flat/shop-house and S10 includes L18 plus other household; only the union S08+S09+S10 is consistent"),
                "sps_new19": (L(10, 18) + N_ALL, "exact", "all financial, real-estate, business, social and unclassified activities plus all non-business recipients"),
                "seki_old9": (["old_KLMN_fin_realestate_business", "old_OPQRS_services", "NONPROD_TOTAL"], "exact",
                              "old SEKI finance/real estate/business + services + household consumption"),
                "seki_kbli17": (K17_SVC + ["NONPROD_TOTAL"], "approximate", "KBLI-2015 K+L+MN+O+P+Q+RSU + household consumption; -1.6% to -1.7% vs old9")}),
        ]},
    "H15": {
        "windows": {"sps_new19": (T("2016-06-01"), END), "seki_kbli17": (T("2016-06-01"), END)},
        "pre": (T("2016-06-01"), T("2017-11-01")), "pre_alt": None,
        # "all-bank gap" = OJK SPI (LBU codes, all commercial banks) vs SEKI (KBLI-2015), 2024-02..2025-02 (check T7)
        "sectors": [
            ("H15_AGR", "Agriculture, forestry and fishery", {
                "sps_new19": (L(1, 2), "exact", "L01+L02 = KBLI A (agriculture incl. fishery)"),
                "seki_kbli17": (["A_agri"], "exact", "KBLI-2015 A; all-bank gap below 0.6%")}),
            ("H15_MIN", "Mining and quarrying", {
                "sps_new19": (["L03"], "exact (level gap)", "mining"),
                "seki_kbli17": (["B_mining"], "exact (level gap)", "KBLI-2015 B; all-bank LBU above KBLI by 8-11%, stable (likely non-resident borrowers)")}),
            ("H15_MAN", "Manufacturing", {
                "sps_new19": (["L04"], "exact (level gap)", "manufacturing"),
                "seki_kbli17": (["C_manuf"], "exact (level gap)", "KBLI-2015 C; all-bank LBU above KBLI by about 4%, stable")}),
            ("H15_UTL", "Electricity, gas, water and waste", {
                "sps_new19": (["L05"], "approximate", "electricity, gas and water"),
                "seki_kbli17": (["D_elec_gas", "E_water_waste"], "approximate", "KBLI-2015 D+E (E adds sewerage/waste); all-bank gap 3.5-5.3%")}),
            ("H15_CON", "Construction", {
                "sps_new19": (["L06"], "exact", "construction"),
                "seki_kbli17": (["F_construction"], "exact", "KBLI-2015 F; all-bank gap below 0.6%")}),
            ("H15_TRD", "Wholesale and retail trade", {
                "sps_new19": (["L07"], "approximate", "wholesale and retail trade"),
                "seki_kbli17": (["G_trade"], "approximate", "KBLI-2015 G (incl. motor-vehicle repair); all-bank gap 1.0-2.2%")}),
            ("H15_ACC", "Accommodation and food services", {
                "sps_new19": (["L08"], "approximate", "accommodation and food"),
                "seki_kbli17": (["I_accom_food"], "approximate", "KBLI-2015 I; all-bank gap below 0.5%")}),
            ("H15_TRN", "Transport, storage, information and communication", {
                "sps_new19": (["L09"], "approximate", "transport, warehousing and communication"),
                "seki_kbli17": (["H_transport", "J_info_comm"], "approximate", "KBLI-2015 H+J; all-bank KBLI above LBU L09 by 3.4-5.8% (J broader)")}),
            ("H15_FIN", "Financial and insurance activities", {
                "sps_new19": (["L10"], "approximate", "financial intermediaries"),
                "seki_kbli17": (["K_finance_insurance"], "approximate", "KBLI-2015 K; all-bank gap 1.9-4.6%")}),
            ("H15_REB", "Real estate, renting and business services", {
                "sps_new19": (["L11"], "approximate", "real estate, renting and business services"),
                "seki_kbli17": (["L_real_estate", "MN_business_services"], "approximate", "KBLI-2015 L+M+N; all-bank gap 5.1-6.3%")}),
            ("H15_SOC", "Public administration, education, health, other services and unclassified", {
                "sps_new19": (L(12, 18), "approximate", "L12..L17 plus L18 'not clearly defined' (no KBLI-2015 counterpart; 1.5 tn in 2016-06, 0 from 2022)"),
                "seki_kbli17": (["O_public_admin", "P_education", "Q_health_social", "RSU_other_services"], "approximate",
                                "KBLI-2015 O+P+Q+R/S/T/U; all-bank LBU L13-L18 above KBLI P+Q+RSU by 16-25%; SPI L12 includes central government")}),
            ("H15_HRE", "Households: house and apartment ownership", {
                "sps_new19": (["N01", "N02"], "exact", "same LBU household categories"),
                "seki_kbli17": (["HH_housing", "HH_flat_apartment"], "exact", "SEKI housing + flat/apartment; all-bank gap below 0.1%")}),
            ("H15_HSH", "Households: shop-house and office-house ownership", {
                "sps_new19": (["N03"], "exact", "same LBU household category"),
                "seki_kbli17": (["HH_shophouse_office"], "exact", "SEKI ruko/rukan; all-bank gap below 0.1%")}),
            ("H15_HVE", "Households: motor vehicles", {
                "sps_new19": (["N04"], "exact", "same LBU household category"),
                "seki_kbli17": (["HH_vehicles"], "exact", "SEKI vehicles; all-bank gap below 0.1%")}),
            ("H15_HOT", "Households: other consumption and other non-business", {
                "sps_new19": (["N05", "N06"], "exact", "other household equipment incl. multipurpose + other non-business"),
                "seki_kbli17": (["HH_other"], "exact", "SEKI household 'Lainnya'; all-bank gap below 0.2%")}),
        ]},
}
PANEL_START = {p: min(lo for lo, _ in spec["windows"].values()) for p, spec in PANELS.items()}

# exhaustiveness: every source code used exactly once per panel and source
EXPECTED = {
    "sps_old9": [f"S{i:02d}" for i in range(1, 11)],
    "sps_new19": L(1, 18) + N_ALL,
    "seki_old9": ["old_A_agri", "old_B_mining", "old_C_manuf", "old_DE_utilities", "old_F_construction",
                  "old_GI_trade_hotel_rest", "old_HJ_transport_comm", "old_KLMN_fin_realestate_business",
                  "old_OPQRS_services", "NONPROD_TOTAL"],
}
V["crosswalk_exhaustive"] = {}
for p, spec in PANELS.items():
    for src in spec["windows"]:
        used = [c for _, _, m in spec["sectors"] for c in m[src][0]]
        assert len(used) == len(set(used)), (p, src, "duplicate code")
        if src == "seki_kbli17":
            exp = ([c for c in SEKI["kbli17"].columns if c not in ("TOTAL", "PROD_TOTAL", "NONPROD_TOTAL") and not c.startswith("HH_")]
                   + (["NONPROD_TOTAL"] if p == "H9" else HH_ITEMS))
        else:
            exp = EXPECTED[src]
        assert sorted(used) == sorted(exp), (p, src, sorted(set(exp) ^ set(used)))
        V["crosswalk_exhaustive"][f"{p}:{src}"] = f"{len(used)} codes, each used once"

# labels for the crosswalk file
LAB_SPS = ojk.drop_duplicates(["classification", "sector_code"]).set_index(["classification", "sector_code"])[["sector_id_label", "sector_en"]]
LAB_BI = bi[bi.bank_group_code == "total"].drop_duplicates(["classification", "sector_code"]).set_index(["classification", "sector_code"])[["sector_label_id", "sector_label_en"]]
xw_rows = []
for p, spec in PANELS.items():
    for sid, slab, maps in spec["sectors"]:
        for src, (codes, quality, basis) in maps.items():
            org, cls = SRC[src]
            lo, hi = spec["windows"][src]
            for c in codes:
                if org == "OJK SPS":
                    lid, len_ = LAB_SPS.loc[(cls, c)]
                else:
                    lid, len_ = LAB_BI.loc[(cls, c)]
                xw_rows.append({"panel": p, "sector_h": sid, "sector_label": slab, "source": org,
                                "source_classification": cls, "source_code": c, "source_label_id": lid,
                                "source_label_en": len_, "valid_from": lo.strftime("%Y-%m-%d"),
                                "valid_to": hi.strftime("%Y-%m-%d"), "mapping_quality": quality, "basis": basis})
XW = pd.DataFrame(xw_rows)

# ----------------------------------------------------------------------------------------------
# 3. Harmonised series
# ----------------------------------------------------------------------------------------------
def hsum(wide, codes):
    miss = [c for c in codes if c not in wide.columns]
    assert not miss, miss
    return wide[codes].sum(axis=1, min_count=len(codes))


def windowed(parts, windows):
    out = pd.Series(np.nan, index=GRID)
    for src, s in parts.items():
        lo, hi = windows[src]
        m = (GRID >= lo) & (GRID <= hi)
        out[m] = s[m]
    return out


LEV, NPF, NOTE = {}, {}, {}
for p, spec in PANELS.items():
    w = spec["windows"]
    for sid, slab, maps in spec["sectors"]:
        isl_parts, isl_npf, isl_note = {}, {}, {}
        if "sps_old9" in maps:
            c = maps["sps_old9"][0]
            isl_parts["sps_old9"] = hsum(SPS_FIN[("old9", "BUSUUS")], c)
            isl_npf["sps_old9"] = hsum(SPS_NPF[("old9", "BUSUUS")], c)
            isl_note["sps_old9"] = SPS_NOTE[("old9", "BUSUUS")][c].any(axis=1).astype(float)
        c19 = maps["sps_new19"][0]
        for bt, key in [("ISL", "BUSUUS"), ("BUS", "BUS"), ("UUS", "UUS")]:
            parts = dict(isl_parts) if bt == "ISL" else {}
            nparts = dict(isl_npf) if bt == "ISL" else {}
            notes = dict(isl_note) if bt == "ISL" else {}
            parts["sps_new19"] = hsum(SPS_FIN[("new19", key)], c19)
            nparts["sps_new19"] = hsum(SPS_NPF[("new19", key)], c19)
            notes["sps_new19"] = SPS_NOTE[("new19", key)][c19].any(axis=1).astype(float)
            LEV[(p, sid, bt)] = windowed(parts, w)
            NPF[(p, sid, bt)] = windowed(nparts, w)
            NOTE[(p, sid, bt)] = windowed(notes, w).fillna(0).astype(bool)
        tparts = {src: hsum(SEKI[SRC[src][1]], maps[src][0]) for src in maps if src.startswith("seki")}
        LEV[(p, sid, "TOTAL")] = windowed(tparts, w)
        LEV[(p, sid, "CONV")] = LEV[(p, sid, "TOTAL")] - LEV[(p, sid, "ISL")]


def sectors(p):
    return [s for s, _, _ in PANELS[p]["sectors"]]


def frame(p, bt):
    return pd.DataFrame({s: LEV[(p, s, bt)] for s in sectors(p)})


# --- adding-up and bridge checks ---------------------------------------------------------------
V["adding_up"] = {}
for p in PANELS:
    st = PANEL_START[p]
    isl = frame(p, "ISL").loc[st:]
    tot = frame(p, "TOTAL").loc[st:]
    if p == "H9":
        sps_total = windowed({"sps_old9": SPS_FIN[("old9", "BUSUUS")]["TOTAL"], "sps_new19": SPS_FIN[("new19", "BUSUUS")]["TOTAL"]},
                             PANELS["H9"]["windows"]).loc[st:]
    else:
        sps_total = SPS_FIN[("new19", "BUSUUS")]["TOTAL"].loc[st:]
    seki_total = windowed({src: SEKI[SRC[src][1]]["TOTAL"] for src in PANELS[p]["windows"] if src.startswith("seki")},
                          PANELS[p]["windows"]).loc[st:]
    bus, uus = frame(p, "BUS").loc[st:], frame(p, "UUS").loc[st:]
    V["adding_up"][p] = {
        "max_gap_sum_ISL_sectors_vs_SPS_TOTAL_rp_bn": r((isl.sum(axis=1, min_count=isl.shape[1]) - sps_total).abs().max(), 3),
        "max_gap_sum_TOTAL_sectors_vs_SEKI_commercial_TOTAL_rp_bn": r((tot.sum(axis=1, min_count=tot.shape[1]) - seki_total).abs().max(), 6),
        "max_gap_ISL_vs_BUS_plus_UUS_rp_bn": r((isl - bus - uus).abs().max().max(), 3),
        "month_of_max_gap_ISL_vs_BUS_plus_UUS": ym((isl - bus - uus).abs().max(axis=1).idxmax()),
        "conv_identity_max_gap_rp_bn": r((frame(p, "CONV").loc[st:] + isl - tot).abs().max().max(), 9),
    }
# old9 vs new19 at H9 level on the overlap months (validates the 2014-06 switch)
ov = {}
for sid, slab, maps in PANELS["H9"]["sectors"]:
    a = hsum(SPS_FIN[("old9", "BUSUUS")], maps["sps_old9"][0]) - hsum(SPS_FIN[("new19", "BUSUUS")], maps["sps_new19"][0])
    b_ = hsum(SPS_NPF[("old9", "BUSUUS")], maps["sps_old9"][0]) - hsum(SPS_NPF[("new19", "BUSUUS")], maps["sps_new19"][0])
    ov[sid] = {"fin": r(a.loc["2014-06-01":"2015-05-01"].abs().max(), 4), "npf": r(b_.loc["2014-06-01":"2015-05-01"].abs().max(), 4)}
V["H9_sps_old9_vs_new19_overlap_2014_06_2015_05_max_abs_gap_rp_bn"] = ov
# SEKI old9 vs kbli17 at H9 level in the 13 overlap months (size of the 2017-07 splice break)
sk = {}
for sid, slab, maps in PANELS["H9"]["sectors"]:
    a = hsum(SEKI["old9"], maps["seki_old9"][0]); b_ = hsum(SEKI["kbli17"], maps["seki_kbli17"][0])
    d = (100 * (b_ / a - 1)).loc["2016-06-01":"2017-06-01"]
    sk[sid] = {"min_pct": r(d.min(), 2), "max_pct": r(d.max(), 2), "2017_06_pct": r(d.loc["2017-06-01"], 2)}
V["H9_seki_kbli17_vs_old9_overlap_2016_06_2017_06_pct_diff"] = sk
# SEKI 2017-08 footnote (one bank re-grouped between private national and government banks): it cancels in the
# commercial-bank sum. Check that no H15 sector of SEKI commercial credit moves abnormally in 2017-08.
chk = {}
for sid, slab, maps in PANELS["H15"]["sectors"]:
    s_ = hsum(SEKI["kbli17"], maps["seki_kbli17"][0])
    d_ = 100 * (np.log(s_) - np.log(s_.shift(1)))
    med = d_.rolling(12, min_periods=6).median().shift(1)
    chk[sid] = r((d_ - med).loc["2017-08-01"], 2)
dtot = 100 * (np.log(SEKI["kbli17"]["TOTAL"]) - np.log(SEKI["kbli17"]["TOTAL"].shift(1)))
V["seki_2017_08_check"] = {"commercial_total_dlog_pct": r(dtot.loc["2017-08-01"], 3),
                           "commercial_total_median_abs_dlog_2016_07_2025_06_pct": r(dtot.loc["2016-07-01":].abs().median(), 3),
                           "abnormal_dlog_by_H15_sector_pct": chk, "max_abs_abnormal_pct": r(max(abs(v) for v in chk.values() if v is not None), 2)}

# ----------------------------------------------------------------------------------------------
# 4. Does SEKI include Islamic financing? (evidence, sections 2 of the note)
# ----------------------------------------------------------------------------------------------
def dlog(s):
    return 100 * (np.log(s) - np.log(s.shift(1)))


IT = {}
com9 = SEKI["old9"]["TOTAL"]
com17 = SEKI["kbli17"]["TOTAL"]
com = com9.where(GRID <= T("2017-06-01"), com17)
isl_tot = SPS_FIN[("old9", "BUSUUS")]["TOTAL"].where(GRID <= T("2014-05-01"), SPS_FIN[("new19", "BUSUUS")]["TOTAL"])
g = dlog(com)
IT["T1_total_level"] = {
    "seki_commercial_2014_04_rp_bn": r(com.loc["2014-04-01"], 1), "seki_commercial_2014_05_rp_bn": r(com.loc["2014-05-01"], 1),
    "seki_commercial_dlog_2014_05_pct": r(g.loc["2014-05-01"], 3),
    "seki_commercial_median_abs_dlog_2009_02_2025_06_pct": r(g.loc["2009-02-01":].abs().median(), 3),
    "isl_total_2014_05_rp_bn": r(isl_tot.loc["2014-05-01"], 1),
    "isl_total_2014_05_pct_of_seki_commercial": r(100 * isl_tot.loc["2014-05-01"] / com.loc["2014-05-01"], 3),
    "largest_monthly_rises_2009_2025_pct": {ym(k): r(v, 2) for k, v in g.loc["2009-02-01":].nlargest(3).items()},
    "largest_monthly_falls_2009_2025_pct": {ym(k): r(v, 2) for k, v in g.loc["2009-02-01":].nsmallest(3).items()},
    "months_with_rise_above_3pct": [ym(k) for k, v in g.loc["2009-02-01":].items() if v > 3],
}
# T2: conventional credit growth at 2014-05 under A (always included) vs B (excluded before 2014-05)
conv_A = com - isl_tot
conv_B = com.where(GRID < T("2014-05-01"), com - isl_tot)
gA, gB = dlog(conv_A), dlog(conv_B)
t2 = {"total": {"A_dlog_2014_05_pct": r(gA.loc["2014-05-01"], 2), "B_dlog_2014_05_pct": r(gB.loc["2014-05-01"], 2),
                "sd_A_dlog_2009_2025_pct": r(gA.loc["2009-02-01":].drop(T("2014-05-01")).std(), 2),
                "min_A_dlog_2009_2025_excl_2014_05_pct": r(gA.loc["2009-02-01":].drop(T("2014-05-01")).min(), 2)}}
for sid in sectors("H9"):
    tot_s, isl_s = LEV[("H9", sid, "TOTAL")], LEV[("H9", sid, "ISL")]
    a_ = dlog(tot_s - isl_s)
    b_ = dlog(tot_s.where(GRID < T("2014-05-01"), tot_s - isl_s))
    sd = a_.loc["2009-02-01":].drop(T("2014-05-01")).std()
    t2[sid] = {"A_dlog_pct": r(a_.loc["2014-05-01"], 2), "B_dlog_pct": r(b_.loc["2014-05-01"], 2), "sd_A_pct": r(sd, 2),
               "A_z": r(a_.loc["2014-05-01"] / sd, 2), "B_z": r(b_.loc["2014-05-01"] / sd, 2)}
IT["T2_conv_growth_2014_05_A_vs_B"] = t2
# T3: same-month mirror of SPS reclassifications in SEKI household items (SEKI old9 vs SPS new19, 2014-06..2017-06)
PAIRS = {"HH_housing": ["N01"], "HH_flat_apartment": ["N02"], "HH_shophouse_office": ["N03"], "HH_vehicles": ["N04"],
         "HH_other": ["N05", "N06"], "old_A_agri": L(1, 2), "old_B_mining": ["L03"], "old_C_manuf": ["L04"],
         "old_DE_utilities": ["L05"], "old_F_construction": ["L06"], "old_GI_trade_hotel_rest": L(7, 8),
         "old_HJ_transport_comm": ["L09"], "old_KLMN_fin_realestate_business": L(10, 11), "old_OPQRS_services": L(12, 18)}
t3 = {}
win = (GRID >= T("2014-07-01")) & (GRID <= T("2017-06-01")) & ~GRID.isin([T("2016-09-01")])
for sc, codes in PAIRS.items():
    s_ = SEKI["old9"][sc]; i_ = hsum(SPS_FIN[("new19", "BUSUUS")], codes)
    dS, dI = s_.diff(), i_.diff()
    dC = dS - dI
    m = win & dS.notna().values & dI.notna().values
    x, y = dI[m], dS[m]
    slope = float(np.polyfit(x.values, y.values, 1)[0])
    t3[sc] = {"isl_codes": "+".join(codes), "dSEKI_2014_07_rp_bn": r(dS.loc["2014-07-01"], 1), "dISL_2014_07_rp_bn": r(dI.loc["2014-07-01"], 1),
              "dCONV_2014_07_rp_bn": r(dC.loc["2014-07-01"], 1), "sd_dSEKI_rp_bn": r(dS[m].std(), 1), "sd_dCONV_rp_bn": r(dC[m].std(), 1),
              "slope_dSEKI_on_dISL": r(slope, 2), "n_months": int(m.sum())}
IT["T3_mirror_test_seki_old9_vs_sps_new19_2014_07_2017_06"] = t3
# T4: conversions of regional banks (BPD) -- SEKI bpd group total at the conversion month
bpd = bi[(bi.classification == "kbli17") & (bi.bank_group_code == "bpd") & (bi.sector_code == "TOTAL")].set_index("date")["credit_rp_bn"].reindex(GRID)
gb = dlog(bpd)
t4 = {"median_abs_dlog_bpd_2016_07_2025_06_pct": r(gb.loc["2016-07-01":].abs().median(), 3)}
for eid, mth in [("E2", "2016-09-01"), ("E3", "2018-09-01"), ("E5", "2022-08-01")]:
    book = float(evt[(evt.event_id == eid) & (evt.date == T(mth)) & (evt.bank_type == "BUS") & (evt.sector_code == "TOTAL")]["abnormal_change_rp_bn"].iloc[0])
    prev, cur = bpd.shift(1).loc[mth], bpd.loc[mth]
    t4[eid] = {"month": mth[:7], "bus_abnormal_jump_rp_bn": r(book, 1), "seki_bpd_dlog_pct": r(gb.loc[mth], 3),
               "implied_bpd_dlog_if_islamic_excluded_pct": r(100 * (np.log(cur - book) - np.log(prev)), 3)}
IT["T4_bpd_group_at_conversions"] = t4
# T5: 2014-05 SPS reclassification by H9 sector (bounds the pre-2014-05 level mismatch of CONV)
t5 = {}
for sid in sectors("H9"):
    s_ = LEV[("H9", sid, "ISL")]
    d = s_.diff(); a = d - d.rolling(12, min_periods=6).median().shift(1)
    t5[sid] = {"abnormal_isl_change_2014_05_rp_bn": r(a.loc["2014-05-01"], 1),
               "as_pct_of_conv_2014_04": r(100 * a.loc["2014-05-01"] / LEV[("H9", sid, "CONV")].loc["2014-04-01"], 2)}
IT["T5_sps_reclassification_2014_05_by_H9_sector"] = t5
# T6: BUS and UUS separately at 2014-05, and UUS at the Riau Kepri conversion (BPD group)
bus_jun14 = SPS_FIN[("new19", "BUS")]["TOTAL"].loc["2014-06-01"]
uus_jun14 = SPS_FIN[("new19", "UUS")]["TOTAL"].loc["2014-06-01"]
gall = g.loc["2009-02-01":]
# growth of the series net of a block X that would have entered in that month: log(level_t - X) - log(level_t-1)
und_bus = 100 * (np.log(com.loc["2014-05-01"] - bus_jun14) - np.log(com.loc["2014-04-01"]))
und_uus = 100 * (np.log(com.loc["2014-05-01"] - uus_jun14) - np.log(com.loc["2014-04-01"]))
uus_brk = float(evt[(evt.event_id == "E5") & (evt.date == T("2022-08-01")) & (evt.bank_type == "UUS") & (evt.sector_code == "TOTAL")]["abnormal_change_rp_bn"].iloc[0])
gb_all = gb.loc["2016-07-01":"2025-06-01"]
und_bpd = 100 * (np.log(bpd.loc["2022-08-01"] + uus_brk) - np.log(bpd.shift(1).loc["2022-08-01"]))
IT["T6_bus_and_uus_separately"] = {
    "bus_2014_06_rp_bn": r(bus_jun14, 1), "uus_2014_06_rp_bn": r(uus_jun14, 1),
    "underlying_dlog_2014_05_if_bus_first_included_pct": r(und_bus, 2),
    "underlying_dlog_2014_05_if_uus_first_included_pct": r(und_uus, 2),
    "min_monthly_dlog_seki_commercial_2009_2025_pct": r(gall.min(), 2),
    "share_of_months_at_or_below_uus_case": r((gall <= und_uus).mean(), 3),
    "share_of_months_at_or_below_bus_case": r((gall <= und_bus).mean(), 3),
    "riau_kepri_2022_08_uus_abnormal_change_rp_bn": r(uus_brk, 1),
    "bpd_dlog_2022_08_pct": r(gb.loc["2022-08-01"], 3),
    "underlying_bpd_dlog_2022_08_if_uus_excluded_pct": r(und_bpd, 3),
    "share_of_bpd_months_2016_07_2025_06_at_or_below": r((gb_all <= und_bpd).mean(), 3),
}


def spi_crosscheck(path):
    """OJK SPI Tabel 3.1.a (credit/financing of all commercial banks, conventional and sharia, by LBU sector)
    against SEKI commercial credit, by H15 sector, for the edition's monthly columns. Validation only."""
    import re
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        rows = list(wb["Kredit LU_3.1.a.-3.5.a."].iter_rows(min_row=1, max_row=55, values_only=True))
    finally:
        wb.close()
    title = " ".join(str(rows[0][0]).split())
    assert title.startswith("Tabel 3.1.a. Kredit/Pembiayaan dan NPL/NPF Bank Umum Kepada Pihak Ketiga Bukan Bank"), title
    mon = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "Mei": 5, "Jun": 6, "Jul": 7, "Agt": 8, "Sep": 9, "Okt": 10, "Nov": 11, "Des": 12}
    cols, year, last = {}, None, 0
    for j in range(2, len(rows[1])):
        y, m = rows[1][j], rows[2][j]
        if y is not None and str(y).strip()[:4].isdigit():
            year = int(str(y).strip()[:4])
        if m is not None and str(m).strip()[:3] in mon:
            mm = mon[str(m).strip()[:3]]
            if last and mm < last and not (y is not None and str(y).strip()[:4].isdigit()):
                year += 1   # a partial year carries its label on its last column (e.g. '2025' above Feb)
            last = mm
            cols[j] = T(year=year, month=mm, day=1)
    code = {}
    for i, rr in enumerate(rows):
        a = str(rr[0]).strip() if rr[0] is not None else ""
        b2 = str(rr[1]).strip() if rr[1] is not None else ""
        mnum = re.match(r"^(\d+)\.$", a)
        if mnum and 1 <= int(mnum.group(1)) <= 18:
            code[i] = f"L{int(mnum.group(1)):02d}"
        elif a == "-" and b2.startswith("Untuk Pemilikan Rumah Tinggal"):
            code[i] = "N01"
        elif a == "-" and "Flat" in b2:
            code[i] = "N02"
        elif a == "-" and "Ruko" in b2:
            code[i] = "N03"
        elif a == "-" and "Kendaraan" in b2:
            code[i] = "N04"
        elif a == "-" and "Peralatan Rumah Tangga" in b2:
            code[i] = "N05"
        elif a.startswith("Bukan Lapangan Usaha Lainnya"):
            code[i] = "N06"
    assert sorted(code.values()) == sorted(L(1, 18) + N_ALL), sorted(code.values())
    spi = pd.DataFrame({c: {d: float(rows[i][j]) for j, d in cols.items()} for i, c in code.items()}).sort_index()
    out = {"table": title[:120], "months": [ym(d) for d in spi.index],
           "note": "2024-03 is provisional in SPI ('Mar *)') and is excluded from the summary statistics"}
    clean_m = [d for d in spi.index if d != T("2024-03-01")]
    pairs = {s: (m["sps_new19"][0], m["seki_kbli17"][0]) for s, _, m in PANELS["H15"]["sectors"]}
    pairs["H15_SOC"] = (L(13, 18), ["P_education", "Q_health_social", "RSU_other_services"])
    pairs["L12_vs_O_public_admin"] = (["L12"], ["O_public_admin"])
    gaps = {}
    for s, (sc, kc) in pairs.items():
        a = spi.loc[clean_m, sc].sum(axis=1)
        b_ = SEKI["kbli17"].loc[clean_m, kc].sum(axis=1)
        pct = 100 * (a / b_ - 1)
        gaps[s if s != "H15_SOC" else "H15_SOC_excl_L12_O"] = {"min_pct": r(pct.min(), 2), "median_pct": r(pct.median(), 2), "max_pct": r(pct.max(), 2),
                                                             "dec2024_spi_rp_bn": r(a.loc["2024-12-01"], 1), "dec2024_seki_rp_bn": r(b_.loc["2024-12-01"], 1)}
    out["spi_vs_seki_pct_gap_by_H15_sector"] = gaps
    hh = {"N01": ["HH_housing"], "N02": ["HH_flat_apartment"], "N03": ["HH_shophouse_office"], "N04": ["HH_vehicles"], "N05+N06": ["HH_other"]}
    out["household_items_max_abs_pct_gap"] = {k: r((100 * (spi.loc[clean_m, k.split("+")].sum(axis=1) / SEKI["kbli17"].loc[clean_m, v].sum(axis=1) - 1)).abs().max(), 3)
                                              for k, v in hh.items()}
    out["household_items_2024_03_pct_gap"] = {k: r(100 * (spi.loc["2024-03-01", k.split("+")].sum() / SEKI["kbli17"].loc["2024-03-01", v].sum() - 1), 2) for k, v in hh.items()}
    d = T("2024-12-01")
    tot_spi, tot_seki = spi.loc[d].sum(), SEKI["kbli17"].loc[d, "TOTAL"]
    out["dec2024_total"] = {"spi_rp_bn": r(tot_spi, 1), "seki_commercial_rp_bn": r(tot_seki, 1), "gap_rp_bn": r(tot_spi - tot_seki, 1),
                            "of_which_L12_minus_O_rp_bn": r(spi.loc[d, "L12"] - SEKI["kbli17"].loc[d, "O_public_admin"], 1),
                            "of_which_households_rp_bn": r(spi.loc[d, N_ALL].sum() - SEKI["kbli17"].loc[d, "NONPROD_TOTAL"], 1),
                            "uus_financing_dec2024_rp_bn": r(SPS_FIN[("new19", "UUS")]["TOTAL"].loc[d], 1),
                            "uus_household_financing_dec2024_rp_bn": r(SPS_FIN[("new19", "UUS")].loc[d, N_ALL].sum(), 1)}
    isl = SPS_FIN[("new19", "BUSUUS")]
    common = [x for x in clean_m if x in isl.dropna(how="all").index]
    out["min_over_codes_and_months_spi_minus_bus_uus_rp_bn"] = r(min((spi.loc[x, L(1, 18) + N_ALL] - isl.loc[x, L(1, 18) + N_ALL]).min() for x in common), 1)
    out["max_islamic_share_of_spi_code_pct"] = r(max((100 * isl.loc[x, L(1, 17)] / spi.loc[x, L(1, 17)]).max() for x in common), 1)
    return out


# T8: SEKI's own sector reshuffle at the footnoted 2014-05 change (old9 commercial, change and abnormal change)
t8 = {}
for sc in ["old_A_agri", "old_B_mining", "old_C_manuf", "old_DE_utilities", "old_F_construction", "old_GI_trade_hotel_rest",
           "old_HJ_transport_comm", "old_KLMN_fin_realestate_business", "old_OPQRS_services"] + HH_ITEMS + ["TOTAL"]:
    s_ = SEKI["old9"][sc]
    d_ = s_.diff()
    a_ = d_ - d_.rolling(12, min_periods=6).median().shift(1)
    t8[sc] = {"chg_rp_bn": r(d_.loc["2014-05-01"], 1), "abnormal_rp_bn": r(a_.loc["2014-05-01"], 1),
              "abnormal_pct": r(100 * a_.loc["2014-05-01"] / s_.shift(1).loc["2014-05-01"], 2)}
IT["T8_seki_old9_reshuffle_2014_05"] = t8
# T9: no other month looks like a first inclusion: every rise above 3% is broad-based across bank groups
grp9 = bi[(bi.classification == "old9") & (bi.sector_code == "TOTAL") & bi.bank_group_code.isin(["persero", "bpd", "bsn", "foreign_joint"])] \
    .pivot(index="date", columns="bank_group_code", values="credit_rp_bn").reindex(GRID)
grp17 = bi[(bi.classification == "kbli17") & (bi.sector_code == "TOTAL") & bi.bank_group_code.isin(["persero", "bpd", "bsn", "foreign_joint", "foreign_branch"])] \
    .pivot(index="date", columns="bank_group_code", values="credit_rp_bn").reindex(GRID)
t9 = {}
for k in [k for k, v in g.loc["2009-02-01":].items() if v > 3]:
    gg = (grp9 if k <= T("2017-06-01") else grp17)
    dd = 100 * (np.log(gg.loc[k]) - np.log(gg.shift(1).loc[k]))
    t9[ym(k)] = {"commercial_dlog_pct": r(g.loc[k], 2), "isl_pct_of_commercial": r(100 * isl_tot.loc[k] / com.loc[k], 2),
                 "bsn_pct_of_commercial": r(100 * gg["bsn"].shift(1).loc[k] / com.shift(1).loc[k], 2),
                 **{f"{c}_dlog_pct": r(v, 2) for c, v in dd.dropna().items()}}
IT["T9_months_with_commercial_rise_above_3pct"] = t9

try:
    IT["T7_spi_crosscheck"] = spi_crosscheck(IN_SPI)
except FileNotFoundError:
    IT["T7_spi_crosscheck"] = {"skipped": "raw SPI file not found"}
IT["decision"] = ("SEKI commercial-bank credit includes BUS and UUS financing in every month 2009-01..2025-06; "
                  "CONV = SEKI commercial - SPS (BUS+UUS) throughout. BUS inclusion is decisive; UUS inclusion is strongly supported, not proven.")
V["inclusion_tests"] = IT

# ----------------------------------------------------------------------------------------------
# 5. Flags
# ----------------------------------------------------------------------------------------------
def abnormal(s):
    d = s.diff()
    a = d - d.rolling(12, min_periods=6).median().shift(1)
    return a, a / s.shift(1)


# Abnormal changes of the Islamic series use their full SPS history (new19 from 2014-06), so that events in the
# first months of H15 (2016-06 start) can be assessed against the previous 12 months.
LEVX = dict(LEV)
for sid, slab, maps in PANELS["H15"]["sectors"]:
    for bt, key in [("ISL", "BUSUUS"), ("BUS", "BUS"), ("UUS", "UUS")]:
        LEVX[("H15", sid, bt)] = hsum(SPS_FIN[("new19", key)], maps["sps_new19"][0])
ABN = {k: abnormal(v) for k, v in LEVX.items()}

BREAKS = [  # id, month, panels, bank types, scope, basis
    ("seki_reclass_2010_01", "2010-01-01", ("H9",), ("CONV", "TOTAL"), "all",
     "SEKI old9 reporting-form reclassification (bi_credit B1): services +357%, construction -21%, utilities -20%"),
    ("seki_reclass_2010_02", "2010-02-01", ("H9",), ("CONV", "TOTAL"), "all",
     "partial reversal of the 2010-01 SEKI reclassification (transport +9.6% then -6.5%, services -10.7%)"),
    ("lsmk_revision_2014_05", "2014-05-01", ("H9",), ("ISL", "BUS", "UUS", "CONV", "TOTAL"), "all",
     "OJK: SPS sector data revised from May 2014 on LSMK basis; BI: coverage/classification change with LBUS/LSMK"),
    ("sps_reclass_2014_07", "2014-07-01", ("H9",), ("ISL", "BUS", "UUS", "CONV"), "all+mirror",
     "new19 reallocation 2014-06 -> 2014-07 (ojk_sector note section 4) and BTPN Syariah spin-off"),
    ("sps_reclass_2015_03", "2015-03-01", ("H9",), ("ISL", "BUS", "UUS", "CONV"), "all+mirror",
     "SPS 'not clearly defined' (L18) -70% (-4.2 tn) reallocated to named sectors (this build)"),
    ("seki_splice_2017_07", "2017-07-01", ("H9",), ("CONV", "TOTAL"), "all",
     "H9 switches SEKI from the old 9-sector to the KBLI-2015 classification"),
    ("seki_adjustment_2024_03", "2024-03-01", ("H9", "H15"), ("CONV", "TOTAL"), "all",
     "BI footnote: 'Terdapat penyesuaian data untuk periode Maret 2024'"),
    ("seki_lbut_2025_01", "2025-01-01", ("H9", "H15"), ("CONV", "TOTAL"), "all",
     "BI footnote: LBUT reporting from Jan-2025, sector assignment changed for all bank groups"),
]
EVENTS = [  # id in ojk_conversion_events.csv, month, kind
    ("E1", "2014-07-01", "spinoff"), ("E2", "2016-09-01", "conversion"), ("E2", "2016-10-01", "followup"),
    ("E3", "2018-09-01", "conversion"), ("E3", "2018-10-01", "followup"), ("E4", "2021-02-01", "merger"),
    ("E5", "2022-08-01", "conversion"), ("E5", "2022-09-01", "followup"), ("S1", "2015-06-01", "scan"),
    ("S2", "2021-10-01", "scan"), ("S2", "2021-11-01", "scan"), ("S2", "2021-12-01", "scan"), ("S3", "2016-12-01", "scan"),
]
for eid, mth, kind in EVENTS:
    assert ((evt.event_id == eid) & (evt.date == T(mth))).any(), (eid, mth)
V["breaks"] = [{"id": b_[0], "month": b_[1][:7], "panels": "+".join(b_[2]), "bank_types": "+".join(b_[3]), "scope": b_[4], "basis": b_[5]} for b_ in BREAKS]
# profile of each break month: dlog (%) by sector of the series the break concerns, plus abnormal % for SEKI breaks
prof = {}
for bid, mth, panels, bts, scope, basis in BREAKS:
    for p in panels:
        for bt in [x for x in ("ISL", "TOTAL") if x in bts]:
            lv = frame(p, bt)
            dl_ = 100 * (np.log(lv) - np.log(lv.shift(1)))
            ab_ = dl_ - dl_.rolling(12, min_periods=6).median().shift(1)
            prof[f"{bid}:{p}:{bt}"] = {s: {"dlog_pct": r(dl_.loc[mth, s], 1), "abnormal_pct": r(ab_.loc[mth, s], 1)} for s in sectors(p)}
o9 = SPS_FIN[("old9", "BUSUUS")]
prof["sps_old9_levels_2014_04_to_2014_05"] = {c: {"2014-04": r(o9.loc["2014-04-01", c], 1), "2014-05": r(o9.loc["2014-05-01", c], 1),
                                                  "dlog_pct": r(100 * np.log(o9.loc["2014-05-01", c] / o9.loc["2014-04-01", c]), 1)}
                                              for c in [f"S{i:02d}" for i in range(1, 11)] + ["TOTAL"]}
V["break_profiles"] = prof
V["events"] = [{"id": e_[0], "month": e_[1][:7], "kind": e_[2],
                "event": str(evt[(evt.event_id == e_[0])]["event"].iloc[0])} for e_ in EVENTS]

FL = {}  # (panel, sector, bank type, date) -> list of reasons


def add(p, s, bt, d, reason):
    FL.setdefault((p, s, bt, T(d)), []).append(reason)


# robust noise scale of each Islamic series: 1.4826 x median |relative abnormal change| over 2014-06..2025-06,
# excluding break and event months
SPECIAL = sorted({T(b_[1]) for b_ in BREAKS} | {T(e_[1]) for e_ in EVENTS})
NOISE = {}
for p in PANELS:
    for s in sectors(p):
        for bt in ("ISL", "BUS", "UUS"):
            rel = ABN[(p, s, bt)][1].loc["2014-06-01":]   # new19 era, where every event lies
            x = rel[~rel.index.isin(SPECIAL)].dropna()
            NOISE[(p, s, bt)] = 1.4826 * float(x.abs().median()) if len(x) else np.nan
V["noise_scale_pct"] = {f"{p}:{bt}": {"median_over_sectors": r(100 * np.nanmedian([NOISE[(p, s, bt)] for s in sectors(p)]), 2),
                                      "min": r(100 * np.nanmin([NOISE[(p, s, bt)] for s in sectors(p)]), 2),
                                      "max": r(100 * np.nanmax([NOISE[(p, s, bt)] for s in sectors(p)]), 2)}
                        for p in PANELS for bt in ("ISL", "BUS", "UUS")}


def footprint(p, s, d):
    """Islamic series of sector s whose abnormal change in month d is >= 1% of the level and >= 3 noise units."""
    hits = {}
    for bt in ("ISL", "BUS", "UUS"):
        v = ABN[(p, s, bt)][1].loc[d]
        nz = NOISE[(p, s, bt)]
        if pd.notna(v) and pd.notna(nz) and nz > 0 and abs(v) >= MATERIAL_REL and abs(v) >= Z_THR * nz:
            hits[bt] = (float(v), float(v / nz))
    return hits


def mirror(p, s, d):
    a = ABN[(p, s, "ISL")][0].loc[d]
    tot_prev = LEV[(p, s, "TOTAL")].shift(1).loc[d]
    return bool(pd.notna(a) and pd.notna(tot_prev) and abs(a) >= MIRROR_REL * tot_prev)


for bid, mth, panels, bts, scope, basis in BREAKS:
    for p in panels:
        if T(mth) < PANEL_START[p]:
            continue
        for s in sectors(p):
            for bt in bts:
                add(p, s, bt, mth, "break_" + bid)
            if scope.endswith("mirror") and mirror(p, s, mth):
                add(p, s, "TOTAL", mth, "break_" + bid + "_mirrored_in_seki")

FOOT = {}
for eid, mth, kind in EVENTS:
    for p in PANELS:
        if T(mth) < PANEL_START[p]:
            continue
        foot = {}
        for s in sectors(p):
            tag = f"event_{eid}_{kind}_{mth[:7]}"
            fp = footprint(p, s, mth)
            if kind == "spinoff":          # UUS -> BUS transfer of a whole bank: BUS and UUS in every sector
                hit = ["BUS", "UUS"]
            elif kind == "conversion":     # whole conventional bank -> BUS: every sector
                hit = ["ISL", "BUS", "UUS", "CONV"]
            else:                          # merger, scan, follow-up: sectors with a footprint above noise
                hit = ["ISL", "BUS", "UUS", "CONV"] if fp else []
            if kind == "merger" and mirror(p, s, mth):
                hit.append("TOTAL")
            for bt in hit:
                add(p, s, bt, mth, tag)
            if hit:
                foot[s] = {"flagged": "+".join(hit),
                           **{f"{bt}_abn_pct": r(100 * ABN[(p, s, bt)][1].loc[mth], 2) for bt in ("ISL", "BUS", "UUS")},
                           **{f"{bt}_z": r(z, 1) for bt, (v, z) in fp.items()}}
        FOOT[f"{eid}_{mth[:7]}_{kind}:{p}"] = foot
V["event_footprints"] = FOOT

# one-month spikes that fully reverse (reporting errors): flag the change into t and into t+1
SPIKES = []
for p in PANELS:
    for s in sectors(p):
        for bt in ("ISL", "BUS", "UUS", "TOTAL"):
            lev = LEV[(p, s, bt)].loc[PANEL_START[p]:]
            d0 = np.log(lev.where(lev > 0)).diff()
            d1 = d0.shift(-1)
            m = ((d0.abs() >= SPIKE) & (d1.abs() >= SPIKE) & (np.sign(d0) != np.sign(d1))
                 & ((d0 + d1).abs() <= SPIKE_OFFSET * np.maximum(d0.abs(), d1.abs()))).fillna(False)
            for t in lev.index[m.values]:
                SPIKES.append({"panel": p, "sector": s, "series": bt, "month": ym(t),
                               "dlog_into_t": r(d0.loc[t], 3), "dlog_into_t1": r(d1.loc[t], 3)})
                targets = [bt] + (["CONV"] if bt in ("ISL", "TOTAL") else [])
                for d in (t, t + pd.offsets.MonthBegin(1)):
                    for t_ in targets:
                        add(p, s, t_, d, f"spike_reversal_{bt}_{ym(t)}")
V["spikes"] = SPIKES

# informational: reallocation index (sum of abnormal sector moves net of the abnormal total move, % of total)
def realloc(p, bt):
    df = frame(p, bt).loc[PANEL_START[p]:]
    k = df.shape[1]
    A = pd.DataFrame({c: abnormal(df[c])[0] for c in df.columns})
    tot = df.sum(axis=1, min_count=k)
    at = abnormal(tot)[0]
    return ((A.abs().sum(axis=1, min_count=k) - at.abs()) / tot.shift(1) * 100).dropna()


INFO = {}


def info(p, s, bt, d, tag):
    INFO.setdefault((p, s, bt, T(d)), []).append(tag)


V["reallocation_index"] = {}
for p in PANELS:
    for bt in ["ISL", "BUS", "UUS", "TOTAL"]:
        R = realloc(p, bt)
        thr = REALLOC_MULT * R.median()
        hi = R[R > thr]
        V["reallocation_index"][f"{p}:{bt}"] = {"median_pct": r(R.median(), 3), "threshold_pct": r(thr, 3),
                                               "months_above": {ym(k): r(v, 2) for k, v in hi.sort_index().items()}}
        tag = "seki_realloc_high" if bt == "TOTAL" else f"{bt.lower()}_realloc_high"
        targets = {"ISL": ["ISL", "CONV"], "BUS": ["BUS"], "UUS": ["UUS"], "TOTAL": ["TOTAL", "CONV"]}[bt]
        for d in hi.index:
            for s in sectors(p):
                for t_ in targets:
                    info(p, s, t_, d, tag)

# ----------------------------------------------------------------------------------------------
# 6. Panel assembly
# ----------------------------------------------------------------------------------------------
rows = []
for p, spec in PANELS.items():
    st = PANEL_START[p]
    dates = GRID[GRID >= st]
    for sid, slab, maps in spec["sectors"]:
        for bt in BANK_TYPES:
            lev = LEV[(p, sid, bt)]
            prev = lev.shift(1)
            isl_lev = LEV[(p, sid, "ISL")]
            npf = NPF.get((p, sid, bt))
            dl = np.log(lev.where(lev > 0)) - np.log(lev.where(lev > 0).shift(1))
            for d in dates:
                c = lev.loc[d]
                reasons = []
                if d == st:
                    reasons.append("panel_first_month")
                if pd.isna(c):
                    reasons.append("level_missing")
                elif d != st and pd.isna(prev.loc[d]):
                    reasons.append("prev_month_missing")
                reasons += FL.get((p, sid, bt, d), [])
                inf = list(INFO.get((p, sid, bt, d), []))
                if bt in ("ISL", "CONV") and p == "H9" and d <= T("2014-04-01"):
                    inf.append("sps_old_sector_basis_pre_lsmk")
                if bt in ("ISL", "BUS", "UUS") and NOTE[(p, sid, bt)].loc[d]:
                    inf.append("sps_source_note")
                ok = len(reasons) == 0
                if bt in ("CONV", "TOTAL") and ok and pd.notna(dl.loc[d]) and abs(dl.loc[d]) > BIG_JUMP:
                    inf.append(bt.lower() + "_large_jump")
                if bt == "CONV" and pd.notna(c) and c <= 0:
                    inf.append("conv_nonpositive")
                if bt == "CONV" and pd.notna(c) and c < isl_lev.loc[d]:
                    inf.append("isl_exceeds_conv")
                src_isl = ""
                src_seki = ""
                for src, (lo, hi) in spec["windows"].items():
                    if lo <= d <= hi:
                        if src.startswith("sps"):
                            src_isl = "SPS " + SRC[src][1]
                        else:
                            src_seki = "SEKI " + SRC[src][1]
                if bt in ("BUS", "UUS") and d < T("2014-06-01"):
                    src_isl = ""
                rows.append({
                    "date": d, "panel": p, "sector_h": sid, "sector_label": slab, "bank_type": bt,
                    "credit_rp_bn": c, "npf_rp_bn": npf.loc[d] if npf is not None else np.nan,
                    "dlog_credit_mom": dl.loc[d], "adj_growth_ok": ok,
                    "flag_reasons": ";".join(dict.fromkeys(reasons)), "info_flags": ";".join(dict.fromkeys(inf)),
                    "src_islamic": src_isl if bt != "TOTAL" else "", "src_seki": src_seki if bt in ("CONV", "TOTAL") else ""})
panel = pd.DataFrame(rows)
order_s = {s: i for i, s in enumerate([s for p in PANELS for s in sectors(p)])}
order_b = {b: i for i, b in enumerate(BANK_TYPES)}
panel = panel.assign(_p=panel.panel.map({"H9": 0, "H15": 1}), _s=panel.sector_h.map(order_s), _b=panel.bank_type.map(order_b)) \
    .sort_values(["_p", "_s", "_b", "date"]).drop(columns=["_p", "_s", "_b"]).reset_index(drop=True)

# spot checks: selected cells recomputed directly from the input files with plain filters
def raw_ojk(cls, bt, codes, d):
    x = ojk[(ojk.classification == cls) & (ojk.bank_type == bt) & (ojk.date == T(d)) & ojk.sector_code.isin(codes)]
    assert len(x) == len(codes)
    return float(x.financing_rp_bn.sum())


def raw_bi(cls, codes, d):
    x = bi[(bi.classification == cls) & (bi.date == T(d)) & bi.sector_code.isin(codes)]
    return float(x[x.bank_group_code == "total"].credit_rp_bn.sum() - x[x.bank_group_code == "bpr"].credit_rp_bn.fillna(0).sum())


SPOT = [
    ("H9", "H9_AGR", "ISL", "2009-01-01", raw_ojk("old9", "BUSUUS", ["S01"], "2009-01-01")),
    ("H9", "H9_SHH", "TOTAL", "2012-06-01", raw_bi("old9", ["old_KLMN_fin_realestate_business", "old_OPQRS_services", "NONPROD_TOTAL"], "2012-06-01")),
    ("H9", "H9_SHH", "ISL", "2012-06-01", raw_ojk("old9", "BUSUUS", ["S08", "S09", "S10"], "2012-06-01")),
    ("H9", "H9_TRN", "CONV", "2020-06-01", raw_bi("kbli17", ["H_transport", "J_info_comm"], "2020-06-01") - raw_ojk("new19", "BUSUUS", ["L09"], "2020-06-01")),
    ("H9", "H9_TRD", "TOTAL", "2016-12-01", raw_bi("old9", ["old_GI_trade_hotel_rest"], "2016-12-01")),
    ("H15", "H15_HSH", "TOTAL", "2024-03-01", raw_bi("kbli17", ["HH_shophouse_office"], "2024-03-01")),
    ("H15", "H15_SOC", "UUS", "2019-04-01", raw_ojk("new19", "UUS", L(12, 18), "2019-04-01")),
    ("H15", "H15_HOT", "ISL", "2023-12-01", raw_ojk("new19", "BUSUUS", ["N05", "N06"], "2023-12-01")),
    ("H15", "H15_FIN", "CONV", "2025-06-01", raw_bi("kbli17", ["K_finance_insurance"], "2025-06-01") - raw_ojk("new19", "BUSUUS", ["L10"], "2025-06-01")),
]
pidx = panel.set_index(["panel", "sector_h", "bank_type", "date"]).credit_rp_bn
V["spot_checks"] = [{"cell": f"{p}/{s}/{bt}/{d[:7]}", "panel_value": r(pidx.loc[(p, s, bt, T(d))], 4), "direct_value": r(x, 4),
                     "abs_gap": r(abs(pidx.loc[(p, s, bt, T(d))] - x), 6)} for p, s, bt, d, x in SPOT]
assert max(c["abs_gap"] for c in V["spot_checks"]) < 1e-6

# ----------------------------------------------------------------------------------------------
# 7. Shares
# ----------------------------------------------------------------------------------------------
srows = []
for p, spec in PANELS.items():
    st = PANEL_START[p]
    dates = GRID[GRID >= st]
    ss = sectors(p) + [p + "_ALL"]
    labs = {s: l for s, l, _ in spec["sectors"]}
    labs[p + "_ALL"] = "All sectors (sum of the panel's sectors)"
    for bt in ["ISL", "BUS", "UUS", "TOTAL"]:
        df = frame(p, bt)
        LEV[(p, p + "_ALL", bt)] = df.sum(axis=1, min_count=df.shape[1])
    tot_isl_all, tot_all = LEV[(p, p + "_ALL", "ISL")], LEV[(p, p + "_ALL", "TOTAL")]
    for s in ss:
        isl, bus, uus, tot = (LEV[(p, s, b)] for b in ["ISL", "BUS", "UUS", "TOTAL"])
        sh = 100 * isl / tot
        shb, shu = 100 * bus / tot, 100 * uus / tot
        lo, hi = spec["pre"]
        pre = sh.loc[lo:hi]
        pre_b, pre_u = shb.loc[lo:hi], shu.loc[lo:hi]
        alt = spec["pre_alt"]
        for d in dates:
            srows.append({
                "date": d, "panel": p, "sector_h": s, "sector_label": labs[s],
                "isl_credit_rp_bn": isl.loc[d], "bus_credit_rp_bn": bus.loc[d], "uus_credit_rp_bn": uus.loc[d],
                "total_credit_rp_bn": tot.loc[d], "isl_share_pct": sh.loc[d], "bus_share_pct": shb.loc[d], "uus_share_pct": shu.loc[d],
                "sector_pct_of_all_isl": 100 * isl.loc[d] / tot_isl_all.loc[d], "sector_pct_of_all_total": 100 * tot.loc[d] / tot_all.loc[d],
                "isl_share_pre_avg_pct": pre.mean(), "bus_share_pre_avg_pct": pre_b.mean() if pre_b.notna().any() else np.nan,
                "uus_share_pre_avg_pct": pre_u.mean() if pre_u.notna().any() else np.nan,
                "pre_period": f"{ym(lo)}..{ym(hi)}", "pre_period_n_months": int(pre.notna().sum()),
                "isl_share_pre_alt_avg_pct": sh.loc[alt[0]:alt[1]].mean() if alt else np.nan,
                "pre_alt_period": f"{ym(alt[0])}..{ym(alt[1])}" if alt else ""})
share = pd.DataFrame(srows)
order_s2 = {s: i for i, s in enumerate([s for p in PANELS for s in sectors(p) + [p + "_ALL"]])}
share = share.assign(_p=share.panel.map({"H9": 0, "H15": 1}), _s=share.sector_h.map(order_s2)) \
    .sort_values(["_p", "_s", "date"]).drop(columns=["_p", "_s"]).reset_index(drop=True)

# ----------------------------------------------------------------------------------------------
# 8. Validation and descriptives
# ----------------------------------------------------------------------------------------------
avail = panel[panel.credit_rp_bn.notna()]
V["conv_checks"] = {
    "n_conv_rows_with_level": int((avail.bank_type == "CONV").sum()),
    "n_conv_nonpositive": int(((avail.bank_type == "CONV") & (avail.credit_rp_bn <= 0)).sum()),
    "n_isl_exceeds_conv": int(panel.info_flags.str.contains("isl_exceeds_conv").sum()),
    "n_conv_large_jump_unflagged": int(panel.info_flags.str.contains("conv_large_jump").sum()),
    "n_total_large_jump_unflagged": int(panel.info_flags.str.contains("total_large_jump").sum()),
    "conv_large_jump_rows": panel[panel.info_flags.str.contains("conv_large_jump")][["date", "panel", "sector_h", "dlog_credit_mom"]]
        .assign(date=lambda x: x.date.dt.strftime("%Y-%m"), dlog_credit_mom=lambda x: x.dlog_credit_mom.round(4)).values.tolist(),
    "min_conv_by_panel_sector_rp_bn": {f"{p}:{s}": r(g_.credit_rp_bn.min(), 1) for (p, s), g_ in avail[avail.bank_type == "CONV"].groupby(["panel", "sector_h"], sort=False)},
    "max_isl_share_pct": {f"{p}:{s}": r(v, 2) for (p, s), v in share[~share.sector_h.str.endswith("_ALL")].groupby(["panel", "sector_h"], sort=False).isl_share_pct.max().items()},
    # sensitivity: level error of CONV if SEKI did NOT include UUS (CONV would then be understated by UUS)
    "uus_as_pct_of_conv_max": {f"{p}:{s}": r((100 * LEV[(p, s, "UUS")] / LEV[(p, s, "CONV")]).max(), 2) for p in PANELS for s in sectors(p)},
    "uus_as_pct_of_conv_2025_06": {f"{p}:{s}": r(100 * LEV[(p, s, "UUS")].loc["2025-06-01"] / LEV[(p, s, "CONV")].loc["2025-06-01"], 2) for p in PANELS for s in sectors(p)},
}
desc = {}
for p in PANELS:
    sub = panel[panel.panel == p]
    av = sub[sub.credit_rp_bn.notna()]
    gr = av[av.dlog_credit_mom.notna()]
    d = {"n_sectors": len(sectors(p)), "first_month": ym(sub.date.min()), "last_month": ym(sub.date.max()),
         "n_months": int(sub.date.nunique()), "rows": len(sub), "rows_with_level": len(av),
         "rows_with_level_by_bank_type": {b: int((av.bank_type == b).sum()) for b in BANK_TYPES},
         "rows_with_mom_change": len(gr),
         "share_flagged_among_rows_with_mom_change_pct": r(100 * (~gr.adj_growth_ok).mean(), 2),
         "share_flagged_by_bank_type_pct": {b: r(100 * (~gr[gr.bank_type == b].adj_growth_ok).mean(), 2) for b in BANK_TYPES},
         "n_adj_growth_ok_true_by_bank_type": {b: int(gr[gr.bank_type == b].adj_growth_ok.sum()) for b in BANK_TYPES}}
    reasons = sub[~sub.adj_growth_ok & sub.credit_rp_bn.notna()].flag_reasons.str.split(";").explode()
    cat = reasons.str.replace(r"_\d{4}-\d{2}$", "", regex=True).str.replace(r"_mirrored_in_seki$", "_mirrored", regex=True)
    d["flag_reason_counts_rows_with_level"] = {k: int(v) for k, v in cat.value_counts().sort_index().items()}
    d["months_with_any_flag_for_CONV"] = sorted({ym(x) for x in sub[(sub.bank_type == "CONV") & ~sub.adj_growth_ok & sub.credit_rp_bn.notna()].date})
    desc[p] = d
V["descriptives_counts"] = desc
# shares over time: annual averages (Islamic data missing 2023-01..11, so 2023 = Dec only)
sh = share.copy()
sh["year"] = sh.date.dt.year
ann = sh.groupby(["panel", "sector_h", "year"], sort=False).isl_share_pct.mean().round(2)
V["isl_share_annual_avg_pct"] = {p: {s: {int(y): r(v, 2) for (pp, ss_, y), v in ann.items() if pp == p and ss_ == s}
                                     for s in sectors(p) + [p + "_ALL"]} for p in PANELS}
busshare = (sh[sh.sector_h.str.endswith("_ALL")].assign(b=lambda x: 100 * x.bus_credit_rp_bn / x.isl_credit_rp_bn)
            .groupby(["panel", "year"]).b.mean().round(2))
V["bus_pct_of_islamic_annual_avg"] = {p: {int(y): r(v, 2) for (pp, y), v in busshare.items() if pp == p and pd.notna(v)} for p in PANELS}
comp = sh[sh.date.dt.month == 6].groupby(["panel", "sector_h", "year"], sort=False).sector_pct_of_all_isl.mean().round(2)
V["sector_pct_of_all_islamic_june"] = {p: {s: {int(y): r(v, 2) for (pp, ss_, y), v in comp.items() if pp == p and ss_ == s and y in (2009, 2012, 2014, 2016, 2019, 2022, 2024, 2025)}
                                           for s in sectors(p)} for p in PANELS}
pre = share.drop_duplicates(["panel", "sector_h"])[["panel", "sector_h", "isl_share_pre_avg_pct", "bus_share_pre_avg_pct", "uus_share_pre_avg_pct", "pre_period", "pre_period_n_months", "isl_share_pre_alt_avg_pct", "pre_alt_period"]]
V["pre_period_shares"] = {f"{x.panel}:{x.sector_h}": {"pre_pct": r(x.isl_share_pre_avg_pct, 3), "pre_bus_pct": r(x.bus_share_pre_avg_pct, 3),
                                                       "pre_uus_pct": r(x.uus_share_pre_avg_pct, 3), "period": x.pre_period, "n": int(x.pre_period_n_months),
                                                       "alt_pct": r(x.isl_share_pre_alt_avg_pct, 3), "alt_period": x.pre_alt_period} for x in pre.itertuples()}
h9pre = pre[(pre.panel == "H9") & ~pre.sector_h.str.endswith("_ALL")]
V["H9_pre_vs_alt_spearman"] = r(h9pre.isl_share_pre_avg_pct.rank().corr(h9pre.isl_share_pre_alt_avg_pct.rank()), 3)

# ----------------------------------------------------------------------------------------------
# 9. Write outputs
# ----------------------------------------------------------------------------------------------
def fmt(df, rounding):
    out = df.copy()
    for c, nd in rounding.items():
        out[c] = out[c].astype(float).round(nd)
    if "date" in out:
        out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    for c in out.columns:
        if out[c].dtype == bool:
            out[c] = np.where(out[c], "TRUE", "FALSE")
    return out


fmt(XW, {}).to_csv(OUT_XW, index=False, lineterminator="\n", encoding="utf-8")
fmt(panel, {"credit_rp_bn": 4, "npf_rp_bn": 4, "dlog_credit_mom": 6}).to_csv(OUT_PANEL, index=False, lineterminator="\n", encoding="utf-8")
fmt(share, {c: 4 for c in share.columns if c.endswith(("_rp_bn", "_pct"))} | {"sector_pct_of_all_isl": 4, "sector_pct_of_all_total": 4}) \
    .to_csv(OUT_SHARE, index=False, lineterminator="\n", encoding="utf-8")
V["outputs"] = {p.split("/")[-1]: {"rows": int(n), "md5": md5(p)} for p, n in [(OUT_XW, len(XW)), (OUT_PANEL, len(panel)), (OUT_SHARE, len(share))]}
print(json.dumps(V, indent=1, ensure_ascii=False))
