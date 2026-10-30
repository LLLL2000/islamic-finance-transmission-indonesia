import sys; sys.path.append(r"C:/Users/consu/AppData/Local/Packages/PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0/LocalCache/local-packages/Python311/site-packages")
"""Builder ojk_sector: Islamic bank (BUS / UUS / BUS+UUS) financing and NPF by economic sector, monthly,
from OJK Statistik Perbankan Syariah (SPS).

Run:  python -I code/py/build_ojk_sector.py            (from anywhere; paths are absolute)
Reads  data/raw/ojk/SPS_*.xls[x]   (data only)
Writes data/clean/ojk_islamic_financing_by_sector.csv
       data/clean/ojk_conversion_events.csv
       prints validation results (copied into notes/data_ojk_sector.md)
"""
import os, re, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
from ojk_sector_lib import norm, date_columns, find_rows, header_rows, clean_value

ROOT = r"C:/Users/consu/Documents/Universidad/Islamic_Finance_Project/wp_dual_banking"
RAW = os.path.join(ROOT, "data", "raw", "ojk")
CLEAN = os.path.join(ROOT, "data", "clean")
LOG = []          # cleaning log (string cells, duplicates, annual-column use)
VAL = {}          # validation results
EDFRAMES = {}     # edition-level parsed frames (before cross-edition selection)
STRCELLS = {}     # (edition, bank_type, date, sector_code, field) -> raw text of cells published as text

# ----------------------------------------------------------------------------------------------
# classification dictionaries
NEW = [  # code, regex on Indonesian label (lower-case), group, English label
    ("L01", r"^pertanian", "business", "Agriculture, hunting and forestry"),
    ("L02", r"^perikanan", "business", "Fishery"),
    ("L03", r"^pertambangan", "business", "Mining and quarrying"),
    ("L04", r"^industri pengolahan", "business", "Manufacturing (processing industry)"),
    ("L05", r"^listrik", "business", "Electricity, gas and water"),
    ("L06", r"^konstruksi", "business", "Construction"),
    ("L07", r"^perdagangan besar", "business", "Wholesale and retail trade"),
    ("L08", r"^penyediaan akomodasi", "business", "Accommodation and food & beverage services"),
    ("L09", r"^transportasi", "business", "Transportation, warehousing and communication"),
    ("L10", r"^perantara keuangan", "business", "Financial intermediaries"),
    ("L11", r"^real estate", "business", "Real estate, renting and business services"),
    ("L12", r"^ad\w* pemerintahan", "business", "Public administration, defence and compulsory social security"),
    ("L13", r"^jasa pendidikan", "business", "Education services"),
    ("L14", r"^jasa kesehatan", "business", "Health services and social activities"),
    ("L15", r"^jasa kemasyarakatan", "business", "Community, socio-cultural, entertainment and other individual services"),
    ("L16", r"^jasa perorangan yang melayani rumah tangga", "business", "Individual services serving households"),
    ("L17", r"^badan internasional", "business", "International and extra-international organisations"),
    ("L18", r"^kegiatan yang belum jelas", "business", "Business activities not clearly defined"),
    ("N01", r"pemilikan rumah tinggal", "non_business", "Households: home ownership"),
    ("N02", r"pemilikan flat", "non_business", "Households: flat/apartment ownership"),
    ("N03", r"pemilikan ruko", "non_business", "Households: shop-house (ruko/rukan) ownership"),
    ("N04", r"pemilikan kendaraan", "non_business", "Households: motor vehicle ownership"),
    ("N05", r"pemilikan peralatan rumah tangga", "non_business", "Households: other household equipment (incl. multipurpose)"),
    ("N06", r"^bukan lapangan usaha lainnya", "non_business", "Non-business recipients: other"),
]
NEW_SKIP = r"^(penerima pembiayaan|rumah tangga( / households)?$|ket\b|ket:|nan$)"
OLD = [
    ("S01", r"^pertanian", "Agriculture, forestry and agricultural facilities"),
    ("S02", r"^pertambangan", "Mining"),
    ("S03", r"^perindustrian", "Manufacturing"),
    ("S04", r"^listrik", "Electricity, gas and water"),
    ("S05", r"^konstruksi", "Construction"),
    ("S06", r"^perdagangan", "Trade, restaurants and hotels"),
    ("S07", r"^pengangkutan", "Transport, warehousing and communication"),
    ("S08", r"^jasa dunia usaha", "Business services"),
    ("S09", r"^jasa sosial", "Social / community services"),
    ("S10", r"^lain", "Others"),
]
# concordance new19 -> old9 (used only for the overlap check; documented in the note)
# (found empirically: old 'Jasa dunia usaha' = L10 + L11 + households' home, flat and shop-house ownership N01-N03;
#  old 'Lain-lain' = L18 + N04-N06; exact to 0.000 bn on 2014-06..2015-05)
NEW2OLD = {"L01": "S01", "L02": "S01", "L03": "S02", "L04": "S03", "L05": "S04", "L06": "S05",
           "L07": "S06", "L08": "S06", "L09": "S07", "L10": "S08", "L11": "S08",
           "L12": "S09", "L13": "S09", "L14": "S09", "L15": "S09", "L16": "S09", "L17": "S09",
           "L18": "S10", "N01": "S08", "N02": "S08", "N03": "S08", "N04": "S10", "N05": "S10", "N06": "S10"}

NEW_EDITIONS = [  # newest first; (edition id, file)
    ("SPS_2025_06", "SPS_2025_06.xlsx"),
    ("SPS_2024_12", "SPS_2024_12.xlsx"),
    ("SPS_2018_12", "SPS_2018_12.xlsx"),
]
OLD_EDITIONS = [
    ("SPS_2015_06", "SPS_2015_06.xlsx"),
    ("SPS_2014_12", "SPS_2014_12.xls"),
]
ED_RANK = {"SPS_2025_06": 5, "SPS_2024_12": 4, "SPS_2018_12": 3, "SPS_2015_06": 2, "SPS_2014_12": 1}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def code_new(lbl):
    l = norm(lbl).lower()
    idl = l.split(" / ")[0]
    for code, rx, grp, en in NEW:
        if re.search(rx, idl):
            return code
    return None


def code_old(lbl):
    l = norm(lbl).lower()
    for code, rx, en in OLD:
        if re.search(rx, l):
            return code
    return None


def series_rows(df, r0, r1, monthly, annual, ed, table, where):
    """Extract {row: {col: value}} for all dated columns (monthly + annual)."""
    out = {}
    cols = list(monthly) + list(annual)
    for r in range(r0, r1):
        out[r] = {c: clean_value(df.iat[r, c], LOG, f"{ed}|{table}|r{r+1}|c{c+1}") for c in cols}
    return out


def to_long(vals, monthly, annual):
    """vals: dict col->value -> list of (date, kind, value)."""
    rec = []
    for c, d in monthly.items():
        rec.append((d, "monthly", vals[c]))
    for c, y in annual.items():
        rec.append((pd.Timestamp(y, 12, 1), "annual", vals[c]))
    return rec


# ----------------------------------------------------------------------------------------------
def parse_new(ed, fn):
    path = os.path.join(RAW, fn)
    sheet = "Tabel 14-14a-14b LapUsaha"
    df = pd.read_excel(path, sheet_name=sheet, header=None)
    titles = find_rows(df, r"^Tabel 14[ab]?\s*\.")
    assert len(titles) == 3, (ed, titles)
    recs, labels = [], {}
    for i, t in enumerate(titles):
        ttl = norm(df.iat[t, 0])
        tag = re.match(r"Tabel 14([ab]?)", ttl).group(1)
        bt = {"": "BUSUUS", "a": "BUS", "b": "UUS"}[tag]
        # sanity: title wording
        if tag == "b":
            assert "Unit Usaha Syariah" in ttl and "Bank Umum Syariah dan" not in ttl, ttl
        yr, mo = header_rows(df, t)
        end = titles[i + 1] if i + 1 < len(titles) else df.shape[0]
        monthly, annual, dups = date_columns(df, yr, mo)
        for dc, kc, d in dups:
            LOG.append(dict(kind="duplicate_month_column", where=f"{ed}|Tabel 14{tag}", date=str(d.date()), col_discarded=dc + 1, col_kept=kc + 1))
        table = f"Tabel 14{tag}"
        cur = None
        for r in range(mo + 1, end):
            lab = df.iat[r, 0]
            if not isinstance(lab, str) or not norm(lab):
                continue
            l = norm(lab).lower()
            if re.match(NEW_SKIP, l):
                continue
            if l.startswith("total pembiayaan"):
                cur, field = "TOTAL", "financing"
                labels.setdefault("TOTAL", norm(lab))
            elif l.startswith("total npf"):
                cur, field = "TOTAL", "npf"
            elif l == "npf":
                field = "npf"
            else:
                cur, field = code_new(lab), "financing"
                if cur is None:
                    raise ValueError(f"unmatched label {ed} {table} row {r+1}: {lab!r}")
                labels.setdefault(cur, norm(lab))
            vals = {c: clean_value(df.iat[r, c], LOG, f"{ed}|{table}|r{r+1}|c{c+1}") for c in list(monthly) + list(annual)}
            for c in vals:
                if isinstance(df.iat[r, c], str) and c in monthly:
                    STRCELLS[(ed, bt, monthly[c], cur, field)] = norm(df.iat[r, c])
            for d, kind, v in to_long(vals, monthly, annual):
                recs.append(dict(date=d, kind=kind, sector_code=cur, field=field, value=v, bank_type=bt,
                                 edition=ed, table=f"SPS {table} ({sheet})"))
    long = pd.DataFrame(recs)
    wide = long.pivot_table(index=["date", "kind", "sector_code", "bank_type", "edition", "table"],
                            columns="field", values="value", aggfunc="first").reset_index()
    return wide, labels


def parse_cross_new(ed, fn):
    """Tabel 13 (by type of use) totals for cross-checking Tabel 14 totals."""
    path = os.path.join(RAW, fn)
    df = pd.read_excel(path, sheet_name="Tabel 13-13a-13b JP-UMKM", header=None)
    titles = find_rows(df, r"^Tabel 13[ab]?\s*\.")
    out = []
    for i, t in enumerate(titles):
        tag = re.match(r"Tabel 13([ab]?)", norm(df.iat[t, 0])).group(1)
        bt = {"": "BUSUUS", "a": "BUS", "b": "UUS"}[tag]
        yr, mo = header_rows(df, t)
        end = titles[i + 1] if i + 1 < len(titles) else df.shape[0]
        monthly, annual, _ = date_columns(df, yr, mo)
        for r in range(mo + 1, end):
            l = norm(df.iat[r, 0]).lower() if isinstance(df.iat[r, 0], str) else ""
            f = "financing" if l.startswith("total pembiayaan") else "npf" if l.startswith("total npf") else None
            if f:
                for c, d in monthly.items():
                    out.append(dict(date=d, bank_type=bt, field=f, value=clean_value(df.iat[r, c], [], "")))
    return pd.DataFrame(out)


def realign_t28_2012(df, mo, monthly, dups):
    """SPS Dec-2014 edition, Tabel 28 (NPF by sector), year 2012: the source has an extra column headed
    '2012 / Jan' placed before the 2011 year-end column, followed by a block headed Jan..Des 2012. Tabel 26
    (financing by quality, 'Non Lancar') and Tabel 30 (NPF by type of use) of the same edition show that the
    extra column is the true January 2012, the block columns headed Jan..Okt hold February..November, the
    column headed Nov repeats the one headed Okt, and the column headed Des is December. Re-map accordingly
    (verified in validate(): Tabel 28 total vs Tabel 26/30 totals)."""
    jan = pd.Timestamp(2012, 1, 1)
    stale = [dc for dc, kc, d in dups if d == jan]
    assert len(stale) == 1, "expected one extra Jan-2012 column in Tabel 28"
    inv = {d: c for c, d in monthly.items()}
    lab = [inv[pd.Timestamp(2012, m, 1)] for m in range(1, 13)]
    rows = [r for r in range(mo + 1, df.shape[0]) if isinstance(df.iat[r, 0], str) and not re.match(r"^(r\)|1\.)", norm(df.iat[r, 0]).lower())]
    a = pd.to_numeric(df.iloc[rows, lab[9]], errors="coerce").values
    b = pd.to_numeric(df.iloc[rows, lab[10]], errors="coerce").values
    assert np.allclose(a, b, equal_nan=True), "Tabel 28: column headed Nov-2012 is not a copy of the one headed Okt-2012"
    for c in lab:
        monthly.pop(c)
    monthly[stale[0]] = jan
    for m in range(1, 11):
        monthly[lab[m - 1]] = pd.Timestamp(2012, m + 1, 1)
    monthly[lab[11]] = pd.Timestamp(2012, 12, 1)
    LOG.append(dict(kind="realigned_columns", where="SPS_2014_12|Tabel 28|2012",
                    detail="extra col headed '2012 Jan' (sheet col %d) -> 2012-01; cols headed Jan..Okt 2012 -> Feb..Nov; col headed Nov (repeat of Okt) dropped; Des unchanged" % (stale[0] + 1)))
    return dict(sorted(monthly.items()))


def parse_old(ed, fn):
    path = os.path.join(RAW, fn)
    xl = pd.ExcelFile(path)
    sh = {s.strip().lower(): s for s in xl.sheet_names}
    res = []
    labels = {}
    for key, field, tno in (("tabel 20 pembiayaan bus uus se", "financing", "Tabel 20"),
                            ("tabel 28 npf bus uus se", "npf", "Tabel 28")):
        sheet = sh[key]
        df = xl.parse(sheet, header=None)
        t = find_rows(df, r"^Tabel %s\s*\." % tno.split()[1])[0]
        yr, mo = header_rows(df, t)
        monthly, annual, dups = date_columns(df, yr, mo)
        for dc, kc, d in dups:
            a = [df.iat[r, dc] for r in range(mo + 1, mo + 12)]
            b = [df.iat[r, kc] for r in range(mo + 1, mo + 12)]
            LOG.append(dict(kind="duplicate_month_column", where=f"{ed}|{tno}", date=str(d.date()),
                            col_discarded=dc + 1, col_kept=kc + 1, discarded_total=a[-1], kept_total=b[-1]))
        if ed == "SPS_2014_12" and tno == "Tabel 28":
            monthly = realign_t28_2012(df, mo, monthly, dups)
        for r in range(mo + 1, df.shape[0]):
            lab = df.iat[r, 0]
            if not isinstance(lab, str):
                continue
            l = norm(lab).lower()
            if l == "total":
                code = "TOTAL"
            elif re.match(r"^(r\)|1\.|\*)", l):
                continue
            else:
                code = code_old(lab)
                if code is None:
                    raise ValueError(f"unmatched old label {ed} {tno} row {r+1}: {lab!r}")
            labels.setdefault(code, norm(lab))
            vals = {c: clean_value(df.iat[r, c], LOG, f"{ed}|{tno}|r{r+1}|c{c+1}") for c in list(monthly) + list(annual)}
            for d, kind, v in to_long(vals, monthly, annual):
                res.append(dict(date=d, kind=kind, sector_code=code, field=field, value=v, bank_type="BUSUUS",
                                edition=ed, tno=tno, sheet=sheet))
    long = pd.DataFrame(res)
    long = long[long.date >= "2009-01-01"]  # 2005-2008 are annual-only columns; out of scope
    tabs = long[["tno", "sheet"]].drop_duplicates().sort_values("tno")
    table_str = " + ".join(f"SPS {r.tno} ({r.sheet.strip()})" for r in tabs.itertuples())
    wide = long.pivot_table(index=["date", "kind", "sector_code", "bank_type", "edition"], columns="field",
                            values="value", aggfunc="first").reset_index()
    wide["table"] = table_str
    return wide, labels


def parse_cross_old(ed, fn):
    """Totals from Tabel 18 (by akad), 22 (by use), 26 (by quality), 30 (NPF by use)."""
    xl = pd.ExcelFile(os.path.join(RAW, fn))
    out = []
    spec = [("tabel 18", r"^total$", "fin_T18"), ("tabel 22", r"^total$", "fin_T22"),
            ("tabel 26", r"^total pembiayaan", "fin_T26"), ("tabel 26", r"^non lancar", "npf_T26"),
            ("tabel 30", r"^total$", "npf_T30")]
    for pre, rx, name in spec:
        s = [x for x in xl.sheet_names if x.strip().lower().startswith(pre + " ") and "bprs" not in x.lower()][0]
        df = xl.parse(s, header=None)
        t = find_rows(df, r"^Tabel %s\s*\." % pre.split()[1])[0]
        yr, mo = header_rows(df, t)
        monthly, annual, _ = date_columns(df, yr, mo)
        r = [i for i in range(mo + 1, df.shape[0]) if isinstance(df.iat[i, 0], str) and re.search(rx, norm(df.iat[i, 0]).lower())][0]
        for c, d in monthly.items():
            out.append(dict(date=d, kind="monthly", name=name, value=clean_value(df.iat[r, c], [], "")))
        for c, y in annual.items():
            out.append(dict(date=pd.Timestamp(y, 12, 1), kind="annual", name=name, value=clean_value(df.iat[r, c], [], "")))
    return pd.DataFrame(out)


# ----------------------------------------------------------------------------------------------
def resolve_within_edition(w, ed, cls):
    """Use annual (year-end) columns: validate against Dec; fill missing Dec; replace a Dec column that is
    an exact copy of November. Returns monthly frame with a 'note' column."""
    w = w.copy()
    w["note"] = ""
    keys = ["sector_code", "bank_type"]
    mon = w[w.kind == "monthly"].set_index(["date"] + keys)
    ann = w[w.kind == "annual"].set_index(["date"] + keys)
    out = mon.copy()
    checks = []
    for d in sorted(ann.index.get_level_values(0).unique()):
        a = ann.xs(d, level=0)
        if d in mon.index.get_level_values(0):
            m = mon.xs(d, level=0)
            prev = d - pd.offsets.MonthBegin(1)
            p = mon.xs(prev, level=0) if prev in mon.index.get_level_values(0) else None
            for f in ("financing", "npf"):
                gap = (m[f] - a[f]).abs().max()
                dup_prev = p is not None and np.allclose(m[f].values, p.reindex(m.index)[f].values, equal_nan=True)
                checks.append(dict(edition=ed, cls=cls, date=str(d.date()), field=f, max_abs_gap_dec_vs_annual=round(float(gap), 6),
                                   dec_equals_nov=bool(dup_prev)))
            # replace Dec by annual when the Dec column is an exact copy of Nov and annual differs
            for f in ("financing", "npf"):
                p_ok = p is not None and np.allclose(m[f].values, p.reindex(m.index)[f].values, equal_nan=True)
                if p_ok and (m[f] - a[f]).abs().max() > 1e-6:
                    idx = [(d,) + k for k in m.index]
                    out.loc[idx, f] = a.reindex(m.index)[f].values
                    out.loc[idx, "note"] = out.loc[idx, "note"] + f"{f}: Dec column in source is an exact copy of Nov; year-end ({d.year}) annual column used; "
                    LOG.append(dict(kind="dec_replaced_by_annual", where=f"{ed}|{cls}", date=str(d.date()), field=f))
        else:
            first_m = mon.index.get_level_values(0).min()
            if d >= first_m:
                add = a.copy()
                add["note"] = f"no monthly Dec-{d.year} column in this edition; value taken from the stand-alone {d.year} year-end column; "
                add.index = pd.MultiIndex.from_tuples([(d,) + k for k in add.index], names=out.index.names)
                out = pd.concat([out, add[out.columns]])
                LOG.append(dict(kind="dec_from_annual_column", where=f"{ed}|{cls}", date=str(d.date())))
    VAL.setdefault("annual_vs_dec", []).extend(checks)
    out = out.reset_index()
    out["kind"] = "monthly"
    return out


def flag_carry_forward(df, cls):
    """flag months where every sector value (financing) equals the previous month exactly."""
    flags = []
    for (ed, bt), g in df.groupby(["edition", "bank_type"]):
        piv = g.pivot_table(index="date", columns="sector_code", values="financing")
        pn = g.pivot_table(index="date", columns="sector_code", values="npf")
        for i in range(1, len(piv)):
            d, dp = piv.index[i], piv.index[i - 1]
            if (d - dp).days > 31:
                continue
            for f, P in (("financing", piv), ("npf", pn)):
                if np.allclose(P.iloc[i].values, P.iloc[i - 1].values, equal_nan=True) and P.iloc[i].abs().sum() > 0:
                    flags.append(dict(cls=cls, edition=ed, bank_type=bt, date=str(d.date()), field=f))
    return flags


def fix_new19(prim):
    """Targeted, self-checking corrections of the new-classification primary series (see note)."""
    prim = prim.copy()
    m = prim.classification == "new19"
    idx = {(r.date, r.sector_code, r.bank_type): i for i, r in prim[m].iterrows()}
    fixes = []

    def get(d, s, b, f):
        i = idx.get((d, s, b))
        return np.nan if i is None else prim.at[i, f]

    def put(d, s, b, f, v, why):
        i = idx[(d, s, b)]
        fixes.append(dict(date=str(d.date()), sector=s, bank_type=b, field=f, old=None if pd.isna(prim.at[i, f]) else round(float(prim.at[i, f]), 6),
                          new=round(float(v), 6), why=why))
        prim.at[i, f] = v
        prim.at[i, "note"] = prim.at[i, "note"] + f"{f}: {why}; "

    dates = sorted(prim[m].date.unique())
    secs = [c for c, *_ in NEW] + ["TOTAL"]
    # C1: UUS column exactly doubled in the source
    for d in dates:
        u, a, b = get(d, "TOTAL", "UUS", "financing"), get(d, "TOTAL", "BUSUUS", "financing"), get(d, "TOTAL", "BUS", "financing")
        imp = a - b
        if np.isfinite(u) and np.isfinite(imp) and abs(u - imp) > 1 and abs(u - 2 * imp) < 1e-4 * u:
            devs = {"financing": [], "npf": []}
            for s_ in secs:
                for f in ("financing", "npf"):
                    src = get(d, s_, "UUS", f)
                    impl = get(d, s_, "BUSUUS", f) - get(d, s_, "BUS", f)
                    if np.isfinite(impl):
                        devs[f].append((abs(src / 2 - impl), s_))
                    put(d, s_, "UUS", f, src / 2, "source UUS column (Tabel 14b) is exactly 2x the true value in this month; halved "
                        "(halved values equal BUS+UUS minus BUS to <0.001 bn for every financing cell, and equal Tabel 13b UUS totals)")
            VAL.setdefault("uus_doubling", []).append(dict(
                date=str(d.date()), uus_total_src=round(u, 3), implied=round(imp, 3),
                max_abs_dev_half_vs_implied_financing=round(max(devs["financing"])[0], 6),
                npf_cells_dev_gt_0_001=[(s_, round(v, 4)) for v, s_ in devs["npf"] if v > 1e-3]))
    # C5: BUS+UUS sector cell inconsistent with both its own total and BUS+UUS components (provisional string typo)
    for d in dates:
        ssum = sum(get(d, s, "BUSUUS", "financing") for s in secs[:-1])
        gap = ssum - get(d, "TOTAL", "BUSUUS", "financing")
        if abs(gap) > 10:
            for s in secs[:-1]:
                comp = get(d, s, "BUS", "financing") + get(d, s, "UUS", "financing")
                if abs(get(d, s, "BUSUUS", "financing") - comp) > 10 and abs((get(d, s, "BUSUUS", "financing") - comp) - gap) < 10:
                    put(d, s, "BUSUUS", "financing", comp, "provisional source cell (text with '*)') inconsistent with the BUS+UUS total; replaced by BUS (14a) + UUS (14b)")
    # C2/C3: fill missing cells from the identity BUS + UUS = BUS+UUS
    filled = []
    for d in dates:
        for s in secs:
            for f in ("financing", "npf"):
                a, b, u = get(d, s, "BUSUUS", f), get(d, s, "BUS", f), get(d, s, "UUS", f)
                if pd.isna(a) and np.isfinite(b) and np.isfinite(u) and (d, s, "BUSUUS") in idx:
                    put(d, s, "BUSUUS", f, b + u, "blank in source; filled as BUS + UUS")
                    filled.append((d, f, b + u))
                elif pd.isna(u) and np.isfinite(a) and np.isfinite(b) and (d, s, "UUS") in idx:
                    put(d, s, "UUS", f, a - b, "blank in source; filled as (BUS+UUS) - BUS")
                elif pd.isna(b) and np.isfinite(a) and np.isfinite(u) and (d, s, "BUS") in idx:
                    put(d, s, "BUS", f, a - u, "blank in source; filled as (BUS+UUS) - UUS")
    # C6: BUS+UUS total that omitted a blank sector cell (checked against older edition / Tabel 13)
    for d, f, v in filled:
        ssum = sum(get(d, s_, "BUSUUS", f) for s_ in secs[:-1])
        tot = get(d, "TOTAL", "BUSUUS", f)
        if abs((ssum - tot) - v) < 0.01:
            put(d, "TOTAL", "BUSUUS", f, tot + v, "source total omitted the blank sector cell; corrected total = sum of sectors "
                "(equals the SPS_2018_12 edition value and the Tabel 13 total)")
    VAL["new19_fixes"] = fixes
    return prim


# ----------------------------------------------------------------------------------------------
def main():
    files = {ed: fn for ed, fn in NEW_EDITIONS + OLD_EDITIONS}
    VAL["files"] = {ed: dict(file=fn, bytes=os.path.getsize(os.path.join(RAW, fn)), sha256=sha256(os.path.join(RAW, fn))) for ed, fn in files.items()}

    # ---------------- new classification
    new_frames, new_labels = [], {}
    for ed, fn in NEW_EDITIONS:
        w, labs = parse_new(ed, fn)
        if not new_labels:
            new_labels = labs
        new_frames.append(resolve_within_edition(w, ed, "new19"))
        EDFRAMES[ed] = new_frames[-1]
    newall = pd.concat(new_frames, ignore_index=True)
    newall["classification"] = "new19"

    # ---------------- old classification
    old_frames, old_labels = [], {}
    for ed, fn in OLD_EDITIONS:
        w, labs = parse_old(ed, fn)
        old_labels = old_labels or labs
        old_frames.append(resolve_within_edition(w, ed, "old9"))
        EDFRAMES[ed] = old_frames[-1]
    oldall = pd.concat(old_frames, ignore_index=True)
    oldall["classification"] = "old9"

    allv = pd.concat([newall, oldall], ignore_index=True)
    VAL["carry_forward_flags"] = flag_carry_forward(allv, "all")

    # ---------------- coverage per edition
    VAL["coverage"] = {}
    for (cls, ed), g in allv.groupby(["classification", "edition"]):
        ds = sorted(g.date.unique())
        VAL["coverage"][f"{cls}|{ed}"] = dict(first=str(pd.Timestamp(ds[0]).date()), last=str(pd.Timestamp(ds[-1]).date()), n_months=len(ds))

    # ---------------- revisions across editions (same classification, same date, sector, bank type)
    rev = []
    for cls, g in allv.groupby("classification"):
        eds = sorted(g.edition.unique(), key=lambda e: -ED_RANK[e])
        base = g[g.edition == eds[0]].set_index(["date", "sector_code", "bank_type"])
        for e in eds[1:]:
            o = g[g.edition == e].set_index(["date", "sector_code", "bank_type"])
            j = base.join(o, how="inner", lsuffix="_new", rsuffix="_old")
            for f in ("financing", "npf"):
                dif = (j[f + "_new"] - j[f + "_old"])
                rel = dif.abs() / j[f + "_old"].abs().where(j[f + "_old"].abs() > 0)
                nrev = int((dif.abs() > 1e-3).sum())
                tot = j.xs("TOTAL", level="sector_code")
                td = (tot[f + "_new"] - tot[f + "_old"]).abs()
                by_month = dif.abs().groupby(level="date").max()
                rev.append(dict(cls=cls, latest=eds[0], older=e, field=f, n_cells=int(len(j)),
                                n_months=int(j.index.get_level_values(0).nunique()),
                                n_cells_revised_gt_0001=nrev, max_abs_diff=round(float(dif.abs().max()), 4),
                                max_rel_diff=round(float(rel.max()), 6) if rel.notna().any() else None,
                                max_abs_diff_total=round(float(td.max()), 4),
                                months_with_any_revision=[str(pd.Timestamp(x).date()) for x in by_month[by_month > 1e-3].index][:40]))
    VAL["revisions"] = rev

    # ---------------- primary selection: latest edition carrying the month (per class x date x bank type)
    allv["rank"] = allv.edition.map(ED_RANK)
    pick = allv.groupby(["classification", "date", "bank_type"])["rank"].max().rename("best").reset_index()
    prim = allv.merge(pick, on=["classification", "date", "bank_type"])
    prim = prim[prim["rank"] == prim["best"]].drop(columns=["rank", "best", "kind"])

    # drop old9 months that are pure carry-forwards when the month exists in new19
    cf = pd.DataFrame(VAL["carry_forward_flags"])
    dropped = []
    if len(cf):
        for r in cf[cf.field == "financing"].itertuples():
            m = (prim.classification == "old9") & (prim.edition == r.edition) & (prim.date == pd.Timestamp(r.date))
            if m.any() and pd.Timestamp(r.date) >= pd.Timestamp("2014-06-01"):
                prim = prim[~m]
                dropped.append(dict(edition=r.edition, date=r.date, reason="old9 month identical to previous month in all sectors (carry-forward); new19 covers this month"))
        for r in cf.itertuples():
            m = (prim.edition == r.edition) & (prim.date == pd.Timestamp(r.date)) & (prim.bank_type == r.bank_type)
            prim.loc[m, "note"] = prim.loc[m, "note"] + f"{r.field}: all sector values identical to previous month in source (suspected carry-forward); "
    VAL["dropped_months"] = dropped
    prim = fix_new19(prim)
    for (ed, bt, d, sc, f), raw in STRCELLS.items():
        mk = (prim.edition == ed) & (prim.bank_type == bt) & (prim.date == d) & (prim.sector_code == sc)
        txt = (f"{f}: published as '-' (nil), set to 0; " if raw.strip() in ("-", "--") else
               f"{f}: published as text '{raw}' (provisional, rounded to Rp 1 bn; read as thousands-separated); ")
        prim.loc[mk, "note"] = prim.loc[mk, "note"] + txt
    mk = (prim.classification == "old9") & (prim.date == pd.Timestamp("2014-05-01"))
    prim.loc[mk, "note"] = prim.loc[mk, "note"] + "series break: from May 2014 OJK revised BUS-UUS data based on LSMK reports (source footnote 1); old9 sectors from 2014-05 are a mapping of the new LSMK sector data; "
    mk = (prim.classification == "new19") & (prim.date == pd.Timestamp("2014-06-01"))
    prim.loc[mk, "note"] = prim.loc[mk, "note"] + "first month of the new classification; large reallocations between sectors in 2014-07 (see data note); "

    # ---------------- labels and output
    lab_new = {c: new_labels.get(c, "") for c, *_ in NEW}
    lab_new["TOTAL"] = new_labels.get("TOTAL", "Total Pembiayaan / Total Financing")
    en_new = {c: en for c, rx, g, en in NEW}; en_new["TOTAL"] = "Total financing (all recipients)"
    grp_new = {c: g for c, rx, g, en in NEW}; grp_new["TOTAL"] = "total"
    en_old = {c: en for c, rx, en in OLD}; en_old["TOTAL"] = "Total"
    grp_old = {c: ("other" if c == "S10" else "business") for c, *_ in OLD}; grp_old["TOTAL"] = "total"

    def idlab(r):
        if r.classification == "new19":
            return lab_new[r.sector_code].split(" / ")[0]
        return old_labels.get(r.sector_code, "")
    prim["sector_id_label"] = [idlab(r) for r in prim.itertuples()]
    prim["sector_en"] = [en_new[r.sector_code] if r.classification == "new19" else en_old[r.sector_code] for r in prim.itertuples()]
    prim["sector_group"] = [grp_new[r.sector_code] if r.classification == "new19" else grp_old[r.sector_code] for r in prim.itertuples()]
    prim = prim.rename(columns={"financing": "financing_rp_bn", "npf": "npf_rp_bn"})
    prim["npf_ratio_pct"] = np.where(prim.financing_rp_bn > 0, 100 * prim.npf_rp_bn / prim.financing_rp_bn, np.nan)
    prim["note"] = prim["note"].str.strip()
    prim["date"] = pd.to_datetime(prim.date).dt.strftime("%Y-%m-%d")
    cols = ["date", "classification", "sector_code", "sector_group", "sector_id_label", "sector_en", "bank_type",
            "financing_rp_bn", "npf_rp_bn", "npf_ratio_pct", "edition", "table", "note"]
    order = {c: i for i, c in enumerate([c for c, *_ in NEW] + [c for c, *_ in OLD] + ["TOTAL"])}
    prim["_o"] = prim.sector_code.map(order)
    prim["_b"] = prim.bank_type.map({"BUSUUS": 0, "BUS": 1, "UUS": 2})
    prim = prim.sort_values(["classification", "date", "_b", "_o"], ascending=[False, True, True, True])[cols]
    prim["financing_rp_bn"] = prim.financing_rp_bn.round(6)
    prim["npf_rp_bn"] = prim.npf_rp_bn.round(6)
    prim["npf_ratio_pct"] = prim.npf_ratio_pct.round(4)
    os.makedirs(CLEAN, exist_ok=True)
    prim.to_csv(os.path.join(CLEAN, "ojk_islamic_financing_by_sector.csv"), index=False, encoding="utf-8")
    VAL["output_rows"] = int(len(prim))
    VAL["output_coverage"] = {f"{c}|{b}": dict(first=g.date.min(), last=g.date.max(), n_months=int(g.date.nunique()))
                              for (c, b), g in prim.groupby(["classification", "bank_type"])}
    allm = pd.date_range("2009-01-01", "2025-06-01", freq="MS").strftime("%Y-%m-%d")
    VAL["missing_months_any_class_BUSUUS"] = [d for d in allm if d not in set(prim[prim.bank_type == "BUSUUS"].date)]
    VAL["missing_months_new19_BUS"] = [d for d in pd.date_range("2014-06-01", "2025-06-01", freq="MS").strftime("%Y-%m-%d")
                                       if d not in set(prim[(prim.bank_type == "BUS")].date)]

    validate(prim, files)
    events(prim)
    print("VALIDATION-JSON-START")
    print(json.dumps(VAL, indent=1, default=str))
    print("LOG:")
    for l in LOG:
        print(json.dumps(l, default=str))


# ----------------------------------------------------------------------------------------------
def validate(prim, files):
    p = prim.copy()
    # 1) sector sum vs reported total
    res = []
    for (cls, bt, ed), g in p.groupby(["classification", "bank_type", "edition"]):
        for f in ("financing_rp_bn", "npf_rp_bn"):
            s = g[g.sector_code != "TOTAL"].groupby("date")[f].sum(min_count=1)
            t = g[g.sector_code == "TOTAL"].set_index("date")[f]
            gap = (s - t).dropna()
            worst = gap.abs().idxmax() if len(gap) else None
            res.append(dict(cls=cls, bank_type=bt, edition=ed, field=f, n_months=int(len(gap)),
                            max_abs_gap=round(float(gap.abs().max()), 6), at=worst,
                            max_rel_gap=round(float((gap.abs() / t.reindex(gap.index)).max()), 8),
                            months_gap_gt_1bn=[d for d, v in gap.items() if abs(v) > 1]))
    VAL["sum_vs_total"] = res
    # 2) BUS + UUS = BUSUUS (new19)
    n = p[p.classification == "new19"]
    res = []
    for f in ("financing_rp_bn", "npf_rp_bn"):
        piv = n.pivot_table(index=["date", "sector_code"], columns="bank_type", values=f)
        gap = (piv.BUS + piv.UUS - piv.BUSUUS).dropna()
        bym = gap.abs().groupby(level="date").max()
        res.append(dict(field=f, n_cells=int(len(gap)), n_months=int(bym.size), max_abs_gap=round(float(gap.abs().max()), 6),
                        at=str(gap.abs().idxmax()), months_gap_gt_0_01=[d for d, v in bym.items() if v > 0.01],
                        max_abs_gap_by_month_top=bym.sort_values(ascending=False).head(8).round(4).to_dict()))
    VAL["bus_plus_uus"] = res
    # 3) cross-table totals
    ct = []
    for ed, fn in NEW_EDITIONS:
        x = parse_cross_new(ed, fn).pivot_table(index=["date", "bank_type"], columns="field", values="value")
        mine = EDFRAMES[ed]
        mine = mine[mine.sector_code == "TOTAL"].set_index(["date", "bank_type"])[["financing", "npf"]]
        j = mine.join(x, how="inner", rsuffix="_t13")
        for f, g in (("financing", "financing_t13"), ("npf", "npf_t13")):
            d = (j[f] - j[g]).abs()
            ct.append(dict(edition=ed, check=f"Tabel 14 total vs Tabel 13 total ({f}), source values before corrections", n=int(d.notna().sum()),
                           max_abs_gap=round(float(d.max()), 6), dates_gt_1bn={str(i[0].date()) + "|" + i[1]: round(float(v), 3) for i, v in d.items() if v > 1}))
    for ed, fn in OLD_EDITIONS:
        x = parse_cross_old(ed, fn)
        x = x[x.kind == "monthly"].pivot_table(index="date", columns="name", values="value")
        mine = EDFRAMES[ed]
        mine = mine[mine.sector_code == "TOTAL"].set_index("date")[["financing", "npf"]]
        j = mine.join(x, how="inner")
        for f, g in (("financing", "fin_T18"), ("financing", "fin_T22"), ("financing", "fin_T26"),
                     ("npf", "npf_T26"), ("npf", "npf_T30")):
            if g not in j:
                continue
            d = (j[f] - j[g]).abs()
            ct.append(dict(edition=ed, check=f"Tabel 20/28 total vs {g}", n=int(d.notna().sum()), max_abs_gap=round(float(d.max()), 6),
                           dates_gt_1bn={str(i.date()): round(float(v), 3) for i, v in d.items() if v > 1}))
    VAL["cross_table_totals"] = ct
    # 4) old vs new on overlap months
    o = p[p.classification == "old9"].set_index(["date", "sector_code"])["financing_rp_bn"]
    on = p[p.classification == "old9"].set_index(["date", "sector_code"])["npf_rp_bn"]
    nb = n[n.bank_type == "BUSUUS"].copy()
    nb["old"] = nb.sector_code.map(lambda c: NEW2OLD.get(c, "TOTAL"))
    agg = nb.groupby(["date", "old"])[["financing_rp_bn", "npf_rp_bn"]].sum()
    agg.index.names = ["date", "sector_code"]
    j = agg.join(o.rename("old_fin")).join(on.rename("old_npf")).dropna(subset=["old_fin"])
    j["gap_fin"] = j.financing_rp_bn - j.old_fin
    j["gap_npf"] = j.npf_rp_bn - j.old_npf
    VAL["old_vs_new_overlap"] = dict(
        months=sorted({d for d, _ in j.index}),
        max_abs_gap_fin=round(float(j.gap_fin.abs().max()), 6), max_abs_gap_npf=round(float(j.gap_npf.abs().max()), 6),
        by_sector_max_abs_gap_fin=j.gap_fin.abs().groupby(level="sector_code").max().round(4).to_dict(),
        by_sector_max_abs_gap_npf=j.gap_npf.abs().groupby(level="sector_code").max().round(4).to_dict(),
        detail_fin=j.gap_fin.round(3).unstack().to_dict(orient="index"))
    # NPF ratio sanity
    VAL["npf_gt_financing_cells"] = int((p.npf_rp_bn > p.financing_rp_bn + 1e-6).sum())
    VAL["negative_cells"] = int(((p.financing_rp_bn < 0) | (p.npf_rp_bn < 0)).sum())
    VAL["missing_values"] = int(p.financing_rp_bn.isna().sum()), int(p.npf_rp_bn.isna().sum())


# ----------------------------------------------------------------------------------------------
EVENTS = [
    # id, label, bank, type, legal effective date (from public announcements, not verified against an
    # official register in this build), months inspected
    ("E1", "BTPN Syariah spin-off (UUS of Bank BTPN -> BUS Bank BTPN Syariah)", "Bank BTPN Syariah", "UUS spin-off to BUS", "2014-07 (approx.)", ["2014-07"]),
    ("E2", "Bank Aceh conversion (conventional BPD with UUS -> BUS Bank Aceh Syariah)", "Bank Aceh Syariah", "conventional bank conversion to BUS", "2016-09 (approx.)", ["2016-09", "2016-10"]),
    ("E3", "Bank NTB conversion (conventional BPD with UUS -> BUS Bank NTB Syariah)", "Bank NTB Syariah", "conventional bank conversion to BUS", "2018-09 (approx.)", ["2018-09", "2018-10"]),
    ("E4", "Merger BRIS + BSM + BNIS into Bank Syariah Indonesia (all three already BUS)", "Bank Syariah Indonesia", "merger within BUS", "2021-02-01", ["2021-02"]),
    ("E5", "Bank Riau Kepri conversion (conventional BPD with UUS -> BUS Bank Riau Kepri Syariah)", "Bank Riau Kepri Syariah", "conventional bank conversion to BUS", "2022 (approx.; jump observed 2022-08)", ["2022-08", "2022-09"]),
    ("S1", "Unidentified BUS/UUS jump flagged by the scan (no bank attributed)", "", "scan candidate", "", ["2015-06"]),
    ("S2", "Unidentified BUS/UUS jumps flagged by the scan (no bank attributed)", "", "scan candidate", "", ["2021-10", "2021-11", "2021-12"]),
    ("S3", "Unidentified UUS jump flagged by the scan (no bank attributed)", "", "scan candidate", "", ["2016-12"]),
]


def events(prim):
    n = prim[prim.classification == "new19"].copy()
    n["date"] = pd.to_datetime(n.date)
    fin = n.pivot_table(index="date", columns=["bank_type", "sector_code"], values="financing_rp_bn").sort_index()
    npf = n.pivot_table(index="date", columns=["bank_type", "sector_code"], values="npf_rp_bn").sort_index()
    # consecutive-month changes only
    full = pd.date_range(fin.index.min(), fin.index.max(), freq="MS")
    fin = fin.reindex(full); npf = npf.reindex(full)
    dfin = fin.diff(); dnpf = npf.diff()
    # scan: months where UUS total falls and BUS total rises (candidate UUS->BUS shifts), and large BUS/UUS moves
    t = dfin.xs("TOTAL", axis=1, level=1)
    med = t.abs().rolling(12, min_periods=6).median().shift(1)
    cand = t[((t.UUS < -0.5 * med.UUS) & (t.BUS > 3 * med.BUS)) | (t.BUS.abs() > 4 * med.BUS) | (t.UUS.abs() > 4 * med.UUS)]
    VAL["event_scan_candidates"] = {str(d.date()): dict(dBUS=round(r.BUS, 1), dUUS=round(r.UUS, 1), dBUSUUS=round(r.BUSUUS, 1),
                                                        medabs12_BUS=round(med.loc[d, "BUS"], 1), medabs12_UUS=round(med.loc[d, "UUS"], 1))
                                    for d, r in cand.iterrows()}
    rows = []
    for eid, lab, bank, typ, eff, months in EVENTS:
        for m in months:
            d = pd.Timestamp(m + "-01")
            if d not in dfin.index or pd.isna(dfin.loc[d]).all():
                rows.append(dict(event_id=eid, event=lab, bank=bank, event_type=typ, effective_date=eff, month=m,
                                 bank_type="", sector_code="", note="month not in data"))
                continue
            win = dfin.loc[d - pd.DateOffset(months=12): d - pd.DateOffset(months=1)]
            for (bt, sc) in fin.columns:
                med12 = win[(bt, sc)].median()
                rows.append(dict(event_id=eid, event=lab, bank=bank, event_type=typ, effective_date=eff, month=m,
                                 bank_type=bt, sector_code=sc,
                                 financing_prev_rp_bn=fin.loc[d - pd.DateOffset(months=1), (bt, sc)],
                                 financing_rp_bn=fin.loc[d, (bt, sc)],
                                 change_rp_bn=dfin.loc[d, (bt, sc)],
                                 median_change_prev12_rp_bn=med12,
                                 abnormal_change_rp_bn=dfin.loc[d, (bt, sc)] - med12,
                                 npf_change_rp_bn=dnpf.loc[d, (bt, sc)]))
    ev = pd.DataFrame(rows)
    en = {c: en for c, rx, g, en in NEW}; en["TOTAL"] = "Total financing"
    ev["sector_en"] = ev.sector_code.map(en)
    for c in ["financing_prev_rp_bn", "financing_rp_bn", "change_rp_bn", "median_change_prev12_rp_bn", "abnormal_change_rp_bn", "npf_change_rp_bn"]:
        ev[c] = ev[c].astype(float).round(3)
    ev["sector_code"] = ev.sector_code.astype(str)
    ev["_b"] = ev.bank_type.map({"BUS": 0, "UUS": 1, "BUSUUS": 2})
    ev = ev.sort_values(["event_id", "month", "_b", "sector_code"]).drop(columns="_b")
    ev = ev[["event_id", "event", "bank", "event_type", "effective_date", "month", "bank_type", "sector_code", "sector_en",
             "financing_prev_rp_bn", "financing_rp_bn", "change_rp_bn", "median_change_prev12_rp_bn", "abnormal_change_rp_bn",
             "npf_change_rp_bn"]]
    ev.rename(columns={"month": "date"}).assign(date=lambda x: x.date + "-01").to_csv(
        os.path.join(CLEAN, "ojk_conversion_events.csv"), index=False, encoding="utf-8")
    VAL["event_totals"] = ev[ev.sector_code == "TOTAL"][["event_id", "month", "bank_type", "change_rp_bn", "median_change_prev12_rp_bn", "abnormal_change_rp_bn"]].to_dict(orient="records")


if __name__ == "__main__":
    main()
