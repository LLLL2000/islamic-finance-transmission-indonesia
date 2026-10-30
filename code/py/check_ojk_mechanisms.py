import sys; sys.path.append(r"C:/Users/consu/AppData/Local/Packages/PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0/LocalCache/local-packages/Python311/site-packages")
"""
Independent spot check of the OJK mechanism outputs (builder ojk_mechanisms).

For a fixed random sample of rows from each output CSV, re-read the cell named in `source_cell` directly with
openpyxl (.xlsx) or xlrd (.xls), parse it, and compare with the value in the CSV. Rows flagged as corrected by the
build are compared with the published value quoted in their note instead. Also prints the row label found in the
workbook next to the expected Indonesian label, so the row mapping can be eyeballed.

Run:  python -I code/py/check_ojk_mechanisms.py
Raw files are read as data only.
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd
import openpyxl
import xlrd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw" / "ojk"
CLEAN = ROOT / "data" / "clean"
N = 250
SEED = 20261029

sys.path.append(str(ROOT / "code" / "py"))
from build_ojk_mechanisms import parse_value  # noqa: E402  (same parser as the build; addressing is independent)

_books = {}


def cell(fname, sheet, r, c):
    key = (fname, sheet)
    if key not in _books:
        p = RAW / fname
        if p.suffix == ".xlsx":
            _books[key] = ("x", openpyxl.load_workbook(p, read_only=False, data_only=True)[sheet])
        else:
            _books[key] = ("s", xlrd.open_workbook(str(p)).sheet_by_name(sheet))
    kind, sh = _books[key]
    if kind == "x":
        return sh.cell(row=r, column=c).value
    v = sh.cell_value(r - 1, c - 1)
    return None if v == "" else v


def label(fname, sheet, r):
    out = []
    for c in range(1, 5):
        try:
            v = cell(fname, sheet, r, c)
        except Exception:
            v = None
        if v not in (None, ""):
            out.append(str(v).replace("\n", " ").strip())
    return " | ".join(out)[:70]


def check(name, df, val, kind_of):
    df = df[df["source_cell"].fillna("").str.match(r"^(fin:)?r\d+c\d+") & df["source_file"].str.endswith(("xls", "xlsx"))]
    smp = df.sample(n=min(N, len(df)), random_state=SEED)
    n_ok = n_bad = n_fix = 0
    bad = []
    for _, row in smp.iterrows():
        cells = row["source_cell"].split(";")
        cref = [c for c in cells if not c.startswith("npf:")][0]
        r, c = [int(x) for x in re.findall(r"\d+", cref)[-2:]]
        raw = cell(row["source_file"], row["source_sheet"], r, c)
        old = "(old)" in str(row["source_table"])
        k = kind_of(row)
        x, _ = parse_value(raw, "fraction" if (k == "ratio" and old) else k)
        if k == "ratio" and old:
            x = x * 100.0      # old tables store fractions; the outputs are in percent
        flag = str(row.get("quality_flag", ""))
        if "corrected" in flag:
            m = re.search(r"published ([-0-9,\.]+)", str(row["note"]))
            pub = float(m.group(1).replace(",", "")) if m else np.nan
            ok = abs(pub - x) < 1e-3 * max(1, abs(x))
            n_fix += 1
        else:
            y = row[val]
            ok = (np.isnan(x) and pd.isna(y)) or (not np.isnan(x) and not pd.isna(y) and abs(x - y) < 1e-6 * max(1, abs(y)))
        if ok:
            n_ok += 1
        else:
            n_bad += 1
            bad.append((row["date"], row["bank_type"], row["source_file"], row["source_sheet"], cref, raw, row[val]))
    print(f"{name:20s} sampled {len(smp):4d} rows: match {n_ok}, mismatch {n_bad} (of which corrected rows checked "
          f"against the published value in the note: {n_fix})")
    for b in bad[:10]:
        print("    MISMATCH", b)
    for _, row in smp.head(4).iterrows():
        cref = [c for c in row["source_cell"].split(";") if not c.startswith("npf:")][0]
        r = int(re.findall(r"\d+", cref)[-2])
        print(f"    label check {row['date']} {row['source_file']} r{r}: csv label_id={str(row['label_id'])[:45]!r} "
              f"workbook={label(row['source_file'], row['source_sheet'], r)!r}")


def main():
    con = pd.read_csv(CLEAN / "ojk_contracts.csv")
    dep = pd.read_csv(CLEAN / "ojk_deposits.csv")
    ret = pd.read_csv(CLEAN / "ojk_deposit_returns.csv")
    mar = pd.read_csv(CLEAN / "ojk_margins.csv")
    check("contracts", con, "financing_rp_bn", lambda r: "nominal")
    check("deposits (reported)", dep[dep.series == "reported"], "deposits_rp_bn", lambda r: "nominal")
    check("deposit returns", ret, "rate_pct", lambda r: "ratio")
    check("margins", mar, "rate_pct", lambda r: "ratio")


if __name__ == "__main__":
    main()
