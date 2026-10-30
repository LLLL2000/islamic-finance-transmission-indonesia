import sys; sys.path.append(r"C:/Users/consu/AppData/Local/Packages/PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0/LocalCache/local-packages/Python311/site-packages")
"""
Builder: bi_deposits (module M, mechanisms)
Parses Bank Indonesia SEKI table I.17 "Posisi simpanan masyarakat pada bank umum dan BPR menurut kelompok
bank dan jenis simpanan" (private deposits of commercial and rural banks by bank group and deposit type,
Rp bn, end of month) from the raw .xls (untrusted data, read only, nothing executed) into a tidy long CSV:
  data/clean/bi_deposits_by_group.csv
and writes validation statistics to output/tables/mech_bi_deposits_validation.csv.

Also reads, read-only and values-only, data/raw/ojk/SPI_2025_02.xlsx (placed there by the bi_credit builder)
for one level cross-check of commercial-bank third-party funds (DPK), which includes the stand-alone Islamic banks.

Run:  python -I code/py/build_bi_deposits.py [project_root]
"""
import os, re, datetime as dt
import numpy as np
import pandas as pd

ROOT = sys.argv[1] if len(sys.argv) > 1 else r"C:/Users/consu/Documents/Universidad/Islamic_Finance_Project/wp_dual_banking"
RAWF = os.path.join(ROOT, "data", "raw", "bi_seki_deposits", "BI_SEKI_TABEL1_17.xls")
SPI = os.path.join(ROOT, "data", "raw", "ojk", "SPI_2025_02.xlsx")
CLEAN = os.path.join(ROOT, "data", "clean")
TAB = os.path.join(ROOT, "output", "tables")
os.makedirs(TAB, exist_ok=True)

MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "mei": 5, "jun": 6, "jul": 7,
          "aug": 8, "agu": 8, "agt": 8, "sep": 9, "oct": 10, "okt": 10, "nov": 11, "dec": 12, "des": 12}
VAL = []   # validation rows: (check, value, note)


def val(check, value, note=""):
    VAL.append((check, value, note))
    print(f"  {check}: {value} {note}")


def norm(s):
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return ""
    s = str(s).replace("\n", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


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
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return np.nan


def date_columns(df, year_row=None, month_row=None, datetime_row=None, first_col=3):
    """(col, date) for monthly columns. Same rules as build_bi_credit.py: a month label is required; the year is
    the numeric year label at that column if present (SEKI puts it at the first column of a year, or at the last
    column of a partial/final year), else carried forward and incremented when the month index falls. Columns
    without a month label (year-end duplicates, spacers) are skipped. Dates must be contiguous."""
    out = []
    if datetime_row is not None:
        for c in range(first_col, df.shape[1]):
            v = df.iat[datetime_row, c]
            if isinstance(v, (dt.datetime, pd.Timestamp)):
                out.append((c, pd.Timestamp(v.year, v.month, 1)))
    else:
        year, prev_m = None, None
        for c in range(first_col, df.shape[1]):
            mv, yv = df.iat[month_row, c], df.iat[year_row, c]
            ylab = None
            try:
                fy = float(str(yv).strip())
                if 1950 < fy < 2100:
                    ylab = int(fy)
            except ValueError:
                pass
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
    ds = [d for _, d in out]
    for a, b in zip(ds, ds[1:]):
        if (b.year - a.year) * 12 + b.month - a.month != 1:
            raise ValueError(f"non-contiguous header dates {a.date()} -> {b.date()}")
    return out


BLOCKS = {"rupiah": "IDR", "valutaasing": "FX", "rupiahvalutaasing": "all", "rupiahdanvalutaasing": "all",
          "jumlah": "all_total", "memoitems": "memo"}
GROUPS = {"bankpersero": "persero", "bankpemerintahdaerah": "bpd", "bankswastanasional": "bsn",
          "bankasingdanbankcampuran": "foreign_joint",
          "kantorcabangdaribankyangberkedudukandiluarnegeri": "foreign_branch",
          "bankperkreditanrakyat": "bpr", "pemerintahpusat": "memo_central_gov", "bukanpenduduk": "memo_non_resident"}
TYPES = {"giro": "demand", "tabungan": "savings", "deposito": "time", "simpananberjangka": "time"}


def parse_sheet(sheet, label_col, cols, start_currency=None):
    """Walk the rows: block headers set the currency, group rows set the group, type rows give the component."""
    df = pd.read_excel(RAWF, sheet_name=sheet, header=None)
    rows = []
    currency, group = start_currency, None
    for r in range(df.shape[0]):
        # label in column 1 or 2 depending on sheet and row level (group rows vs type rows): first non-empty
        k = next((key(df.iat[r, c]) for c in (1, 2) if key(df.iat[r, c])), "")
        if not k:
            continue
        if k in BLOCKS:
            b = BLOCKS[k]
            if b == "all_total":
                currency, group, typ = "all", "total", "total"
            elif b == "memo":
                currency, group = "na", None
                continue
            else:
                currency, group, typ = b, "total", "total"
        elif k in GROUPS:
            group, typ = GROUPS[k], "total"
        elif k in TYPES:
            typ = TYPES[k]
        else:
            continue
        if currency is None or group is None:
            raise ValueError(f"{sheet} row {r}: label '{k}' outside a block")
        for c, d in cols(df):
            rows.append((d, currency, group, typ, to_num(df.iat[r, c]), sheet, r + 1, c + 1))
    out = pd.DataFrame(rows, columns=["date", "currency", "bank_group_code", "deposit_type", "deposits_rp_bn",
                                      "source_sheet", "sheet_row", "sheet_col"])
    # the 'Rupiah Valuta Asing' block header and the 'Jumlah' row are both the Rp+FX total of all groups:
    # keep the first, and check that they agree
    kk = ["date", "currency", "bank_group_code", "deposit_type"]
    dup = out[out.duplicated(kk, keep=False)]
    if len(dup):
        if not ((dup.currency == "all") & (dup.bank_group_code == "total") & (dup.deposit_type == "total")).all():
            raise ValueError(f"{sheet}: unexpected duplicate keys")
        rng = dup.groupby("date").deposits_rp_bn.agg(lambda v: v.max() - v.min())
        val(f"rpfx_header_vs_jumlah_maxabs[{sheet}]", round(float(rng.max()), 4), "Rp bn")
        out = out.drop_duplicates(kk, keep="first")
    return out


print("== SEKI I.17 private deposits by bank group and type")
s0209 = parse_sheet("Th 2002-2009", 1, lambda df: date_columns(df, year_row=5, month_row=6))
s1012 = parse_sheet("Th 2010-2012", 1, lambda df: date_columns(df, year_row=5, month_row=6))
s1024 = parse_sheet("Th 2010-2024", 2, lambda df: date_columns(df, year_row=3, month_row=4))
s25a = parse_sheet("1.17_1", 2, lambda df: date_columns(df, year_row=3, month_row=4))
s25b = parse_sheet("1.17_2", 2, lambda df: date_columns(df, year_row=3, month_row=4), start_currency="all")
for nm, x in [("Th 2002-2009", s0209), ("Th 2010-2012", s1012), ("Th 2010-2024", s1024), ("1.17_1", s25a), ("1.17_2", s25b)]:
    val(f"sheet_span[{nm}]", f"{x.date.min().date()}..{x.date.max().date()}", f"{len(x)} cells")

K = ["date", "currency", "bank_group_code", "deposit_type"]


def overlap(a, b, lab):
    m = a.merge(b, on=K, suffixes=("_a", "_b"))
    m = m[m.deposits_rp_bn_a.notna() & m.deposits_rp_bn_b.notna()]
    d = (m.deposits_rp_bn_a - m.deposits_rp_bn_b).abs()
    val(f"overlap_maxabs[{lab}]", round(float(d.max()), 4) if len(d) else "none",
        f"{len(m)} cells, {int((d > 0.01).sum())} differ by >0.01 Rp bn")
    big = m[d > 0.01]
    if len(big):
        val(f"overlap_diff_months[{lab}]", ";".join(sorted(set(big.date.dt.strftime("%Y-%m")))),
            "groups: " + ";".join(sorted(set(big.bank_group_code))))
        rel = (d / m.deposits_rp_bn_b.abs())[d > 0.01]
        val(f"overlap_maxrel[{lab}]", round(float(rel.max()), 5), "relative to newer sheet")
    return m


overlap(s1012, s1024, "Th 2010-2012 vs Th 2010-2024")
m25 = overlap(s1024, pd.concat([s25a, s25b]), "Th 2010-2024 vs 1.17_x (LBUT vintage), 2025-01..03")
tot = m25[(m25.bank_group_code == "total") & (m25.deposit_type == "total") & (m25.currency == "all")]
for _, r in tot.iterrows():
    val(f"lbut_total_gap[{r.date.date()}]", round(r.deposits_rp_bn_b - r.deposits_rp_bn_a, 1), "Rp bn, LBUT minus old vintage")

# newest sheet wins: 2002-2009 sheet for <=2009-12, 'Th 2010-2024' for 2010-01..2024-12, 1.17_x from 2025-01
d = pd.concat([s0209[s0209.date <= "2009-12-01"],
               s1024[(s1024.date >= "2010-01-01") & (s1024.date <= "2024-12-01")],
               s25a, s25b], ignore_index=True)
assert not d.duplicated(K).any()

# derived commercial-bank aggregate = persero + bpd + bsn + foreign (joint to 2024-12, branch from 2025-01)
com = d[d.bank_group_code.isin(["persero", "bpd", "bsn", "foreign_joint", "foreign_branch"])]
cnt = com.groupby(["date", "currency", "deposit_type"]).deposits_rp_bn.agg(["sum", "count", lambda v: v.isna().sum()])
cnt.columns = ["sum", "n", "nmiss"]
cnt = cnt.reset_index()
bad = cnt[(cnt.n != 4) | (cnt.nmiss > 0)]
val("commercial_groups_incomplete_cells", len(bad), "(date x currency x type cells without exactly 4 non-missing groups)")
cnt = cnt[(cnt.n == 4) & (cnt.nmiss == 0)]
cb = cnt.assign(bank_group_code="commercial_banks", deposits_rp_bn=cnt["sum"], source_sheet="derived",
                sheet_row=np.nan, sheet_col=np.nan)[K + ["deposits_rp_bn", "source_sheet", "sheet_row", "sheet_col"]]
d = pd.concat([d, cb], ignore_index=True)
d["flag"] = ""
d.loc[(d.date >= "2025-01-01") & d.bank_group_code.isin(["bsn", "foreign_branch"]), "flag"] = "lbut_2025_group_reclass"
d.loc[(d.date >= "2025-01-01") & (d.bank_group_code == "commercial_banks"), "flag"] = "lbut_2025_vintage"
d = d.sort_values(K).reset_index(drop=True)

# ---- validation: identities ---------------------------------------------------------------------------
w = d.pivot_table(index=["date", "currency", "bank_group_code"], columns="deposit_type", values="deposits_rp_bn",
                  aggfunc="first").reset_index()
w = w[w.currency.isin(["IDR", "FX", "all"])]
w = w[w[["demand", "savings", "time"]].notna().any(axis=1)]   # block-header rows carry no type split
gap = (w.demand.fillna(0) + w.savings.fillna(0) + w.time.fillna(0) - w.total).abs()
val("types_vs_group_total_maxabs", round(float(gap.max()), 4), f"Rp bn over {int(gap.notna().sum())} group-months (missing giro = 0 for BPR)")
g = d[(d.deposit_type == "total") & d.currency.isin(["IDR", "FX", "all"])]
gp = g.pivot_table(index=["date", "currency"], columns="bank_group_code", values="deposits_rp_bn", aggfunc="first")
grp = ["persero", "bpd", "bsn", "foreign_joint", "foreign_branch", "bpr"]
s = gp[[c for c in grp if c in gp]].sum(axis=1, min_count=1)
gap2 = (s - gp["total"]).abs()
val("groups_vs_block_total_maxabs", round(float(gap2.max()), 4), f"Rp bn over {int(gap2.notna().sum())} currency-months")
cp = d[(d.bank_group_code == "commercial_banks")].pivot_table(index=["date", "deposit_type"], columns="currency",
                                                                values="deposits_rp_bn", aggfunc="first")
gap3 = (cp["IDR"] + cp["FX"] - cp["all"]).abs()
val("commercial_idr_plus_fx_vs_all_maxabs", round(float(gap3.max()), 4), f"Rp bn over {int(gap3.notna().sum())} cells")

# ---- SPI level cross-check: commercial-bank DPK (incl. BUS) at Dec-2023 and Dec-2024 ---------------------
try:
    sp = pd.read_excel(SPI, sheet_name="Keg.usaha KBMI 1.1.-1.5.", header=None)
    r = [i for i in range(sp.shape[0]) if key(sp.iat[i, 1]).startswith("danapihakketiga")][0]
    spi = {"2023-12-01": to_num(sp.iat[r, 3]), "2024-12-01": to_num(sp.iat[r, 14])}
    assert str(sp.iat[1, 3]).startswith("2023") and norm(sp.iat[2, 14]).lower().startswith("des")
    for dd, v in spi.items():
        c = d[(d.date == dd) & (d.bank_group_code == "commercial_banks") & (d.currency == "all") & (d.deposit_type == "total")].deposits_rp_bn.iloc[0]
        mg = d[(d.date == dd) & d.bank_group_code.isin(["memo_central_gov", "memo_non_resident"]) & (d.deposit_type == "total")].deposits_rp_bn.sum()
        val(f"spi_dpk_commercial[{dd[:7]}]", round(v, 1), "Rp bn, OJK SPI Tabel 1.1 'Dana Pihak Ketiga', all commercial banks incl. BUS (row %d)" % (r + 1))
        val(f"seki_private_commercial[{dd[:7]}]", round(c, 1), "Rp bn, SEKI I.17 sum of the 4 commercial groups, Rp+FX")
        val(f"seki_memo_cg_plus_nonres[{dd[:7]}]", round(mg, 1), "Rp bn, SEKI I.17 memo items (not by group; not in group totals)")
except Exception as e:  # validation only
    val("spi_check", "skipped", repr(e))

out = os.path.join(CLEAN, "bi_deposits_by_group.csv")
d["date"] = d.date.dt.strftime("%Y-%m-%d")
d.to_csv(out, index=False, float_format="%.6f")
val("rows_written", len(d), out)
pd.DataFrame(VAL, columns=["check", "value", "note"]).to_csv(os.path.join(TAB, "mech_bi_deposits_validation.csv"), index=False)
print("done")
