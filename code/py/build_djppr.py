import sys; sys.path.append(r"C:/Users/consu/AppData/Local/Packages/PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0/LocalCache/local-packages/Python311/site-packages")
"""
Build the DJPPR sovereign investor-base data (supplementary module).

Inputs  : data/raw/djppr/*.xlsx|xls  (Internet Archive copies of DJPPR open downloads)
Outputs : data/clean/djppr_holdings_daily.csv
          data/clean/djppr_nonresident_maturity_monthly.csv
Validation results are printed to stdout (copied into notes/data_djppr.md).

Run:  python -I code/py/build_djppr.py            (build from raw files on disk)
      python -I code/py/build_djppr.py --fetch    (first GET any missing raw file from web.archive.org)
"""
import base64
import collections
import datetime as dt
import hashlib
import os
import re
import urllib.request

import openpyxl
import pandas as pd
import xlrd

ROOT = r"C:/Users/consu/Documents/Universidad/Islamic_Finance_Project/wp_dual_banking"
RAW = os.path.join(ROOT, "data", "raw", "djppr")
CLEAN = os.path.join(ROOT, "data", "clean")
OUT_DAILY = os.path.join(CLEAN, "djppr_holdings_daily.csv")
OUT_NR = os.path.join(CLEAN, "djppr_nonresident_maturity_monthly.csv")

ORIG = "https://djppr.kemenkeu.go.id/uploads/files/dmodata/in/5Statistik/"
OWN = ORIG + "6Kepemilikan_SBN_yang_dapat_Diperdagangkan/"
# local file -> (wayback timestamp, original URL, CDX sha1 digest (base32) of the payload)
MANIFEST = {
    "DJPPR_SBN_Ownership_2003_2006.xlsx": ("20220701010715", OWN + "Kepemilikan%20SBN%20Domestik%20yang%20Dapat%20Diperdagangkan_2003-2006.xlsx", "Y5JRXFPI5R4KYUDYEX7FLKXX4UC2RZCL"),
    "DJPPR_SBN_Ownership_2007_2015.xlsx": ("20220701010702", OWN + "Kepemilikan%20SBN%20Domestik%20yang%20Dapat%20Diperdagangkan_2007-2015_Updates.xlsx", "2JYZHHIUXPZRQDM4WH6HANEVTTEU7M3K"),
    "DJPPR_SBN_Ownership_Daily_2016.xlsx": ("20220701010650", OWN + "122016/Kepemilikan%20SBN%20Harian%20-SBNOwnership%20Daily(18).xlsx", "56V3SD3FBP5SNGJ6S2ZJPIOOZOFIQ6EX"),
    "DJPPR_SBN_Ownership_Daily_2017.xlsx": ("20220701010639", OWN + "122017/SBN%20Ownership%20Daily%202017.xlsx", "7PAQRYW7NTS2YOF73T5TT2AUSYDGPDND"),
    "DJPPR_SBN_Ownership_Daily_2018.xlsx": ("20220701010559", OWN + "122018/SBN%20Ownership%20Daily%202018_Desember(1).xlsx", "SR2Q5GYIJYTDSCUJMR7FUGA6O2MWCEQ5"),
    "DJPPR_SBN_Ownership_Daily_2019.xlsx": ("20220701010625", OWN + "2019/SBN%20Ownership%20Daily%202019_desember%20(1).xlsx", "GM4HW7SJQ7BXMWCZIV4447JZJTL3WBAZ"),
    "DJPPR_SBN_Ownership_Daily_2020.xlsx": ("20220701010611", OWN + "2020/SBN%20Ownership%20Daily%202020_Desember_(1).xlsx", "KP55MDQADUNXS4TO6VBRNHTSN2XWOB3W"),
    "DJPPR_SBN_Ownership_Daily_2021.xlsx": ("20220701010547", OWN + "2021/SBN%20Ownership%20Daily%202021_31%20Desember.xlsx", "D4LUHUCH67UYSSTUNPOZAFELLJXWBPRS"),
    "DJPPR_SBN_Ownership_Daily_2022H1.xlsx": ("20220701010536", OWN + "2022/SBN%20Ownership%20Daily%202022_Jun(15).xlsx", "MXHR4K4CGMGMTFRUB7KXGZSOJZT6JCD2"),
    "DJPPR_SBN_NonResident_byMaturity_2008_2016.xlsx": ("20220701010741", ORIG + "Kepemilikan_SBN_Rupiah_oleh_Asing/Posisi%20Kepemilikan%20SBN%20oleh%20Non-Residen%20-%20Per%20Sektor%20Maturity_2008-2016.xlsx", "3SI76PB3O5XZHMOISQJPMESFOYBVZYP5"),
    "DJPPR_SBN_NonResident_byMaturity_2017_May2022.xlsx": ("20220701010731", ORIG + "Kepemilikan_SBN_Rupiah_oleh_Asing/Posisi%20Kepemilikan%20SBN%20oleh%20Non-Residen-%20Per%20Sektor%20Maturity_2017%20-%20Mei%202022.xlsx", "UNCUSOQW4W32M33CU2SV4T5FAPOSWHA6"),
    "DJPPR_Outstanding_SBN_2021.xls": ("20220726143658", ORIG + "1Posisi_Utang/2Posisi_SUN/2021/Outstanding%20SBN%20as%20of%20December%2031,%202021.xls", "LSTU4RNTPJ5GG3VULNPIX7E5HFMYHKNS"),
}
DAILY_FILES = ["DJPPR_SBN_Ownership_Daily_%s.xlsx" % y for y in ("2016", "2017", "2018", "2019", "2020", "2021", "2022H1")]
DEC2015_FILE = "DJPPR_SBN_Ownership_2007_2015.xlsx"
NR_FILE = "DJPPR_SBN_NonResident_byMaturity_2017_May2022.xlsx"
NR_OLD_FILE = "DJPPR_SBN_NonResident_byMaturity_2008_2016.xlsx"
OUTST_FILE = "DJPPR_Outstanding_SBN_2021.xls"

# harmonised holder code -> (English label, level, parent, row_type)
#   row_type: reported = additive component of its parent; memo = "of which"/memo line (not additive);
#             derived = constructed by this script (not in the source)
HOLDERS = {
    "total": ("Total tradable Rupiah SBN outstanding", 0, "", "reported"),
    "banks": ("Banks (incl. SBN used in monetary operations with BI)", 1, "total", "reported"),
    "banks_conventional": ("Conventional banks", 2, "banks", "reported"),
    "banks_islamic": ("Islamic (sharia) banks", 2, "banks", "reported"),
    "state_institutions": ("State institutions", 1, "total", "reported"),
    "bi_net": ("Bank Indonesia, net (excl. SBN used in monetary operations with banks)", 2, "state_institutions", "reported"),
    "bi_gross": ("Bank Indonesia, gross (memo)", 3, "bi_net", "memo"),
    "bi_monetary_ops": ("SBN used in BI monetary operations with banks (memo; bi_gross - bi_net)", 3, "bi_net", "memo"),
    "nonbanks": ("Non-banks", 1, "total", "reported"),
    "mutual_funds": ("Mutual funds", 2, "nonbanks", "reported"),
    "insurance": ("Insurance companies", 2, "nonbanks", "reported"),
    "pension_funds": ("Pension funds", 2, "nonbanks", "reported"),
    "insurance_pension": ("Insurance companies and pension funds", 2, "nonbanks", "reported"),
    "nonresidents": ("Non-residents", 2, "nonbanks", "reported"),
    "nonresidents_foreign_gov_cb": ("Non-residents: of which foreign governments & central banks (memo)", 3, "nonresidents", "memo"),
    "individuals": ("Individuals", 2, "nonbanks", "reported"),
    "others": ("Others (securities companies, corporates, foundations, etc.)", 2, "nonbanks", "reported"),
    "securities_companies": ("Securities companies (Dec 2015 file only)", 3, "others", "memo"),
    "others_excl_securities": ("Others excl. securities companies (Dec 2015 file only)", 3, "others", "memo"),
}

# normalised Indonesian label (2016-2022 daily files) -> holder code
DAILY_LABELS = {
    "bank*": "banks",
    "bank konvensional": "banks_conventional",
    "bank syariah": "banks_islamic",
    "institusi negara": "state_institutions",
    "bank indonesia (net, tidak termasuk sbn yang digunakan dalam operasi moneter dengan bank)": "bi_net",
    "- bank indonesia (gross)": "bi_gross",
    "- sbn yang digunakan dalam operasi moneter dengan bank": "bi_monetary_ops",
    "non-bank": "nonbanks",
    "reksadana": "mutual_funds",
    "asuransi": "insurance",
    "dana pensiun": "pension_funds",
    "asuransi dan dana pensiun": "insurance_pension",
    "non residen": "nonresidents",
    "- termasuk pemerintah & bank sentral negara asing": "nonresidents_foreign_gov_cb",
    "individu": "individuals",
    "lain-lain": "others",
    "total": "total",
}
# 2007-2015 file (bilingual labels), used for Dec 2015 only
DEC2015_LABELS = {
    "bank/banks": "banks",
    "institusi pemerintah/ government institution": "state_institutions",
    "bank indonesia *": "bi_net",
    "non-bank/non-banks": "nonbanks",
    "reksadana/ mutual funds": "mutual_funds",
    "asuransi/ insurance company": "insurance",
    "asing/ foreign holders": "nonresidents",
    "- incl. pemerintah & bank sentral negara asing/ incl. foreign government(s) & central bank(s) **": "nonresidents_foreign_gov_cb",
    "dana pensiun/ pension funds": "pension_funds",
    "sekuritas/ securities company": "securities_companies",
    "individu/ individual": "individuals",
    "lain-lain/ others": "others_excl_securities",
    "total/ total": "total",
}
INSTR = {"SUN": "SUN", "SBSN": "SBSN", "TOTAL": "SBN"}
PCT_SKIPPED = collections.Counter()
VALUE_BLANK = []
STRAY = []
MONTHS_ID = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "mei": 5, "jun": 6, "jul": 7, "aug": 8, "agu": 8,
             "sep": 9, "oct": 10, "okt": 10, "nov": 11, "dec": 12, "des": 12}


def norm(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def clean_label(s):
    return re.sub(r"\s+", " ", str(s)).strip()


def b32sha1(path):
    with open(path, "rb") as f:
        return base64.b32encode(hashlib.sha1(f.read()).digest()).decode()


def wayback(name):
    ts, orig, _ = MANIFEST[name]
    return "https://web.archive.org/web/%sid_/%s" % (ts, orig)


def provenance(fetch):
    print("== PROVENANCE (sha1 of local file vs Internet Archive CDX digest)")
    for name, (ts, orig, dig) in MANIFEST.items():
        p = os.path.join(RAW, name)
        if not os.path.exists(p) and fetch:
            print("   fetching", wayback(name))
            with urllib.request.urlopen(wayback(name), timeout=300) as r, open(p, "wb") as f:
                f.write(r.read())
        if not os.path.exists(p):
            raise SystemExit("missing raw file %s (run with --fetch)" % name)
        got = b32sha1(p)
        print("   %-52s %s  %s" % (name, "MATCH" if got == dig else "MISMATCH " + got, ts))
        if got != dig:
            raise SystemExit("digest mismatch for " + name)


def sheet_month(title):
    t = norm(title)
    for k, v in MONTHS_ID.items():
        if t.startswith(k):
            return v
    raise ValueError("cannot read month from sheet name %r" % title)


# --------------------------------------------------------------------------- daily
def parse_daily_sheet(path, ws, year):
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    hdr = [i for i, r in enumerate(rows) if r and isinstance(r[0], str) and norm(r[0]) == "institusi"]
    if len(hdr) != 2:
        raise ValueError("%s %s: expected 2 INSTITUSI header rows, found %d" % (path, ws.title, len(hdr)))
    out_v, out_p = [], []
    for block, h in zip(("value", "pct"), hdr):
        drow, irow = rows[h], rows[h + 1]
        cols, cur = [], None
        # the sheets carry an English-label copy of the table to the right, headed 'INSTITUTION', with no values
        en_col = next((j for j in range(1, len(drow)) if isinstance(drow[j], str) and norm(drow[j]) == "institution"), None)
        last = en_col if en_col is not None else len(drow)
        if en_col is not None:
            stray = [(r + 1, j + 1) for r in range(h, min(h + 20, len(rows))) for j in range(en_col + 1, len(rows[r]))
                     if isinstance(rows[r][j], (int, float))]
            if stray:  # scratch numbers right of the English-label copy; outside the table, ignored but reported
                STRAY.append((os.path.basename(path), ws.title, block, [(rr, openpyxl.utils.get_column_letter(cc), rows[rr - 1][cc - 1]) for rr, cc in stray]))
        for j in range(1, last):
            if drow[j] is not None:
                if not isinstance(drow[j], dt.datetime):
                    raise ValueError("non-date header %r in %s %s" % (drow[j], path, ws.title))
                cur = drow[j].date()
            lab = irow[j] if j < len(irow) else None
            if lab is not None:
                cols.append((j, cur, INSTR[str(lab).strip().upper()]))
        r = h + 2
        while True:
            row = rows[r]
            lab = row[0]
            if lab is None:
                raise ValueError("blank label inside block at row %d of %s %s" % (r + 1, path, ws.title))
            code = DAILY_LABELS.get(norm(lab))
            if code is None:
                raise ValueError("unknown holder label %r in %s %s" % (lab, path, ws.title))
            lab_en = clean_label(row[en_col]) if en_col is not None and row[en_col] is not None else ""
            for j, d, ins in cols:
                v = row[j]
                if block == "pct" and not isinstance(v, (int, float)):
                    PCT_SKIPPED[repr(v)] += 1  # a few % cells are blank or '#REF!' (block used only for checks)
                    continue
                if block == "value" and v is None:
                    VALUE_BLANK.append((os.path.basename(path), ws.title.strip(), openpyxl.utils.get_column_letter(j + 1) + str(r + 1), str(d), code, ins))
                    v = float("nan")  # blank cell kept as missing, not as zero
                if not isinstance(v, (int, float)):
                    raise ValueError("non-numeric cell %r at row %d col %d in %s %s" % (v, r + 1, j + 1, path, ws.title))
                rec = dict(date=d, holder=code, holder_label_id=clean_label(lab), holder_label_en_djppr=lab_en,
                           instrument=ins, value=float(v),
                           source_file=os.path.basename(path), source_sheet=ws.title.strip(), row=r + 1, col=j + 1)
                (out_v if block == "value" else out_p).append(rec)
            if code == "total":
                break
            r += 1
    return out_v, out_p


def load_daily():
    vals, pcts = [], []
    for name in DAILY_FILES:
        p = os.path.join(RAW, name)
        year = int(name[-9:-5]) if name[-9:-5].isdigit() else int(name.split("_")[-1][:4])
        wb = openpyxl.load_workbook(p, data_only=True, read_only=True)
        for ws in wb.worksheets:
            v, q = parse_daily_sheet(p, ws, year)
            m = sheet_month(ws.title)
            for rec in v + q:
                rec["home"] = (rec["date"].month == m and rec["date"].year == year)
            vals += v
            pcts += q
    return pd.DataFrame(vals), pd.DataFrame(pcts)


def load_dec2015():
    p = os.path.join(RAW, DEC2015_FILE)
    wb = openpyxl.load_workbook(p, data_only=True, read_only=True)
    ws = wb["Des"]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    assert norm(rows[2][0]).startswith("a. dalam triliun rupiah"), rows[2][0]
    drow = rows[3]
    cols = [(j, drow[j].date()) for j in range(1, len(drow)) if isinstance(drow[j], dt.datetime)]
    out = []
    for r in range(4, len(rows)):
        lab = rows[r][0]
        if lab is None:
            break
        code = DEC2015_LABELS.get(norm(lab))
        if code is None:
            raise ValueError("unknown Dec-2015 label %r" % lab)
        for j, d in cols:
            lid, _, len_ = clean_label(lab).partition("/")
            out.append(dict(date=d, holder=code, holder_label_id=lid.strip(), holder_label_en_djppr=len_.strip(), instrument="SBN",
                            value=float(rows[r][j]), source_file=DEC2015_FILE, source_sheet="Des", row=r + 1, col=j + 1,
                            home=True))
        if code == "total":
            break
    return pd.DataFrame(out)


def dedup(df, label):
    """Same (date, holder, instrument) can appear in two monthly sheets (overlap columns). Keep the 'home' sheet."""
    key = ["date", "holder", "instrument"]
    g = df.groupby(key)["value"]
    spread = (g.max() - g.min())
    ndup_dates = df[df.duplicated(key, keep=False)]["date"].nunique()
    print("   %s: %d dates appear in two sheets; max abs difference between the copies = %.6f"
          % (label, ndup_dates, spread.max()))
    if spread.max() > 1e-9:
        print(spread[spread > 1e-9].reset_index().to_string())
    df = df.sort_values(key + ["home"], ascending=[True, True, True, False])
    return df.drop_duplicates(key, keep="first")


def show(diff, ctx=None):
    bad = diff[diff.abs() > 0.0015]
    if len(bad):
        t = bad.rename("gap").to_frame()
        if ctx is not None:
            t = t.join(ctx)
        print("      " + t.to_string().replace(chr(10), chr(10) + "      "))


def gap(a, b):
    d = (a - b).abs()
    return d.max(), int((d > 0.0015).sum()), len(d)




def validate_daily(df, pct, label):
    print("== DAILY VALIDATION (%s)" % label)
    w = df.pivot_table(index=["date", "instrument"], columns="holder", values="value", aggfunc="first", dropna=False)
    w16 = w[w.index.get_level_values("date") >= dt.date(2015, 12, 31)]
    m, n, N = gap(w["banks"] + w["state_institutions"] + w["nonbanks"], w["total"])
    print("   [V1] banks + state_institutions + nonbanks vs total: max abs gap %.6f Rp tn; %d of %d date x instrument cells > 0.0015" % (m, n, N))
    m, n, N = gap(w16["banks_conventional"] + w16["banks_islamic"], w16["banks"])
    print("   [V2] conventional + islamic banks vs banks: max abs gap %.6f; %d of %d > 0.0015" % (m, n, N))
    show(w16["banks_conventional"] + w16["banks_islamic"] - w16["banks"])
    m, n, N = gap(w["bi_net"], w["state_institutions"])
    print("   [V3a] bi_net vs state_institutions: max abs gap %.6f; %d of %d > 0.0015" % (m, n, N))
    m, n, N = gap(w16["bi_gross"] - w16["bi_monetary_ops"], w16["bi_net"])
    print("   [V3b] bi_gross - bi_monetary_ops vs bi_net: max abs gap %.6f; %d of %d > 0.0015" % (m, n, N))
    show(w16["bi_gross"] - w16["bi_monetary_ops"] - w16["bi_net"])
    ip = w["insurance_pension"].fillna(w["insurance"] + w["pension_funds"])
    oth = w["others"].fillna(w["others_excl_securities"] + w["securities_companies"])
    nb = w["mutual_funds"] + ip + w["nonresidents"] + w["individuals"] + oth
    m, n, N = gap(nb, w["nonbanks"])
    print("   [V4] mutual funds + insurance&pension + non-residents + individuals + others vs nonbanks: max abs gap %.6f; %d of %d > 0.0015" % (m, n, N))
    show(nb - w["nonbanks"])
    sp = df.pivot_table(index=["date", "holder"], columns="instrument", values="value", aggfunc="first", dropna=False)
    sp = sp[sp["SUN"].notna() | sp["SBSN"].notna()]
    m, n, N = gap(sp["SUN"] + sp["SBSN"], sp["SBN"])
    print("   [V5] SUN + SBSN vs SBN (TOTAL column), all holders: max abs gap %.6f Rp tn; %d of %d date x holder cells > 0.0015" % (m, n, N))
    show(sp["SUN"] + sp["SBSN"] - sp["SBN"], sp)
    t = sp.xs("total", level="holder")
    m, n, N = gap(t["SUN"] + t["SBSN"], t["SBN"])
    print("   [V5b] SUN + SBSN vs SBN for the total row: max abs gap %.6f; %d of %d > 0.0015" % (m, n, N))
    print("   [V5c] missing (NaN) holdings: %d rows; by holder x instrument: %s"
          % (df.value.isna().sum(), df[df.value.isna()].groupby(["holder", "instrument"]).size().to_dict()))
    if pct is not None:
        pv = pct.pivot_table(index=["date", "instrument", "holder"], values="value", aggfunc="first")["value"]
        tv = df.set_index(["date", "instrument", "holder"])["value"]
        tt = df[df.holder == "total"].set_index(["date", "instrument"])["value"]
        sh = (tv / tt.reindex(tv.index.droplevel("holder")).values * 100).reindex(pv.index)
        d = (sh - pv).abs()
        print("   [V6] reported %% block vs computed share (value/total*100): max abs gap %.4f pp over %d cells; cells > 0.01 pp: %d"
              % (d.max(), d.notna().sum(), int((d > 0.01).sum())))
        if (d > 0.01).sum():
            bad = d[d > 0.01].reset_index()
            print("        by holder x instrument: %s; dates %s..%s"
                  % (bad.groupby(["holder", "instrument"]).size().to_dict(), bad.date.min(), bad.date.max()))
    neg = df[df.value < 0]
    print("   [V7] negative holdings: %d rows; by holder x instrument: %s; dates %s..%s"
          % (len(neg), neg.groupby(["holder", "instrument"]).size().to_dict(), neg.date.min(), neg.date.max()))
    if label.startswith("after"):
        dates = sorted(df.date.unique())
        wk = [d for d in dates if d.weekday() >= 5]
        print("   [V8] %d distinct dates %s..%s; weekend dates: %s" % (len(dates), dates[0], dates[-1], wk))
        per_m = collections.Counter((d.year, d.month) for d in dates)
        print("   [V8b] trading days per month: min %d %s, max %d %s, months %d"
              % (min(per_m.values()), min(per_m, key=per_m.get), max(per_m.values()), max(per_m, key=per_m.get), len(per_m)))
        gaps = [(str(dates[i - 1]), str(dates[i])) for i in range(1, len(dates)) if (dates[i] - dates[i - 1]).days > 4]
        print("   [V8c] gaps > 4 calendar days between consecutive observations: %s" % gaps)
        isl = df[(df.holder == "banks_islamic") & (df.instrument == "SUN")]
        print("   [V9] banks_islamic SUN: %d obs, non-zero %d, NaN %d" % (len(isl), int(((isl.value != 0) & isl.value.notna()).sum()), int(isl.value.isna().sum())))


def external_outstanding(df):
    """Compare holdings totals by instrument with DJPPR 'Outstanding SBN' (tradable, Rupiah denominated)."""
    print("== EXTERNAL CHECK vs %s (I. Tradable securities, 'Total Rupiah Denominated' of SUN and of SBSN)" % OUTST_FILE)
    b = xlrd.open_workbook(os.path.join(RAW, OUTST_FILE))
    res = []
    for s in b.sheets():
        asof = str(s.cell_value(1, 0))
        d = dt.datetime.strptime(asof.replace("As of ", "").strip(), "%B %d, %Y").date()
        sec, vals = None, {}
        for i in range(s.nrows):
            a, c = norm(s.cell_value(i, 0)), norm(s.cell_value(i, 1))
            if a.startswith("ii. non tradable"):
                break
            if a.startswith("a. government debt"):
                sec = "SUN"
            elif a.startswith("b. government islamic"):
                sec = "SBSN"
            if c == "total rupiah denominated":
                vals[sec] = float(s.cell_value(i, 7)) / 1e12
        for ins in ("SUN", "SBSN"):
            res.append(dict(date=d, instrument=ins, outstanding=vals[ins]))
    o = pd.DataFrame(res)
    h = df[df.holder == "total"][["date", "instrument", "value"]]
    m = o.merge(h, on=["date", "instrument"], how="left")
    m["gap"] = m["value"] - m["outstanding"]
    print("   %d as-of dates in 2021; matched to a daily ownership date: %d of %d date x instrument" % (o.date.nunique(), m.value.notna().sum(), len(m)))
    mm = m.dropna()
    for ins in ("SUN", "SBSN"):
        x = mm[mm.instrument == ins]
        print("   %s: max abs gap %.4f Rp tn; |gap| > 0.0015: %d of %d" % (ins, x.gap.abs().max(), int((x.gap.abs() > 0.0015).sum()), len(x)))
    bad = mm[mm.gap.abs() > 0.0015]
    if len(bad):
        print(bad.to_string())
    if m.value.isna().any():
        print("   as-of dates with no daily ownership column:", [str(x) for x in sorted(m[m.value.isna()].date.unique())])


def apply_qa(df):
    """Source-cell repairs. Every changed cell is flagged in qa_flag with the source value."""
    df = df.set_index(["date", "holder", "instrument"]).sort_index()
    df["qa_flag"] = ""
    nfix = collections.Counter()

    def setv(k, v, flag):
        df.loc[k, "qa_flag"] = (df.loc[k, "qa_flag"] + "; " if df.loc[k, "qa_flag"] else "") + flag
        df.loc[k, "value"] = v

    # A. dates on which the SBSN columns were not filled in (total SBSN == 0): SBSN and SBN unusable
    tot = df.xs("total", level="holder")["value"].unstack("instrument")
    bad_dates = list(tot[(tot["SBSN"] == 0) & (tot["SUN"] > 0)].index)
    for d in bad_dates:
        for k in list(df.loc[d].index):
            if k[1] in ("SBSN", "SBN"):
                src = df.loc[(d,) + k, "value"]
                setv((d,) + k, float("nan"), "sbsn_columns_not_filled_in_source_set_missing(source=%s)"
                     % ("blank" if pd.isna(src) else "%.6f" % float(src)))
                nfix["A_sbsn_not_filled"] += 1
    # B/C. blank cells
    for k in df.index[df.value.isna()]:
        d, h, ins = k
        if d in bad_dates:
            continue
        if h == "banks_islamic" and ins == "SUN":
            sbn, sbsn = df.loc[(d, h, "SBN"), "value"], df.loc[(d, h, "SBSN"), "value"]
            if abs(sbn - sbsn) < 0.0015:
                setv(k, 0.0, "blank_in_source_set_to_0(SBN=SBSN)")
                nfix["B_blank_islamic_sun_to_0"] += 1
                continue
        df.loc[k, "qa_flag"] = "blank_in_source"
        nfix["C_blank_kept_missing"] += 1
        other = "SBSN" if ins == "SUN" else "SUN"
        sbn = df.loc[(d, h, "SBN"), "value"]
        if ins != "SBN" and abs(sbn - df.loc[(d, h, other), "value"]) < 0.0015:
            setv((d, h, "SBN"), float("nan"), "sbn_excludes_blank_%s_component_set_missing(source=%.6f)" % (ins, float(sbn)))
            nfix["C_sbn_incomplete_set_missing"] += 1
    # D. SBN (TOTAL column) cells that do not equal SUN + SBSN of the same row: replace by SUN + SBSN
    w = df["value"].unstack("instrument")
    w = w[w["SUN"].notna() & w["SBSN"].notna() & w["SBN"].notna()]
    g = (w["SUN"] + w["SBSN"] - w["SBN"]).abs()
    for (d, h) in g[g > 0.0015].index:
        src = w.loc[(d, h), "SBN"]
        setv((d, h, "SBN"), w.loc[(d, h), "SUN"] + w.loc[(d, h), "SBSN"],
             "sbn_cell_inconsistent_replaced_by_sun_plus_sbsn(source=%.6f)" % float(src))
        nfix["D_sbn_replaced"] += 1
    print("   QA repairs: %s" % dict(nfix))
    print("   dates with SBSN columns not filled: %s" % [str(x) for x in bad_dates])
    return df.reset_index()


def build_daily():
    print("== DAILY PARSE")
    raw, pct = load_daily()
    print("   parsed %d value cells and %d percentage cells from %d files" % (len(raw), len(pct), len(DAILY_FILES)))
    print("   non-numeric cells skipped in the %% block (block used only for checks): %s" % dict(PCT_SKIPPED))
    print("   blank cells in the Rp tn block: %d" % len(VALUE_BLANK))
    for x in VALUE_BLANK:
        print("     %s %s %s date %s holder %s %s" % x)
    for x in STRAY:
        print("   stray numbers right of the English-label column (ignored): %s %s %s %s" % x)
    df = dedup(raw, "2016-2022 files, Rp tn block")
    pct = dedup(pct, "2016-2022 files, % block")
    d15 = load_dec2015()
    a = d15[d15.date == dt.date(2015, 12, 31)].set_index("holder")["value"]
    b = df[(df.date == dt.date(2015, 12, 31)) & (df.instrument == "SBN")].set_index("holder")["value"]
    gaps = {k: a[k] - b[k] for k in ["banks", "state_institutions", "bi_net", "nonbanks", "mutual_funds", "insurance",
                                     "nonresidents", "nonresidents_foreign_gov_cb", "pension_funds", "individuals", "total"]}
    gaps["others(=Lain-lain+Sekuritas)"] = a["others_excl_securities"] + a["securities_companies"] - b["others"]
    print("   [V0] 2015-12-31 in the 2007-2015 file vs the 2016 file (SBN): max abs gap %.6f Rp tn over %d holders"
          % (max(abs(x) for x in gaps.values()), len(gaps)))
    d15 = d15[d15.date < dt.date(2015, 12, 31)]
    df = pd.concat([d15, df], ignore_index=True)
    df["holder_label_en_djppr"] = df["holder_label_en_djppr"].fillna("")

    validate_daily(df, pct, "before QA repairs, as published")
    df = apply_qa(df)

    der = []
    w = df.pivot_table(index=["date", "instrument"], columns="holder", values="value", aggfunc="first", dropna=False)
    x = (w["insurance"] + w["pension_funds"])
    x = x[w["insurance"].notna() | w["pension_funds"].notna()]
    for (d, ins), v in x.items():
        der.append(dict(date=d, holder="insurance_pension", holder_label_id="(derived: Asuransi + Dana Pensiun)",
                        holder_label_en_djppr="", instrument=ins, value=v, source_file="derived", source_sheet="", qa_flag=""))
    x = (w["others_excl_securities"] + w["securities_companies"]).dropna()
    for (d, ins), v in x.items():
        der.append(dict(date=d, holder="others", holder_label_id="(derived: Lain-lain + Sekuritas)",
                        holder_label_en_djppr="", instrument=ins, value=v, source_file="derived", source_sheet="", qa_flag=""))
    df = pd.concat([df, pd.DataFrame(der)], ignore_index=True)
    print("   derived rows added: %d (insurance_pension 2015-12..2019-12; others Dec 2015)" % len(der))
    assert not df.duplicated(["date", "holder", "instrument"]).any()

    validate_daily(df, None, "after QA repairs, output")
    external_outstanding(df)

    df["holder_en"] = df.holder.map(lambda h: HOLDERS[h][0])
    df["level"] = df.holder.map(lambda h: HOLDERS[h][1])
    df["parent"] = df.holder.map(lambda h: HOLDERS[h][2])
    df["row_type"] = df.holder.map(lambda h: HOLDERS[h][3])
    df.loc[df.source_file == "derived", "row_type"] = "derived"
    df["instrument_split_available"] = df.date >= dt.date(2015, 12, 31)
    order = {h: i for i, h in enumerate(HOLDERS)}
    df["_o"] = df.holder.map(order)
    df["_i"] = df.instrument.map({"SUN": 0, "SBSN": 1, "SBN": 2})
    df = df.sort_values(["date", "_o", "_i"])
    df["holdings_rp_tn"] = df.value.round(6)
    df["date"] = pd.to_datetime(df.date).dt.strftime("%Y-%m-%d")
    df["source_cell"] = [("" if pd.isna(r) else "%s%d" % (openpyxl.utils.get_column_letter(int(c)), int(r)))
                         for r, c in zip(df.row, df.col)]
    cols = ["date", "holder", "holder_en", "holder_label_id", "holder_label_en_djppr", "level", "parent", "row_type",
            "instrument", "holdings_rp_tn", "instrument_split_available", "qa_flag", "source_file", "source_sheet", "source_cell"]
    df[cols].to_csv(OUT_DAILY, index=False, encoding="utf-8")
    print("   wrote %s: %d rows, %d dates, %d holders; rows with qa_flag: %d"
          % (OUT_DAILY, len(df), df.date.nunique(), df.holder.nunique(), int((df.qa_flag != "").sum())))
    print("   rows by holder x instrument (non-missing values):")
    print(df.pivot_table(index="holder", columns="instrument", values="holdings_rp_tn", aggfunc="count").fillna(0).astype(int).to_string())
    return df


# --------------------------------------------------------------------------- non-resident by maturity
BUCKETS = {"0-1": ("y00_01", "0 to 1 year"), ">1-2": ("y01_02", "over 1 to 2 years"), ">2-5": ("y02_05", "over 2 to 5 years"),
           ">5-10": ("y05_10", "over 5 to 10 years"), ">10": ("y10_plus", "over 10 years"), "total": ("total", "Total")}
TOL_BN = 0.5


def nr_checks(nr, label):
    w = nr.pivot_table(index=["month", "instrument"], columns="maturity_bucket", values="holdings_rp_bn", aggfunc="first")
    d = (w[["y00_01", "y01_02", "y02_05", "y05_10", "y10_plus"]].sum(axis=1) - w["total"]).abs()
    print("   [M1 %s] sum of buckets vs Total: max abs gap %.4f Rp bn over %d month x instrument cells; > %.1f bn: %d"
          % (label, d.max(), len(d), TOL_BN, int((d > TOL_BN).sum())))
    v = nr.pivot_table(index=["month", "maturity_bucket"], columns="instrument", values="holdings_rp_bn", aggfunc="first")
    d = (v["SUN"] + v["SBSN"] - v["SBN"]).abs()
    print("   [M2 %s] SUN + SBSN vs SBN by bucket: max abs gap %.4f Rp bn over %d month x bucket cells; > %.1f bn: %d"
          % (label, d.max(), len(d), TOL_BN, int((d > TOL_BN).sum())))
    neg = nr[nr.holdings_rp_bn < 0]
    print("   [M6 %s] negative values: %d" % (label, len(neg)))


def daily_lookup(daily):
    dd = daily[(daily.holder == "nonresidents")].copy()
    dd["d"] = pd.to_datetime(dd.date).dt.date
    dmap = {(r.d, r.instrument): r.holdings_rp_tn * 1000 for r in dd.itertuples()}
    bymonth = collections.defaultdict(list)
    for x in sorted(dd.d.unique()):
        bymonth[(x.year, x.month)].append(x)
    return dmap, bymonth


def match_daily(value_bn, month, ins, obs_date, dmap, bymonth):
    """Daily date in the same month whose non-resident holdings equal value_bn within TOL_BN (header date preferred)."""
    days = bymonth[(month.year, month.month)]
    hits = [x for x in days if not pd.isna(dmap.get((x, ins), float("nan"))) and abs(dmap[(x, ins)] - value_bn) <= TOL_BN]
    last = days[-1]
    gl = value_bn - dmap.get((last, ins), float("nan"))
    if not hits:
        return None, last, gl
    return (obs_date if obs_date in hits else hits[-1]), last, gl


def build_nr(daily):
    print("== NON-RESIDENT BY MATURITY PARSE (%s)" % NR_FILE)
    dmap, bymonth = daily_lookup(daily)
    wb = openpyxl.load_workbook(os.path.join(RAW, NR_FILE), data_only=True, read_only=True)
    recs, dropped = [], []
    for ws in wb.worksheets:
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        blocks = {}
        for i, r in enumerate(rows):
            t = r[1] if len(r) > 1 else None
            if isinstance(t, str) and t.strip().startswith("Kepemilikan"):
                ins = t.split()[1]
                assert ins in ("SBN", "SBSN", "SUN"), t
                assert norm(rows[i + 2][1]) == "[rp miliar/idr billion]", rows[i + 2][1]
                assert norm(rows[i + 3][1]) == "sektor/sector", rows[i + 3][1]
                blocks[ins] = i + 3
        assert set(blocks) == {"SBN", "SBSN", "SUN"}, (ws.title, blocks)
        ncol = max(len(rows[h]) for h in blocks.values())
        for j in range(2, ncol):
            hdrs = {k: (rows[h][j] if j < len(rows[h]) else None) for k, h in blocks.items()}
            if all(v is None for v in hdrs.values()):
                continue
            colL = openpyxl.utils.get_column_letter(j + 1)
            if not all(isinstance(v, dt.datetime) for v in hdrs.values()):
                tots = {k: rows[h + 6][j] for k, h in blocks.items()}
                dropped.append((ws.title.strip(), colL, {k: str(v)[:10] for k, v in hdrs.items()}, tots))
                continue
            months = {(v.year, v.month) for v in hdrs.values()}
            assert len(months) == 1, (ws.title, j, hdrs)
            for ins, h in blocks.items():
                for r in range(h + 1, h + 7):
                    code, en = BUCKETS[norm(rows[r][1])]
                    v = rows[r][j]
                    assert isinstance(v, (int, float)), (ws.title, r, j, v)
                    recs.append(dict(month=dt.date(hdrs[ins].year, hdrs[ins].month, 1), obs_date=hdrs[ins].date(),
                                     instrument=ins, maturity_bucket=code, maturity_label_id=rows[r][1].strip(),
                                     maturity_en=en, holdings_rp_bn=float(v), holdings_rp_bn_source=float(v),
                                     source_sheet=ws.title.strip(), source_cell="%s%d" % (colL, r + 1), qa_flag=""))
    nr = pd.DataFrame(recs)
    print("   working/check columns dropped (a block header is not a date); their Total row and daily dates (header month or month before) with the same value:")
    for sh, colL, hd, tots in dropped:
        info = {}
        for k, v in tots.items():
            ref = max(x for x in hd.values() if x[:4].isdigit())  # a real date header of the same column
            ry, rm = int(ref[:4]), int(ref[5:7])
            window = {(ry, rm), (ry - (rm == 1), 12 if rm == 1 else rm - 1)}  # header month and the month before
            hits = sorted(str(x) for (x, ins), val in dmap.items() if ins == k and (x.year, x.month) in window
                          and not pd.isna(val) and abs(val - v) <= TOL_BN)
            info[k] = (v, hits)
        print("     sheet %s col %s headers %s -> %s" % (sh, colL, hd, info))
    dup = nr[nr.duplicated(["month", "instrument", "maturity_bucket"], keep=False)]
    print("   duplicate month x instrument x bucket after dropping check columns: %d rows" % len(dup))
    print("== NON-RESIDENT VALIDATION")
    nr_checks(nr, "as published")
    months = sorted(nr.month.unique())
    exp = pd.period_range("2017-01", "2022-05", freq="M")
    miss = [str(p) for p in exp if p.to_timestamp().date() not in set(months)]
    print("   [M3] months %s..%s: %d (expected %d); missing: %s" % (months[0], months[-1], len(months), len(exp), miss))

    # months whose published 'SUN' block actually holds SBN (SUN + SBSN): its Total equals the daily non-resident
    # SBN on a date of that month and equals no daily SUN value of that month
    tot = nr[nr.maturity_bucket == "total"].set_index(["month", "instrument"])
    relabel = []
    for mth in months:
        sun_pub = tot.loc[(mth, "SUN"), "holdings_rp_bn"]
        obs = tot.loc[(mth, "SUN"), "obs_date"]
        as_sbn, _, _ = match_daily(sun_pub, mth, "SBN", obs, dmap, bymonth)
        as_sun, _, _ = match_daily(sun_pub, mth, "SUN", obs, dmap, bymonth)
        if as_sbn is not None and as_sun is None:
            relabel.append(mth)
    print("   [M7] months whose published SUN block Total equals a daily non-resident SBN (SUN+SBSN) value and no daily SUN value: %d -> %s"
          % (len(relabel), [str(m)[:7] for m in relabel]))
    for mth in relabel:
        sel = nr.month == mth
        sun = nr[sel & (nr.instrument == "SUN")].set_index("maturity_bucket")["holdings_rp_bn_source"]
        sbsn = nr[sel & (nr.instrument == "SBSN")].set_index("maturity_bucket")["holdings_rp_bn_source"]
        for i in nr.index[sel & (nr.instrument == "SUN")]:
            b = nr.at[i, "maturity_bucket"]
            nr.at[i, "holdings_rp_bn"] = sun[b] - sbsn[b]
            nr.at[i, "qa_flag"] = "published_SUN_block_is_SBN; corrected SUN = published SUN - published SBSN"
        for i in nr.index[sel & (nr.instrument == "SBN")]:
            b = nr.at[i, "maturity_bucket"]
            nr.at[i, "holdings_rp_bn"] = sun[b]
            nr.at[i, "qa_flag"] = "published_SBN_block_double_counts_SBSN; corrected SBN = published SUN block"
    if relabel:
        nr_checks(nr, "after correction")

    out = []
    tot = nr[nr.maturity_bucket == "total"]
    for r in tot.itertuples():
        md, last, gl = match_daily(r.holdings_rp_bn, r.month, r.instrument, r.obs_date, dmap, bymonth)
        mp, _, _ = match_daily(r.holdings_rp_bn_source, r.month, r.instrument, r.obs_date, dmap, bymonth)
        out.append(dict(month=r.month, instrument=r.instrument, obs_date=r.obs_date, total_bn=r.holdings_rp_bn,
                        daily_match_date=md, published_matches=mp is not None, last_trading_day=last,
                        gap_vs_last_trading_day_bn=gl))
    c = pd.DataFrame(out)
    nm = c[c.daily_match_date.isna()]
    print("   [M4] monthly Total equals daily non-resident holdings (within %.1f Rp bn) on a date of the same month: "
          "%d of %d month x instrument after correction; %d of %d as published"
          % (TOL_BN, c.daily_match_date.notna().sum(), len(c), int(c.published_matches.sum()), len(c)))
    print("   [M4a] matched on the header date itself: %d; matched on another date of the month: %d"
          % (int((c.daily_match_date == c.obs_date).sum()), int((c.daily_match_date.notna() & (c.daily_match_date != c.obs_date)).sum())))
    x = c[c.daily_match_date.notna() & (c.daily_match_date != c.obs_date)]
    print("        " + x[["month", "instrument", "obs_date", "daily_match_date"]].to_string().replace(chr(10), chr(10) + "        "))
    print("   [M4b] no daily match in the month (gap = monthly - daily on the month's last trading day, Rp bn):")
    print("        " + nm[["month", "instrument", "obs_date", "total_bn", "last_trading_day", "gap_vs_last_trading_day_bn"]].to_string().replace(chr(10), chr(10) + "        "))
    nr = nr.merge(c[["month", "instrument", "daily_match_date", "gap_vs_last_trading_day_bn"]], on=["month", "instrument"], how="left")
    nomatch = nr.daily_match_date.isna()
    nr.loc[nomatch, "qa_flag"] = nr.loc[nomatch, "qa_flag"].map(lambda f: (f + "; " if f else "") + "total_not_equal_to_any_daily_value_in_month")

    ws = openpyxl.load_workbook(os.path.join(RAW, NR_OLD_FILE), data_only=True, read_only=True).worksheets[0]
    titles = [r[1] for r in ws.iter_rows(values_only=True) if len(r) > 1 and isinstance(r[1], str) and r[1].startswith("Kepemilikan")]
    print("   [M5] %s: blocks = %s -> SBN only, no SUN/SBSN split, not exported" % (NR_OLD_FILE, titles))

    order_i = {"SUN": 0, "SBSN": 1, "SBN": 2}
    order_b = {v[0]: i for i, v in enumerate(BUCKETS.values())}
    nr["_i"] = nr.instrument.map(order_i)
    nr["_b"] = nr.maturity_bucket.map(order_b)
    nr = nr.sort_values(["month", "_i", "_b"])
    nr["date"] = pd.to_datetime(nr.month).dt.strftime("%Y-%m-%d")
    nr["obs_date"] = pd.to_datetime(nr.obs_date).dt.strftime("%Y-%m-%d")
    nr["daily_match_date"] = pd.to_datetime(nr.daily_match_date).dt.strftime("%Y-%m-%d").fillna("")
    for cname in ("holdings_rp_bn", "holdings_rp_bn_source"):
        nr[cname] = nr[cname].round(3)
    nr["gap_vs_daily_last_trading_day_rp_bn"] = nr.gap_vs_last_trading_day_bn.round(3)
    nr["source_file"] = NR_FILE
    cols = ["date", "obs_date", "instrument", "maturity_bucket", "maturity_label_id", "maturity_en", "holdings_rp_bn",
            "holdings_rp_bn_source", "daily_match_date", "gap_vs_daily_last_trading_day_rp_bn", "qa_flag",
            "source_file", "source_sheet", "source_cell"]
    nr[cols].to_csv(OUT_NR, index=False, encoding="utf-8")
    print("   wrote %s: %d rows, %d months, rows with qa_flag: %d" % (OUT_NR, len(nr), nr.date.nunique(), int((nr.qa_flag != "").sum())))
    return nr


def reread_check(daily, nr, n=400, seed=1):
    """Re-open the raw workbooks and compare a random sample of output rows with the cell they cite."""
    print("== CELL RE-READ CHECK (random sample of output rows vs the cited source cell)")
    import random
    rnd = random.Random(seed)
    books = {}

    def cell(f, sh, ref):
        if f not in books:
            books[f] = openpyxl.load_workbook(os.path.join(RAW, f), data_only=True)
        return books[f][sh if sh in books[f].sheetnames else sh + " "][ref].value

    d = daily[(daily.qa_flag == "") & (daily.source_file != "derived")]
    idx = rnd.sample(list(d.index), n)
    bad = [(d.at[i, "source_file"], d.at[i, "source_sheet"], d.at[i, "source_cell"]) for i in idx
           if abs(cell(d.at[i, "source_file"], d.at[i, "source_sheet"], d.at[i, "source_cell"]) - d.at[i, "holdings_rp_tn"]) > 5e-7]
    print("   [V10] daily: %d sampled rows (unflagged, non-derived), mismatches: %d %s" % (n, len(bad), bad[:5]))
    idx = rnd.sample(list(nr.index), min(n, len(nr)))
    bad = [i for i in idx if abs(cell(NR_FILE, nr.at[i, "source_sheet"], nr.at[i, "source_cell"]) - nr.at[i, "holdings_rp_bn_source"]) > 5e-4]
    print("   [M8] monthly: %d sampled rows, holdings_rp_bn_source vs cited cell mismatches: %d" % (len(idx), len(bad)))


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    provenance("--fetch" in sys.argv)
    os.makedirs(CLEAN, exist_ok=True)
    daily = build_daily()
    nr = build_nr(daily)
    reread_check(daily, nr)
