import sys; sys.path.append(r"C:/Users/consu/AppData/Local/Packages/PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0/LocalCache/local-packages/Python311/site-packages")
"""
Build the OJK SPS "mechanism" series (builder: ojk_mechanisms).

Reads the Statistik Perbankan Syariah (SPS) workbooks in data/raw/ojk/ and writes
  data/clean/ojk_contracts.csv        financing and NPF by contract (akad), Tabel 11 (all ccy) / 12 (Rupiah); old Tabel 18
  data/clean/ojk_deposits.csv         DPK composition, Tabel 22; old Tabel 14 (+ harmonised 2009-2025 series)
  data/clean/ojk_deposit_returns.csv  equivalent rate of return on deposits, Tabel 17 section I; old Tabel 36
  data/clean/ojk_margins.csv          financing rates: Tabel 17 section II (by contract), Tabel 18 (use x size), Tabel 19 (sector); old Tabel 36
  data/clean/ojk_aggregates.csv       headline aggregates: Tabel 1, 2, 6, 11, 22; old Tabel 6, 14, 18, 26, 38
Editions: SPS_2025_06, SPS_2024_12, SPS_2018_12 (new format, 2014-06+); SPS_2015_06, SPS_2014_12 (old format,
2009-01..2014-05). Source errors found by accounting identities are corrected in FIXES_* (flagged, published value
kept in `note`). Data note: notes/data_ojk_mechanisms.md

Run:  python -I code/py/build_ojk_mechanisms.py
Raw files are treated as data only (values are read, nothing is executed). Validation results are printed to stdout.
"""
import re
import zipfile
import datetime as dt
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "ojk"
CLEAN = ROOT / "data" / "clean"

# (file, edition yyyy-mm, format). Later editions have priority (they carry revisions).
EDITIONS = [
    ("SPS_2025_06.xlsx", "2025-06", "new"),
    ("SPS_2024_12.xlsx", "2024-12", "new"),
    ("SPS_2023_12.xlsx", "2023-12", "new"),   # optional (Internet Archive copy), used if present
    ("SPS_2018_12.xlsx", "2018-12", "new"),
    ("SPS_2015_06.xlsx", "2015-06", "old"),   # old format; monthly 2014-01..2015-05 (+ annual 2009-2013)
    ("SPS_2014_12.xls", "2014-12", "old"),    # old format; monthly 2009-01..2014-12
]
OLD_EDITIONS = {"2014-12", "2015-06"}
MIN_DATE = pd.Timestamp("2009-01-01")
NEW_FORMAT_START = pd.Timestamp("2014-06-01")   # first month of the restructured SPS (BUS/UUS split)

MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "mei": 5, "may": 5, "jun": 6, "jul": 7, "ags": 8, "agt": 8,
          "agu": 8, "aug": 8, "sep": 9, "okt": 10, "oct": 10, "nov": 11, "des": 12, "dec": 12}
WARN = []


def warn(msg):
    WARN.append(msg)


# --------------------------------------------------------------------------------------------
# reading helpers
# --------------------------------------------------------------------------------------------
def xlsx_merged_ranges(path):
    """Map sheet name -> list of (r0, c0, r1, c1) 0-based merged ranges, parsed from the sheet XML."""
    out = {}
    with zipfile.ZipFile(path) as z:
        wb = z.read("xl/workbook.xml").decode("utf8")
        rels = z.read("xl/_rels/workbook.xml.rels").decode("utf8")
        rid2t = {}
        for m in re.finditer(r"<Relationship\b[^>]*>", rels):
            tag = m.group(0)
            i = re.search(r'Id="([^"]+)"', tag); t = re.search(r'Target="([^"]+)"', tag)
            if i and t:
                rid2t[i.group(1)] = t.group(1)
        for m in re.finditer(r"<sheet\b[^>]*>", wb):
            tag = m.group(0)
            name = re.search(r'name="([^"]*)"', tag).group(1)
            rid = re.search(r'r:id="([^"]+)"', tag).group(1)
            tgt = rid2t[rid].lstrip("/")
            tgt = tgt if tgt.startswith("xl/") else "xl/" + tgt
            name = (name.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                    .replace("&quot;", '"').replace("&apos;", "'"))
            xml = z.read(tgt).decode("utf8", errors="replace")
            rngs = []
            for mm in re.finditer(r'<mergeCell ref="([A-Z]+)(\d+):([A-Z]+)(\d+)"', xml):
                c0, r0, c1, r1 = mm.groups()
                rngs.append((int(r0) - 1, col2i(c0), int(r1) - 1, col2i(c1)))
            out[name] = rngs
    return out


def col2i(s):
    n = 0
    for ch in s:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


class Book:
    def __init__(self, fname, edition, fmt):
        self.fname, self.edition, self.fmt = fname, edition, fmt
        self.path = RAW / fname
        self.xl = pd.ExcelFile(self.path)
        self.merged = xlsx_merged_ranges(self.path) if self.path.suffix == ".xlsx" else {}
        self._cache = {}

    def sheet(self, pattern):
        rx = re.compile(pattern, re.I)
        hits = [s for s in self.xl.sheet_names if rx.search(s)]
        if len(hits) != 1:
            raise RuntimeError(f"{self.fname}: pattern {pattern!r} matched {hits}")
        return hits[0]

    def values(self, sh):
        if sh not in self._cache:
            self._cache[sh] = self.xl.parse(sh, header=None)
        return self._cache[sh]


def is_blank(v):
    return v is None or (isinstance(v, float) and np.isnan(v)) or (isinstance(v, str) and v.strip() == "")


def year_of(v):
    if isinstance(v, (int, float, np.integer, np.floating)) and not is_blank(v):
        if float(v).is_integer() and 1990 <= v <= 2040:
            return int(v)
        return None
    if isinstance(v, str):
        m = re.match(r"^\s*((?:19|20)\d{2})\b", v)
        if m:
            return int(m.group(1))
    return None


def month_of(v):
    if isinstance(v, str):
        s = v.strip().lower()[:3]
        return MONTHS.get(s)
    return None


def parse_value(v, kind):
    """Return (float or nan, flag). kind: 'nominal' (Rp bn) or 'ratio' (% or fraction).
    Strings such as '9,546 r)' (revised marker) or '94,67 r)' are parsed; flag records it."""
    if is_blank(v):
        return np.nan, ""
    if isinstance(v, (int, float, np.integer, np.floating)):
        return float(v), ""
    s = str(v).strip()
    if s in ("-", "--", "n.a", "na", "n/a"):
        return np.nan, "dash"
    if re.fullmatch(r"-+\s*[rR]?\)?\*?", s):          # '-r', '- r)': revised dash = not available
        return np.nan, "dash"
    rev = bool(re.search(r"[rR]\)?\s*$|\*\)?\s*$", s))
    s2 = re.sub(r"\s*[rR]\)?\s*$|\s*\*\)?\s*$", "", s).replace("\xa0", "").strip()
    s2 = s2.replace(" ", "")
    pct = s2.endswith("%")
    s2 = s2.rstrip("%")
    if not re.fullmatch(r"-?[0-9.,]+", s2):
        return np.nan, "unparsed:" + s[:20]
    if kind in ("ratio", "fraction"):
        if s2.count(",") + s2.count(".") > 1:
            return np.nan, "ambiguous:" + s[:20]
        x = float(s2.replace(",", "."))
        if kind == "fraction" and pct:   # old tables store fractions; a text cell written as '14.06%' is in percent
            x = x / 100.0
    else:  # nominal, Rp bn: ',' is a thousands separator; '.' followed by exactly 3 digits is too
        t = s2.replace(",", "")
        if re.fullmatch(r"-?\d{1,3}(\.\d{3})+", t):
            t = t.replace(".", "")
        x = float(t)
    return x, ("string_revised" if rev else "string")


# --------------------------------------------------------------------------------------------
# block and column-date detection
# --------------------------------------------------------------------------------------------
TITLE_RX = re.compile(r"^\s*[Tt]abel\s*\.?\s*(\d+)\s*\.?\s*([abc])?[\s\.]")


def find_blocks(df, table_no):
    """Rows holding a 'Tabel <n>[a|b].' title. Returns list of (row, letter, title)."""
    out = []
    for i in range(df.shape[0]):
        for j in range(min(4, df.shape[1])):
            v = df.iat[i, j]
            if isinstance(v, str):
                m = TITLE_RX.match(v)
                if m and int(m.group(1)) == table_no:
                    out.append((i, m.group(2), v))
                    break
    return out


def bank_type_of(letter, title):
    ind = title.split("(")[0]
    has_bus, has_uus = "Bank Umum Syariah" in ind, "Unit Usaha Syariah" in ind
    if letter is None:
        bt = "BUS_UUS"
        if not (has_bus and has_uus):
            warn(f"title without a/b letter but not combined: {title[:90]!r}")
    else:
        bt = {"a": "BUS", "b": "UUS"}[letter]
        if (bt == "BUS" and has_uus and not has_bus) or (bt == "UUS" and has_bus and not has_uus):
            raise RuntimeError(f"letter/title mismatch {letter} {title[:80]!r}")
    return bt


def header_rows(df, t):
    for r in range(t + 1, min(t + 6, df.shape[0])):
        ys = [j for j in range(1, df.shape[1]) if year_of(df.iat[r, j]) is not None]
        if len(ys) >= 2:
            mr = r + 1 if r + 1 < df.shape[0] and sum(month_of(df.iat[r + 1, j]) is not None
                                                       for j in range(df.shape[1])) >= 2 else None
            return r, mr
    raise RuntimeError(f"no year header after row {t}")


def add_month(ts, k=1):
    return (ts + pd.DateOffset(months=k)).normalize()


# Column-date overrides for header blocks whose month labels are missing AND shorter than 12 columns, where the
# default rule (span ends in December) is ambiguous. Each entry was verified against an accounting identity
# (see validation output: "Tabel 6a override check").
#   Tabel 6a (BUS) in the 2024-12 and 2025-06 editions: the unlabeled 2022 block has 11 columns (cols 99..109, 0-based);
#   BUS = BUS+UUS (Tabel 6) - UUS (Tabel 6b) identifies them as Jan, Mar, Apr, ..., Dec 2022 (Feb 2022 is absent).
_T6A_2022 = {99: "2022-01", **{100 + k: f"2022-{k + 3:02d}" for k in range(10)}}
OVERRIDES = {
    ("SPS_2025_06.xlsx", "Tabel 6a KegiatanUsaha", 0): _T6A_2022,
    ("SPS_2024_12.xlsx", "Tabel 6a KegiatanUsaha", 0): _T6A_2022,
}


def map_columns(df, merged, yr, mr, tag, override=None):
    """Assign a month (Timestamp, first of month) to every data column of a block.
    Returns (dict col->date, list of duplicate annual cols as (col, dup_of_col), first data col)."""
    ncol = df.shape[1]
    # cells covered by a merged range (other than its top-left cell) are invisible in Excel but may keep a stale
    # cached value (e.g. a ghost 'Des' under a merged annual header); ignore them
    hidden = set()
    for (r0, c0, r1, c1) in merged:
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if (r, c) != (r0, c0):
                    hidden.add((r, c))
    ylab = {j: year_of(df.iat[yr, j]) for j in range(ncol)
            if year_of(df.iat[yr, j]) is not None and (yr, j) not in hidden}
    mlab = {j: month_of(df.iat[mr, j]) for j in range(ncol) if (mr, j) not in hidden} if mr is not None else {}
    mlab = {j: m for j, m in mlab.items() if m is not None}
    # year spans
    span_of = {}
    ycols = sorted(ylab)
    mrng = {(r0, c0): (r1, c1) for (r0, c0, r1, c1) in merged}
    spans = []
    for k, j in enumerate(ycols):
        if (yr, j) in mrng:
            r1, c1 = mrng[(yr, j)]
            a, b = j, c1
        elif merged:  # xlsx: unmerged year label covers itself (and following month-labelled cols until next label)
            nxt = ycols[k + 1] if k + 1 < len(ycols) else ncol
            b = j
            while b + 1 < nxt and (b + 1) in mlab:
                b += 1
            a = j
        else:         # xls without merge info: forward fill until the next year label
            nxt = ycols[k + 1] if k + 1 < len(ycols) else ncol
            last_lab = max([c for c in list(mlab) + ycols if c < nxt] + [j])
            a, b = j, last_lab
        spans.append((a, b, ylab[j]))
        for c in range(a, b + 1):
            span_of[c] = (a, b, ylab[j])
    first = min(ycols)
    last = max([b for a, b, y in spans] + list(mlab))
    dates, dups = {}, []
    prev, prev_col = None, None
    override = {int(k): pd.Timestamp(v + "-01") for k, v in (override or {}).items()}
    ambiguous = set()
    for j in range(first, last + 1):
        sp = span_of.get(j)
        if j in override:
            d = override[j]; how = "override"
        elif j in mlab:
            if sp is None:
                if prev is None:
                    raise RuntimeError(f"{tag}: month label without year at col {j}")
                y = prev.year
            else:
                y = sp[2]
            d = pd.Timestamp(y, mlab[j], 1)
            if prev is not None and d < prev:      # month sequence wrapped inside a year block (e.g. Jan after Des)
                d = pd.Timestamp(d.year + 1, d.month, 1)
            how = "label"
        elif sp is not None:
            a, b, y = sp
            if any(c in mlab for c in range(a, b + 1)):
                # a year span that has month labels elsewhere: unlabeled column inside -> annual/aggregate column
                d = pd.Timestamp(y, 12, 1); how = "annual_in_span"
            elif a == b:
                d = pd.Timestamp(y, 12, 1); how = "annual"
            else:
                L = b - a + 1
                if L > 12:
                    raise RuntimeError(f"{tag}: year span of {L} cols without month labels")
                d = pd.Timestamp(y, 12 - (b - j), 1); how = "span_seq"
                if L < 12 and (a, b) not in ambiguous and j == a:
                    # accept a short unlabeled span only if it continues the preceding month without a gap
                    if prev is None or add_month(prev) != d:
                        ambiguous.add((a, b))
                        warn(f"{tag}: unlabeled {y} block of {L} columns (cols {a}..{b}) does not continue "
                             f"{prev.date() if prev is not None else None}; columns DROPPED (no override)")
                if (a, b) in ambiguous:
                    continue
        else:
            if prev is None:
                continue
            # orphan column: continue the monthly sequence if it holds any data
            col = df.iloc[mr + 1 if mr is not None else yr + 1:, j]
            if col.map(lambda v: not is_blank(v)).sum() == 0:
                continue
            d = add_month(prev); how = "orphan_seq"
        if prev is not None and d == prev:
            dups.append((j, prev_col))
            continue
        if prev is not None and d < prev:
            if d >= MIN_DATE:
                warn(f"{tag}: non-increasing date at col {j}: {d.date()} after {prev.date()} ({how})")
            continue
        if how == "orphan_seq" or how == "span_seq":
            pass
        dates[j] = d
        prev, prev_col = d, j
    return dates, dups, first


def block_rows(df, t, nxt, first_col, mr, yr):
    """Rows of a block after the header with their label text (label columns only)."""
    start = (mr if mr is not None else yr) + 1
    rows = []
    for i in range(start, nxt):
        parts = []
        for j in range(first_col):
            v = df.iat[i, j]
            if not is_blank(v):
                parts.append(str(v).replace("\n", " ").replace("\xa0", " ").strip())
        lab = " || ".join(p for p in parts if p)
        if lab:
            rows.append((i, lab))
    return rows


def norm(s):
    s = s.lower().replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def id_part(lab):
    """Indonesian part of a label: drop leading numbering and the English text after ' / '."""
    s = lab.split(" || ")[-1] if " || " in lab else lab
    s = re.sub(r"\s+", " ", s).strip()
    s = s.split(" / ")[0].split("/ ")[0].strip()
    s = re.sub(r"^([0-9]+|[a-zA-Z]|[ivx]+)[\.\)]\s*", "", s, flags=re.I).strip()
    s = re.sub(r"^-\s*", "", s).strip()
    return s


# --------------------------------------------------------------------------------------------
# generic block extraction
# --------------------------------------------------------------------------------------------
def extract(book, sheet_pat, table_no, mapper, kind, table_label, bank_override=None):
    """Parse all blocks of a table. mapper(rows) -> list of (row, keys dict, id_path).
    Returns long DataFrame with date, bank_type, value, flag + keys + provenance, and diagnostics."""
    sh = book.sheet(sheet_pat)
    df = book.values(sh)
    merged = book.merged.get(sh, [])
    blocks = find_blocks(df, table_no)
    if not blocks:
        raise RuntimeError(f"{book.fname}/{sh}: no block titles for table {table_no}")
    recs, dupchk = [], []
    for k, (t, letter, title) in enumerate(blocks):
        nxt = blocks[k + 1][0] if k + 1 < len(blocks) else df.shape[0]
        bt = bank_override or bank_type_of(letter, title)
        yr, mr = header_rows(df, t)
        tag = f"{book.fname}/{sh}/block@{t}"
        dates, dups, first = map_columns(df, merged, yr, mr, tag, OVERRIDES.get((book.fname, sh, t)))
        rows = block_rows(df, t, nxt, first, mr, yr)
        mapped = mapper(rows)
        # annual columns that differ from their December column: if the December column is a stale copy of
        # November (identical in every mapped row), the annual column carries the true December value
        good_dups = []
        for (j, j0) in dups:
            vj = [parse_value(df.iat[i, j], kind)[0] for (i, _, _) in mapped]
            v0 = [parse_value(df.iat[i, j0], kind)[0] for (i, _, _) in mapped]
            same = all(np.isnan(a) or np.isnan(b) or abs(a - b) < 1e-6 for a, b in zip(vj, v0))
            if same:
                good_dups.append((j, j0)); continue
            pj = [c for c in dates if dates[c] == add_month(dates[j0], -1)]
            if pj:
                vp = [parse_value(df.iat[i, pj[0]], kind)[0] for (i, _, _) in mapped]
                stale = all((np.isnan(a) and np.isnan(b)) or (not np.isnan(a) and not np.isnan(b) and abs(a - b) < 1e-6)
                            for a, b in zip(v0, vp))
            else:
                stale = False
            if stale:
                warn(f"{tag}: December column {j0} ({dates[j0].date()}) repeats November; using annual column {j} instead")
                dates[j] = dates.pop(j0)
            else:
                warn(f"{tag}: annual column {j} differs from December column {j0} ({dates[j0].date()}); "
                     f"December column kept")
                good_dups.append((j, j0))
        dups = good_dups
        # the latest month of an edition is sometimes a placeholder that repeats the previous month in every row
        # (e.g. June 2015 in SPS_2015_06): drop it
        if len(dates) >= 2:
            jl = max(dates, key=lambda c: dates[c])
            jp = [c for c in dates if dates[c] == add_month(dates[jl], -1)]
            if jp:
                vl = [parse_value(df.iat[i, jl], kind)[0] for (i, _, _) in mapped]
                vp = [parse_value(df.iat[i, jp[0]], kind)[0] for (i, _, _) in mapped]
                pairs = [(a, b) for a, b in zip(vl, vp) if not (np.isnan(a) and np.isnan(b))]
                if pairs and sum(abs(b) > 0 for a, b in pairs) >= 3 and \
                        all(not np.isnan(a) and not np.isnan(b) and abs(a - b) < 1e-9 for a, b in pairs):
                    warn(f"{tag}: last month column {jl} ({dates[jl].date()}) repeats {dates[jp[0]].date()} in every "
                         f"row; dropped as a placeholder")
                    dates.pop(jl)
        for (i, keys, idp) in mapped:
            for j, d in dates.items():
                if d < MIN_DATE:
                    continue
                x, flag = parse_value(df.iat[i, j], kind)
                if np.isnan(x) and flag == "":
                    continue
                kk = {a: b for a, b in keys.items() if a != "bank_type"}
                rec = dict(date=d, bank_type=keys.get("bank_type", bt), value=x, flag=flag, label_id=idp, **kk,
                           source_file=book.fname, source_sheet=sh, source_table=table_label,
                           edition=book.edition, cell=f"r{i + 1}c{j + 1}")
                recs.append(rec)
            for (j, j0) in dups:
                a, fa = parse_value(df.iat[i, j], kind); b, fb = parse_value(df.iat[i, j0], kind)
                if not (np.isnan(a) or np.isnan(b)):
                    dupchk.append(abs(a - b))
    out = pd.DataFrame(recs)
    diag = dict(n_dup_cells=len(dupchk), max_dup_gap=(max(dupchk) if dupchk else 0.0))
    return out, diag


# --------------------------------------------------------------------------------------------
# row mappers
# --------------------------------------------------------------------------------------------
UNMAPPED = []

CONTRACT_EN = {
    "profit_sharing": "Profit-sharing financing (total)", "mudharabah": "Mudharabah", "musyarakah": "Musyarakah",
    "other_profit_sharing": "Other profit-sharing financing", "receivables": "Receivables (total)",
    "murabahah": "Murabahah", "qardh": "Qardh", "istishna": "Istishna", "ijarah": "Ijarah incl. leasing receivables (total)",
    "ijarah_syndicated": "Ijarah: syndicated financing", "ijarah_channeling": "Ijarah: financing through channeling",
    "ijarah_executing": "Ijarah: financing through executing", "ijarah_other": "Ijarah: other ijarah",
    "salam": "Salam", "multijasa": "Multijasa", "other": "Other contracts (old format 'Lainnya')",
    "total": "Total financing",
}
CONTRACT_GROUP = {"profit_sharing": "profit_sharing", "mudharabah": "profit_sharing", "musyarakah": "profit_sharing",
                  "other_profit_sharing": "profit_sharing", "receivables": "receivables", "murabahah": "receivables",
                  "qardh": "receivables", "istishna": "receivables", "ijarah": "ijarah", "ijarah_syndicated": "ijarah",
                  "ijarah_channeling": "ijarah", "ijarah_executing": "ijarah", "ijarah_other": "ijarah",
                  "salam": "salam", "multijasa": "other", "other": "other", "total": "total"}
CONTRACT_LEVEL = {"profit_sharing": "group", "receivables": "group", "ijarah": "group", "total": "total",
                  "ijarah_syndicated": "ijarah_component", "ijarah_channeling": "ijarah_component",
                  "ijarah_executing": "ijarah_component", "ijarah_other": "ijarah_component"}


def contract_code(l):
    if l.startswith("total pembiayaan") or l in ("total",) or l.startswith("ii. pembiayaan, piutang"):
        return "total"
    if "bagi hasil lainnya" in l:
        return "other_profit_sharing"
    if "pembiayaan bagi hasil" in l:
        return "profit_sharing"
    if "sindikasi" in l:
        return "ijarah_syndicated"
    if "channeling" in l:
        return "ijarah_channeling"
    if "executing" in l:
        return "ijarah_executing"
    if "sewa lainnya" in l:
        return "ijarah_other"
    if "pembiayaan sewa" in l or "ijarah" in l:
        return "ijarah"
    if re.search(r"(^|\W)piutang\b", l):
        return "receivables"
    for k in ("mudharabah", "musyarakah", "murabahah", "qardh", "salam", "multijasa"):
        if k in l:
            return k
    if "istishna" in l or "i'stishna" in l:
        return "istishna"
    if l.startswith("lainnya"):
        return "other"
    return None


def map_contracts(rows):
    out, last = [], None
    for i, lab in rows:
        l = norm(lab)
        if l.startswith("npf"):
            if last is not None:
                out.append((i, dict(contract_code=last[0], measure="npf"), last[1]))
            continue
        if l.startswith("r)") or l.startswith("1.") and "revisi" in l or "angka-angka" in l or "revisi data" in l:
            continue
        c = contract_code(l)
        if c is None:
            UNMAPPED.append(("contracts", lab)); last = None; continue
        last = (c, id_part(lab))
        out.append((i, dict(contract_code=c, measure="financing"), id_part(lab)))
    return out


TENOR_EN = {"1m": "1 month", "3m": "3 months", "6m": "6 months", "12m": "12 months", "gt12m": "> 12 months", "all": "all tenors"}


def tenor_of(l):
    if re.search(r">\s*12\s*bulan", l):
        return "gt12m"
    for n, c in (("12", "12m"), ("6", "6m"), ("3", "3m"), ("1", "1m")):
        if re.search(r"(^|[^0-9>])" + n + r"\s*bulan", l):
            return c
    return None


def is_note(l):
    return l.startswith("r)") or "angka-angka" in l or "revisi data" in l or l.startswith('"-"') or \
        l.startswith("1) mulai") or l.startswith("1) ||") or l.startswith("ket") or l.startswith("*)") or \
        l.startswith("keterangan")


def map_deposits_new(rows):
    out = []
    grp = instr = ccy = None
    pth = {}
    for i, lab in rows:
        l = norm(lab)
        if is_note(l):
            continue
        ip = id_part(lab)
        ten = tenor_of(l)
        if ten:
            out.append((i, dict(fund_type=grp, instrument="time", currency=ccy, tenor=ten),
                        " > ".join([pth["g"], pth["i"], pth["c"], ip])))
            continue
        if re.search(r"\brupiah\b", l) or "valas" in l:
            ccy = "IDR" if "rupiah" in l else "FX"; pth["c"] = ip
            out.append((i, dict(fund_type=grp, instrument=instr, currency=ccy, tenor="all"),
                        " > ".join([pth["g"], pth["i"], ip])))
            continue
        hit = None
        for k, c in (("giro", "demand"), ("tabungan", "savings"), ("deposito", "time")):
            if k in l:
                hit = c
        if hit and "dana" not in l:
            instr, ccy = hit, None; pth["i"] = ip
            out.append((i, dict(fund_type=grp, instrument=instr, currency="all", tenor="all"),
                        " > ".join([pth["g"], ip])))
            continue
        if "simpanan wadiah" in l:
            grp = "wadiah"
        elif "non profit sharing" in l:
            grp = "investment_non_profit_sharing"
        elif "profit sharing" in l:
            grp = "investment_profit_sharing"
        else:
            UNMAPPED.append(("deposits_new", lab)); continue
        instr = ccy = None; pth = {"g": ip}
        out.append((i, dict(fund_type=grp, instrument="all", currency="all", tenor="all"), ip))
    return out


def map_deposits_old(rows):
    out = []
    instr = None
    for i, lab in rows:
        l = norm(lab)
        if is_note(l):
            continue
        ip = id_part(lab)
        ten = tenor_of(l)
        if ten:
            out.append((i, dict(fund_type="mudharabah", instrument="time", currency="all", tenor=ten),
                        "Deposito iB - Akad Mudharabah > " + ip)); continue
        if l.startswith("total"):
            out.append((i, dict(fund_type="total", instrument="all", currency="all", tenor="all"), ip)); continue
        if "giro" in l:
            out.append((i, dict(fund_type="all_labelled_wadiah", instrument="demand", currency="all", tenor="all"),
                        "Giro iB - Akad Wadiah")); continue
        if "deposito" in l:
            out.append((i, dict(fund_type="mudharabah", instrument="time", currency="all", tenor="all"),
                        "Deposito iB - Akad Mudharabah")); continue
        if "tabungan" in l:
            instr = "savings"
            out.append((i, dict(fund_type="all", instrument="savings", currency="all", tenor="all"), "Tabungan iB")); continue
        if "akad wadiah" in l and instr == "savings":
            out.append((i, dict(fund_type="wadiah", instrument="savings", currency="all", tenor="all"),
                        "Tabungan iB > Akad Wadiah")); continue
        if "akad mudharabah" in l and instr == "savings":
            out.append((i, dict(fund_type="mudharabah", instrument="savings", currency="all", tenor="all"),
                        "Tabungan iB > Akad Mudharabah")); continue
        UNMAPPED.append(("deposits_old", lab))
    return out


def map_rates_new(rows):
    """Tabel 17: section I deposits -> kind 'deposit'; section II financing by contract -> kind 'financing'."""
    out = []
    sec = None
    fund = instr = None; ccy = None; contract = None; base = ""; cbase = ""
    for i, lab in rows:
        l = norm(lab)
        if is_note(l):
            continue
        ip = id_part(lab)
        if l.startswith("i. dana pihak ketiga"):
            sec = "dep"; out.append((i, dict(kind="deposit", fund_type="all", instrument="all", currency="all", tenor="all"),
                                     "Dana Pihak Ketiga")); continue
        if l.startswith("ii. pembiayaan"):
            sec = "fin"; contract = "total"; cbase = "Pembiayaan, Piutang dan Salam"
            out.append((i, dict(kind="financing", contract_code="total", currency="all"), cbase)); continue
        if sec == "dep":
            ten = tenor_of(l)
            if ten:
                out.append((i, dict(kind="deposit", fund_type=fund, instrument=instr, currency=ccy, tenor=ten),
                            f"{base} > {'Rupiah' if ccy == 'IDR' else 'Valas'} > {ip}")); continue
            if re.search(r"\brupiah\b", l) or "valas" in l:
                ccy = "IDR" if "rupiah" in l else "FX"
                out.append((i, dict(kind="deposit", fund_type=fund, instrument=instr, currency=ccy, tenor="all"),
                            f"{base} > {ip}")); continue
            m = re.match(r"^\d\.\s*(giro|tabungan|deposito) ib (wadiah|mudharabah)", l)
            if m:
                instr = {"giro": "demand", "tabungan": "savings", "deposito": "time"}[m.group(1)]
                fund = m.group(2); ccy = None; base = ip
                out.append((i, dict(kind="deposit", fund_type=fund, instrument=instr, currency="all", tenor="all"), ip)); continue
            UNMAPPED.append(("rates_dep", lab)); continue
        if sec == "fin":
            if re.search(r"\brupiah\b", l) or "valas" in l:
                ccy = "IDR" if "rupiah" in l else "FX"
                out.append((i, dict(kind="financing", contract_code=contract, currency=ccy), f"{cbase} > {ip}")); continue
            c = contract_code(l)
            if c is None:
                UNMAPPED.append(("rates_fin", lab)); continue
            contract = c; cbase = ip
            out.append((i, dict(kind="financing", contract_code=c, currency="all"), ip)); continue
        UNMAPPED.append(("rates_pre", lab))
    return out


def map_rates_old(rows):
    out = []
    sec = None
    for i, lab in rows:
        l = norm(lab)
        if is_note(l):
            continue
        ip = id_part(lab)
        if l.startswith("dana pihak ketiga"):
            sec = "dep"; continue
        if l.startswith("pembiayaan"):
            sec = "fin"; continue
        if sec == "dep":
            ten = tenor_of(l)
            if ten:
                out.append((i, dict(kind="deposit", fund_type="mudharabah", instrument="time", currency="unspecified",
                                    tenor=ten), "Deposito iB > " + ip)); continue
            if "giro" in l:
                out.append((i, dict(kind="deposit", fund_type="all", instrument="demand", currency="unspecified",
                                    tenor="all"), "Giro iB")); continue
            if "tabungan" in l:
                out.append((i, dict(kind="deposit", fund_type="all", instrument="savings", currency="unspecified",
                                    tenor="all"), "Tabungan iB")); continue
            if "deposito" in l:
                continue  # header row without values
        if sec == "fin":
            c = contract_code(l.replace("akad ", ""))
            if c:
                out.append((i, dict(kind="financing", contract_code=c, currency="unspecified"), ip)); continue
        UNMAPPED.append(("rates_old", lab))
    return out


USE_EN = {"working_capital": "Working capital", "investment": "Investment", "consumption": "Consumption"}
SIZE_EN = {"all": "all debtor sizes", "msme": "MSME (UMKM)", "non_msme": "non-MSME"}


def map_use_size(rows):
    out = []
    use = size = None; ub = sb = ""
    for i, lab in rows:
        l = norm(lab)
        if is_note(l):
            continue
        ip = id_part(lab)
        if "modal kerja" in l or "investasi" in l or "konsumsi" in l:
            use = "working_capital" if "modal kerja" in l else ("investment" if "investasi" in l else "consumption")
            size = "all"; ub = ip; sb = None
            out.append((i, dict(category_code=use, sub_category="all", currency="all"), ub)); continue
        if re.search(r"\brupiah\b", l) or "valas" in l:
            c = "IDR" if "rupiah" in l else "FX"
            out.append((i, dict(category_code=use, sub_category=size, currency=c),
                        " > ".join([x for x in (ub, sb, ip) if x]))); continue
        if "bukan umkm" in l:
            size = "non_msme"; sb = ip
        elif "umkm" in l:
            size = "msme"; sb = ip
        else:
            UNMAPPED.append(("use_size", lab)); continue
        out.append((i, dict(category_code=use, sub_category=size, currency="all"), f"{ub} > {sb}"))
    return out


SECTORS = [  # (keyword in Indonesian label, code, English label, group)
    ("pertanian", "agriculture", "Agriculture, hunting and forestry", "business"),
    ("perikanan", "fishery", "Fishery", "business"),
    ("pertambangan", "mining", "Mining and quarrying", "business"),
    ("industri pengolahan", "manufacturing", "Manufacturing (processing industry)", "business"),
    ("listrik", "electricity_gas_water", "Electricity, gas and water", "business"),
    ("konstruksi", "construction", "Construction", "business"),
    ("perdagangan", "trade", "Wholesale and retail trade", "business"),
    ("akomodasi", "accommodation_food", "Accommodation and food & beverage", "business"),
    ("transportasi", "transport_storage_communication", "Transportation, warehousing and communication", "business"),
    ("perantara keuangan", "financial_intermediation", "Financial intermediaries", "business"),
    ("real estate", "real_estate_business_services", "Real estate, renting and business services", "business"),
    ("pemerintahan", "public_administration", "Government administration, defence and compulsory social security", "business"),
    ("jasa pendidikan", "education", "Education services", "business"),
    ("jasa kesehatan", "health_social", "Health services and social activities", "business"),
    ("jasa kemasyarakatan", "community_social_personal", "Community, socio-cultural, entertainment and other individual services", "business"),
    ("melayani rumah tangga", "household_employers", "Individual services serving households", "business"),
    ("badan internasional", "international_organisations", "International and other extra-international agencies", "business"),
    ("belum jelas", "not_clearly_defined", "Business activities not clearly defined", "business"),
    ("rumah tinggal", "hh_house", "Households: home ownership", "non_business"),
    ("flat atau apartemen", "hh_apartment", "Households: flat/apartment ownership", "non_business"),
    ("ruko atau rukan", "hh_shophouse", "Households: shop-house/office-house ownership", "non_business"),
    ("kendaraan bermotor", "hh_vehicle", "Households: motor vehicle ownership", "non_business"),
    ("peralatan rumah tangga", "hh_other_goods", "Households: other household equipment (incl. multipurpose loans)", "non_business"),
    ("bukan lapangan usaha lainnya", "non_business_other", "Non-business recipients: others", "non_business"),
]
SECTOR_EN = {c: e for _, c, e, _ in SECTORS}
SECTOR_GRP = {c: g for _, c, _, g in SECTORS}


def map_sector(rows):
    out = []
    sec = None; sb = ""
    for i, lab in rows:
        l = norm(lab)
        if is_note(l):
            continue
        ip = id_part(lab)
        if l.startswith("penerima pembiayaan") or l.startswith("rumah tangga"):
            continue
        if re.search(r"^(a\.|b\.)?\s*(rupiah|valas)", l):
            c = "IDR" if "rupiah" in l else "FX"
            out.append((i, dict(category_code=sec, sub_category=SECTOR_GRP.get(sec), currency=c), f"{sb} > {ip}")); continue
        hit = None
        for kw, code, en, g in SECTORS:
            if kw in l:
                hit = code; break
        if hit is None:
            UNMAPPED.append(("sector", lab)); sec = None; continue
        sec = hit; sb = ip
        out.append((i, dict(category_code=sec, sub_category=SECTOR_GRP[sec], currency="all"), ip))
    return out


def map_t1(rows):
    """Tabel 1a/1b (new): ratios and FDR components."""
    out = []
    ctx = None
    for i, lab in rows:
        l = norm(lab)
        ip = id_part(lab)
        if l.startswith("car (%)"):
            out.append((i, dict(indicator="car_pct", kind="ratio"), ip)); ctx = None; continue
        if l.startswith("roa (%)"):
            out.append((i, dict(indicator="roa_pct", kind="ratio"), ip)); ctx = None; continue
        if l.startswith("npf net (%)"):
            out.append((i, dict(indicator="npf_net_pct_reported", kind="ratio"), ip)); ctx = None; continue
        if l.startswith("npf (%)"):
            out.append((i, dict(indicator="npf_gross_pct_reported", kind="ratio"), ip)); ctx = None; continue
        if l.startswith("fdr (%)"):
            out.append((i, dict(indicator="fdr_pct_reported", kind="ratio"), ip)); ctx = "fdr"; continue
        if l.startswith("bopo (%)"):
            out.append((i, dict(indicator="bopo_pct", kind="ratio"), ip)); ctx = None; continue
        if ctx == "fdr" and "pembiayaan kepada pihak ketiga bukan bank" in l:
            out.append((i, dict(indicator="fdr_financing_nonbank_rp_bn", kind="nominal"), "FDR > " + ip)); continue
        if ctx == "fdr" and "dana pihak ketiga" in l:
            out.append((i, dict(indicator="fdr_dpk_rp_bn", kind="nominal"), "FDR > " + ip)); ctx = None; continue
    return out


def map_t2(rows):
    out = []
    bt = None
    for i, lab in rows:
        l = norm(lab)
        ip = id_part(lab)
        if l.startswith("bank umum syariah"):
            bt = "BUS"; continue
        if l.startswith("unit usaha syariah"):
            bt = "UUS"; continue
        if l.startswith("bank pembiayaan rakyat") or l.startswith("bank perekonomian rakyat"):
            bt = None; continue
        if l.startswith("total aset bus dan uus"):
            out.append((i, dict(indicator="total_assets_rp_bn", bank_type="BUS_UUS"), ip)); continue
        if bt and "total aset" in l:
            out.append((i, dict(indicator="total_assets_rp_bn", bank_type=bt), ip)); continue
        if bt == "BUS" and re.search(r"jumlah bank\b", l) and "konvensional" not in l:
            out.append((i, dict(indicator="number_of_banks", bank_type=bt), ip)); continue
        if bt == "UUS" and "konvensional yang memiliki uus" in l:
            out.append((i, dict(indicator="number_of_banks", bank_type=bt), ip)); continue
    return out


def map_t6(rows):
    out = []
    side = None
    for i, lab in rows:
        l = norm(lab)
        ip = id_part(lab)
        if l.startswith("komponen aset"):
            side = "A"; continue
        if l.startswith("komponen kewajiban"):
            side = "L"; continue
        if side == "L" and re.match(r"^1 \|\| dana pihak ketiga", l):
            out.append((i, dict(indicator="dpk_rp_bn"), ip)); continue
        if side == "A":
            if "pembiayaan bagi hasil kepada pihak ketiga bukan bank" in l:
                out.append((i, dict(indicator="t6_ps_financing_nonbank"), ip)); continue
            if "piutang kepada pihak ketiga bukan bank" in l:
                out.append((i, dict(indicator="t6_receivables_nonbank"), ip)); continue
            if "ijarah" in l and "pihak ketiga bukan bank" in l:
                out.append((i, dict(indicator="t6_ijarah_nonbank"), ip)); continue
            if re.match(r"^11 \|\| salam", l):
                out.append((i, dict(indicator="t6_salam"), ip)); continue
    return out


def map_old_t6(rows):
    out = []
    side = None
    for i, lab in rows:
        l = norm(lab)
        ip = id_part(lab)
        if l.startswith("aktiva"):
            side = "A"; continue
        if l.startswith("pasiva"):
            side = "L"; continue
        if l.startswith("total aktiva"):
            out.append((i, dict(indicator="total_assets_rp_bn"), ip)); continue
        if side == "A" and re.match(r"^5 \|\| pembiayaan$", l):
            out.append((i, dict(indicator="old_t6_financing_rp_bn"), ip)); continue
        if side == "L" and re.match(r"^1 \|\| dana pihak ketiga", l):
            out.append((i, dict(indicator="old_t6_dpk_rp_bn"), ip)); continue
    return out


def map_old_t38(rows):
    out = []
    for i, lab in rows:
        l = norm(lab)
        ip = id_part(lab)
        for k, ind in (("car", "car_pct"), ("roa", "roa_pct"), ("npf", "npf_gross_pct_reported"),
                       ("fdr", "fdr_pct_reported"), ("bopo", "bopo_pct")):
            if re.match(r"^\d \|\| " + k + r"\b", l):
                out.append((i, dict(indicator=ind, kind="ratio"), ip))
    return out


def map_old_t26(rows):
    """Old Tabel 26 (financing by collectibility, BUS+UUS): 'Non Lancar' (= NPF, coll. 3-5) and 'Total Pembiayaan'."""
    out = []
    codes = {"non lancar": "old_t26_npf_rp_bn", "total pembiayaan": "old_t26_financing_rp_bn",
             "lancar": "old_t26_lancar", "- lancar": "old_t26_l_lancar", "- dalam perhatian khusus": "old_t26_l_dpk",
             "- kurang lancar": "old_t26_nl_kl", "- diragukan": "old_t26_nl_d", "- macet": "old_t26_nl_m"}
    for i, lab in rows:
        l = norm(lab)
        if l in codes:
            out.append((i, dict(indicator=codes[l]), lab))
    return out


# --------------------------------------------------------------------------------------------
# main build
# --------------------------------------------------------------------------------------------
def qflag(flag):
    f = str(flag) if flag is not None and not (isinstance(flag, float) and np.isnan(flag)) else ""
    if f.startswith("string"):
        return "parsed_from_text"
    return f


def combine(frames, keys):
    """Stack candidates from all editions, keep the latest edition for each key+date; report revisions."""
    df = pd.concat([f for f in frames if f is not None and len(f)], ignore_index=True)
    df = df.sort_values("edition", ascending=False, kind="stable")
    kk = ["date", "bank_type"] + keys
    best = df.drop_duplicates(kk, keep="first").copy()
    # revision diagnostics: compare each other edition against the chosen value
    m = df.merge(best[kk + ["value", "edition"]], on=kk, suffixes=("", "_best"))
    m = m[m["edition"] != m["edition_best"]]
    m["period"] = np.where(m["date"] < NEW_FORMAT_START, "a", "b")
    rev = []
    for (e, eb, _), g in m.groupby(["edition", "edition_best", "period"]):
        d = (g["value"] - g["value_best"]).abs()
        worst = g.loc[d.idxmax()] if d.max() > 1e-6 else None
        rev.append(dict(edition=e, vs=eb, n_overlap=len(g), n_diff=int((d > 1e-6).sum()),
                        max_abs_diff=float(d.max()), date_min=g["date"].min().date(), date_max=g["date"].max().date(),
                        worst=("" if worst is None else f" (largest at {worst['date']:%Y-%m} {worst['bank_type']} "
                               f"{str(worst['label_id'])[:40]!r})")))
    return best, pd.DataFrame(rev)


def coverage(df, by):
    out = []
    for k, g in df.groupby(by):
        ds = sorted(g["date"].unique())
        full = pd.date_range(ds[0], ds[-1], freq="MS")
        missing = sorted(set(full) - set(ds))
        out.append((k, pd.Timestamp(ds[0]).date(), pd.Timestamp(ds[-1]).date(), len(ds), missing))
    return out


def fmt_missing(missing):
    if not missing:
        return "none"
    runs, start, prev = [], missing[0], missing[0]
    for d in missing[1:]:
        if d == add_month(prev):
            prev = d
        else:
            runs.append((start, prev)); start = prev = d
    runs.append((start, prev))
    return ", ".join(f"{a:%Y-%m}" if a == b else f"{a:%Y-%m}..{b:%Y-%m}" for a, b in runs)


# --------------------------------------------------------------------------------------------
# corrections of source errors. Each one was found by an accounting identity (BUS + UUS = BUS+UUS block, components
# = total) and is applied to the value kept from the latest edition; every corrected cell is flagged and the
# published value is kept in the note. Rules: diff = (BUS+UUS block) - (other bank type); sum = BUS + UUS;
# scale1000 = published value x 1000 (decimal-separator error); missing = set to NaN.
# --------------------------------------------------------------------------------------------
FIXES_CONTRACTS = [
    dict(date="2021-10", bank_type="UUS", rule="diff",
         match=dict(currency="IDR", measure="financing", contract_code=["murabahah", "receivables", "total"]),
         why="Oct-2021 Tabel 12b (UUS, Rupiah): murabahah, receivables and total are 1,370.9 below Tabel 12 minus "
             "Tabel 12a, which would put UUS foreign-currency murabahah (Tabel 11b - 12b) at 1,540 against ~170 in "
             "Sep and Nov; replaced by Tabel 12 minus Tabel 12a"),
]
FIXES_DEPOSITS = [
    dict(date="2017-11", bank_type="BUS_UUS", rule="sum",
         match=dict(fund_type="investment_non_profit_sharing", instrument="time", currency="IDR", tenor="all"),
         why="Nov-2017 Tabel 22 Rupiah time deposits published as 80.069 (a misplaced figure; Tabel 17 shows the same "
             "80.07 as a 3-month rate); replaced by Tabel 22a + 22b, which equals the sum of its tenor rows"),
    dict(date="2020-06", bank_type="BUS_UUS", rule="scale1000",
         match=dict(fund_type="investment_non_profit_sharing", instrument="time", currency="FX", tenor="1m"),
         why="Jun-2020 Tabel 22 FX 1-month time deposits published as 11.690 (decimal-separator error); x1000 "
             "restores FX tenors = FX total and BUS + UUS = BUS+UUS"),
    dict(date="2020-06", bank_type="UUS", rule="scale1000",
         match=dict(fund_type="investment_non_profit_sharing", instrument="time", currency="FX", tenor="1m"),
         why="Jun-2020 Tabel 22b FX 1-month time deposits published as 5.253 (decimal-separator error); x1000 "
             "restores FX tenors = FX total"),
    dict(date="2022-05", bank_type="BUS_UUS", rule="sum",
         match=dict(fund_type="investment_non_profit_sharing", instrument="time", currency="FX", tenor="1m"),
         why="May-2022 Tabel 22 FX 1-month time deposits (13,802.5) exceed Tabel 22a + 22b (10,739.2) by 3,063.2 and "
             "break FX tenors = FX total; replaced by Tabel 22a + 22b"),
    dict(date="2019-07", bank_type="UUS", rule="diff", match=dict(),
         why="Jul-2019 Tabel 22b (UUS) repeats the June-2019 column in every row and disagrees with Tabel 6b DPK; "
             "replaced by Tabel 22 minus Tabel 22a"),
    dict(date="2024-12", bank_type="UUS", rule="diff",
         match=dict(fund_type="investment_non_profit_sharing", instrument="time", currency="IDR", tenor=["1m", "6m"]),
         why="Dec-2024 Tabel 22b Rupiah time deposits: the 6-month row repeats the 3-month row (31,950.1) and the "
             "1-month row is lower by the same 20,549.2; replaced by Tabel 22 minus Tabel 22a"),
]
LEAK_2017_11 = ("Nov-2017: the BUS FDR (80.069046%, Tabel 1a) is pasted into this BUS+UUS cell (it also appears in "
                "Tabel 17, 18, 19 and 22); set to missing")
FIXES_RETURNS = [
    dict(date="2017-11", bank_type="BUS_UUS", rule="missing",
         match=dict(fund_type="mudharabah", instrument="time", currency="IDR", tenor="3m"),
         why=LEAK_2017_11 + " (BUS 6.31, UUS 5.49)"),
] + [
    dict(date=d, bank_type="BUS_UUS", rule="missing",
         match=dict(fund_type="mudharabah", instrument="time", currency="unspecified", tenor="gt12m"),
         why="old Tabel 36 >12-month rate between 33.7% and 50.7% in Jan-2011..Jun-2012 (other tenors 4-9%; the "
             ">12-month stock is only Rp 5-50 bn); implausible, set to missing")
    for d in ["2011-01", "2011-02", "2011-03", "2011-04", "2011-06", "2011-07", "2011-08", "2011-09", "2011-10",
              "2011-11", "2011-12", "2012-01", "2012-02", "2012-03", "2012-04", "2012-05", "2012-06"]
]
FIXES_MARGINS = [
    dict(date="2017-11", bank_type="BUS_UUS", rule="missing",
         match=dict(dimension="sector", category_code="construction", currency="all"), why=LEAK_2017_11),
    dict(date="2017-11", bank_type="BUS_UUS", rule="missing",
         match=dict(dimension="use_size", category_code="consumption", currency="FX"), why=LEAK_2017_11),
    dict(date="2010-04", bank_type="BUS_UUS", rule="missing",
         match=dict(dimension="contract", category_code=["mudharabah", "murabahah"], currency="unspecified"),
         why="old Tabel 36 Apr-2010 rate of 77-85% (11.4-17.9% in the months around it); implausible, set to missing"),
    dict(date="2010-05", bank_type="BUS_UUS", rule="missing",
         match=dict(dimension="contract", category_code="murabahah", currency="unspecified"),
         why="old Tabel 36 May-2010 murabahah rate of 80.7% (15-16% around it); implausible, set to missing"),
    dict(date="2010-06", bank_type="BUS_UUS", rule="missing",
         match=dict(dimension="contract", category_code=["murabahah", "ijarah"], currency="unspecified"),
         why="old Tabel 36 Jun-2010: murabahah 73.3% and ijarah 121.1% (15-16% and 0.5-0.6% around it); "
             "implausible, set to missing"),
]
FIX_LOG = []


def apply_fixes(df, fixes, keys, name):
    df = df.copy()
    for fx in fixes:
        d = pd.Timestamp(fx["date"] + "-01")
        sel = (df["date"] == d) & (df["bank_type"] == fx["bank_type"])
        for k, v in fx["match"].items():
            sel &= df[k].isin(v if isinstance(v, list) else [v])
        if not sel.any():
            raise RuntimeError(f"fix matched nothing: {name} {fx}")
        same = df[df["date"] == d].set_index(["bank_type"] + keys)["value"]
        for i in df.index[sel]:
            kk = tuple(df.at[i, k] for k in keys)
            old = df.at[i, "value"]
            if fx["rule"] == "diff":
                other = "BUS" if fx["bank_type"] == "UUS" else "UUS"
                new = same.get(("BUS_UUS",) + kk, np.nan) - same.get((other,) + kk, np.nan)
            elif fx["rule"] == "sum":
                new = same.get(("BUS",) + kk, np.nan) + same.get(("UUS",) + kk, np.nan)
            elif fx["rule"] == "scale1000":
                new = old * 1000.0
            else:
                new = np.nan
            if fx["rule"] != "missing" and np.isnan(new):
                if not fx["match"]:
                    warn(f"fix {name} {fx['date']} {fx['bank_type']} {kk}: not computable (a block value is blank); kept")
                    continue
                raise RuntimeError(f"fix could not be computed: {name} {fx['date']} {kk}")
            if fx["rule"] == "diff" and abs(new - old) < 1e-6:
                continue      # cell already consistent (possible when a whole column is replaced)
            df.at[i, "value"] = new
            df.at[i, "flag"] = "corrected:" + fx["rule"]
            df.at[i, "fixnote"] = f"published {old:,.3f}; {fx['why']}"
            FIX_LOG.append((name, fx["date"], fx["bank_type"], kk, old, new, fx["rule"]))
    return df


def main():
    books = []
    for f, e, fmt in EDITIONS:
        if (RAW / f).exists():
            books.append(Book(f, e, fmt))
            print(f"edition loaded: {f}")
        else:
            print(f"edition not present (skipped): {f}")
    diags = {}
    C, D, R, M, A = [], [], [], [], []
    for b in books:
        if b.fmt == "new":
            for tno, pat, ccy in ((11, r"^\s*tabel\s*11\b", "all"), (12, r"^\s*tabel\s*12\b", "IDR")):
                x, dg = extract(b, pat, tno, map_contracts, "nominal", f"Tabel {tno}")
                x["currency"] = ccy; C.append(x); diags[(b.fname, f"T{tno}")] = dg
            x, dg = extract(b, r"^\s*tabel\s*22\b", 22, map_deposits_new, "nominal", "Tabel 22")
            D.append(x); diags[(b.fname, "T22")] = dg
            x, dg = extract(b, r"^\s*tabel\s*17\b", 17, map_rates_new, "ratio", "Tabel 17")
            R.append(x[x["kind"] == "deposit"].drop(columns=["contract_code"], errors="ignore"))
            fin = x[x["kind"] == "financing"].copy()
            fin["dimension"] = "contract"; fin["category_code"] = fin["contract_code"]
            fin["sub_category"] = fin["contract_code"].map(CONTRACT_GROUP)
            M.append(fin); diags[(b.fname, "T17")] = dg
            x, dg = extract(b, r"^\s*tabel\s*18\b", 18, map_use_size, "ratio", "Tabel 18")
            x["dimension"] = "use_size"; M.append(x); diags[(b.fname, "T18")] = dg
            x, dg = extract(b, r"^\s*tabel\s*19\b", 19, map_sector, "ratio", "Tabel 19")
            x["dimension"] = "sector"; M.append(x); diags[(b.fname, "T19")] = dg
            # aggregates
            if b.edition != "2018-12":   # Tabel 1 of the 2018 edition is laid out differently (no 1a/1b blocks)
                x, dg = extract(b, r"^\s*tabel\s*1\b", 1, map_t1, "ratio", "Tabel 1")
                # nominal rows must be re-parsed as nominal
                sh = b.sheet(r"^\s*tabel\s*1\b"); dfv = b.values(sh)
                nm = x["indicator"].str.endswith("_rp_bn")
                for idx in x.index[nm]:
                    r_, c_ = [int(t) for t in re.findall(r"\d+", x.at[idx, "cell"])]
                    x.at[idx, "value"], x.at[idx, "flag"] = parse_value(dfv.iat[r_ - 1, c_ - 1], "nominal")
                A.append(x); diags[(b.fname, "T1")] = dg
            x, dg = extract(b, r"^\s*tabel\s*2\b", 2, map_t2, "nominal", "Tabel 2", bank_override="TMP")
            A.append(x); diags[(b.fname, "T2")] = dg
            for pat, bt in ((r"^\s*tabel\s*6\s", "BUS_UUS"), (r"^\s*tabel\s*6a\b", "BUS"), (r"^\s*tabel\s*6b\b", "UUS")):
                x, dg = extract(b, pat, 6, map_t6, "nominal", "Tabel 6" + {"BUS_UUS": "", "BUS": "a", "UUS": "b"}[bt],
                                bank_override=bt)
                A.append(x); diags[(b.fname, "T6" + bt)] = dg
        else:
            x, dg = extract(b, r"^\s*tabel\s*18\b", 18, map_contracts, "nominal", "Tabel 18 (old)", bank_override="BUS_UUS")
            x["currency"] = "all"; C.append(x); diags[(b.fname, "T18old")] = dg
            x, dg = extract(b, r"^\s*tabel\s*14\b", 14, map_deposits_old, "nominal", "Tabel 14 (old)", bank_override="BUS_UUS")
            D.append(x); diags[(b.fname, "T14old")] = dg
            x, dg = extract(b, r"^\s*tabel\s*36\b", 36, map_rates_old, "fraction", "Tabel 36 (old)", bank_override="BUS_UUS")
            x["value"] = x["value"] * 100.0   # fractions -> percent
            R.append(x[x["kind"] == "deposit"].drop(columns=["contract_code"], errors="ignore"))
            fin = x[x["kind"] == "financing"].copy()
            fin["dimension"] = "contract"; fin["category_code"] = fin["contract_code"]
            fin["sub_category"] = fin["contract_code"].map(CONTRACT_GROUP)
            M.append(fin); diags[(b.fname, "T36old")] = dg
            x, dg = extract(b, r"^\s*tabel\s*6\s", 6, map_old_t6, "nominal", "Tabel 6 (old)", bank_override="BUS_UUS")
            A.append(x); diags[(b.fname, "T6old")] = dg
            x, dg = extract(b, r"^\s*tabel\s*38\b", 38, map_old_t38, "fraction", "Tabel 38 (old)", bank_override="BUS_UUS")
            x["value"] = x["value"] * 100.0
            x.loc[x["indicator"] == "car_pct", "bank_type"] = "BUS"   # footnote 1): CAR (and ROE) BUS only
            A.append(x); diags[(b.fname, "T38old")] = dg
            x, dg = extract(b, r"^\s*tabel\s*26\b", 26, map_old_t26, "nominal", "Tabel 26 (old)", bank_override="BUS_UUS")
            A.append(x); diags[(b.fname, "T26old")] = dg

    if UNMAPPED:
        print("\nUNMAPPED LABELS (ignored):")
        for k, lab in sorted(set(UNMAPPED)):
            print(f"  [{k}] {lab[:110]}")

    # old-format values for months the new format also covers: kept aside for the overlap validation only
    OVL = {}
    for name, frames in (("contracts", C), ("deposits", D), ("returns", R), ("margins", M), ("aggregates", A)):
        z = pd.concat([f for f in frames if f is not None and len(f)], ignore_index=True)
        OVL[name] = z[z["edition"].isin(OLD_EDITIONS) & (z["date"] >= NEW_FORMAT_START)].copy()

    # ---------------------------------------------------------------- contracts
    con, rev_c = combine(C, ["contract_code", "measure", "currency"])
    # old format is used only before the new format starts (the new format supersedes it from 2014-06)
    con = con[~(con["edition"].isin(OLD_EDITIONS) & (con["date"] >= NEW_FORMAT_START))]
    con["fixnote"] = ""
    con = apply_fixes(con, FIXES_CONTRACTS, ["contract_code", "measure", "currency"], "contracts")
    con["cellref"] = con["measure"].str[:3] + ":" + con["cell"]
    conw = con.pivot_table(index=["date", "bank_type", "currency", "contract_code"], columns="measure",
                           values="value", aggfunc="first").reset_index()
    meta = con.drop_duplicates(["date", "bank_type", "currency", "contract_code"]).set_index(
        ["date", "bank_type", "currency", "contract_code"])
    conw = conw.join(meta[["label_id", "source_file", "source_sheet", "source_table", "flag"]],
                     on=["date", "bank_type", "currency", "contract_code"])
    conw = conw.rename(columns={"financing": "financing_rp_bn", "npf": "npf_rp_bn"})
    conw["contract_group"] = conw["contract_code"].map(CONTRACT_GROUP)
    conw["level"] = conw["contract_code"].map(CONTRACT_LEVEL).fillna("contract")
    conw["label_en"] = conw["contract_code"].map(CONTRACT_EN)
    grpk = ["date", "bank_type", "currency", "contract_code"]
    fx = con.groupby(grpk)["fixnote"].agg(lambda x: " | ".join(v for v in x if v))
    cells = con.groupby(grpk)["cellref"].agg(lambda x: ";".join(sorted(x)))
    conw["source_cell"] = [cells.get(k, "") for k in zip(*[conw[c] for c in grpk])]
    base = np.where(conw["source_table"].str.contains("old"),
                    "old SPS format (BUS+UUS only, no NPF by contract)", "")
    fxn = np.array([fx.get(k, "") for k in zip(*[conw[c] for c in grpk])], dtype=object)
    conw["note"] = [" | ".join(s for s in (a, b) if s) for a, b in zip(base, fxn)]
    oldmus = conw["source_table"].str.contains("old") & (conw["contract_code"] == "musyarakah")
    conw.loc[oldmus, "note"] = conw.loc[oldmus, "note"] + (
        "; old 'Akad Musyarakah' = new musyarakah + other profit-sharing financing (overlap 2014-06..2015-05)")
    old_mar12 = (conw["date"] == pd.Timestamp("2012-03-01")) & (conw["contract_code"] == "total")
    conw.loc[old_mar12, "note"] = conw.loc[old_mar12, "note"] + (
        " | Mar-2012: old Tabel 18 (= Tabel 6 'Pembiayaan') total 104,238.6 disagrees with Tabels 20/22/26 (109,115.7); "
        "Tabel 18 kept because its contract rows add up to it")
    qf = con.assign(q=con["flag"].map(qflag)).groupby(grpk)["q"].agg(
        lambda x: ";".join(sorted({v for v in x if v})))
    conw["quality_flag"] = [qf.get(k, "") for k in zip(conw["date"], conw["bank_type"], conw["currency"], conw["contract_code"])]
    contracts = conw[["date", "bank_type", "currency", "contract_code", "contract_group", "level", "label_id", "label_en",
                      "financing_rp_bn", "npf_rp_bn", "source_file", "source_sheet", "source_table", "source_cell",
                      "quality_flag", "note"]]
    contracts = contracts.sort_values(["currency", "bank_type", "contract_code", "date"]).reset_index(drop=True)

    # ---------------------------------------------------------------- deposits
    dep, rev_d = combine(D, ["fund_type", "instrument", "currency", "tenor"])
    dep = dep[~(dep["edition"].isin(OLD_EDITIONS) & (dep["date"] >= NEW_FORMAT_START))]
    dep["fixnote"] = ""
    dep = apply_fixes(dep, FIXES_DEPOSITS, ["fund_type", "instrument", "currency", "tenor"], "deposits")
    dep["series"] = "reported"
    dep["quality_flag"] = dep["flag"].map(qflag)
    dep["note"] = dep["fixnote"]
    # (a) tenor rows published as zeros although the currency row is positive -> placeholders, set to missing
    tm = (dep["instrument"] == "time") & dep["currency"].isin(["IDR", "FX"]) & ~dep["edition"].isin(OLD_EDITIONS)
    for (d, bt, fu, cc), g in dep[tm].groupby(["date", "bank_type", "fund_type", "currency"]):
        ten = g[g["tenor"] != "all"]; top = g[g["tenor"] == "all"]["value"]
        if len(ten) and ten["value"].abs().sum() == 0 and len(top) and top.iloc[0] > 0:
            dep.loc[ten.index, "note"] = (f"published as 0 although the {cc} time-deposit total is "
                                          f"{top.iloc[0]:,.1f}; treated as not reported")
            dep.loc[ten.index, "value"] = np.nan
            dep.loc[ten.index, "quality_flag"] = "zero_placeholder_set_missing"
        # (b) currency total implausibly small relative to its own tenor rows (misplaced cell)
        ts = ten["value"].sum(min_count=1)
        if len(top) and not np.isnan(ts) and ts > 1000 and top.iloc[0] < 0.01 * ts:
            i0 = top.index[0]
            dep.loc[i0, "note"] = (f"published value {top.iloc[0]:,.3f} is implausible (its tenor rows sum to "
                                   f"{ts:,.1f}); set to missing")
            dep.loc[i0, "value"] = np.nan
            dep.loc[i0, "quality_flag"] = "implausible_set_missing"
    dep = dep[~(dep["value"].isna() & (dep["quality_flag"] == ""))]
    # harmonised series (both formats)
    H = []
    new = dep[~dep["edition"].isin(OLD_EDITIONS)]
    old = dep[dep["edition"].isin(OLD_EDITIONS)]

    def hsum(g, cond, code, fund, instr, tenor, lab_id, n):
        # all n components must be present (no partial sums)
        gg = g[cond(g)]
        s = gg.groupby(["date", "bank_type"])["value"].agg(["sum", "count"]).reset_index()
        q = gg.groupby(["date", "bank_type"])["quality_flag"].agg(
            lambda x: ("component_" + ";".join(sorted({v for v in x if v}))) if any(v for v in x) else "")
        s = s.merge(q.rename("quality_flag").reset_index(), on=["date", "bank_type"], how="left")
        s = s[s["count"] == n].rename(columns={"sum": "value"})
        s["fund_type"], s["instrument"], s["currency"], s["tenor"] = fund, instr, "all", tenor
        s["label_id"] = lab_id; s["series"] = "harmonised"; s["hcode"] = code
        return s

    fnew = lambda g: g["fund_type"].isin(["wadiah", "investment_non_profit_sharing", "investment_profit_sharing"])
    mud = ["investment_non_profit_sharing", "investment_profit_sharing"]
    H += [
        hsum(new, lambda g: fnew(g) & (g.instrument == "all"), "h_total", "total", "all", "all",
             "Total DPK (jumlah Dana Simpanan Wadiah + Dana Investasi Non Profit Sharing + Dana Investasi Profit Sharing)", 3),
        hsum(new, lambda g: fnew(g) & (g.instrument == "demand") & (g.currency == "all"), "h_demand", "all", "demand", "all",
             "Giro (semua akad)", 3),
        hsum(new, lambda g: (g.fund_type == "wadiah") & (g.instrument == "demand") & (g.currency == "all"), "h_demand_w",
             "wadiah", "demand", "all", "Giro Wadiah", 1),
        hsum(new, lambda g: g.fund_type.isin(mud) & (g.instrument == "demand") & (g.currency == "all"), "h_demand_m",
             "mudharabah", "demand", "all", "Giro Mudharabah (Dana Investasi Non Profit Sharing + Profit Sharing)", 2),
        hsum(new, lambda g: fnew(g) & (g.instrument == "savings") & (g.currency == "all"), "h_sav", "all", "savings", "all",
             "Tabungan (semua akad)", 3),
        hsum(new, lambda g: (g.fund_type == "wadiah") & (g.instrument == "savings") & (g.currency == "all"), "h_sav_w",
             "wadiah", "savings", "all", "Tabungan Wadiah", 1),
        hsum(new, lambda g: g.fund_type.isin(mud) & (g.instrument == "savings") & (g.currency == "all"), "h_sav_m",
             "mudharabah", "savings", "all", "Tabungan Mudharabah (Dana Investasi Non Profit Sharing + Profit Sharing)", 2),
        hsum(new, lambda g: g.fund_type.isin(mud) & (g.instrument == "time") & (g.currency == "all") & (g.tenor == "all"),
             "h_time", "mudharabah", "time", "all", "Deposito Mudharabah (Dana Investasi Non Profit Sharing + Profit Sharing)", 2),
    ]
    for t in ("1m", "3m", "6m", "12m", "gt12m"):
        H.append(hsum(new, lambda g, t=t: g.fund_type.isin(mud) & (g.instrument == "time") & g.currency.isin(["IDR", "FX"])
                      & (g.tenor == t), "h_time_" + t, "mudharabah", "time", t,
                      f"Deposito Mudharabah {TENOR_EN[t]} (Rupiah + Valas, Non Profit Sharing + Profit Sharing)", 4))
    # old format equivalents
    omap = [(lambda g: g.fund_type == "total", "h_total", "total", "all", "all"),
            (lambda g: g.fund_type == "all_labelled_wadiah", "h_demand", "all", "demand", "all"),
            (lambda g: (g.fund_type == "all") & (g.instrument == "savings"), "h_sav", "all", "savings", "all"),
            (lambda g: (g.fund_type == "wadiah") & (g.instrument == "savings"), "h_sav_w", "wadiah", "savings", "all"),
            (lambda g: (g.fund_type == "mudharabah") & (g.instrument == "savings"), "h_sav_m", "mudharabah", "savings", "all"),
            (lambda g: (g.fund_type == "mudharabah") & (g.instrument == "time") & (g.tenor == "all"), "h_time", "mudharabah", "time", "all")]
    omap += [(lambda g, t=t: (g.fund_type == "mudharabah") & (g.instrument == "time") & (g.tenor == t), "h_time_" + t,
              "mudharabah", "time", t) for t in ("1m", "3m", "6m", "12m", "gt12m")]
    for cond, code, fund, instr, ten in omap:
        s = old[cond(old)].copy()
        s = s[["date", "bank_type", "value", "label_id", "quality_flag", "source_file", "cell", "note"]].assign(
            fund_type=fund, instrument=instr, currency="all", tenor=ten, series="harmonised", hcode=code, count=1)
        H.append(s)
    hh = pd.concat(H, ignore_index=True)
    hh["source_sheet"] = np.where(hh["date"] < NEW_FORMAT_START, "tabel 14 Komposisi DPK", "Tabel 22-22a-22b Komposisi DPK")
    hh["cell"] = np.where(hh["date"] < NEW_FORMAT_START, hh["cell"], "sum of reported rows")
    hh["source_table"] = np.where(hh["date"] < NEW_FORMAT_START, "Tabel 14 (old)", "Tabel 22 (sum of reported rows)")
    # attach the edition actually used for new-format harmonised rows
    srcmap = new.groupby(["date", "bank_type"])["source_file"].agg(lambda s: "+".join(sorted(set(s))))
    sel = hh["date"] >= NEW_FORMAT_START
    hh.loc[sel, "source_file"] = [srcmap.get((d, bt), "") for d, bt in zip(hh.loc[sel, "date"], hh.loc[sel, "bank_type"])]
    hh["note"] = hh["note"].fillna("")
    # new-format harmonised rows built from corrected components carry the correction notes
    fixed = new[new["fixnote"] != ""]
    for (d, bt), g in fixed.groupby(["date", "bank_type"]):
        sel = (hh["date"] == d) & (hh["bank_type"] == bt) & hh["quality_flag"].fillna("").str.contains("corrected")
        hh.loc[sel, "note"] = "built from corrected component(s): " + " | ".join(sorted(set(g["fixnote"])))[:400]
    hh.loc[(hh["hcode"] == "h_demand") & (hh["date"] < NEW_FORMAT_START), "note"] = \
        "old row 'Giro iB - Akad Wadiah' = all demand deposits (wadiah + mudharabah); see overlap check in the data note"
    FUND_EN = {"wadiah": "Wadiah", "investment_non_profit_sharing": "Non-profit-sharing investment fund (mudharabah)",
               "investment_profit_sharing": "Profit-sharing investment fund (mudharabah)", "total": "Total DPK",
               "all": "all contracts", "mudharabah": "Mudharabah", "all_labelled_wadiah": "all contracts (old row labelled Wadiah)"}
    INSTR_EN = {"all": "all instruments", "demand": "demand deposits (giro)", "savings": "savings (tabungan)",
                "time": "time deposits (deposito)"}
    CCY_EN = {"all": "all currencies", "IDR": "Rupiah", "FX": "foreign currency", "unspecified": "currency not specified"}

    def dep_en(r):
        parts = [FUND_EN.get(r["fund_type"], r["fund_type"])]
        if r["instrument"] != "all": parts.append(INSTR_EN[r["instrument"]])
        if r["currency"] != "all": parts.append(CCY_EN[r["currency"]])
        if r["tenor"] != "all": parts.append(TENOR_EN[r["tenor"]])
        return " - ".join(parts)

    dep["note"] = np.where(dep["fund_type"] == "all_labelled_wadiah",
                           "old row 'Giro iB - Akad Wadiah' includes mudharabah demand deposits", dep["note"])
    jan25 = ((dep["date"] == pd.Timestamp("2025-01-01")) & (dep["instrument"] == "time") & (dep["currency"] == "IDR")
             & (dep["tenor"] == "all") & (dep["fund_type"] == "investment_non_profit_sharing"))
    dep.loc[jan25, "note"] = ("Jan-2025: the published Rupiah time-deposit row equals the sum of the 1-12 month rows; "
                              "the >12 month row is not included in it. Kept as published")
    deposits = pd.concat([dep.assign(hcode=""), hh], ignore_index=True)
    deposits["label_en"] = deposits.apply(dep_en, axis=1)
    deposits["series_code"] = np.where(deposits["series"] == "harmonised", deposits["hcode"], "")
    deposits = deposits.rename(columns={"value": "deposits_rp_bn"})
    deposits = deposits.rename(columns={"cell": "source_cell"})
    deposits = deposits[["date", "bank_type", "series", "series_code", "fund_type", "instrument", "currency", "tenor",
                         "label_id", "label_en", "deposits_rp_bn", "source_file", "source_sheet", "source_table",
                         "source_cell", "quality_flag", "note"]]
    deposits = deposits.sort_values(["series", "bank_type", "series_code", "fund_type", "instrument", "currency", "tenor",
                                     "date"]).reset_index(drop=True)

    # ---------------------------------------------------------------- deposit returns
    ret, rev_r = combine(R, ["fund_type", "instrument", "currency", "tenor"])
    ret = ret[~(ret["edition"].isin(OLD_EDITIONS) & (ret["date"] >= NEW_FORMAT_START))]
    ret["fixnote"] = ""
    ret = apply_fixes(ret, FIXES_RETURNS, ["fund_type", "instrument", "currency", "tenor"], "returns")
    ret["label_en"] = ret.apply(lambda r: dep_en(r) if r["fund_type"] != "all" or r["instrument"] != "all"
                                else "All third-party funds (DPK)", axis=1)
    ret["note"] = np.where(ret["source_table"].str.contains("old"),
                           "old SPS format (Tabel 36): giro/tabungan not split by contract; currency not stated (time "
                           "deposit rates track the deposit-weighted Rupiah+FX average of Tabel 17); level break at "
                           "2014-06 (see data note)", "")
    ret["note"] = [" | ".join(s for s in (a, b) if s) for a, b in zip(ret["note"], ret["fixnote"])]
    ret["quality_flag"] = ret["flag"].map(qflag)
    for cond, lab in ((ret["value"] > 30, "outlier_gt30pct"), (ret["value"] == 0, "zero_published")):
        ret.loc[cond, "quality_flag"] = (ret.loc[cond, "quality_flag"] + ";" + lab).str.strip(";")
    returns = ret.rename(columns={"value": "rate_pct", "cell": "source_cell"})[
        ["date", "bank_type", "fund_type", "instrument", "currency", "tenor", "label_id", "label_en", "rate_pct",
         "source_file", "source_sheet", "source_table", "source_cell", "quality_flag", "note"]]
    returns = returns.sort_values(["bank_type", "fund_type", "instrument", "currency", "tenor", "date"]).reset_index(drop=True)

    # ---------------------------------------------------------------- margins
    mar, rev_m = combine(M, ["dimension", "category_code", "sub_category", "currency"])
    mar = mar[~(mar["edition"].isin(OLD_EDITIONS) & (mar["date"] >= NEW_FORMAT_START))]
    mar["fixnote"] = ""
    mar = apply_fixes(mar, FIXES_MARGINS, ["dimension", "category_code", "sub_category", "currency"], "margins")

    def mar_en(r):
        if r["dimension"] == "contract":
            b = "Equivalent rate, " + CONTRACT_EN.get(r["category_code"], r["category_code"])
        elif r["dimension"] == "use_size":
            b = f"Average margin, {USE_EN[r['category_code']]}, {SIZE_EN[r['sub_category']]}"
        else:
            b = "Average margin, " + SECTOR_EN[r["category_code"]]
        return b + ("" if r["currency"] == "all" else " - " + CCY_EN[r["currency"]])

    mar["label_en"] = mar.apply(mar_en, axis=1)
    mar["note"] = np.where(mar["source_table"].str.contains("old"),
                           "old SPS format (Tabel 36), currency not stated; ijarah method changed Oct 2012; level break "
                           "at 2014-06 (see data note)", "")
    mar["note"] = [" | ".join(s for s in (a, b) if s) for a, b in zip(mar["note"], mar["fixnote"])]
    mar["quality_flag"] = mar["flag"].map(qflag)
    for cond, lab in ((mar["value"] > 50, "outlier_gt50pct"), (mar["value"] < 0, "negative_rate"),
                      (mar["value"] == 0, "zero_published")):
        mar.loc[cond, "quality_flag"] = (mar.loc[cond, "quality_flag"] + ";" + lab).str.strip(";")
    margins = mar.rename(columns={"value": "rate_pct", "cell": "source_cell"})[
        ["date", "bank_type", "dimension", "category_code", "sub_category", "currency", "label_id", "label_en", "rate_pct",
         "source_file", "source_sheet", "source_table", "source_cell", "quality_flag", "note"]]
    margins = margins.sort_values(["dimension", "bank_type", "category_code", "sub_category", "currency", "date"]).reset_index(drop=True)

    # ---------------------------------------------------------------- aggregates
    agg_raw = pd.concat(A, ignore_index=True)
    agg_raw["kind"] = agg_raw.get("kind", np.nan)
    ag, rev_a = combine([agg_raw], ["indicator"])
    ag = ag[~(ag["edition"].isin(OLD_EDITIONS) & (ag["date"] >= NEW_FORMAT_START))]
    agw = ag.pivot_table(index=["date", "bank_type"], columns="indicator", values="value", aggfunc="first")
    # derived from other outputs
    tot = contracts[(contracts.contract_code == "total") & (contracts.currency == "all")].set_index(["date", "bank_type"])
    dsum = deposits[(deposits.series == "harmonised") & (deposits.series_code == "h_total")].set_index(["date", "bank_type"])
    rows = []

    def put(d, bt, ind, val, unit, lid, len_, src, stab, note="", qf="", cell=""):
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return
        rows.append(dict(date=d, bank_type=bt, indicator=ind, value=float(val), unit=unit, label_id=lid, label_en=len_,
                         source_file=src, source_table=stab, source_cell=cell, quality_flag=qf, note=note))

    agsrc = ag.set_index(["date", "bank_type", "indicator"])
    LAB = {
        "total_assets_rp_bn": ("Total Aset", "Total assets", "Rp bn"),
        "number_of_banks": ("Jumlah Bank (BUS) / Jumlah BUK yang memiliki UUS (UUS)", "Number of banks (BUS: Islamic banks; UUS: conventional banks with an Islamic window)", "count"),
        "dpk_rp_bn": ("Dana Pihak Ketiga", "Third-party funds (DPK)", "Rp bn"),
        "car_pct": ("CAR", "Capital adequacy ratio", "%"),
        "roa_pct": ("ROA", "Return on assets", "%"),
        "bopo_pct": ("BOPO", "Operating expenses / operating income", "%"),
        "npf_gross_pct_reported": ("NPF (gross)", "Non-performing financing ratio, gross (reported)", "%"),
        "npf_net_pct_reported": ("NPF Net", "Non-performing financing ratio, net (reported)", "%"),
        "fdr_pct_reported": ("FDR", "Financing-to-deposit ratio (reported)", "%"),
        "fdr_financing_nonbank_rp_bn": ("FDR: Pembiayaan kepada Pihak Ketiga Bukan Bank", "FDR numerator: financing to non-bank third parties", "Rp bn"),
        "fdr_dpk_rp_bn": ("FDR: Dana Pihak Ketiga", "FDR denominator: third-party funds", "Rp bn"),
    }
    NOTE_OLD = {"total_assets_rp_bn": "old Tabel 6 'TOTAL AKTIVA' (includes inter-office assets 'Antar kantor Aktiva')",
                "car_pct": "old Tabel 38: CAR is BUS only (footnote 1)",
                "fdr_pct_reported": "old Tabel 38", "npf_gross_pct_reported": "old Tabel 38", "roa_pct": "old Tabel 38",
                "bopo_pct": "old Tabel 38"}
    for (d, bt, ind), r in agsrc.iterrows():
        if ind in LAB:
            lid, len_, unit = LAB[ind]
            note = NOTE_OLD.get(ind, "") if r["edition"] in OLD_EDITIONS else ""
            if ind == "dpk_rp_bn" and d >= NEW_FORMAT_START:
                note = "Tabel 6 'Dana Pihak Ketiga'"
            put(d, bt, ind, r["value"], unit, r["label_id"] or lid, len_, r["source_file"], r["source_table"],
                note, qflag(r["flag"]), r["cell"])
    # total financing and NPF by contract table
    for (d, bt), r in tot.iterrows():
        put(d, bt, "financing_rp_bn", r["financing_rp_bn"], "Rp bn", "Total Pembiayaan (menurut akad)",
            "Total financing (sum over contracts, all currencies)", r["source_file"], r["source_table"],
            r["note"] if isinstance(r["note"], str) else "", "", r["source_cell"])
        if not np.isnan(r["npf_rp_bn"]):
            put(d, bt, "npf_rp_bn", r["npf_rp_bn"], "Rp bn", "NPF / Total NPF (menurut akad)",
                "Non-performing financing (Rp bn)", r["source_file"], r["source_table"], "", "", r["source_cell"])
            put(d, bt, "npf_gross_pct_computed", 100 * r["npf_rp_bn"] / r["financing_rp_bn"], "%", "NPF / Total Pembiayaan",
                "NPF ratio computed from Tabel 11 (NPF / total financing)", r["source_file"], r["source_table"], "", "computed")
    # old format NPF (Rp bn) from old Tabel 26 'Non Lancar' (collectibility 3-5), BUS+UUS, before 2014-06
    if "old_t26_npf_rp_bn" in agw:
        for (d, bt), v in agw["old_t26_npf_rp_bn"].dropna().items():
            if d >= NEW_FORMAT_START:
                continue
            s = agsrc.loc[(d, bt, "old_t26_npf_rp_bn")]
            comp = agw.loc[(d, bt), ["old_t26_nl_kl", "old_t26_nl_d", "old_t26_nl_m"]].sum(min_count=3)
            note, qf = "old Tabel 26 'Non Lancar' (Kurang Lancar + Diragukan + Macet)", ""
            if not np.isnan(comp) and abs(comp - v) > 0.5:
                FIX_LOG.append(("aggregates", f"{d:%Y-%m}", bt, ("npf_rp_bn (old Tabel 26)",), v, comp, "sum"))
                note = (f"published Non Lancar {v:,.3f} omits Macet; replaced by Kurang Lancar + Diragukan + Macet "
                        f"= {comp:,.3f} (ratio then matches Tabel 38 NPF)")
                qf, v = "corrected:sum", comp
            put(d, bt, "npf_rp_bn", v, "Rp bn", "Non Lancar (Tabel 26)", "Non-performing financing (Rp bn)",
                s["source_file"], s["source_table"], note, qf, s["cell"])
            ft = agw.loc[(d, bt), "old_t26_financing_rp_bn"]
            put(d, bt, "npf_gross_pct_computed", 100 * v / ft, "%", "Non Lancar / Total Pembiayaan (Tabel 26)",
                "NPF ratio computed from old Tabel 26 (Non Lancar / Total Pembiayaan)", s["source_file"], s["source_table"],
                "", "computed")
    # DPK before 2014-06: old Tabel 14 total (consistent with the deposits file); from 2014-06 Tabel 6, with the
    # Tabel 22 sum as fallback where Tabel 6 has no column for the month
    have6 = {(d, bt) for (d, bt, ind) in agsrc.index if ind == "dpk_rp_bn"}
    for (d, bt), r in dsum.iterrows():
        if d < NEW_FORMAT_START:
            note = "old Tabel 14 'Total'"
            if d == pd.Timestamp("2012-03-01"):
                note += ("; Mar-2012: Tabel 14 total 119,638.7 vs old Tabel 6 'Dana Pihak Ketiga' 114,317.7 "
                         "(source inconsistency)")
            put(d, bt, "dpk_rp_bn", r["deposits_rp_bn"], "Rp bn", "Total DPK (Tabel 14)", "Third-party funds (DPK)",
                r["source_file"], "Tabel 14 (old)", note, "", r["source_cell"])
        elif (d, bt) not in have6:
            put(d, bt, "dpk_rp_bn", r["deposits_rp_bn"], "Rp bn", "Total DPK (jumlah Tabel 22)", "Third-party funds (DPK)",
                r["source_file"], "Tabel 22 (sum of reported rows)",
                "Tabel 6 has no column for this month; sum of Tabel 22 groups used", "fallback_tabel22_sum")
    # financing to non-bank parties from Tabel 6
    if {"t6_ps_financing_nonbank", "t6_receivables_nonbank", "t6_ijarah_nonbank"} <= set(agw.columns):
        fnb = agw[["t6_ps_financing_nonbank", "t6_receivables_nonbank", "t6_ijarah_nonbank"]].sum(axis=1, min_count=3)
        fnb = fnb + agw.get("t6_salam", pd.Series(0.0, index=agw.index)).fillna(0.0)
        for (d, bt), v in fnb.dropna().items():
            src = agsrc.loc[(d, bt, "t6_ps_financing_nonbank")]
            put(d, bt, "financing_nonbank_rp_bn", v, "Rp bn",
                "Pembiayaan bagi hasil + piutang + ijarah kepada pihak ketiga bukan bank + salam (Tabel 6)",
                "Financing to non-bank third parties (Tabel 6 components)", src["source_file"], src["source_table"], "",
                "computed")
    out = pd.DataFrame(rows)
    # computed FDR (total financing by contract / DPK)
    piv = out.pivot_table(index=["date", "bank_type"], columns="indicator", values="value", aggfunc="first")
    if "financing_rp_bn" in piv and "dpk_rp_bn" in piv:
        f = (100 * piv["financing_rp_bn"] / piv["dpk_rp_bn"]).dropna()
        for (d, bt), v in f.items():
            put(d, bt, "fdr_pct_computed", v, "%", "Total Pembiayaan / DPK",
                "FDR computed as total financing (contracts table) / DPK", "derived", "derived", "", "computed")
    aggregates = pd.DataFrame(rows).sort_values(["indicator", "bank_type", "date"]).reset_index(drop=True)
    aggregates = aggregates[["date", "bank_type", "indicator", "value", "unit", "label_id", "label_en", "source_file",
                             "source_table", "source_cell", "quality_flag", "note"]]

    # ---------------------------------------------------------------- write
    CLEAN.mkdir(parents=True, exist_ok=True)
    for name, df in (("ojk_contracts", contracts), ("ojk_deposits", deposits), ("ojk_deposit_returns", returns),
                     ("ojk_margins", margins), ("ojk_aggregates", aggregates)):
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        df.to_csv(CLEAN / f"{name}.csv", index=False, encoding="utf-8", float_format="%.6f")
        print(f"wrote {name}.csv: {len(df)} rows")

    validate(contracts, deposits, returns, margins, aggregates, agw, dict(contracts=rev_c, deposits=rev_d, returns=rev_r,
                                                                          margins=rev_m, aggregates=rev_a), diags)
    validate_more(contracts, deposits, returns, margins, aggregates, OVL)


# --------------------------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------------------------
def gap_stats(a, b):
    j = pd.concat([a.rename("a"), b.rename("b")], axis=1, join="inner").dropna()
    d = (j["a"] - j["b"]).abs()
    if not len(d):
        return "no overlap"
    rel = (d / j["b"].abs().replace(0, np.nan)).max()
    worst = d.idxmax()
    return (f"n={len(d)}, max abs gap {d.max():.4f} (at {worst}), mean abs gap {d.mean():.4f}, max rel gap "
            f"{0 if np.isnan(rel) else rel:.2e}, n(gap>0.01)={(d > 0.01).sum()}, n(gap>1)={(d > 1).sum()}")


def validate(con, dep, ret, mar, agg, agw, revs, diags):
    P = print
    P("\n-- quality_flag counts --")
    for name, df in (("contracts", con), ("deposits", dep), ("deposit_returns", ret), ("margins", mar), ("aggregates", agg)):
        vc = df["quality_flag"].fillna("").replace("", "(none)").value_counts()
        P(f"  {name}: " + ", ".join(f"{k}={v}" for k, v in vc.items()))
    P("\n================ VALIDATION ================")
    P("\n-- Column/date mapping: annual duplicate columns checked against the December column --")
    for k, v in diags.items():
        P(f"  {k[0]:18s} {k[1]:10s} dup cells={v['n_dup_cells']:5d} max |annual - Dec| = {v['max_dup_gap']:.6g}")
    if WARN:
        P("\n-- Warnings --")
        for w in WARN:
            P("  " + w)
    # coverage
    P("\n-- Coverage (monthly) --")
    for name, df, by in (("contracts", con[con.currency == "all"], ["bank_type"]),
                         ("contracts IDR (T12)", con[con.currency == "IDR"], ["bank_type"]),
                         ("deposits harmonised", dep[dep.series == "harmonised"], ["bank_type"]),
                         ("deposits reported", dep[dep.series == "reported"], ["bank_type"]),
                         ("deposit returns", ret, ["bank_type"]),
                         ("margins", mar, ["dimension", "bank_type"]),
                         ("aggregates", agg, ["indicator", "bank_type"])):
        for k, a, b, n, miss in coverage(df, by):
            P(f"  {name:20s} {str(k):45s} {a} .. {b}  n={n:3d}  missing: {fmt_missing(miss)}")

    # contracts
    P("\n-- Contracts: components vs totals (Rp bn) --")
    for ccy in ("all", "IDR"):
        c = con[con.currency == ccy]
        for meas in ("financing_rp_bn", "npf_rp_bn"):
            w = c.pivot_table(index=["date", "bank_type"], columns="contract_code", values=meas, aggfunc="first")
            if w.empty or "total" not in w:
                continue
            leaves = [k for k in ("mudharabah", "musyarakah", "other_profit_sharing", "murabahah", "qardh", "istishna",
                                  "ijarah", "salam", "multijasa", "other") if k in w]
            s = w[leaves].sum(axis=1, min_count=1)
            P(f"  [{ccy}] {meas}: sum of contracts vs Total: {gap_stats(s, w['total'])}")
            for grp, comps in (("profit_sharing", ["mudharabah", "musyarakah", "other_profit_sharing"]),
                               ("receivables", ["murabahah", "qardh", "istishna"]),
                               ("ijarah", ["ijarah_syndicated", "ijarah_channeling", "ijarah_executing", "ijarah_other"])):
                if grp in w and all(k in w for k in comps):
                    P(f"  [{ccy}] {meas}: {grp} components vs group row: {gap_stats(w[comps].sum(axis=1, min_count=1), w[grp])}")
            # BUS + UUS = combined
            wt = w["total"].unstack("bank_type")
            if {"BUS", "UUS", "BUS_UUS"} <= set(wt.columns):
                P(f"  [{ccy}] {meas}: BUS + UUS vs BUS_UUS (total): {gap_stats(wt['BUS'] + wt['UUS'], wt['BUS_UUS'])}")
            if meas == "financing_rp_bn":
                allc = w.drop(columns=["total"]).stack()
                P(f"  [{ccy}] negative financing values: {(allc < 0).sum()}")
    P("  multijasa rows present: " + str((con.contract_code == "multijasa").any()))
    P("  old-format 'Lainnya' (other) max value: " + str(con.loc[con.contract_code == "other", "financing_rp_bn"].max()))

    # deposits
    P("\n-- Deposits: components vs totals (Rp bn) --")
    r = dep[dep.series == "reported"]
    for bt in ("BUS_UUS", "BUS", "UUS"):
        x = r[(r.bank_type == bt) & (r.date >= NEW_FORMAT_START)]
        if x.empty:
            continue
        key = lambda g: g.set_index("date")["deposits_rp_bn"]
        chk = []
        for fund in ("wadiah", "investment_non_profit_sharing", "investment_profit_sharing"):
            f = x[x.fund_type == fund]
            top = key(f[(f.instrument == "all")])
            ins = f[(f.instrument != "all") & (f.currency == "all") & (f.tenor == "all")].groupby("date")["deposits_rp_bn"].sum()
            chk.append((f"{fund}: instruments vs group", ins, top))
            for instr in f.instrument.unique():
                if instr == "all":
                    continue
                g = f[f.instrument == instr]
                a = key(g[(g.currency == "all") & (g.tenor == "all")])
                cc = g[(g.currency != "all") & (g.tenor == "all")].groupby("date")["deposits_rp_bn"].sum()
                chk.append((f"{fund}/{instr}: Rp+FX vs instrument", cc, a))
                if instr == "time":
                    for ccy in ("IDR", "FX"):
                        tt = g[(g.currency == ccy) & (g.tenor != "all")].groupby("date")["deposits_rp_bn"].sum()
                        chk.append((f"{fund}/time/{ccy}: tenors vs currency row", tt, key(g[(g.currency == ccy) & (g.tenor == "all")])))
        for lab, a, b in chk:
            P(f"  [{bt}] {lab}: {gap_stats(a, b)}")
    h = dep[dep.series == "harmonised"]
    ht = h[h.series_code == "h_total"].set_index(["date", "bank_type"])["deposits_rp_bn"]
    t6 = agw["dpk_rp_bn"].dropna() if "dpk_rp_bn" in agw else pd.Series(dtype=float)
    P(f"  Sum of Tabel 22 groups vs Tabel 6 'Dana Pihak Ketiga' (all bank types, 2014-06+): {gap_stats(ht, t6)}")
    if "fdr_dpk_rp_bn" in agw:
        P(f"  Sum of Tabel 22 groups vs Tabel 1 FDR denominator DPK (BUS, UUS): {gap_stats(ht, agw['fdr_dpk_rp_bn'].dropna())}")
    htw = ht.unstack("bank_type")
    if {"BUS", "UUS", "BUS_UUS"} <= set(htw.columns):
        P(f"  Deposits total BUS + UUS vs BUS_UUS: {gap_stats(htw['BUS'] + htw['UUS'], htw['BUS_UUS'])}")
    hw = h.pivot_table(index=["date", "bank_type"], columns="series_code", values="deposits_rp_bn", aggfunc="first")
    P(f"  harmonised demand + savings + time vs total (all periods): "
      f"{gap_stats(hw[['h_demand', 'h_sav', 'h_time']].sum(axis=1, min_count=3), hw['h_total'])}")
    P(f"  harmonised savings wadiah + mudharabah vs savings: {gap_stats(hw[['h_sav_w', 'h_sav_m']].sum(axis=1, min_count=2), hw['h_sav'])}")
    ten = hw[[f"h_time_{t}" for t in ("1m", "3m", "6m", "12m", "gt12m")]].sum(axis=1, min_count=5)
    old_mask = hw.index.get_level_values("date") < NEW_FORMAT_START
    P(f"  tenor sum vs time deposits, new format: {gap_stats(ten[~old_mask], hw['h_time'][~old_mask])}")
    g = (ten[old_mask] - hw["h_time"][old_mask]).abs()
    bad = g[g > 1]
    P(f"  tenor sum vs time deposits, OLD format (2009-01..2014-05): {gap_stats(ten[old_mask], hw['h_time'][old_mask])}")
    if len(bad):
        P("    months with |gap| > Rp 1 bn: " + ", ".join(f"{d:%Y-%m} ({v:,.0f})" for (d, bt), v in bad.items()))
    if "old_t6_dpk_rp_bn" in agw:
        P(f"  OLD Tabel 14 total vs OLD Tabel 6 DPK: {gap_stats(ht, agw['old_t6_dpk_rp_bn'].dropna())}")

    # returns / margins
    P("\n-- Rates: ranges and checks (%) --")
    for name, df in (("deposit returns", ret), ("margins", mar)):
        v = df["rate_pct"]
        P(f"  {name}: n={len(v)}, min={v.min():.4f}, max={v.max():.4f}, n(<0)={(v < 0).sum()}, n(==0)={(v == 0).sum()}, "
          f"n(>30)={(v > 30).sum()}")
    big = mar[mar.rate_pct > 30]
    if len(big):
        P("    margins > 30%: " + "; ".join(f"{r.date:%Y-%m} {r.bank_type} {r.dimension}/{r.category_code}/{r.currency} {r.rate_pct:.1f}"
                                         for r in big.head(15).itertuples()) + (" ..." if len(big) > 15 else ""))
    bigr = ret[ret.rate_pct > 30]
    if len(bigr):
        P("    returns > 30%: " + "; ".join(f"{r.date:%Y-%m} {r.bank_type} {r.instrument}/{r.currency}/{r.tenor} {r.rate_pct:.1f}"
                                         for r in bigr.head(15).itertuples()))
    # old vs new deposit returns on overlap Jun-Dec 2014 (old values are superseded, read them from the raw old file again)
    P("\n-- Aggregates --")
    a = agg.pivot_table(index=["date", "bank_type"], columns="indicator", values="value", aggfunc="first")
    ta = a["total_assets_rp_bn"].unstack("bank_type")
    P(f"  total assets BUS + UUS vs BUS_UUS: {gap_stats(ta['BUS'] + ta['UUS'], ta['BUS_UUS'])}")
    for ind in ("dpk_rp_bn", "financing_nonbank_rp_bn", "financing_rp_bn", "npf_rp_bn"):
        if ind in a:
            tb = a[ind].unstack("bank_type")
            if {"BUS", "UUS", "BUS_UUS"} <= set(tb.columns):
                P(f"  {ind} BUS + UUS vs BUS_UUS: {gap_stats(tb['BUS'] + tb['UUS'], tb['BUS_UUS'])}")
    for ind in ("dpk_rp_bn", "financing_nonbank_rp_bn"):
        tb = a[ind].unstack("bank_type")
        sel = tb.index[(tb.index >= "2022-01-01") & (tb.index <= "2022-12-01")]
        P(f"  Tabel 6a override check 2022 ({ind}): BUS + UUS vs BUS_UUS: "
          f"{gap_stats((tb['BUS'] + tb['UUS']).loc[sel], tb['BUS_UUS'].loc[sel])}")
    if "fdr_financing_nonbank_rp_bn" in a:
        fr = 100 * a["fdr_financing_nonbank_rp_bn"] / a["fdr_dpk_rp_bn"]
        P(f"  reported FDR vs its own components (BUS, UUS): {gap_stats(fr.dropna(), a['fdr_pct_reported'].dropna())}")
        P(f"  Tabel 6 non-bank financing vs Tabel 1 FDR numerator: "
          f"{gap_stats(a['financing_nonbank_rp_bn'].dropna(), a['fdr_financing_nonbank_rp_bn'].dropna())}")
    P(f"  reported FDR vs computed FDR (total financing/DPK): {gap_stats(a['fdr_pct_computed'].dropna(), a['fdr_pct_reported'].dropna())}")
    P(f"  reported gross NPF vs computed (Tabel 11): {gap_stats(a['npf_gross_pct_computed'].dropna(), a['npf_gross_pct_reported'].dropna())}")
    if "old_t6_financing_rp_bn" in agw:
        P(f"  OLD Tabel 18 total financing vs OLD Tabel 6 'Pembiayaan': "
          f"{gap_stats(a['financing_rp_bn'].dropna(), agw['old_t6_financing_rp_bn'].dropna())}")
    if "t6_ps_financing_nonbank" in agw:
        P(f"  Tabel 11 total vs Tabel 6 non-bank financing: {gap_stats(a['financing_rp_bn'].dropna(), a['financing_nonbank_rp_bn'].dropna())}")
    P("\n-- Revisions between editions (value of other edition vs value kept) --")
    for name, rv in revs.items():
        if rv is None or rv.empty:
            continue
        for x in rv.itertuples():
            P(f"  {name:11s} {x.edition} vs kept {x.vs}: overlap {x.n_overlap:6d} cells ({x.date_min}..{x.date_max}), "
              f"differ(>1e-6) {x.n_diff:6d}, max abs diff {x.max_abs_diff:.4f}{x.worst}")


def _cmp(label, old, new, unit):
    """old/new: Series indexed by date. Prints n, max and mean abs gap, and the max relative gap for levels."""
    j = pd.concat([old.rename("o"), new.rename("n")], axis=1, join="inner").dropna()
    if not len(j):
        print(f"  {label:62s} no overlap")
        return
    d = (j["o"] - j["n"]).abs()
    rel = (d / j["n"].abs().replace(0, np.nan)).max()
    extra = f", max rel {0 if np.isnan(rel) else rel:.2e}" if unit == "Rp bn" else ""
    thr = 1 if unit == "Rp bn" else 0.5
    print(f"  {label:62s} n={len(j):2d} ({j.index.min():%Y-%m}..{j.index.max():%Y-%m}) max|gap|={d.max():10.3f} "
          f"mean|gap|={d.mean():9.3f} {unit}{extra}, n(|gap|>{thr})={int((d > thr).sum())}")


def validate_more(con, dep, ret, mar, agg, OVL):
    P = print
    P("\n-- Corrections applied (published -> corrected) --")
    for (name, d, bt, kk, old, new, rule) in FIX_LOG:
        P(f"  {name:9s} {d} {bt:7s} {'/'.join(map(str, kk)):60s} {old:14,.3f} -> {new:14,.3f}  ({rule})")
    P(f"  total corrected cells: {len(FIX_LOG)}")

    P("\n-- Stale-column scan: months whose values repeat the previous month in every non-zero row (final outputs) --")
    found = 0
    for name, df, val, keys in (
            ("contracts", con, "financing_rp_bn", ["currency", "contract_code"]),
            ("deposits", dep[dep.series == "reported"], "deposits_rp_bn", ["fund_type", "instrument", "currency", "tenor"]),
            ("returns", ret, "rate_pct", ["fund_type", "instrument", "currency", "tenor"]),
            ("margins", mar, "rate_pct", ["dimension", "category_code", "sub_category", "currency"])):
        for bt, g in df.groupby("bank_type"):
            w = g.pivot_table(index=keys, columns="date", values=val, aggfunc="first")
            cols = list(w.columns)
            for a, b in zip(cols[:-1], cols[1:]):
                if add_month(pd.Timestamp(a)) != pd.Timestamp(b):
                    continue
                x, y = w[a], w[b]
                m = x.notna() & y.notna() & (x != 0)
                if m.sum() >= 5 and (x[m] == y[m]).all():
                    P(f"  {name:9s} {bt:7s} {pd.Timestamp(b):%Y-%m} repeats {pd.Timestamp(a):%Y-%m} "
                      f"in all {int(m.sum())} non-zero rows")
                    found += 1
    P(f"  stale months found: {found}")

    P("\n-- Old SPS format vs new SPS format on overlapping months (BUS+UUS) --")
    P("   old = SPS_2014_12 (2014-06..2014-12) and SPS_2015_06 (2014-06..2015-05); new = values kept in the outputs")
    oc = OVL["contracts"]
    oc = oc[(oc["measure"] == "financing")]
    nc = con[(con.bank_type == "BUS_UUS") & (con.currency == "all")]
    for ed, g in oc.groupby("edition"):
        for code in ("mudharabah", "musyarakah", "murabahah", "salam", "istishna", "ijarah", "qardh", "total"):
            o = g[g.contract_code == code].set_index("date")["value"]
            n = nc[nc.contract_code == code].set_index("date")["financing_rp_bn"]
            _cmp(f"contracts {ed} old Tabel 18 {code}", o, n, "Rp bn")
    od = OVL["deposits"]
    h = dep[(dep.series == "harmonised") & (dep.bank_type == "BUS_UUS")]

    def hs(c):
        return h[h.series_code == c].set_index("date")["deposits_rp_bn"]

    for ed, g in od.groupby("edition"):
        def sel(f, i, t="all"):
            return g[(g.fund_type == f) & (g.instrument == i) & (g.tenor == t)].set_index("date")["value"]
        _cmp(f"deposits {ed} old Total vs h_total", sel("total", "all"), hs("h_total"), "Rp bn")
        _cmp(f"deposits {ed} old Giro iB-Wadiah vs all giro (h_demand)", sel("all_labelled_wadiah", "demand"),
             hs("h_demand"), "Rp bn")
        _cmp(f"deposits {ed} old Giro iB-Wadiah vs giro wadiah (h_demand_w)", sel("all_labelled_wadiah", "demand"),
             hs("h_demand_w"), "Rp bn")
        _cmp(f"deposits {ed} old Tabungan vs h_sav", sel("all", "savings"), hs("h_sav"), "Rp bn")
        _cmp(f"deposits {ed} old Tabungan wadiah vs h_sav_w", sel("wadiah", "savings"), hs("h_sav_w"), "Rp bn")
        _cmp(f"deposits {ed} old Tabungan mudharabah vs h_sav_m", sel("mudharabah", "savings"), hs("h_sav_m"), "Rp bn")
        _cmp(f"deposits {ed} old Deposito vs h_time", sel("mudharabah", "time"), hs("h_time"), "Rp bn")
        for t in ("1m", "3m", "6m", "12m", "gt12m"):
            _cmp(f"deposits {ed} old Deposito {t} vs h_time_{t}", sel("mudharabah", "time", t), hs("h_time_" + t), "Rp bn")
    orr = OVL["returns"]
    orr = orr[orr["kind"] == "deposit"]
    nr = ret[ret.bank_type == "BUS_UUS"]

    def ns(f, i, c, t="all"):
        return nr[(nr.fund_type == f) & (nr.instrument == i) & (nr.currency == c) & (nr.tenor == t)].set_index("date")["rate_pct"]

    for ed, g in orr.groupby("edition"):
        def sel(i, t="all"):
            return g[(g.instrument == i) & (g.tenor == t)].set_index("date")["value"]
        _cmp(f"returns {ed} old Giro iB vs new giro wadiah IDR", sel("demand"), ns("wadiah", "demand", "IDR"), "pp")
        _cmp(f"returns {ed} old Giro iB vs new giro mudharabah IDR", sel("demand"), ns("mudharabah", "demand", "IDR"), "pp")
        _cmp(f"returns {ed} old Tabungan iB vs new tabungan wadiah IDR", sel("savings"), ns("wadiah", "savings", "IDR"), "pp")
        _cmp(f"returns {ed} old Tabungan iB vs new tabungan mudharabah IDR", sel("savings"),
             ns("mudharabah", "savings", "IDR"), "pp")
        for t in ("1m", "3m", "6m", "12m", "gt12m"):
            _cmp(f"returns {ed} old Deposito {t} vs new IDR {t}", sel("time", t), ns("mudharabah", "time", "IDR", t), "pp")
            _cmp(f"returns {ed} old Deposito {t} vs new FX {t}", sel("time", t), ns("mudharabah", "time", "FX", t), "pp")
    # old time-deposit rates vs the deposit-weighted Rupiah + FX average of the new Tabel 17 rates
    dr = dep[(dep.bank_type == "BUS_UUS") & (dep.series == "reported") & (dep.instrument == "time")
             & dep.fund_type.isin(["investment_non_profit_sharing", "investment_profit_sharing"])]
    for ed, g in orr.groupby("edition"):
        for t in ("1m", "3m", "6m", "12m", "gt12m"):
            o = g[(g.instrument == "time") & (g.tenor == t)].set_index("date")["value"]
            num = den = 0
            for c in ("IDR", "FX"):
                v = dr[(dr.currency == c) & (dr.tenor == t)].groupby("date")["deposits_rp_bn"].sum()
                num = num + ns("mudharabah", "time", c, t) * v
                den = den + v
            _cmp(f"returns {ed} old Deposito {t} vs new weighted IDR+FX {t}", o, num / den, "pp")
    om = OVL["margins"]
    om = om[om["kind"] == "financing"]
    nm = mar[(mar.bank_type == "BUS_UUS") & (mar.dimension == "contract")]
    for ed, g in om.groupby("edition"):
        for code in ("mudharabah", "musyarakah", "murabahah", "istishna", "ijarah", "qardh"):
            o = g[g.contract_code == code].set_index("date")["value"]
            for ccy in ("all", "IDR"):
                n = nm[(nm.category_code == code) & (nm.currency == ccy)].set_index("date")["rate_pct"]
                _cmp(f"margins {ed} old Tabel 36 {code} vs new {ccy}", o, n, "pp")
    oa = OVL["aggregates"]
    na = agg[agg.bank_type == "BUS_UUS"].pivot_table(index="date", columns="indicator", values="value", aggfunc="first")
    nb = agg[agg.bank_type == "BUS"].pivot_table(index="date", columns="indicator", values="value", aggfunc="first")
    for ed, g in oa.groupby("edition"):
        def gi(ind):
            return g[g.indicator == ind].set_index("date")["value"]
        _cmp(f"aggregates {ed} old T6 total aktiva vs new total assets", gi("total_assets_rp_bn"), na["total_assets_rp_bn"], "Rp bn")
        _cmp(f"aggregates {ed} old T6 DPK vs new DPK (Tabel 6)", gi("old_t6_dpk_rp_bn"), na["dpk_rp_bn"], "Rp bn")
        _cmp(f"aggregates {ed} old T6 Pembiayaan vs new total financing", gi("old_t6_financing_rp_bn"),
             na["financing_rp_bn"], "Rp bn")
        _cmp(f"aggregates {ed} old T26 Non Lancar vs new NPF (Tabel 11)", gi("old_t26_npf_rp_bn"), na["npf_rp_bn"], "Rp bn")
        _cmp(f"aggregates {ed} old T38 NPF % vs new computed NPF %", gi("npf_gross_pct_reported"),
             na["npf_gross_pct_computed"], "pp")
        _cmp(f"aggregates {ed} old T38 FDR % vs new computed FDR %", gi("fdr_pct_reported"), na["fdr_pct_computed"], "pp")
        _cmp(f"aggregates {ed} old T38 CAR % (BUS) vs new CAR % (BUS)", gi("car_pct"), nb["car_pct"], "pp")

    P("\n-- Old format internal checks (2009-01..2014-05, values kept) --")
    a = agg[(agg.bank_type == "BUS_UUS") & (agg.date < NEW_FORMAT_START)].pivot_table(
        index="date", columns="indicator", values="value", aggfunc="first")
    c_old = con[(con.bank_type == "BUS_UUS") & (con.date < NEW_FORMAT_START)]
    w = c_old.pivot_table(index="date", columns="contract_code", values="financing_rp_bn", aggfunc="first")
    leaves = [k for k in ("mudharabah", "musyarakah", "murabahah", "salam", "istishna", "ijarah", "qardh", "other") if k in w]
    _cmp("old Tabel 18 sum of contracts vs Total", w[leaves].sum(axis=1), w["total"], "Rp bn")
    _cmp("old Tabel 26 NPF ratio (computed) vs Tabel 38 NPF", a["npf_gross_pct_computed"], a["npf_gross_pct_reported"], "pp")
    _cmp("old FDR computed (T18 total / T14 DPK) vs Tabel 38 FDR", a["fdr_pct_computed"], a["fdr_pct_reported"], "pp")
    hd = dep[(dep.series == "harmonised") & (dep.date < NEW_FORMAT_START)].pivot_table(
        index="date", columns="series_code", values="deposits_rp_bn", aggfunc="first")
    _cmp("old Tabel 14 giro + tabungan + deposito vs Total", hd[["h_demand", "h_sav", "h_time"]].sum(axis=1),
         hd["h_total"], "Rp bn")
    _cmp("old Tabel 14 tabungan wadiah + mudharabah vs tabungan", hd[["h_sav_w", "h_sav_m"]].sum(axis=1), hd["h_sav"], "Rp bn")
    _cmp("old Tabel 14 tenor rows vs deposito",
         hd[[f"h_time_{t}" for t in ("1m", "3m", "6m", "12m", "gt12m")]].sum(axis=1), hd["h_time"], "Rp bn")

    P("\n-- Missing values, duplicate keys and negatives in the outputs --")
    for name, df, keys, val in (
            ("contracts", con, ["date", "bank_type", "currency", "contract_code"], "financing_rp_bn"),
            ("deposits", dep, ["date", "bank_type", "series", "series_code", "fund_type", "instrument", "currency",
                               "tenor"], "deposits_rp_bn"),
            ("returns", ret, ["date", "bank_type", "fund_type", "instrument", "currency", "tenor"], "rate_pct"),
            ("margins", mar, ["date", "bank_type", "dimension", "category_code", "sub_category", "currency"], "rate_pct"),
            ("aggregates", agg, ["date", "bank_type", "indicator"], "value")):
        P(f"  {name:10s} rows={len(df):6d} duplicate keys={int(df.duplicated(keys).sum())} "
          f"missing {val}={int(df[val].isna().sum())} negative {val}={int((df[val] < 0).sum())}")


if __name__ == "__main__":
    main()
