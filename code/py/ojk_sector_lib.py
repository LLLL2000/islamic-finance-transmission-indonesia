"""Parsing helpers for OJK Statistik Perbankan Syariah (SPS) sector tables.

Used by build_ojk_sector.py (builder: ojk_sector). Reads raw OJK workbooks only as data
(pandas/openpyxl/xlrd cell values); nothing from the raw folder is executed.
"""
import re
import numpy as np
import pandas as pd

MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "mei": 5, "may": 5, "jun": 6, "jul": 7,
          "agt": 8, "ags": 8, "agu": 8, "aug": 8, "sep": 9, "okt": 10, "oct": 10, "nov": 11,
          "des": 12, "dec": 12}


def norm(s):
    return re.sub(r"\s+", " ", str(s)).strip()


def month_of(v):
    if not isinstance(v, str):
        return None
    m = re.match(r"\s*([A-Za-z]{3})", v)
    return MONTHS.get(m.group(1).lower()) if m else None


def year_of(v):
    if isinstance(v, (int, float, np.integer, np.floating)) and not pd.isna(v):
        if 2000 <= float(v) <= 2035 and float(v) == int(v):
            return int(v)
    if isinstance(v, str) and re.fullmatch(r"\s*20\d\d\s*", v):
        return int(v)
    return None


def clean_value(v, log, where):
    """Numeric cell -> float. Strings with revision markers are parsed and logged."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return np.nan
    if isinstance(v, (int, float, np.integer, np.floating)):
        return float(v)
    s = str(v).strip()
    if s == "":
        return np.nan
    if s in ("-", "--"):  # OJK convention: dash = nil
        log.append(dict(kind="dash_cell_set_to_zero", where=where, raw=s))
        return 0.0
    core = re.sub(r"[*r\)\(\s]", "", s)
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", core):  # Indonesian thousands separator
        val = float(core.replace(".", "").replace(",", "."))
    elif re.fullmatch(r"\d+(,\d+)?", core):
        val = float(core.replace(",", "."))
    elif re.fullmatch(r"\d+\.\d+", core):
        val = float(core)
    else:
        log.append(dict(kind="unparsed_string", where=where, raw=s))
        return np.nan
    log.append(dict(kind="string_cell_parsed", where=where, raw=s, value=val))
    return val


def date_columns(df, yr_row, mo_row, first_col=1, last_col=None):
    """Map sheet columns to dates.

    Returns (monthly, annual, dups):
      monthly: dict col -> Timestamp (first of month)
      annual:  dict col -> year (stand-alone year column with no month label = year-end position)
      dups:    list of (col_discarded, col_kept, date) for duplicated monthly dates (later column kept)
    Rules: year cells are forward-filled across columns (merged headers); a month label whose year is
    inherited (not written in that column) and that would not move time forward rolls into the next
    year; an unlabeled block of exactly 12 columns under one year cell is Jan..Dec; an unlabeled
    single column under its own year cell is an annual (year-end) column.
    """
    ncol = df.shape[1] if last_col is None else last_col
    yrs_explicit = {c: year_of(df.iat[yr_row, c]) for c in range(first_col, ncol)}
    mos = {c: month_of(df.iat[mo_row, c]) for c in range(first_col, ncol)}
    # blocks: start at each explicit year cell
    starts = [c for c in range(first_col, ncol) if yrs_explicit[c] is not None]
    blocks = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else ncol
        blocks.append((s, e, yrs_explicit[s]))
    monthly, annual, seen = {}, {}, {}
    dups = []
    last = None
    for s, e, y in blocks:
        cols = list(range(s, e))
        labeled = [c for c in cols if mos[c] is not None]
        if not labeled:
            # unlabeled: width 1 -> annual ; width 12 -> Jan..Dec ; else trim trailing empty cols
            data_cols = [c for c in cols if df.iloc[:, c].apply(lambda v: isinstance(v, (int, float)) and not pd.isna(v)).sum() > 0]
            if len(data_cols) == 1 and data_cols[0] == s:
                annual[s] = y
                continue
            if len(data_cols) == 12 and data_cols == cols[:12]:
                for k, c in enumerate(data_cols):
                    d = pd.Timestamp(y, k + 1, 1)
                    if d in seen:
                        dups.append((seen[d], c, d)); monthly.pop(seen[d])
                    monthly[c] = d; seen[d] = c; last = d
                continue
            raise ValueError(f"cannot date unlabeled block cols {s}-{e} year {y} data_cols={data_cols}")
        yy = y
        for c in cols:
            mo = mos[c]
            if mo is None:
                continue
            d = pd.Timestamp(yy, mo, 1)
            if c != s and last is not None and d <= last and yrs_explicit[c] is None:
                yy += 1
                d = pd.Timestamp(yy, mo, 1)
            if d in seen:
                dups.append((seen[d], c, d)); monthly.pop(seen[d])
            monthly[c] = d; seen[d] = c; last = d
    return monthly, annual, dups


def find_rows(df, pattern, col=0):
    rx = re.compile(pattern, re.I)
    return [i for i in range(df.shape[0]) if isinstance(df.iat[i, col], str) and rx.search(norm(df.iat[i, col]))]


def header_rows(df, title_row):
    """year row = first row after the title with >=1 year cell in cols>=1; month row = next row."""
    for r in range(title_row + 1, min(title_row + 6, df.shape[0])):
        if sum(year_of(v) is not None for v in df.iloc[r, 1:]) >= 1:
            return r, r + 1
    raise ValueError(f"no year row after {title_row}")
