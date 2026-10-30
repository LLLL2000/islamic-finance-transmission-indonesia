import sys; sys.path.append(r"C:/Users/consu/AppData/Local/Packages/PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0/LocalCache/local-packages/Python311/site-packages")
"""
Builder: bi_credit
Parses Bank Indonesia SEKI tables (raw .xls files, untrusted data, read only) into tidy long CSVs:
  data/clean/bi_credit_by_sector_group.csv   (SEKI I.4)
  data/clean/bi_lending_rates.csv            (SEKI I.26)
  data/clean/bi_money_market_rates.csv       (SEKI I.25 / file TABEL1_25_1)
  data/clean/bi_deposit_rates.csv            (SEKI I.28)
  data/clean/bi_sbn_outstanding.csv          (SEKI IV.4 / file TABEL4_4)
and prints validation statistics (used in notes/data_bi.md).

Run:  python -I code/py/build_bi_credit.py [project_root]
"""
import os, re, datetime as dt
import numpy as np
import pandas as pd

ROOT = sys.argv[1] if len(sys.argv) > 1 else r"C:/Users/consu/Documents/Universidad/Islamic_Finance_Project/wp_dual_banking"
RAW = os.path.join(ROOT, "data", "raw", "bi")
CLEAN = os.path.join(ROOT, "data", "clean")
os.makedirs(CLEAN, exist_ok=True)

MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "mei": 5, "jun": 6, "jul": 7,
          "aug": 8, "agu": 8, "agt": 8, "sep": 9, "oct": 10, "okt": 10, "nov": 11, "dec": 12, "des": 12}


def norm(s):
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return ""
    s = str(s).replace("\n", " ").replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def key(s):
    return re.sub(r"[^a-z0-9]", "", norm(s).lower())


def to_num(v):
    if v is None:
        return np.nan
    if isinstance(v, (int, float, np.integer, np.floating)):
        return float(v)
    s = str(v).strip()
    if s in ("", "-", "--", "n.a", "na", "n.a."):
        return np.nan
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return np.nan


def read_sheet(fname, sheet):
    return pd.read_excel(os.path.join(RAW, fname), sheet_name=sheet, header=None)


def date_columns(df, year_row=None, month_row=None, datetime_row=None, first_col=3, last_col=None, allow_gaps=False):
    """Return list of (col, date) for monthly columns.
    - datetime_row: header row holding real datetimes (used as-is).
    - else year_row/month_row: month label in month_row; the year is the numeric label in year_row
      at that column if present (SEKI places year labels at the first column of a year or at the
      last column of a partial year, always matching that column's own year), otherwise carried
      forward and incremented when the month index falls (strictly) below the previous one.
    Columns without a month label (annual/year-end duplicate columns, spacer columns) are skipped.
    Repeated identical month labels in a row map to the same date (merged later, non-null wins)."""
    out = []
    last_col = df.shape[1] if last_col is None else last_col
    if datetime_row is not None:
        for c in range(first_col, last_col):
            v = df.iat[datetime_row, c]
            if isinstance(v, (dt.datetime, pd.Timestamp)):
                out.append((c, pd.Timestamp(v.year, v.month, 1)))
        return out
    year, prev_m = None, None
    for c in range(first_col, last_col):
        mv = df.iat[month_row, c]
        yv = df.iat[year_row, c] if year_row is not None else None
        ylab = None
        if isinstance(yv, (int, float, np.integer, np.floating)) and not pd.isna(yv) and 1950 < float(yv) < 2100:
            ylab = int(yv)
        if isinstance(mv, (dt.datetime, pd.Timestamp)):
            out.append((c, pd.Timestamp(mv.year, mv.month, 1)))
            year, prev_m = mv.year, mv.month
            continue
        if not isinstance(mv, str):
            continue
        mk = re.sub(r"[^a-z]", "", mv.lower())[:3]
        if mk not in MONTHS:
            continue
        m = MONTHS[mk]
        if ylab is not None:
            year = ylab
        elif year is not None and prev_m is not None and m < prev_m:
            year += 1
        if year is None:
            raise ValueError(f"no year for column {c}")
        out.append((c, pd.Timestamp(year, m, 1)))
        prev_m = m
    # sanity: dates must be non-decreasing and contiguous (allowing one repeated duplicate)
    ds = [d for _, d in out]
    for a, b in zip(ds, ds[1:]):
        gap = (b.year - a.year) * 12 + b.month - a.month
        if gap not in (0, 1) and not (allow_gaps and gap > 1):
            raise ValueError(f"non-contiguous header dates {a.date()} -> {b.date()}")
    return out


def row_values(df, r, cols):
    """dict date -> value for row r, merging duplicate-date columns (non-null wins)."""
    vals = {}
    for c, d in cols:
        v = to_num(df.iat[r, c])
        if d in vals and not np.isnan(vals[d]):
            if not np.isnan(v) and abs(v - vals[d]) > 1e-9:
                print(f"   WARNING duplicate date {d.date()} row {r} conflicting {vals[d]} vs {v}")
            continue
        vals[d] = v
    return vals


# ---------------------------------------------------------------------------------------------
# 1. SEKI I.4 credit by bank group x sector
# ---------------------------------------------------------------------------------------------
GROUPS = {
    "bankpersero": ("persero", "Bank Persero", "State-owned banks"),
    "bankpemerintahdaerah": ("bpd", "Bank Pemerintah Daerah", "Regional government banks"),
    "bankswastanasional": ("bsn", "Bank Swasta Nasional", "Private national banks"),
    "bankasingdanbankcampuran": ("foreign_joint", "Bank Asing dan Bank Campuran", "Foreign and joint-venture banks"),
    "kantorcabangdaribankyangberkedudukandiluarnegeri": ("foreign_branch", "Kantor Cabang dari Bank yang Berkedudukan di Luar Negeri", "Branch offices of foreign banks"),
    "bankperkreditanrakyat": ("bpr", "Bank Perkreditan Rakyat", "Rural banks (BPR)"),
    "jumlah": ("total", "Jumlah", "Total (commercial banks + BPR)"),
    "jumlah1sd5": ("total", "Jumlah (1 s.d. 5)", "Total (1 through 5: commercial banks + BPR)"),
    "memoitems": ("memo", "Memo Items", "Memo items"),
}

SECTORS_OLD = {
    "pinjamanberdasarkanlapanganusaha": ("PROD_TOTAL", "sector_aggregate", "Loans by industrial origin (sum of sectors)"),
    "pertanianpeternakankehutananperikanan": ("old_A_agri", "sector", "Agriculture, livestock, forestry & fishery"),
    "pertambangandanpenggalian": ("old_B_mining", "sector", "Mining and quarrying"),
    "industripengolahan": ("old_C_manuf", "sector", "Manufacturing"),
    "listrikgasdanairbersih": ("old_DE_utilities", "sector", "Electricity, gas and water supply"),
    "konstruksi": ("old_F_construction", "sector", "Construction"),
    "perdaganganhoteldanrestoran": ("old_GI_trade_hotel_rest", "sector", "Trade, hotels and restaurants"),
    "pengangkutandankomunikasi": ("old_HJ_transport_comm", "sector", "Transport and communication"),
    "keuanganrealestatdanjasaperusahaan": ("old_KLMN_fin_realestate_business", "sector", "Finance, real estate and business services"),
    "jasajasa": ("old_OPQRS_services", "sector", "Services"),
    "pinjamankepadabukanlapanganusaha": ("NONPROD_TOTAL", "sector_aggregate", "Loans to non-industrial origin (household consumption)"),
}
SECTORS_NEW = {
    "pinjamanberdasarkanlapanganusaha": ("PROD_TOTAL", "sector_aggregate", "Loans by industrial origin (sum of sectors)"),
    "pertaniankehutananperikanan": ("A_agri", "sector", "Agriculture, forestry & fishery"),
    "pertambangandanpenggalian": ("B_mining", "sector", "Mining and quarrying"),
    "industripengolahan": ("C_manuf", "sector", "Manufacturing"),
    "pengadaanlistrikdangas": ("D_elec_gas", "sector", "Electricity and gas supply"),
    "pengadaanairpengelolaansampahlimbahdandaurulang": ("E_water_waste", "sector", "Water supply, sewerage, waste management"),
    "konstruksi": ("F_construction", "sector", "Construction"),
    "perdaganganbesardaneceranreparasimobildanmotor": ("G_trade", "sector", "Wholesale and retail trade; repair of motor vehicles"),
    "transportasidanpergudangan": ("H_transport", "sector", "Transportation and storage"),
    "penyediaanakomodasidanmakanminum": ("I_accom_food", "sector", "Accommodation and food service"),
    "penyediaanakomodasidanminum": ("I_accom_food", "sector", "Accommodation and food service"),
    "informasidankomunikasi": ("J_info_comm", "sector", "Information and communication"),
    "jasakeuangandanasuransi": ("K_finance_insurance", "sector", "Financial and insurance activities"),
    "realestate": ("L_real_estate", "sector", "Real estate"),
    "jasaperusahaan": ("MN_business_services", "sector", "Business services"),
    "administrasipemerintahanpertahanandanjaminansosialwajib": ("O_public_admin", "sector", "Public administration, defence, compulsory social security"),
    "jasapendidikan": ("P_education", "sector", "Education"),
    "jasakesehatandankegiatanlainnya": ("Q_health_social", "sector", "Health and social work"),
    "jasalainnya": ("RSU_other_services", "sector", "Other service activities"),
    "pinjamankepadabukanlapanganusahakonsumsirumahtangga": ("NONPROD_TOTAL", "sector_aggregate", "Loans to non-industrial origin (household consumption)"),
}
HH = {
    "rumahtinggal": ("HH_housing", "Housing"),
    "flatdanapartemen": ("HH_flat_apartment", "Flat and apartment"),
    "rumahtokorukodanrumahkantorrukan": ("HH_shophouse_office", "Shophouse and office-house"),
    "kendaraanbermotor": ("HH_vehicles", "Motor vehicles"),
    "lainnya": ("HH_other", "Other household loans"),
}
MEMO = {
    "pemerintahpusat": ("MEMO_central_gov", "Central government"),
    "bukanpenduduk": ("MEMO_non_resident", "Non-residents"),
    "rupiah": ("rp", "Rupiah"),
    "valas": ("fx", "Foreign currency"),
}


def parse_i4_sheet(sheet, classification, label_col, en_col, hdr, row_range):
    df = read_sheet("BI_SEKI_TABEL1_4.xls", sheet)
    cols = date_columns(df, **hdr)
    secmap = SECTORS_OLD if classification == "old9" else SECTORS_NEW
    recs = []
    group = None
    memo_parent = None
    for r in range(*row_range):
        lab = norm(df.iat[r, label_col])
        if not lab:
            continue
        k = key(re.sub(r"^\d+\.\s*", "", lab))
        en = norm(df.iat[r, en_col]) if en_col < df.shape[1] else ""
        if k in GROUPS:
            group = GROUPS[k]
            sec = ("TOTAL", "group_total", "Total loans of the bank group")
            memo_parent = None
        elif group and group[0] == "memo":
            if k in ("rupiah", "valas"):
                sc = f"{memo_parent}_{MEMO[k][0]}"
                sec = (sc, "memo", MEMO[k][1])
            else:
                memo_parent = MEMO[k][0]
                sec = (memo_parent, "memo", MEMO[k][1])
        elif k in secmap:
            sec = secmap[k]
        elif k in HH:
            sec = (HH[k][0], "consumption_item", HH[k][1])
        else:
            raise ValueError(f"unmapped label in {sheet} row {r}: {lab!r}")
        vals = row_values(df, r, cols)
        for d, v in vals.items():
            if group[0] == "memo" and np.isnan(v):
                continue  # memo items only published from 2010
            recs.append(dict(date=d, classification=classification, source_sheet=sheet, sheet_row=r + 1,
                             bank_group_code=group[0], bank_group_id=group[1], bank_group_en=group[2],
                             sector_code=sec[0], sector_level=sec[1], sector_label_id=lab,
                             sector_label_en=en if en else sec[2], credit_rp_bn=v))
    return pd.DataFrame(recs), cols


def build_i4():
    print("\n=== SEKI I.4 credit by bank group and sector ===")
    parts = []
    d1, c1 = parse_i4_sheet("Th 2002-2017", "old9", 1, 190, dict(datetime_row=7), (8, 117))
    d2, c2 = parse_i4_sheet("Th 2016-2024", "kbli17", 2, 121, dict(year_row=3, month_row=4), (5, 155))
    d3 = [parse_i4_sheet(s, "kbli17", 2, 26, dict(year_row=3, month_row=4), (5, 55))[0] for s in ("I.4_1", "I.4_2", "I.4_3")]
    d3 = pd.concat(d3)
    for nm, d in (("Th 2002-2017", d1), ("Th 2016-2024", d2), ("I.4_1..3", d3)):
        print(f"  {nm}: {d.date.min().date()} .. {d.date.max().date()}  months={d.date.nunique()} rows={len(d)} nan={d.credit_rp_bn.isna().sum()}")
    # overlap Jan-Mar 2025 between 'Th 2016-2024' and I.4_1..3 : LBUT sheets preferred
    ov = d2[d2.date >= "2025-01-01"]
    d2p = d2[d2.date < "2025-01-01"]
    ov_cmp = ov.merge(d3, on=["date", "bank_group_code", "sector_code"], how="outer", suffixes=("_old", "_new"))
    df = pd.concat([d1, d2p, d3], ignore_index=True)
    df["flag"] = ""

    def add_flag(mask, txt):
        df.loc[mask, "flag"] = np.where(df.loc[mask, "flag"] == "", txt, df.loc[mask, "flag"] + ";" + txt)

    # (a) months where the BPR block is published as all zeros (2002-03, 2002-07): BPR not reported, total excludes BPR
    bz = df[(df.bank_group_code == "bpr") & (df.sector_code == "TOTAL") & (df.credit_rp_bn == 0)].date.unique()
    print(f"  BPR block published as 0 (not reported) in: {[pd.Timestamp(x).strftime('%Y-%m') for x in bz]}")
    add_flag(df.date.isin(bz) & (df.bank_group_code == "bpr"), "bpr_zero_not_reported")
    add_flag(df.date.isin(bz) & (df.bank_group_code == "total"), "total_excludes_bpr")
    # (b) single-month BPR level dips (no footnote): 2024-06, 2024-11, 2025-01
    dips = pd.to_datetime(["2024-06-01", "2024-11-01", "2025-01-01"])
    add_flag(df.date.isin(dips) & (df.bank_group_code == "bpr"), "bpr_dip_suspected_partial_reporting")
    add_flag(df.date.isin(dips) & (df.bank_group_code == "total"), "total_includes_bpr_dip")
    # (c) Jan-2025 LBUT: joint-venture banks move from foreign group into private national banks
    add_flag((df.date >= "2025-01-01") & (df.bank_group_code == "bsn"), "lbut_2025_includes_former_joint_banks")
    # (d) May-2026 unexplained reallocation between private national and state banks (~Rp 268 tn)
    add_flag((df.date >= "2026-05-01") & df.bank_group_code.isin(["bsn", "persero"]), "reclass_2026_05_bsn_to_persero_unexplained")
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    order = ["date", "classification", "bank_group_code", "bank_group_id", "bank_group_en", "sector_code",
             "sector_level", "sector_label_id", "sector_label_en", "credit_rp_bn", "flag", "source_sheet", "sheet_row"]
    df = df[order].sort_values(["classification", "bank_group_code", "sector_code", "date"])
    dup = df.duplicated(["date", "classification", "bank_group_code", "sector_code"]).sum()
    print(f"  duplicate keys (date, classification, group, sector): {dup}")
    df.to_csv(os.path.join(CLEAN, "bi_credit_by_sector_group.csv"), index=False, encoding="utf-8")
    print(f"  wrote bi_credit_by_sector_group.csv rows={len(df)}")
    validate_i4(df, ov_cmp, d2)
    return df


def validate_i4(df, ov_cmp, d2_full):
    x = df.copy()
    x["date"] = pd.to_datetime(x["date"])
    w = x[x.bank_group_code != "memo"]
    print("\n  --- I.4 validation ---")
    for cls, sub in w.groupby("classification"):
        piv = sub.pivot_table(index=["date", "bank_group_code"], columns="sector_code", values="credit_rp_bn", aggfunc="first")
        sect = [c for c in piv.columns if (sub[sub.sector_code == c].sector_level.iloc[0] == "sector")]
        hh = [c for c in piv.columns if c.startswith("HH_")]
        g1 = (piv[sect].sum(axis=1, min_count=1) - piv["PROD_TOTAL"])
        g2 = (piv[hh].sum(axis=1, min_count=1) - piv["NONPROD_TOTAL"])
        g3 = (piv["PROD_TOTAL"] + piv["NONPROD_TOTAL"] - piv["TOTAL"])
        print(f"  [{cls}] {len(sect)} sectors; group-month cells={len(piv)}")
        for nm, g in (("sum of sectors - PROD_TOTAL", g1), ("sum of HH items - NONPROD_TOTAL", g2), ("PROD+NONPROD - TOTAL", g3)):
            ga = g.abs()
            worst = ga.idxmax() if ga.notna().any() else None
            print(f"     {nm}: max abs gap {ga.max():.4f} Rp bn at {worst[0].date() if worst else None} {worst[1] if worst else ''}; cells>1bn: {(ga > 1).sum()}")
            if (ga > 1).sum():
                bad = ga[ga > 1]
                for (d, gcode), v in bad.head(12).items():
                    print(f"        {d.date()} {gcode}: gap {g.loc[(d, gcode)]:.3f}")
        # groups -> total
        tot = sub[sub.bank_group_code == "total"].pivot_table(index="date", columns="sector_code", values="credit_rp_bn", aggfunc="first")
        grp = sub[sub.bank_group_code != "total"].pivot_table(index="date", columns="sector_code", values="credit_rp_bn", aggfunc="sum")
        gap = (grp - tot)
        ga = gap.abs()
        print(f"     sum of 5 groups - published total, all {ga.shape[1]} sector rows x {ga.shape[0]} months: max abs gap {np.nanmax(ga.values):.4f} Rp bn; cells>1bn: {(ga > 1).sum().sum()}")
        gt = gap["TOTAL"]
        bad = gt[gt.abs() > 1]
        for d, v in bad.items():
            print(f"        TOTAL gap {d.date()}: {v:.3f} (published total {tot.loc[d, 'TOTAL']:.1f})")
        if (ga > 1).sum().sum():
            badc = ga.stack()
            badc = badc[badc > 1]
            print(f"        months with any sector gap>1bn: {sorted(set(i[0].strftime('%Y-%m') for i in badc.index))[:40]}")
    # old vs new classification overlap 2016-06..2017-06
    print("\n  --- old9 vs kbli17 overlap ---")
    a = w[(w.classification == "old9") & (w.date >= "2016-06-01")]
    b = w[(w.classification == "kbli17") & (w.date <= "2017-06-01")]
    for sc in ("TOTAL", "PROD_TOTAL", "NONPROD_TOTAL", "HH_housing", "HH_vehicles", "HH_other"):
        pa = a[a.sector_code == sc].pivot_table(index="date", columns="bank_group_code", values="credit_rp_bn")
        pb = b[b.sector_code == sc].pivot_table(index="date", columns="bank_group_code", values="credit_rp_bn")
        dd = (pb - pa)
        rel = (dd / pa * 100)
        print(f"   {sc}: new-old (Rp bn) by group, months={len(dd)}")
        for g in ["persero", "bpd", "bsn", "foreign_joint", "bpr", "total"]:
            if g in dd:
                print(f"      {g:14s} mean {dd[g].mean():12.1f}  min {dd[g].min():12.1f}  max {dd[g].max():12.1f}  mean% {rel[g].mean():7.3f}")
    # sector mapping comparison for total group, Jun 2016
    for d in ("2016-06-01", "2017-06-01"):
        ta = a[(a.bank_group_code == "total") & (a.date == d)].set_index("sector_code").credit_rp_bn
        tb = b[(b.bank_group_code == "total") & (b.date == d)].set_index("sector_code").credit_rp_bn
        print(f"   total, {d}: old9 sectors: " + ", ".join(f"{k}={v:,.0f}" for k, v in ta.items() if k.startswith("old_")))
        print(f"   total, {d}: kbli sectors: " + ", ".join(f"{k}={v:,.0f}" for k, v in tb.items() if k[:2] in [c + "_" for c in "ABCDEFGHIJKLOPQ"] or k.startswith(("MN_", "RSU_"))))
        # comparable aggregates
        comp = {
            "mining": (ta.get("old_B_mining"), tb.get("B_mining")),
            "manufacturing": (ta.get("old_C_manuf"), tb.get("C_manuf")),
            "construction": (ta.get("old_F_construction"), tb.get("F_construction")),
            "utilities D+E": (ta.get("old_DE_utilities"), tb.get("D_elec_gas") + tb.get("E_water_waste")),
            "trade+accom G+I": (ta.get("old_GI_trade_hotel_rest"), tb.get("G_trade") + tb.get("I_accom_food")),
            "transport+ICT H+J": (ta.get("old_HJ_transport_comm"), tb.get("H_transport") + tb.get("J_info_comm")),
            "fin+RE+business K+L+MN": (ta.get("old_KLMN_fin_realestate_business"), tb.get("K_finance_insurance") + tb.get("L_real_estate") + tb.get("MN_business_services")),
            "agriculture": (ta.get("old_A_agri"), tb.get("A_agri")),
            "services O+P+Q+RSU": (ta.get("old_OPQRS_services"), tb.get("O_public_admin") + tb.get("P_education") + tb.get("Q_health_social") + tb.get("RSU_other_services")),
        }
        for k, (o, n) in comp.items():
            print(f"      {d} {k:24s} old {o:12,.0f} new {n:12,.0f} diff {n - o:12,.0f} ({(n - o) / o * 100:7.2f}%)")
    # month-on-month jumps at documented breaks (total group and by group)
    print("\n  --- documented break months: m/m change of TOTAL by group (Rp bn and %) ---")
    for cls, months in (("old9", ["2009-12-01", "2010-01-01", "2014-04-01", "2014-05-01", "2014-06-01"]),
                        ("kbli17", ["2017-07-01", "2017-08-01", "2017-09-01", "2024-02-01", "2024-03-01", "2024-04-01",
                                    "2024-12-01", "2025-01-01", "2025-02-01", "2026-04-01", "2026-05-01", "2026-06-01"])):
        sub = w[(w.classification == cls) & (w.sector_code == "TOTAL")].pivot_table(index="date", columns="bank_group_code", values="credit_rp_bn")
        ch = sub.diff()
        pc = sub.pct_change(fill_method=None) * 100
        typ = pc.abs().median()
        print(f"   [{cls}] median |m/m %| by group: " + ", ".join(f"{g}={typ[g]:.2f}" for g in sub.columns))
        for m in months:
            m = pd.Timestamp(m)
            if m in ch.index:
                print(f"     {m.date()}: " + ", ".join(f"{g}={ch.loc[m, g]:,.0f} ({pc.loc[m, g]:.2f}%)" for g in sub.columns if not np.isnan(ch.loc[m, g])))
    # Jan 2025: foreign_joint -> foreign_branch
    print("\n  --- overlap Jan-Mar 2025: 'Th 2016-2024' (old vintage) vs I.4_1..3 (LBUT vintage) ---")
    for (gold, gnew) in (("persero", "persero"), ("bpd", "bpd"), ("bsn", "bsn"), ("foreign_joint", "foreign_branch"), ("bpr", "bpr"), ("total", "total")):
        o = d2_full[(d2_full.bank_group_code == gold) & (d2_full.sector_code == "TOTAL") & (d2_full.date >= "2025-01-01")].set_index("date").credit_rp_bn
        n = df[(df.bank_group_code == gnew) & (df.sector_code == "TOTAL") & (df.date.isin(["2025-01-01", "2025-02-01", "2025-03-01"]))].copy()
        n["date"] = pd.to_datetime(n["date"])
        n = n.set_index("date").credit_rp_bn
        print("     " + f"{gold}->{gnew}: " + "; ".join(f"{d.date()} old {o.get(d, np.nan):,.1f} new {n.get(d, np.nan):,.1f} diff {n.get(d, np.nan) - o.get(d, np.nan):,.1f}" for d in o.index))
    oc = ov_cmp.dropna(subset=["credit_rp_bn_old", "credit_rp_bn_new"])
    oc = oc[oc.bank_group_code != "memo"]
    dif = (oc.credit_rp_bn_new - oc.credit_rp_bn_old).abs()
    print(f"     all matching (group,sector) cells Jan-Mar 2025 (same group code): n={len(oc)} max abs diff {dif.max():.3f}; cells>1bn {(dif > 1).sum()}")
    for g, s in oc[dif > 1].groupby("bank_group_code"):
        print(f"        group {g}: {len(s)} cells >1bn, max {(s.credit_rp_bn_new - s.credit_rp_bn_old).abs().max():,.1f}")


# ---------------------------------------------------------------------------------------------
# 2. Rates by bank group (I.26 lending, I.28 deposits)
# ---------------------------------------------------------------------------------------------
RATE_GROUPS = {
    "bankpersero": ("persero", "Bank Persero", "State-owned banks"),
    "bankpemerintahdaerah": ("bpd", "Bank Pemerintah Daerah", "Regional government banks"),
    "bankswastanasional": ("bsn", "Bank Swasta Nasional", "Private national banks"),
    "bankasingdanbankcampuran": ("foreign_joint", "Bank Asing dan Bank Campuran", "Foreign and joint-venture banks"),
    "kantorcabangdaribankyangberkedudukandiluarnegeri": ("foreign_branch", "Kantor Cabang dari Bank yang Berkedudukan di Luar Negeri", "Branch offices of foreign banks"),
    "bankumum": ("commercial_banks", "Bank Umum", "All commercial banks"),
}
LOAN_TYPES = {
    "pinjamanmodalkerjayangdiberikan": ("working_capital", "Working capital loans"),
    "pinjamaninvestasiyangdiberikan": ("investment", "Investment loans"),
    "pinjamankonsumsiyangdiberikan": ("consumption", "Consumer loans"),
}
TENORS = {"1bulan": ("1m", "1 month"), "3bulan": ("3m", "3 months"), "6bulan": ("6m", "6 months"),
          "12bulan": ("12m", "12 months"), "24bulan": ("24m", "24 months")}


def parse_rate_table(fname, sheets, item_map, item_name, value_name):
    """sheets: list of (sheet, year_row, month_row, row_range) ordered oldest -> newest."""
    frames = []
    for sheet, yr, mr, rr, *opt in sheets:
        df = read_sheet(fname, sheet)
        cols = date_columns(df, year_row=yr, month_row=mr, last_col=(opt[0] if opt else None))
        group = None
        recs = []
        for r in range(*rr):
            lab = norm(df.iat[r, 2])
            if not lab:
                continue
            k = key(lab)
            if k in RATE_GROUPS:
                group = RATE_GROUPS[k]
                continue
            if k not in item_map:
                raise ValueError(f"unmapped {fname} {sheet} row {r} {lab!r}")
            it = item_map[k]
            for d, v in row_values(df, r, cols).items():
                recs.append(dict(date=d, bank_group_code=group[0], bank_group_id=group[1], bank_group_en=group[2],
                                 **{f"{item_name}_code": it[0], f"{item_name}_label_id": lab, f"{item_name}_label_en": it[1]},
                                 raw_value=v, source_sheet=sheet))
        f = pd.DataFrame(recs)
        print(f"  {fname} '{sheet}': {f.date.min().date()}..{f.date.max().date()} months={f.date.nunique()} rows={len(f)}")
        frames.append(f)
    # overlap comparison and newest-sheet-wins
    keycols = ["date", "bank_group_code", f"{item_name}_code"]
    allf = pd.concat([f.assign(_rank=i) for i, f in enumerate(frames)], ignore_index=True)
    allf["value"] = allf["raw_value"].where(allf["raw_value"] != 0)  # 0 = not reported in SEKI rate tables
    for i in range(len(frames)):
        for j in range(i + 1, len(frames)):
            a = allf[allf._rank == i]; b = allf[allf._rank == j]
            m = a.merge(b, on=keycols, suffixes=("_a", "_b"))
            m = m.dropna(subset=["value_a", "value_b"])
            if len(m):
                dd = (m.value_b - m.value_a).abs()
                print(f"   overlap '{frames[i].source_sheet.iloc[0]}' vs '{frames[j].source_sheet.iloc[0]}': {m.date.min().date()}..{m.date.max().date()} cells={len(m)} max abs diff {dd.max():.4f} pp; cells>0.005pp: {(dd > 0.005).sum()}")
                if (dd > 0.005).sum():
                    big = m[dd > 0.005]
                    print(f"      months with diffs: {sorted(set(big.date.dt.strftime('%Y-%m')))[:30]}")
                    for g, gg in big.groupby("bank_group_code"):
                        print(f"        {g}: {len(gg)} cells, max abs diff {(gg.value_b - gg.value_a).abs().max():.3f} pp")
    # newest sheet wins among NON-MISSING values (a zero/'-' in a newer sheet never overrides an older value)
    allf = allf.rename(columns={"value": value_name})
    nz, nn = int((allf["raw_value"] == 0).sum()), int(allf["raw_value"].isna().sum())
    allf = allf.dropna(subset=[value_name]).sort_values("_rank").drop_duplicates(keycols, keep="last")
    print(f"   dropped zero cells (=not reported)={nz}; dropped empty/'-' cells={nn} (counted over all sheets, before de-duplication); kept={len(allf)}")
    allf = allf.sort_values(["bank_group_code", f"{item_name}_code", "date"])
    allf["date"] = allf["date"].dt.strftime("%Y-%m-%d")
    out = allf[["date", "bank_group_code", "bank_group_id", "bank_group_en", f"{item_name}_code", f"{item_name}_label_id",
                f"{item_name}_label_en", value_name, "source_sheet"]]
    return out


def build_lending():
    print("\n=== SEKI I.26 lending rates ===")
    out = parse_rate_table("BI_SEKI_TABEL1_26.xls",
                           [("Th 1990-2008", 5, 6, (8, 28), 250), ("Th 2009-2018 ", 5, 6, (8, 28)),
                            ("Th 2010-2024", 3, 4, (5, 25)), ("1.26", 3, 4, (5, 25))],
                           LOAN_TYPES, "loan_type", "rate_pct_pa")
    out.to_csv(os.path.join(CLEAN, "bi_lending_rates.csv"), index=False, encoding="utf-8")
    v = out
    print(f"  wrote bi_lending_rates.csv rows={len(out)} range {v.date.min()}..{v.date.max()}")
    print(f"  rate range: {v.rate_pct_pa.min()}..{v.rate_pct_pa.max()}")
    for g, s in v.groupby(["bank_group_code", "loan_type_code"]):
        print(f"    {g}: first {s.date.min()} last {s.date.max()} n={len(s)} min {s.rate_pct_pa.min()} max {s.rate_pct_pa.max()}")
    return out


def build_deposit():
    print("\n=== SEKI I.28 time deposit rates ===")
    f = os.path.join(RAW, "BI_SEKI_TABEL1_28.xls")
    if not os.path.exists(f):
        print("  I.28 not available - skipped")
        return None
    out = parse_rate_table("BI_SEKI_TABEL1_28.xls",
                           [("Th 1990-2008", 5, 6, (8, 38)), ("Th 2009-2018", 5, 6, (8, 38)),
                            ("Th 2010-2024", 3, 4, (5, 35)), ("1.28", 3, 4, (5, 35))],
                           TENORS, "tenor", "rate_pct_pa")
    out.to_csv(os.path.join(CLEAN, "bi_deposit_rates.csv"), index=False, encoding="utf-8")
    v = out
    print(f"  wrote bi_deposit_rates.csv rows={len(out)} range {v.date.min()}..{v.date.max()}")
    print(f"  rate range: {v.rate_pct_pa.min()}..{v.rate_pct_pa.max()}")
    for g, s in v.groupby(["bank_group_code", "tenor_code"]):
        print(f"    {g}: first {s.date.min()} last {s.date.max()} n={len(s)} min {s.rate_pct_pa.min()} max {s.rate_pct_pa.max()}")
    return out


# ---------------------------------------------------------------------------------------------
# 3. I.25 policy / money-market rates
# ---------------------------------------------------------------------------------------------
TENOR_RE = [
    (r"^1haripagi$", "on_am", "overnight, morning session"), (r"^1harisore$", "on_pm", "overnight, afternoon session"),
    (r"^1hari$", "on", "overnight (1 day)"), (r"^(\d+)hari$", "{0}d", "{0} days"), (r"^(\d+)bulan$", "{0}m", "{0} months"),
    (r"^keseluruhan$", "all", "all maturities (weighted)"),
]
INSTR = {  # normalised instrument header -> (code, english)
    "birate": ("bi_rate", "BI Rate"), "policyrate": ("policy_rate", "Policy rate (BI Rate up to Jul-2016, BI 7-Day (Reverse) Repo Rate from Aug-2016, end of month)"),
    "sertifikatbankindonesia": ("sbi", "Bank Indonesia Certificates (SBI)"),
    "sertifikatbankindonesiasyariahsbis": ("sbis", "Bank Indonesia Sharia Certificates (SBIS)"),
    "sertifikatbankindonesiasyariah": ("sbis", "Bank Indonesia Sharia Certificates (SBIS)"),
    "sukukbankindonesia2": ("sukbi", "Bank Indonesia Sukuk (SukBI)"),
    "sertifikatdepositbankindonesia2": ("sdbi", "Bank Indonesia Deposit Certificates (SDBI)"),
    "sertifikatdepositbankindonesia3": ("sdbi", "Bank Indonesia Deposit Certificates (SDBI)"),
    "sekuritasrupiahbankindonesiasrbi4": ("srbi", "Bank Indonesia Rupiah Securities (SRBI)"),
    "bankindonesiafloatingratenotebifrn5": ("bi_frn", "Bank Indonesia Floating Rate Note (BI-FRN)"),
    "reversereposuratberharganegara3": ("rr_sbn", "Reverse repo of government securities (SBN)"),
    "reversereposuratberharganegara6": ("rr_sbn", "Reverse repo of government securities (SBN)"),
    "reversereposuratberhargasyariahnegara4": ("rr_sbsn", "Reverse repo of sharia government securities (SBSN)"),
    "reversereposuratberhargasyariahnegara7": ("rr_sbsn", "Reverse repo of sharia government securities (SBSN)"),
    "repo": ("repo", "Repo (BI lending against securities)"),
    "fasilitassimpananbankindonesia": ("fasbi", "BI deposit facility (FASBI)"),
    "depositfacilitydhfasilitassimpananbankindonesia": ("fasbi", "BI deposit facility (Deposit Facility, formerly FASBI)"),
    "lendingfacilitydanfinancingfacility": ("lending_facility", "Lending facility and (sharia) financing facility"),
    "fasilitassimpananbankindonesiasyariah": ("fasbis", "BI sharia deposit facility (FASBIS)"),
    "pasaruangantarbankpagi": ("puab_am", "Rupiah interbank money market (PUAB), morning"),
    "pasaruangantarbankrupiahsore": ("puab_pm", "Rupiah interbank money market (PUAB), afternoon"),
    "pasaruangantarbankvalas": ("puab_fx", "FX interbank money market (PUAB valas)"),
    "jibor": ("jibor", "JIBOR"),
    "sukubungapenjaminan2": ("guarantee", "Deposit guarantee (LPS) rate"),
    "pasaruangantarbanksyariah": ("puas", "Sharia interbank money market (PUAS) rate of return"),
    "depositoinvestasimudharabah": ("mudharabah_deposit", "Mudharabah investment deposit rate of return"),
}
REPO_SUB = {"sbi": "sbi", "sun": "sun", "sbis": "sbis", "sbsn": "sbsn"}
GUAR_SUB = {"puab3": ("puab", "interbank"), "deposito1bulan": ("dep_1m", "1-month deposits"),
            "deposito3bulan": ("dep_3m", "3-month deposits"), "simpananpihakketiga": ("third_party_funds", "third-party funds")}
OLD_II29 = {  # 'Th 1990-2003' single-label rows
    "sbi1bulan": ("sbi_1m", "SBI 1 month"), "sbi3bulan": ("sbi_3m", "SBI 3 months"), "sbi6bulan": ("sbi_6m", "SBI 6 months"),
    "fasbi1hari": ("fasbi_on", "FASBI overnight"), "fasbi7hari": ("fasbi_7d", "FASBI 7 days"),
    "puab1hari": ("puab_on", "PUAB overnight"), "puabkeseluruhan": ("puab_all", "PUAB all maturities"),
    "jibor1hari": ("jibor_on", "JIBOR overnight"), "jibor1bulan": ("jibor_1m", "JIBOR 1 month"), "jibor3bulan": ("jibor_3m", "JIBOR 3 months"),
    "maksimumprogrampenjaminanpuabinterbank": ("guarantee_max_puab", "Max. guarantee-programme rate, interbank"),
    "maksimumprogrampenjaminandeposito1bulan": ("guarantee_max_dep_1m", "Max. guarantee-programme rate, 1-month deposits"),
    "maksimumprogrampenjaminandeposito3bulan": ("guarantee_max_dep_3m", "Max. guarantee-programme rate, 3-month deposits"),
    "swbi": ("swbi", "Bank Indonesia Wadiah Certificates (SWBI) bonus"), "puas": ("puas", "Sharia interbank money market (PUAS)"),
}


def tenor_code(k):
    for pat, c, e in TENOR_RE:
        m = re.match(pat, k)
        if m:
            return c.format(*m.groups()), e.format(*m.groups()).replace("1 months", "1 month").replace("1 days", "1 day")
    return None


def parse_mm_sheet(sheet, hdr, rr, inst_col, ten_col, en_col):
    df = read_sheet("BI_SEKI_TABEL1_25_1.xls", sheet)
    cols = date_columns(df, **hdr)
    recs = []
    inst, inst_lab = None, ""
    for r in range(*rr):
        a = norm(df.iat[r, inst_col]); b = norm(df.iat[r, ten_col]) if ten_col != inst_col else ""
        if not a and not b:
            continue
        en = norm(df.iat[r, en_col]) if en_col is not None and en_col < df.shape[1] else ""
        if sheet == "Th 1990-2003":
            code, ename = OLD_II29[key(a)]
            lab_id = a
        else:
            lab = a or b
            # in 'Th 2002-2009' instruments sit in col 1 and tenors/sub-items in col 2; later sheets use col 2 for both
            k = key(lab)
            tc = None if (a and sheet == "Th 2002-2009") else tenor_code(k)
            if sheet == "Th 2002-2009" and not a and inst and inst[0] == "repo" and k in REPO_SUB:
                code, ename = f"repo_{REPO_SUB[k]}", f"Repo rate, {lab} collateral"
                lab_id = f"{inst_lab} > {lab}"
            elif inst and inst[0] == "guarantee" and k in GUAR_SUB:
                code, ename = f"guarantee_{GUAR_SUB[k][0]}", f"Deposit guarantee rate, {GUAR_SUB[k][1]}"
                lab_id = f"{inst_lab} > {lab}"
            elif tc and inst is not None:
                code, ename = f"{inst[0]}_{tc[0]}", f"{inst[1]}, {tc[1]}"
                lab_id = f"{inst_lab} > {lab}"
            elif k in INSTR:
                inst, inst_lab = INSTR[k], lab
                code, ename = inst
                lab_id = lab
            else:
                raise ValueError(f"unmapped I.25 {sheet} row {r} {lab!r} key={k}")
        vals = row_values(df, r, cols)
        if all(np.isnan(v) for v in vals.values()):
            continue  # pure header row
        for d, v in vals.items():
            recs.append(dict(date=d, series_code=code, label_id=lab_id, label_en=ename,
                             label_en_source=en, raw_value=v, source_sheet=sheet, sheet_row=r + 1))
    f = pd.DataFrame(recs)
    print(f"  '{sheet}': {f.date.min().date()}..{f.date.max().date()} months={f.date.nunique()} series={f.series_code.nunique()} rows={len(f)}")
    return f


def build_mm():
    print("\n=== SEKI I.25 (TABEL1_25_1) policy and money-market rates ===")
    frames = [
        parse_mm_sheet("Th 1990-2003", dict(year_row=5, month_row=6), (8, 23), 1, 1, None),
        parse_mm_sheet("Th 2002-2009", dict(datetime_row=6), (8, 44), 1, 2, 136),
        parse_mm_sheet("Th 2010-2016", dict(year_row=4, month_row=5), (6, 43), 2, 2, 97),
        parse_mm_sheet("1.25A_1", dict(year_row=4, month_row=5), (6, 58), 2, 2, 132),
        parse_mm_sheet("1.25A_2", dict(year_row=4, month_row=5), (6, 23), 2, 2, 132),
    ]
    allf = pd.concat([f.assign(_rank=i) for i, f in enumerate(frames)], ignore_index=True)
    allf["rate_pct_pa"] = allf.raw_value.where(allf.raw_value != 0)
    # overlaps
    for i, j in ((0, 1), (2, 3), (1, 2)):
        a = allf[allf._rank == i]; b = allf[allf._rank == j]
        m = a.merge(b, on=["date", "series_code"], suffixes=("_a", "_b")).dropna(subset=["rate_pct_pa_a", "rate_pct_pa_b"])
        if len(m):
            dd = (m.rate_pct_pa_b - m.rate_pct_pa_a).abs()
            print(f"   overlap sheet{i} vs sheet{j}: {m.date.min().date()}..{m.date.max().date()} cells={len(m)} series={m.series_code.nunique()} max abs diff {dd.max():.4f}; >0.005: {(dd > 0.005).sum()}")
            if (dd > 0.005).sum():
                print("      " + "; ".join(f"{r.series_code} {r.date.date()} {r.rate_pct_pa_a}->{r.rate_pct_pa_b}" for r in m[dd > 0.005].head(10).itertuples()))
    # newest sheet wins among NON-MISSING values (a zero/'-' in a newer sheet never overrides an older value)
    nz, nn = int((allf.raw_value == 0).sum()), int(allf.raw_value.isna().sum())
    allf = allf.dropna(subset=["rate_pct_pa"]).sort_values("_rank").drop_duplicates(["date", "series_code"], keep="last")
    print(f"   dropped zero cells (=no operation/not issued)={nz}; dropped empty/'-' cells={nn} (counted over all sheets, before de-duplication); kept={len(allf)}")
    allf = allf.sort_values(["series_code", "date"])
    # one English label per series (from the newest sheet); label_id keeps the original Indonesian row label
    allf["label_en"] = allf.groupby("series_code")["label_en"].transform("last")
    allf["date"] = allf.date.dt.strftime("%Y-%m-%d")
    out = allf[["date", "series_code", "label_id", "label_en", "rate_pct_pa", "source_sheet", "sheet_row"]]
    out.to_csv(os.path.join(CLEAN, "bi_money_market_rates.csv"), index=False, encoding="utf-8")
    v = out
    print(f"  wrote bi_money_market_rates.csv rows={len(out)}")
    cov = v.groupby("series_code").agg(first=("date", "min"), last=("date", "max"), n=("date", "size"), lab=("label_en", "first"))
    print(cov.to_string())
    return out


# ---------------------------------------------------------------------------------------------
# 4. IV.4 SBN outstanding (SUN vs SBSN)
# ---------------------------------------------------------------------------------------------
SBN_ROWS = {  # sheet row index -> (series_code, instrument, breakdown)
    6: ("sun_total", "SUN", "total"), 7: ("sun_bonds_total", "SUN", "total"),
    8: ("sun_bonds_bytype_total", "SUN", "by_type"), 9: ("sun_bonds_fixed", "SUN", "by_type"),
    10: ("sun_bonds_variable", "SUN", "by_type"), 11: ("sun_bonds_hedge", "SUN", "by_type"),
    12: ("sun_bonds_ori_retail", "SUN", "by_type"), 13: ("sun_bonds_zero_coupon", "SUN", "by_type"),
    14: ("sun_bonds_byholder_total", "SUN", "by_holder"), 15: ("sun_bonds_h_gov_banks", "SUN", "by_holder"),
    16: ("sun_bonds_h_private_national_banks", "SUN", "by_holder"), 17: ("sun_bonds_h_joint_banks", "SUN", "by_holder"),
    18: ("sun_bonds_h_foreign_banks", "SUN", "by_holder"), 19: ("sun_bonds_h_regional_dev_banks", "SUN", "by_holder"),
    20: ("sun_bonds_h_bank_indonesia", "SUN", "by_holder"), 21: ("sun_bonds_h_customers", "SUN", "by_holder"),
    22: ("sun_bonds_h_other_institutions", "SUN", "by_holder"),
    23: ("spn_total", "SUN", "total"), 24: ("spn_byholder_total", "SUN", "by_holder"),
    25: ("spn_h_gov_banks", "SUN", "by_holder"), 26: ("spn_h_private_national_banks", "SUN", "by_holder"),
    27: ("spn_h_joint_banks", "SUN", "by_holder"), 28: ("spn_h_foreign_banks", "SUN", "by_holder"),
    29: ("spn_h_regional_dev_banks", "SUN", "by_holder"), 30: ("spn_h_bank_indonesia", "SUN", "by_holder"),
    31: ("spn_h_customers", "SUN", "by_holder"),
    32: ("sbsn_total", "SBSN", "total"), 33: ("sbsn_bytype_total", "SBSN", "by_type"),
    34: ("sbsn_ifr_sdhi", "SBSN", "by_type"), 35: ("sbsn_fixed_rate", "SBSN", "by_type"),
    36: ("sbsn_retail_sukuk", "SBSN", "by_type"), 37: ("sbsn_spn_syariah", "SBSN", "by_type"),
    38: ("sbsn_savings_sukuk", "SBSN", "by_type"),
}


def build_sbn():
    print("\n=== SEKI IV.4 SBN outstanding ===")
    df = read_sheet("BI_SEKI_TABEL4_4.xls", "4.4")
    cols = date_columns(df, year_row=4, month_row=5, allow_gaps=True)  # Dec-2008, Dec-2009, then monthly from Jan-2010
    recs = []
    for r, (code, ins, brk) in SBN_ROWS.items():
        lab = norm(df.iat[r, 2]); en = norm(df.iat[r, 227])
        for d, v in row_values(df, r, cols).items():
            recs.append(dict(date=d, instrument=ins, series_code=code, breakdown=brk, label_id=lab, label_en=en,
                             outstanding_rp_bn=v, source_sheet="4.4", sheet_row=r + 1))
    f = pd.DataFrame(recs)
    piv = f.pivot_table(index="date", columns="series_code", values="outstanding_rp_bn")
    z = piv.fillna(0)
    chk = {
        "SUN - (bonds + SPN)": z.sun_total - z.sun_bonds_total - z.spn_total,
        "bonds - sum(type)": z.sun_bonds_total - z[["sun_bonds_fixed", "sun_bonds_variable", "sun_bonds_hedge", "sun_bonds_ori_retail", "sun_bonds_zero_coupon"]].sum(axis=1),
        "bonds - sum(holders)": z.sun_bonds_total - z[[c for c in piv.columns if c.startswith("sun_bonds_h_")]].sum(axis=1),
        "SPN - sum(holders)": z.spn_total - z[[c for c in piv.columns if c.startswith("spn_h_")]].sum(axis=1),
        "SBSN - sum(type)": z.sbsn_total - z[["sbsn_ifr_sdhi", "sbsn_fixed_rate", "sbsn_retail_sukuk", "sbsn_spn_syariah", "sbsn_savings_sukuk"]].sum(axis=1),
    }
    print(f"  dates {piv.index.min().date()}..{piv.index.max().date()} n={len(piv)}")
    for k, g in chk.items():
        print(f"   {k}: max abs gap {g.abs().max():.3f} Rp bn at {g.abs().idxmax().date()}; months>1bn {(g.abs() > 1).sum()}")
        if (g.abs() > 1).sum():
            print("      " + ", ".join(f"{d.date()}:{v:,.1f}" for d, v in g[g.abs() > 1].head(15).items()))
    ifr = piv.sbsn_ifr_sdhi.dropna(); fx = piv.sbsn_fixed_rate.dropna()
    print(f"   sbsn_ifr_sdhi non-missing {ifr.index.min().date()}..{ifr.index.max().date()}; sbsn_fixed_rate non-missing {fx.index.min().date()}..{fx.index.max().date()}")
    sh = (piv.sbsn_total / (piv.sbsn_total + piv.sun_total) * 100)
    print("   SBSN share of SBN (%): " + ", ".join(f"{d.year}-{d.month:02d}:{sh.loc[d]:.1f}" for d in sh.index if d.month == 12 or d == sh.index[-1]))
    print(f"   dropped cells shown as '-' (nil) in source: {int(f.outstanding_rp_bn.isna().sum())}")
    f = f.dropna(subset=["outstanding_rp_bn"])
    f = f.sort_values(["series_code", "date"])
    f["date"] = f.date.dt.strftime("%Y-%m-%d")
    f.to_csv(os.path.join(CLEAN, "bi_sbn_outstanding.csv"), index=False, encoding="utf-8")
    print(f"  wrote bi_sbn_outstanding.csv rows={len(f)} nan={f.outstanding_rp_bn.isna().sum()}")
    return f


if __name__ == "__main__":
    build_i4()
    build_lending()
    build_deposit()
    build_mm()
    build_sbn()
    print("\nDONE")
