import sys; sys.path.append(r"C:/Users/consu/AppData/Local/Packages/PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0/LocalCache/local-packages/Python311/site-packages")
"""Builder shocks_macro: US monetary policy shocks, macro controls and BI policy-shock candidates.

Run (from anywhere):
    python -I code/py/shocks_macro_download.py      # only needed once; skips files already present
    python -I code/py/build_shocks_macro.py         # builds the four outputs and prints validation

Outputs (data/clean/):
    us_shocks_events.csv      long, one row per (event, shock)
    us_shocks_monthly.csv     long, one row per (month, shock), 1990-01..2026-09
    macro_monthly.csv         wide, one column per series, 2005-01..2026-09
    bi_policy_candidates.csv  wide, BI domestic shock candidates, 2005-01..2026-09
Raw inputs are read only; nothing in data/raw is executed.
"""
import os
import datetime
import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
RAW = os.path.join(ROOT, "data", "raw")
SHK = os.path.join(RAW, "shocks")
FRED = os.path.join(RAW, "fred")
MAC = os.path.join(RAW, "macro")
BI = os.path.join(RAW, "bi")
OUT = os.path.join(ROOT, "data", "clean")
os.makedirs(OUT, exist_ok=True)

US_START, US_END = "1990-01-01", "2026-09-01"
MAC_START, MAC_END = "2005-01-01", "2026-09-01"
SAMPLE = ("2009-01-01", "2025-12-01")   # estimation window used for summary statistics
SWITCH_DAY = pd.Timestamp("2016-08-19")
SPLICE_MFG = "2010-01-01"               # first month of the post-break OECD manufacturing index  # BI rate -> BI 7-day reverse repo rate

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 400)
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.append(s)


def mstart(s):
    """Any date-like -> first day of month (Timestamp)."""
    return pd.to_datetime(s).dt.to_period("M").dt.to_timestamp()


# =====================================================================================
# 1. US monetary policy shocks
# =====================================================================================
UNIT_JK = "pp; JK pc1 scaled to the s.d. of the ED4 surprise (% p.a.)"
UNIT_JK_SP = "percent; 100 x log change S&P 500 in 30-min window"
UNIT_USMPD = "pp; surprise normalised to move the 1y Treasury yield one-for-one"
UNIT_BS = "pp; first PC of ED1-ED4 scaled to unit effect on ED4"
UNIT_SW = "standard deviations (factors standardised to unit variance, 1991-2019)"

SHOCK_META = {
    # shock: (source, unit, description, coverage_start, coverage_end)
    "jk_pc1": ("Jarocinski-Karadi update (Oct 2026)", UNIT_JK, "policy surprise factor pc1 (MP1, FF4, ED2-ED4)", "1990-02-01", "2026-09-01"),
    "jk_mp_median": ("Jarocinski-Karadi update (Oct 2026)", UNIT_JK, "pure monetary policy shock, median rotation", "1990-02-01", "2026-09-01"),
    "jk_cbi_median": ("Jarocinski-Karadi update (Oct 2026)", UNIT_JK, "central bank information shock, median rotation", "1990-02-01", "2026-09-01"),
    "jk_mp_pm": ("Jarocinski-Karadi update (Oct 2026)", UNIT_JK, "pure monetary policy shock, poor man's sign restriction", "1990-02-01", "2026-09-01"),
    "jk_cbi_pm": ("Jarocinski-Karadi update (Oct 2026)", UNIT_JK, "central bank information shock, poor man's sign restriction", "1990-02-01", "2026-09-01"),
    "jk_sp500": ("Jarocinski-Karadi update (Oct 2026)", UNIT_JK_SP, "S&P 500 surprise used for the sign restrictions", "1990-02-01", "2026-09-01"),
    "usmpd_stmt": ("SF Fed USMPD, Acosta et al. (2025), mps.csv", UNIT_USMPD, "FOMC statement surprise (30-min window)", "1994-02-01", "2026-09-01"),
    "usmpd_pc": ("SF Fed USMPD, Acosta et al. (2025), mps.csv", UNIT_USMPD, "press conference surprise (70-min window); 0 in months without a press conference", "2011-04-01", "2026-09-01"),
    "usmpd_me": ("SF Fed USMPD, Acosta et al. (2025), mps.csv", UNIT_USMPD, "monetary event surprise = statement + press conference (100-min window)", "1994-02-01", "2026-09-01"),
    "bs_mps": ("Bauer-Swanson (2023), SF Fed update to Dec 2023", UNIT_BS, "monetary policy surprise MPS", "1988-02-01", "2023-12-01"),
    "bs_mps_orth": ("Bauer-Swanson (2023), SF Fed update to Dec 2023", UNIT_BS, "MPS orthogonalised to pre-announcement macro/financial news, event level, summed", "1988-02-01", "2023-12-01"),
    "bs_mps_orth_authors_m": ("Bauer-Swanson (2023), SF Fed update to Dec 2023", UNIT_BS, "authors' MONTHLY MPS_ORTH (sheet 'Monthly (update 2023)', re-orthogonalised at monthly frequency); not a sum of events", "1988-02-01", "2023-12-01"),
    "sw_ffr": ("Swanson (2021, JME) factors", UNIT_SW, "federal funds rate factor", "1991-07-01", "2019-06-01"),
    "sw_fg": ("Swanson (2021, JME) factors", UNIT_SW, "forward guidance factor", "1991-07-01", "2019-06-01"),
    "sw_lsap": ("Swanson (2021, JME) factors", UNIT_SW, "LSAP factor as in col E of the file (col F, its negative, not kept); sign checked against BS 10y note surprise, see note", "1991-07-01", "2019-06-01"),
}


def load_us_events():
    ev = []
    # --- Jarocinski-Karadi, event level -------------------------------------------
    jk = pd.read_csv(os.path.join(SHK, "jk", "shocks_fed_jk_t.csv"))
    jk["ts"] = pd.to_datetime(jk["start"], format="%Y-%m-%d %H:%M")
    ren = {"pc1": "jk_pc1", "MP_median": "jk_mp_median", "CBI_median": "jk_cbi_median",
           "MP_pm": "jk_mp_pm", "CBI_pm": "jk_cbi_pm", "SP500": "jk_sp500"}
    for c, s in ren.items():
        ev.append(pd.DataFrame({"date": jk.ts.dt.normalize(), "time_et": jk.ts.dt.strftime("%H:%M"),
                                "shock": s, "value": jk[c].astype(float)}))
    # --- USMPD constructed surprises (mps.csv) ------------------------------------
    mp = pd.read_csv(os.path.join(SHK, "usmpd", "mps_zip", "mps.csv"), na_values=["NA"])
    mp["Date"] = pd.to_datetime(mp["Date"])
    for c, s in {"STMT": "usmpd_stmt", "PC": "usmpd_pc", "ME": "usmpd_me"}.items():
        x = mp[["Date", c]].rename(columns={"Date": "date", c: "value"})
        if c == "PC":  # NA = statement without a press conference -> no PC event
            x = x.dropna(subset=["value"])
        ev.append(x.assign(time_et="", shock=s))
    # --- Bauer-Swanson FOMC-level ----------------------------------------------
    bs = pd.read_excel(os.path.join(SHK, "bauer_swanson", "monetary-policy-surprises-data.xlsx"),
                       sheet_name="FOMC (update 2023)")
    bs["Date"] = pd.to_datetime(bs["Date"])
    for c, s in {"MPS": "bs_mps", "MPS_ORTH": "bs_mps_orth"}.items():
        t = pd.to_datetime(bs.Time.astype(str).str.strip().str.lower(), format="%I:%M%p", errors="coerce").dt.strftime("%H:%M")
        assert t.notna().all(), "unparsed BS time"
        ev.append(pd.DataFrame({"date": bs.Date, "time_et": t, "shock": s,
                                "value": bs[c].astype(float), "unscheduled": bs.Unscheduled}))
    # --- Swanson (2021) factors -------------------------------------------------
    sw = pd.read_excel(os.path.join(SHK, "swanson", "pre-and-post-ZLB-factors-extended.xlsx"), header=None)
    sw = sw.iloc[2:, 1:6]
    sw.columns = ["date", "ffr", "fg", "lsap", "neg_lsap"]
    sw = sw.dropna(subset=["date"])
    sw["date"] = pd.to_datetime(sw["date"].astype(str).str.replace(" 00:00:00", "", regex=False), format="mixed")
    assert np.allclose(sw.lsap.astype(float), -sw.neg_lsap.astype(float)), "Swanson col F != -col E"
    for c, s in {"ffr": "sw_ffr", "fg": "sw_fg", "lsap": "sw_lsap"}.items():
        ev.append(pd.DataFrame({"date": sw.date, "time_et": "", "shock": s, "value": sw[c].astype(float)}))
    ev = pd.concat(ev, ignore_index=True)
    ev["value"] = ev["value"] + 0.0  # drop negative zeros written as '-0' in the JK files
    ev["source"] = ev.shock.map(lambda s: SHOCK_META[s][0])
    ev["unit"] = ev.shock.map(lambda s: SHOCK_META[s][1])
    ev["unscheduled"] = ev.get("unscheduled")
    ev = ev.sort_values(["date", "time_et", "shock"]).reset_index(drop=True)
    return ev, jk, mp, bs, sw


def us_monthly(ev, bs):
    months = pd.date_range(US_START, US_END, freq="MS")
    ev = ev.assign(month=mstart(ev.date))
    g = ev.groupby(["shock", "month"])
    agg = pd.DataFrame({"value": g.value.sum(min_count=1),
                        "n_events": g.value.size(),
                        "n_missing": g.value.apply(lambda v: v.isna().sum())}).reset_index()
    # a month with any event whose value is missing is set to NaN (not a partial sum)
    agg.loc[agg.n_missing > 0, "value"] = np.nan
    out = []
    for s, (src, unit, desc, c0, c1) in SHOCK_META.items():
        if s == "bs_mps_orth_authors_m":
            continue
        a = agg[agg.shock == s].set_index("month")
        df = pd.DataFrame(index=months)
        df["value"] = a.value.reindex(months)
        df["n_events"] = a.n_events.reindex(months).fillna(0).astype(int)
        inc = (df.index >= c0) & (df.index <= c1)
        df.loc[inc & (df.n_events == 0), "value"] = 0.0
        df.loc[~inc, "value"] = np.nan
        df["in_coverage"] = inc.astype(int)
        df["shock"] = s
        out.append(df)
    # Bauer-Swanson authors' monthly MPS_ORTH (re-orthogonalised at monthly frequency)
    bm = pd.read_excel(os.path.join(SHK, "bauer_swanson", "monetary-policy-surprises-data.xlsx"),
                       sheet_name="Monthly (update 2023)")
    bm["month"] = pd.to_datetime(dict(year=bm.Year, month=bm.Month, day=1))
    bm = bm.set_index("month")
    df = pd.DataFrame(index=months)
    df["value"] = bm.MPS_ORTH.reindex(months)
    nb = agg[agg.shock == "bs_mps"].set_index("month").n_events
    df["n_events"] = nb.reindex(months).fillna(0).astype(int)
    df["in_coverage"] = ((df.index >= "1988-02-01") & (df.index <= "2023-12-01")).astype(int)
    df["shock"] = "bs_mps_orth_authors_m"
    out.append(df)
    m = pd.concat(out).rename_axis("date").reset_index()
    m["source"] = m.shock.map(lambda s: SHOCK_META[s][0])
    m["unit"] = m.shock.map(lambda s: SHOCK_META[s][1])
    m["description"] = m.shock.map(lambda s: SHOCK_META[s][2])
    return m[["date", "shock", "value", "unit", "n_events", "in_coverage", "source", "description"]], bm


def validate_us(ev, m, jk, mp, bs, bm):
    log("\n=== US shocks: validation ===")
    log("events per shock (rows):", ev.groupby("shock").size().to_dict())
    # identities
    log("JK identity max|MP_median+CBI_median-pc1| =", float((jk.MP_median + jk.CBI_median - jk.pc1).abs().max()),
        "; max|MP_pm+CBI_pm-pc1| =", float((jk.MP_pm + jk.CBI_pm - jk.pc1).abs().max()))
    # JK authors' monthly file vs our sums
    jm = pd.read_csv(os.path.join(SHK, "jk", "shocks_fed_jk_m.csv"))
    jm["date"] = pd.to_datetime(dict(year=jm.year, month=jm.month, day=1))
    w = m.pivot(index="date", columns="shock", values="value")
    for a, b in [("pc1_hf", "jk_pc1"), ("MP_median", "jk_mp_median"), ("CBI_median", "jk_cbi_median"),
                 ("MP_pm", "jk_mp_pm"), ("CBI_pm", "jk_cbi_pm"), ("SP500_hf", "jk_sp500")]:
        x = jm.set_index("date")[a]
        y = w[b].reindex(x.index)
        log(f"JK monthly file {a} vs sum of events {b}: n={x.notna().sum()} max abs gap={np.nanmax(np.abs(x - y)):.2e}")
    # BS authors' monthly MPS vs our sums
    for a, b in [("MPS", "bs_mps"), ("MPS_ORTH", "bs_mps_orth")]:
        x = bm[a].reindex(w.index)
        y = w[b]
        both = x.notna() & y.notna()
        gap = (x - y)[both].abs()
        log(f"BS authors' monthly {a} vs our event sum {b} (1990-01..2023-12): n={both.sum()} max abs gap={gap.max():.4f} "
            f"months with gap>1e-6: {(gap > 1e-6).sum()}; corr={x[both].corr(y[both]):.4f}")
        bad = gap[gap > 1e-6]
        if len(bad) and a == "MPS":
            log("   months with MPS gap:", [d.strftime('%Y-%m') for d in bad.index][:20])
        nan_ours = y.index[y.isna() & x.notna() & (y.index <= "2023-12-01")]
        nan_auth = x.index[x.isna() & y.notna()]
        log(f"   NaN in ours but not authors: {[d.strftime('%Y-%m') for d in nan_ours]}; NaN in authors but not ours: {[d.strftime('%Y-%m') for d in nan_auth]}")
    # USMPD counts
    log("USMPD mps.csv events:", len(mp), mp.Date.min().date(), "to", mp.Date.max().date(), "; PC non-missing:", mp.PC.notna().sum(),
        "; max|STMT+PC-ME| over PC events =", float((mp.STMT + mp.PC - mp.ME).abs().max()))
    # sign of the Swanson LSAP factor: correlate with the BS 10y Treasury-note futures surprise
    sw_ev = ev[ev.shock.str.startswith("sw_")].pivot_table(index="date", columns="shock", values="value")
    t10 = bs.set_index("Date")["TNOTE10"].groupby(level=0).sum(min_count=1)
    z = sw_ev.join(t10, how="inner").dropna()
    log(f"Swanson factors vs BS TNOTE10 surprise (n={len(z)}): corr ffr={z.sw_ffr.corr(z.TNOTE10):.3f}, fg={z.sw_fg.corr(z.TNOTE10):.3f}, lsap={z.sw_lsap.corr(z.TNOTE10):.3f}")
    # cross-source event-level correlations on common dates
    d = ev.groupby(["date", "shock"]).value.sum(min_count=1).unstack()
    for a, b in [("jk_pc1", "usmpd_stmt"), ("jk_pc1", "bs_mps"), ("usmpd_stmt", "bs_mps"), ("jk_pc1", "usmpd_me")]:
        z = d[[a, b]].dropna()
        log(f"event-level corr({a},{b}) on {len(z)} common dates = {z[a].corr(z[b]):.3f}")


def summarise_us(m, ev):
    w = m.pivot(index="date", columns="shock", values="value")
    s = w.loc[SAMPLE[0]:SAMPLE[1]]
    cols = ["jk_pc1", "jk_mp_median", "jk_cbi_median", "jk_mp_pm", "jk_cbi_pm", "usmpd_stmt", "usmpd_me",
            "usmpd_pc", "bs_mps", "bs_mps_orth", "bs_mps_orth_authors_m", "sw_ffr", "sw_fg", "sw_lsap"]
    log(f"\n=== US shocks: monthly summary {SAMPLE[0][:7]}..{SAMPLE[1][:7]} ===")
    st = pd.DataFrame({"n_nonmissing": s[cols].notna().sum(), "n_nonzero": (s[cols].fillna(0) != 0).sum(),
                       "mean": s[cols].mean(), "sd": s[cols].std(), "min": s[cols].min(), "max": s[cols].max()})
    log(st.round(4).to_string())
    log("\nPairwise correlations (monthly, pairwise complete):")
    main = ["jk_pc1", "jk_mp_median", "jk_cbi_median", "jk_mp_pm", "jk_cbi_pm", "usmpd_stmt", "usmpd_me", "bs_mps", "bs_mps_orth", "bs_mps_orth_authors_m"]
    log(s[main].corr().round(3).to_string())
    log("\nSame, restricted to 2009-01..2023-12 (all series available, BS ends 2023-12):")
    s2 = w.loc[SAMPLE[0]:"2023-12-01", main]
    log(s2.corr().round(3).to_string())
    log("\nUSMPD pc vs others (2011-04..2025-12):")
    log(w.loc["2011-04-01":SAMPLE[1], ["usmpd_pc", "usmpd_stmt", "usmpd_me", "jk_pc1", "jk_mp_median"]].corr().round(3).to_string())
    return st


# =====================================================================================
# 2. Macro controls
# =====================================================================================
def fred(sid):
    d = pd.read_csv(os.path.join(FRED, f"{sid}.csv"))
    d.columns = ["date", "value"]
    d["date"] = pd.to_datetime(d["date"])
    d["value"] = pd.to_numeric(d["value"], errors="coerce")  # FRED writes '.' or '' for missing
    return d.set_index("date")["value"]


def daily_to_monthly(s, how):
    s = s.dropna()
    g = s.groupby(s.index.to_period("M"))
    r = g.mean() if how == "mean" else g.last()
    r.index = r.index.to_timestamp()
    return r


def bis_series(fn, daily=False):
    d = pd.read_csv(os.path.join(MAC, fn))
    d = d[["TIME_PERIOD", "OBS_VALUE"]].copy()
    d["OBS_VALUE"] = pd.to_numeric(d["OBS_VALUE"], errors="coerce")
    d["date"] = pd.to_datetime(d["TIME_PERIOD"])
    return d.set_index("date")["OBS_VALUE"].sort_index()


def imf_series(fn, filt):
    d = pd.read_csv(os.path.join(MAC, fn), low_memory=False)
    for k, v in filt.items():
        d = d[d[k] == v]
    d = d[["TIME_PERIOD", "OBS_VALUE"]].copy()
    d["date"] = pd.to_datetime(d["TIME_PERIOD"].str.replace("-M", "-", regex=False) + "-01")
    return d.set_index("date")["OBS_VALUE"].astype(float).sort_index()


def oecd_series(fn, filt):
    d = pd.read_csv(os.path.join(MAC, fn))
    for k, v in filt.items():
        d = d[d[k] == v]
    assert d.TIME_PERIOD.is_unique, (fn, filt)
    d = d[["TIME_PERIOD", "OBS_VALUE"]].copy()
    d["date"] = pd.to_datetime(d["TIME_PERIOD"] + "-01")
    return d.set_index("date")["OBS_VALUE"].astype(float).sort_index()


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def seki_row(path, sheet, row_pred, year_row=None, month_row=None, nth=1):
    """Read one data row of a SEKI sheet into a monthly Series (end-of-period values).

    row_pred(label_text) -> bool selects the row (nth match). Column dates come either from a
    datetime row (month_row holding datetimes) or from a year row + month-name row; for the latter
    years are assigned sequentially by block of Jan..Dec and checked against the year labels.
    """
    df = pd.read_excel(path, sheet_name=sheet, header=None)
    lab = df.iloc[:, 1].astype(str).str.strip() + " | " + df.iloc[:, 2].astype(str).str.strip()
    if isinstance(row_pred, int):  # explicit row index
        r = row_pred
    else:
        hits = [i for i in range(len(df)) if row_pred(lab.iloc[i])]
        assert len(hits) == 1 or nth > 1, f"ambiguous SEKI row label in {sheet}: {[lab.iloc[i] for i in hits]}"
        r = hits[nth - 1]
    vals, dates = [], []
    mr = df.iloc[month_row]
    if isinstance(mr.iloc[3], (pd.Timestamp, datetime.datetime)):
        for c in range(3, df.shape[1]):
            if isinstance(mr.iloc[c], (pd.Timestamp, datetime.datetime)):
                dates.append(pd.Timestamp(mr.iloc[c])); vals.append(df.iat[r, c])
    else:
        yr_labels = [(c, int(str(df.iat[year_row, c]).strip())) for c in range(3, df.shape[1])
                     if str(df.iat[year_row, c]).strip().isdigit()]
        year = yr_labels[0][1] - 1
        blocks = []
        for c in range(3, df.shape[1]):
            m = str(mr.iloc[c]).strip()
            if m in MONTHS:
                if m == "Jan":
                    year += 1
                    blocks.append([year, c, c])
                blocks[-1][2] = c
                dates.append(pd.Timestamp(year, MONTHS.index(m) + 1, 1)); vals.append(df.iat[r, c])
        # every year label must sit inside (or one column before) the block assigned to that year
        for c, y in yr_labels:
            blk = [b for b in blocks if b[0] == y]
            assert blk and blk[0][1] - 1 <= c <= blk[0][2], f"SEKI year label {y} at col {c} outside its block {blk} ({sheet})"
    s = pd.Series(pd.to_numeric(pd.Series(vals, dtype=object), errors="coerce").values, index=pd.DatetimeIndex(dates))  # '-' -> NaN
    return s.sort_index(), lab.iloc[r]


def load_seki():
    p1 = os.path.join(BI, "BI_SEKI_TABEL1_25_1.xls")
    p2 = os.path.join(MAC, "BI_SEKI_TABEL1_25_2.xls")
    is_ = lambda txt: (lambda l: l.split(" | ")[-1].startswith(txt) or l.split(" | ")[0].startswith(txt))
    out, labels = {}, {}
    # policy rate (end of period)
    a, la = seki_row(p1, "Th 2002-2009", lambda l: l.startswith("BI Rate"), month_row=6)
    b, lb = seki_row(p1, "Th 2010-2016", lambda l: "Policy Rate" in l, year_row=4, month_row=5)
    c, lc = seki_row(p1, "1.25A_1", lambda l: "Policy Rate" in l, year_row=4, month_row=5)
    out["seki_policy_rate"] = pd.concat([a, b, c]); labels["seki_policy_rate"] = [la, lb, lc]
    # JIBOR 1 month: the '1 Bulan' row after the 'JIBOR' header
    def jibor1m(sheet, year_row=None, month_row=None):
        df = pd.read_excel(p2, sheet_name=sheet, header=None)
        lab = (df.iloc[:, 1].astype(str).str.strip() + " | " + df.iloc[:, 2].astype(str).str.strip())
        h = [i for i in range(len(df)) if "JIBOR" in lab.iloc[i]][0]
        r = [i for i in range(h + 1, h + 4) if "1 Bulan" in lab.iloc[i]][0]
        return seki_row(p2, sheet, r, year_row=year_row, month_row=month_row)
    a, la = jibor1m("Th 2002-2009", month_row=6)
    b, lb = jibor1m("Th 2010-2017", year_row=4, month_row=5)
    c, lc = jibor1m("1.25B", year_row=4, month_row=5)
    out["seki_jibor_1m"] = pd.concat([a, b, c]); labels["seki_jibor_1m"] = [la, lb, lc]
    # guard against picking an SBI/PUAB '1 Bulan' row: JIBOR 1m must exceed the SBI 1m rate on average
    sbi, _ = seki_row(p2, "Th 2002-2009", 10, month_row=6)
    assert (a - sbi).dropna().mean() > 0 and not np.allclose(a.dropna(), sbi.reindex(a.dropna().index)), "JIBOR row looks like SBI"
    d, ld = seki_row(p2, "1.25B", lambda l: "INDONIA 6)" in l, year_row=4, month_row=5)
    out["seki_indonia"] = d; labels["seki_indonia"] = [ld]
    e, le = seki_row(p2, "1.25B", lambda l: l.endswith("30 Hari"), year_row=4, month_row=5)
    out["seki_cindonia_30d"] = e; labels["seki_cindonia_30d"] = [le]
    for k, s in out.items():
        assert s.index.is_unique, k
        out[k] = s.where(s != 0)  # SEKI writes 0 for "not published" (JIBOR 2026, INDONIA pre-Aug 2018)
    return out, labels


def load_policy_daily():
    s = bis_series("bis_cbpol_D_ID.csv")
    raw = s.copy()
    f = s.ffill()
    return raw, f


def build_macro(pol_daily_ff, seki):
    idx = pd.date_range(MAC_START, MAC_END, freq="MS")
    M = pd.DataFrame(index=idx)
    # --- US / global ------------------------------------------------------------
    vix = fred("VIXCLS")
    M["us_vix_avg_index"] = daily_to_monthly(vix, "mean")
    M["us_vix_eom_index"] = daily_to_monthly(vix, "last")
    M["brent_imf_usd_bbl"] = fred("POILBREUSDM")
    M["brent_spot_avg_usd_bbl"] = daily_to_monthly(fred("DCOILBRENTEU"), "mean")
    M["us_indpro_index_2017eq100_sa"] = fred("INDPRO")
    M["us_cpi_index_1982_84eq100_sa"] = fred("CPIAUCSL")
    M["us_cpi_yoy_pct"] = 100 * (fred("CPIAUCSL") / fred("CPIAUCSL").shift(12) - 1)
    M["us_core_cpi_index_1982_84eq100_sa"] = fred("CPILFESL")
    M["us_2y_yield_avg_pct"] = fred("GS2")
    M["us_2y_yield_eom_pct"] = daily_to_monthly(fred("DGS2"), "last")
    M["us_fedfunds_eff_avg_pct"] = pd.read_csv(os.path.join(SHK, "fred", "FEDFUNDS.csv"), index_col=0, parse_dates=True).iloc[:, 0]
    dx = fred("DTWEXBGS")
    M["usd_broad_avg_index_2006jan_eq100"] = daily_to_monthly(dx, "mean")
    M["usd_broad_eom_index_2006jan_eq100"] = daily_to_monthly(dx, "last")
    M["usd_broad_old_avg_index_1997jan_eq100"] = fred("TWEXBMTH")
    M["commodity_all_imf_index_2016eq100"] = fred("PALLFNFINDEXM")
    M["commodity_energy_imf_index_2016eq100"] = fred("PNRGINDEXM")
    M["commodity_nonfuel_imf_index_2016eq100"] = fred("PNFUELINDEXM")
    # --- Indonesia ----------------------------------------------------------------
    # official rate (IMF ER = BI middle rate / JISDOR, matches OECD MEI) as main; BIS XRU kept as alternative
    M["idr_per_usd_avg"] = imf_series("imf_er_M_IDN.csv", {"TYPE_OF_TRANSFORMATION": "PA_RT"})
    M["idr_per_usd_eom"] = imf_series("imf_er_M_IDN.csv", {"TYPE_OF_TRANSFORMATION": "EOP_RT"})
    M["idr_per_usd_avg_bis"] = bis_series("bis_xru_M_ID.csv")
    M["idr_per_usd_eom_bis"] = bis_series("bis_xru_M_ID_eop.csv")
    M["idr_per_usd_avg_pct_chg_mom"] = 100 * np.log(M["idr_per_usd_avg"] / M["idr_per_usd_avg"].shift(1))
    M["idn_neer_broad_index_2020eq100"] = bis_series("bis_eer_M_ID.csv")
    M["idn_cpi_index_2022eq100"] = imf_series("imf_cpi_M_IDN.csv", {"COICOP_1999": "_T", "TYPE_OF_TRANSFORMATION": "IX"})
    M["idn_cpi_yoy_pct"] = imf_series("imf_cpi_M_IDN.csv", {"COICOP_1999": "_T", "TYPE_OF_TRANSFORMATION": "YOY_PCH_PA_PT"})
    M["idn_cpi_mom_pct"] = imf_series("imf_cpi_M_IDN.csv", {"COICOP_1999": "_T", "TYPE_OF_TRANSFORMATION": "POP_PCH_PA_PT"})
    # OECD SDMX manufacturing production (2015=100) has an unspliced level break between 2009-12 and
    # 2010-01 (BPS base change). From 2010-01 use OECD as published; for 2005-01..2009-12 back-cast the
    # NSA index with the growth of FRED IDNPRMNTO01IXOBM (older OECD MEI vintage, consistently spliced;
    # its growth equals IMF PI 'C'). The SA index is left missing before 2010-01.
    o_nsa = oecd_series("oecd_indserv_M_IDN.csv", {"MEASURE": "PRVM", "ACTIVITY": "C", "ADJUSTMENT": "N"})
    o_sa = oecd_series("oecd_indserv_M_IDN.csv", {"MEASURE": "PRVM", "ACTIVITY": "C", "ADJUSTMENT": "Y"})
    fr = fred("IDNPRMNTO01IXOBM")
    t0 = pd.Timestamp(SPLICE_MFG)
    back = (o_nsa.loc[t0] * fr / fr.loc[t0]).loc[:t0 - pd.offsets.MonthBegin(1)]
    M["idn_mfg_prod_index_2015eq100_nsa_spliced"] = pd.concat([back, o_nsa.loc[t0:]])
    M["idn_mfg_prod_index_2015eq100_sa"] = o_sa.loc[t0:]
    M["idn_mfg_prod_yoy_pct"] = 100 * (M["idn_mfg_prod_index_2015eq100_nsa_spliced"] / M["idn_mfg_prod_index_2015eq100_nsa_spliced"].shift(12) - 1)
    # policy rate: raw (as published, with the Aug-2016 instrument switch) and break-adjusted
    raw_eom = daily_to_monthly(pol_daily_ff, "last")
    raw_avg = daily_to_monthly(pol_daily_ff, "mean")
    M["idn_policy_rate_eom_pct"] = raw_eom
    M["idn_policy_rate_avg_pct"] = raw_avg
    M["idn_policy_instrument"] = np.where(M.index < "2016-08-01", "BI Rate",
                                  np.where(M.index > "2016-08-01", "BI 7-day (Reverse) Repo Rate", "switch month (BI Rate to 19-Aug-2016 then BI-7DRR)"))
    M.loc[M.index < "2005-07-01", "idn_policy_instrument"] = ""  # BIS series starts 5-Jul-2005
    M["idn_jibor_1m_eom_pct"] = seki["seki_jibor_1m"]
    M["idn_indonia_eom_pct"] = seki["seki_indonia"]
    M["idn_interbank_3m_oecd_pct"] = oecd_series("oecd_finmark_M_IDN.csv", {"MEASURE": "IR3TIB"})
    M["idn_interbank_call_oecd_pct"] = oecd_series("oecd_finmark_M_IDN.csv", {"MEASURE": "IRSTCI"})
    M = M.loc[MAC_START:MAC_END]
    M.index.name = "date"
    return M


def validate_macro(M, pol_raw, seki):
    log("\n=== Macro: validation ===")
    def cmp(a, b, name, rel=False, start=MAC_START, end=MAC_END):
        a, b = a.loc[start:end], b.reindex(a.index)
        both = a.notna() & b.notna()
        g = (a - b)[both].abs()
        if rel:
            g = (g / b[both].abs()) * 100
        top = g.sort_values(ascending=False).head(3)
        log(f"{name}: n={both.sum()} max abs gap={g.max():.4g}{'%' if rel else ''} mean={g.mean():.4g}{'%' if rel else ''} corr={a[both].corr(b[both]):.5f}"
            f"; largest gaps: {', '.join(f'{k:%Y-%m}:{v:.3g}' for k, v in top.items())}")
    cmp(M.idr_per_usd_avg_bis, M.idr_per_usd_avg, "IDR/USD avg: BIS XRU vs IMF ER PA_RT", rel=True)
    cmp(M.idr_per_usd_eom_bis, M.idr_per_usd_eom, "IDR/USD eom: BIS XRU vs IMF ER EOP_RT", rel=True)
    cmp(M.idr_per_usd_avg, fred("CCUSMA02IDM618N"), "IDR/USD avg: IMF ER vs FRED/OECD CCUSMA02IDM618N", rel=True)
    cmp(M.idr_per_usd_eom, fred("CCUSSP02IDM650N"), "IDR/USD eom: IMF ER vs FRED/OECD CCUSSP02IDM650N (to 2023-12)", rel=True)
    cmp(M.idr_per_usd_avg_bis, daily_to_monthly(bis_series("bis_xru_D_ID.csv"), "mean"), "IDR/USD: BIS monthly avg vs mean of BIS daily", rel=True)
    cmp(M.idn_cpi_yoy_pct, bis_series("bis_cpi_M_ID.csv"), "IDN CPI yoy: IMF vs BIS WS_LONG_CPI 771")
    cmp(M.idn_cpi_yoy_pct, fred("CPALTT01IDM659N"), "IDN CPI yoy: IMF vs OECD CPALTT01IDM659N (to 2025-04)")
    ix = M.idn_cpi_index_2022eq100
    cmp(100 * (ix / ix.shift(12) - 1), M.idn_cpi_yoy_pct, "IDN CPI: yoy recomputed from IMF index vs IMF yoy")
    o_nsa = oecd_series("oecd_indserv_M_IDN.csv", {"MEASURE": "PRVM", "ACTIVITY": "C", "ADJUSTMENT": "N"})
    cmp(o_nsa, fred("IDNPRMNTO01IXOBM"), "IDN mfg production NSA, as published 2005-2009: OECD SDMX vs FRED (break)", rel=True, end="2009-12-01")
    cmp(o_nsa, fred("IDNPRMNTO01IXOBM"), "IDN mfg production NSA 2010-2022: OECD SDMX vs FRED", rel=True, start="2010-01-01", end="2022-12-01")
    cmp(o_nsa, fred("IDNPRMNTO01IXOBM"), "IDN mfg production NSA 2023: OECD SDMX vs FRED (revision)", rel=True, start="2023-01-01", end="2023-12-01")
    sp = M.idn_mfg_prod_index_2015eq100_nsa_spliced
    pi_ix = imf_series("imf_pi_M_IDN.csv", {"PRODUCTION_INDEX": "C", "TYPE_OF_TRANSFORMATION": "IX"})
    cmp(np.log(sp).diff(), np.log(pi_ix).diff(), "IDN mfg production: m/m log growth, spliced index vs IMF PI 'C' (to 2019-04)")
    log(f"   OECD NSA 2009-12 -> 2010-01 as published: {o_nsa.loc['2009-12-01']:.2f} -> {o_nsa.loc['2010-01-01']:.2f}; spliced: {sp.loc['2009-12-01']:.2f} -> {sp.loc['2010-01-01']:.2f}")
    pi = imf_series("imf_pi_M_IDN.csv", {"PRODUCTION_INDEX": "C", "TYPE_OF_TRANSFORMATION": "YOY_PCH_PT"})
    cmp(M.idn_mfg_prod_yoy_pct, pi, "IDN mfg production yoy: OECD vs IMF PI 'C' yoy (to 2019-04)")
    cmp(M.brent_imf_usd_bbl, M.brent_spot_avg_usd_bbl, "Brent: IMF POILBREUSDM vs avg of daily DCOILBRENTEU", rel=True)
    cmp(M.us_2y_yield_avg_pct, daily_to_monthly(fred("DGS2"), "mean"), "US 2y: GS2 vs average of DGS2")
    cmp(M.usd_broad_avg_index_2006jan_eq100, M.usd_broad_old_avg_index_1997jan_eq100, "Dollar: DTWEXBGS avg vs old TWEXBMTH (levels differ by base; corr only)")
    # policy rate
    bism = bis_series("bis_cbpol_M_ID.csv")
    cmp(M.idn_policy_rate_eom_pct, bism, "IDN policy rate: eom of BIS daily vs BIS monthly (eop)")
    cmp(M.idn_policy_rate_eom_pct, seki["seki_policy_rate"], "IDN policy rate: eom of BIS daily vs SEKI I.25 policy rate row (eop)")
    gap = (M.idn_policy_rate_eom_pct - seki["seki_policy_rate"].reindex(M.index)).dropna()
    log("   months where BIS eom != SEKI:", {d.strftime('%Y-%m'): round(v, 3) for d, v in gap[gap.abs() > 1e-9].items()})
    imf = imf_series("imf_mfs_ir_M_IDN.csv", {"INDICATOR": "MFS166_RT_PT_A_PT"})
    cmp(M.idn_policy_rate_eom_pct, imf, "IDN policy rate: eom of BIS daily vs IMF MFS166")
    gap = (M.idn_policy_rate_eom_pct - imf.reindex(M.index)).dropna()
    log("   months where BIS eom != IMF MFS166:", {d.strftime('%Y-%m'): round(v, 3) for d, v in gap[gap.abs() > 1e-9].items()})
    cmp(M.idn_jibor_1m_eom_pct, M.idn_interbank_3m_oecd_pct, "JIBOR 1m (SEKI eom) vs OECD 3m interbank (level diff expected)")
    log("coverage (first..last non-missing) per column:")
    for c in M.columns:
        s = M[c].replace("", np.nan).dropna()
        log(f"   {c}: {s.index.min():%Y-%m}..{s.index.max():%Y-%m} n={len(s)}" if len(s) else f"   {c}: EMPTY")


# =====================================================================================
# 3. BI domestic shock candidates
# =====================================================================================
def build_bi(pol_raw, pol_ff, seki, M):
    log("\n=== BI policy candidates ===")
    # Clean the daily series: one data error in BIS. BI raised the BI Rate to 7.75% at the extra Board
    # meeting of 18-Nov-2014 and held it until the 17-Feb-2015 cut; there was no Board decision on
    # 25-Nov or 1-Dec-2014. BIS shows 7.50 on 25-28 Nov 2014 (a -25bp/+25bp round trip); BI's own SEKI
    # Table I.25 shows 7.75 at end-Nov-2014. IMF MFS166 (7.50 for Nov-2014) evidently carries the same
    # error. We set 25-30 Nov 2014 to 7.75. The assertion makes a rerun fail loudly if BIS revises it.
    ff = pol_ff.copy()
    log("BIS daily 15-Nov..5-Dec-2014:", {d.strftime('%m-%d'): v for d, v in pol_raw.loc["2014-11-15":"2014-12-05"].dropna().items()})
    seki_nov = seki["seki_policy_rate"].get(pd.Timestamp("2014-11-01"))
    imf_nov = imf_series("imf_mfs_ir_M_IDN.csv", {"INDICATOR": "MFS166_RT_PT_A_PT"}).get(pd.Timestamp("2014-11-01"))
    log(f"   SEKI eop Nov-2014 = {seki_nov}; IMF MFS166 Nov-2014 = {imf_nov}")
    expected = {"2014-11-24": 7.75, "2014-11-25": 7.5, "2014-11-28": 7.5, "2014-12-01": 7.75}
    assert all(abs(ff.loc[k] - v) < 1e-9 for k, v in expected.items()), "BIS Nov-2014 pattern changed: review the correction"
    ff.loc["2014-11-25":"2014-11-30"] = 7.75
    fix_applied = True
    log("   correction 25-30 Nov 2014 -> 7.75 applied:", fix_applied)

    d = ff.diff()
    d = d[d.abs() > 1e-9]
    switch = d.loc[[SWITCH_DAY]] if SWITCH_DAY in d.index else pd.Series(dtype=float)
    log("raw daily change on 19-Aug-2016 (instrument switch, not a policy move):", switch.to_dict())
    dec = d.drop(index=SWITCH_DAY, errors="ignore")
    dec = dec.loc["2005-07-06":]  # first obs 5-Jul-2005 is the start of the series, not a decision
    log(f"policy-rate change days (excl. switch): {len(dec)}; hikes {int((dec > 0).sum())}, cuts {int((dec < 0).sum())}")
    log("   ", {k.strftime('%Y-%m-%d'): v for k, v in dec.items()})

    # break-adjusted daily level: cumulate daily changes with the switch-day jump set to 0;
    # anchored so that it equals the BI-7DRR from 19-Aug-2016 on (pre-switch BI Rate shifted by -1.25 pp)
    dd = ff.diff().fillna(0.0)
    dd.loc[SWITCH_DAY] = 0.0
    adj = ff.iloc[0] + dd.cumsum()
    shift = float(ff.loc[SWITCH_DAY] - adj.loc[SWITCH_DAY])
    adj = adj + shift
    assert np.allclose(adj.loc[SWITCH_DAY:], ff.loc[SWITCH_DAY:]), "adjusted level must equal 7DRR after switch"
    assert np.allclose(adj.loc[:"2016-08-18"] - ff.loc[:"2016-08-18"], shift), "constant shift before the switch"
    log(f"break adjustment: pre-switch BI Rate shifted by {shift:+.2f} pp (only changes are meaningful)")

    idx = pd.date_range(MAC_START, MAC_END, freq="MS")
    B = pd.DataFrame(index=idx)
    B.index.name = "date"
    B["policy_rate_eom_raw_pct"] = daily_to_monthly(ff, "last")
    B["policy_rate_avg_raw_pct"] = daily_to_monthly(ff, "mean")
    B["policy_rate_eom_adj_pct"] = daily_to_monthly(adj, "last")
    B["policy_rate_avg_adj_pct"] = daily_to_monthly(adj, "mean")
    B["policy_instrument"] = M["idn_policy_instrument"].reindex(idx)
    B["data_note"] = ""
    if fix_applied:
        B.loc["2014-11-01", "data_note"] = "BIS daily shows 7.50 on 25-28 Nov 2014 (data error); set to 7.75 (SEKI I.25, BI Board decisions)"
    B.loc["2016-08-01", "data_note"] = "19-Aug-2016 switch BI Rate 6.50 -> BI-7DRR 5.25 is not a policy move; adjusted change = 0"
    # (a) monthly changes
    B["d_policy_eom_raw_pp"] = B.policy_rate_eom_raw_pct.diff()
    B["d_policy_eom_adj_pp"] = B.policy_rate_eom_adj_pct.diff()
    B["d_policy_avg_adj_pp"] = B.policy_rate_avg_adj_pct.diff()
    # (b) decisions from the daily series
    dm = dec.groupby(dec.index.to_period("M"))
    B["decision_month"] = 0
    B["n_rate_changes"] = 0
    B["decision_size_pp"] = 0.0
    B["decision_dates"] = ""
    for p, g in dm:
        t = p.to_timestamp()
        if t in B.index:
            B.loc[t, "decision_month"] = 1
            B.loc[t, "n_rate_changes"] = len(g)
            B.loc[t, "decision_size_pp"] = g.sum()
            B.loc[t, "decision_dates"] = ";".join(f"{k:%Y-%m-%d}({v:+.2f})" for k, v in g.items())
    B.loc[B.index < "2005-08-01", ["decision_month", "n_rate_changes", "decision_size_pp"]] = np.nan  # series starts 5-Jul-2005
    B["decision_sign"] = np.sign(B["decision_size_pp"])
    # (c) interbank
    B["jibor_1m_eom_pct"] = seki["seki_jibor_1m"].reindex(idx)
    B["d_jibor_1m_pp"] = B.jibor_1m_eom_pct.diff()
    B["d_jibor_1m_decision_pp"] = np.where(B.decision_month == 1, B.d_jibor_1m_pp, np.where(B.decision_month == 0, 0.0, np.nan))
    B.loc[B.d_jibor_1m_pp.isna(), "d_jibor_1m_decision_pp"] = np.nan
    B["d_jibor_1m_minus_d_policy_pp"] = B.d_jibor_1m_pp - B.d_policy_eom_adj_pp
    B["indonia_eom_pct"] = seki["seki_indonia"].reindex(idx)
    B["d_indonia_pp"] = B.indonia_eom_pct.diff()
    B["d_indonia_decision_pp"] = np.where(B.decision_month == 1, B.d_indonia_pp, np.where(B.decision_month == 0, 0.0, np.nan))
    B.loc[B.d_indonia_pp.isna(), "d_indonia_decision_pp"] = np.nan

    # validation
    s = B.loc[SAMPLE[0]:SAMPLE[1]]
    log(f"sum of daily decision sizes == monthly change of adjusted eom level: max abs gap = "
        f"{(B.decision_size_pp - B.d_policy_eom_adj_pp).loc['2005-08-01':].abs().max():.2e}")
    log(f"Aug-2016: raw eom change {B.loc['2016-08-01','d_policy_eom_raw_pp']:+.2f}, adjusted {B.loc['2016-08-01','d_policy_eom_adj_pp']:+.2f}")
    log(f"{SAMPLE[0][:7]}..{SAMPLE[1][:7]}: decision months {int(s.decision_month.sum())} of {len(s)}; hikes {int((s.decision_size_pp>0).sum())}, cuts {int((s.decision_size_pp<0).sum())}; "
        f"months with >1 change {int((s.n_rate_changes>1).sum())}")
    log(f"   sd d_policy_eom_adj_pp={s.d_policy_eom_adj_pp.std():.4f}; sd d_jibor_1m_pp={s.d_jibor_1m_pp.std():.4f}; sd d_jibor_1m_decision_pp={s.d_jibor_1m_decision_pp.std():.4f}")
    dmask = s.decision_month == 1
    log(f"   corr(d_jibor_1m, decision_size) in decision months = {s.loc[dmask,'d_jibor_1m_pp'].corr(s.loc[dmask,'decision_size_pp']):.3f} (n={int(dmask.sum())});"
        f" OLS slope = {np.polyfit(s.loc[dmask,'decision_size_pp'], s.loc[dmask,'d_jibor_1m_pp'], 1)[0]:.3f}")
    log(f"   corr(d_jibor_1m, d_policy_eom_adj) all months = {s.d_jibor_1m_pp.corr(s.d_policy_eom_adj_pp):.3f}; "
        f"sd of d_jibor_1m in non-decision months = {s.loc[~dmask,'d_jibor_1m_pp'].std():.4f}")
    log("   JIBOR 1m missing months in sample:", [d.strftime('%Y-%m') for d in s.index[s.jibor_1m_eom_pct.isna()]])
    return B, fix_applied


def us_shock_vs_bi(m, B):
    w = m.pivot(index="date", columns="shock", values="value")
    s = B.join(w[["jk_mp_median", "jk_pc1", "usmpd_stmt"]]).loc[SAMPLE[0]:SAMPLE[1]]
    log("\n=== Cross-check: BI candidates vs US shocks (2009-2025, monthly) ===")
    log(s[["d_policy_eom_adj_pp", "decision_size_pp", "d_jibor_1m_pp", "jk_mp_median", "jk_pc1", "usmpd_stmt"]].corr().round(3).to_string())


def main():
    ev, jk, mp, bs, sw = load_us_events()
    m, bm = us_monthly(ev, bs)
    validate_us(ev, m, jk, mp, bs, bm)
    summarise_us(m, ev)
    evo = ev[["date", "time_et", "shock", "value", "unit", "source", "unscheduled"]].copy()
    evo["date"] = evo.date.dt.strftime("%Y-%m-%d")
    evo.to_csv(os.path.join(OUT, "us_shocks_events.csv"), index=False, float_format="%.10g")
    mo = m.copy()
    mo["date"] = mo.date.dt.strftime("%Y-%m-%d")
    mo.to_csv(os.path.join(OUT, "us_shocks_monthly.csv"), index=False, float_format="%.10g")

    seki, labels = load_seki()
    log("\nSEKI rows used:", labels)
    for k, s in seki.items():
        s2 = s.dropna()
        log(f"   {k}: {s2.index.min():%Y-%m}..{s2.index.max():%Y-%m} n={len(s2)}")
    pol_raw, pol_ff = load_policy_daily()
    M = build_macro(pol_ff, seki)
    validate_macro(M, pol_raw, seki)
    B, fixed = build_bi(pol_raw, pol_ff, seki, M)
    if fixed:  # use the corrected daily series for the macro policy-rate columns as well
        ff = pol_ff.copy(); ff.loc["2014-11-25":"2014-11-30"] = 7.75
        M["idn_policy_rate_eom_pct"] = daily_to_monthly(ff, "last").reindex(M.index)
        M["idn_policy_rate_avg_pct"] = daily_to_monthly(ff, "mean").reindex(M.index)
        M["idn_policy_rate_eom_adj_pct"] = B.policy_rate_eom_adj_pct
        M["idn_policy_rate_avg_adj_pct"] = B.policy_rate_avg_adj_pct
    us_shock_vs_bi(m, B)
    Mo = M.copy(); Mo.index = Mo.index.strftime("%Y-%m-%d")
    Mo.to_csv(os.path.join(OUT, "macro_monthly.csv"), float_format="%.6g")
    Bo = B.copy(); Bo.index = Bo.index.strftime("%Y-%m-%d")
    Bo.to_csv(os.path.join(OUT, "bi_policy_candidates.csv"), float_format="%.6g")
    log("\nwrote:", [os.path.join(OUT, f) for f in ["us_shocks_events.csv", "us_shocks_monthly.csv", "macro_monthly.csv", "bi_policy_candidates.csv"]])
    log("rows:", len(evo), len(mo), len(Mo), len(Bo))


if __name__ == "__main__":
    main()
