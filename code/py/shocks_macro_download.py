import sys; sys.path.append(r"C:/Users/consu/AppData/Local/Packages/PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0/LocalCache/local-packages/Python311/site-packages")
"""Builder shocks_macro, step 0: download the open macro series used by build_shocks_macro.py.

Every file is fetched with a plain GET (no custom headers except the documented SDMX
`Accept` content-type for the IMF API) from a documented public endpoint and saved verbatim
under data/raw/fred/ or data/raw/macro/. A manifest (url, saved file, UTC time, bytes,
sha256, http status) is written to data/raw/macro/download_manifest_shocks_macro.csv.

Usage:  python -I code/py/shocks_macro_download.py [--force]
Without --force, files that already exist are not downloaded again (rerunnable).
"""
import hashlib, os, time, datetime as dt
import requests
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
RAW_FRED = os.path.join(ROOT, "data", "raw", "fred")
RAW_MACRO = os.path.join(ROOT, "data", "raw", "macro")
FORCE = "--force" in sys.argv

FRED_IDS = [
    # US / global
    "VIXCLS",            # CBOE VIX, daily close
    "POILBREUSDM",       # Brent, IMF PCPS, USD/bbl monthly average
    "DCOILBRENTEU",      # Brent spot (EIA), daily
    "INDPRO",            # US industrial production index 2017=100, SA
    "CPIAUCSL",          # US CPI-U all items, SA
    "CPILFESL",          # US core CPI, SA
    "GS2",               # 2y Treasury CMT, monthly average
    "DGS2",              # 2y Treasury CMT, daily
    "DTWEXBGS",          # nominal broad dollar index, daily (from 2006-01)
    "TWEXBMTH",          # old broad dollar index, monthly, discontinued (for 2005 back-fill check)
    "PALLFNFINDEXM",     # IMF global price index of all commodities, 2016=100
    "PNRGINDEXM",        # IMF global price index of energy
    "PNFUELINDEXM",      # IMF non-fuel commodities
    "EFFR",              # effective fed funds rate, daily (for reference)
    # Indonesia (OECD MEI / IMF via FRED)
    "CCUSMA02IDM618N",   # IDR per USD, monthly average (OECD MEI)
    "CCUSSP02IDM650N",   # IDR per USD, end of month (OECD MEI)
    "IDNCPIALLMINMEI",   # Indonesia CPI all items index 2015=100 (OECD MEI)
    "CPALTT01IDM659N",   # Indonesia CPI, growth same period previous year (OECD MEI)
    "CPALTT01IDM657N",   # Indonesia CPI, growth previous period (OECD MEI)
    "IDNPROINDMISMEI",   # Indonesia production of total industry (OECD MEI)
    "IDNPRMNTO01IXOBM",  # Indonesia manufacturing production index (OECD MEI)
    "IDNSLRTTO01IXOBM",  # Indonesia retail trade volume (OECD MEI)
    "IR3TIB01IDM156N",   # Indonesia 3-month interbank rate (OECD MEI)
    "IRSTCI01IDM156N",   # Indonesia immediate (call money / interbank) rate (OECD MEI)
    "INTDSRIDM193N",     # Indonesia discount rate (IMF IFS), discontinued 2013
]

# IMF SDMX 2.1 (documented: https://api.imf.org/external/sdmx/2.1/), CSV via documented Accept type.
IMF_CSV = {"Accept": "application/vnd.sdmx.data+csv;version=1.0.0"}
IMF_QUERIES = {
    # key = COUNTRY.INDEX_TYPE.COICOP_1999.TYPE_OF_TRANSFORMATION.FREQUENCY (DSD_CPI 5.0.0)
    "imf_cpi_M_IDN.csv": "https://api.imf.org/external/sdmx/2.1/data/IMF.STA,CPI/IDN.CPI._T.IX+YOY_PCH_PA_PT+POP_PCH_PA_PT.M",
    # key = COUNTRY.INDICATOR.TYPE_OF_TRANSFORMATION.FREQUENCY (DSD_ER_PUB 4.0.0)
    "imf_er_M_IDN.csv": "https://api.imf.org/external/sdmx/2.1/data/IMF.STA,ER/IDN.XDC_USD.EOP_RT+PA_RT.M",
    # key = COUNTRY.PRODUCTION_INDEX.TYPE_OF_TRANSFORMATION.FREQUENCY (DSD_IPI 8.0.0); IDN stops 2019-04
    "imf_pi_M_IDN.csv": "https://api.imf.org/external/sdmx/2.1/data/IMF.STA,PI/IDN...M",
}
# OECD SDMX REST (documented: https://sdmx.oecd.org/public/rest/), short-term economic statistics
OECD_QUERIES = {
    "oecd_indserv_M_IDN.csv": "https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_INDSERV,/IDN.M.......?format=csvfilewithlabels",
    "oecd_finmark_M_IDN.csv": "https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_FINMARK,/IDN.M.......?format=csvfilewithlabels",
}
# BIS stats API (documented SDMX REST v1)
BIS_QUERIES = {
    "bis_cbpol_D_ID.csv": "https://stats.bis.org/api/v1/data/WS_CBPOL/D.ID/all?format=csv",
    "bis_cbpol_M_ID.csv": "https://stats.bis.org/api/v1/data/WS_CBPOL/M.ID/all?format=csv",
    "bis_xru_M_ID.csv": "https://stats.bis.org/api/v1/data/WS_XRU/M.ID.IDR.A/all?format=csv",
    "bis_xru_M_ID_eop.csv": "https://stats.bis.org/api/v1/data/WS_XRU/M.ID.IDR.E/all?format=csv",
    "bis_xru_D_ID.csv": "https://stats.bis.org/api/v1/data/WS_XRU/D.ID.IDR.A/all?format=csv",
    "bis_eer_M_ID.csv": "https://stats.bis.org/api/v1/data/WS_EER/M.N.B.ID/all?format=csv",
    "bis_cpi_M_ID.csv": "https://stats.bis.org/api/v1/data/WS_LONG_CPI/M.ID.771/all?format=csv",
    "bis_cpi_index_M_ID.csv": "https://stats.bis.org/api/v1/data/WS_LONG_CPI/M.ID.628/all?format=csv",
}

manifest = []


def fetch(url, dest, headers=None):
    if os.path.exists(dest) and not FORCE:
        manifest.append(dict(url=url, file=os.path.relpath(dest, ROOT), status="cached",
                             utc=None, bytes=os.path.getsize(dest), sha256=sha(dest)))
        return True
    try:
        r = requests.get(url, headers=headers, timeout=120)
    except Exception as e:  # record and move on
        manifest.append(dict(url=url, file="", status=f"error {type(e).__name__}", utc=now(), bytes=0, sha256=""))
        print("ERR", url, e)
        return False
    ok = r.status_code == 200 and len(r.content) > 50
    if ok:
        with open(dest, "wb") as f:
            f.write(r.content)
    manifest.append(dict(url=url, file=os.path.relpath(dest, ROOT) if ok else "", status=r.status_code,
                         utc=now(), bytes=len(r.content), sha256=sha(dest) if ok else ""))
    print(r.status_code, len(r.content), url)
    time.sleep(1.0)
    return ok


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    os.makedirs(RAW_FRED, exist_ok=True)
    os.makedirs(RAW_MACRO, exist_ok=True)
    for sid in FRED_IDS:
        fetch(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", os.path.join(RAW_FRED, f"{sid}.csv"))
    for fn, url in IMF_QUERIES.items():
        fetch(url, os.path.join(RAW_MACRO, fn), headers=IMF_CSV)
    for fn, url in OECD_QUERIES.items():
        fetch(url, os.path.join(RAW_MACRO, fn))
    for fn, url in BIS_QUERIES.items():
        fetch(url, os.path.join(RAW_MACRO, fn))
    # Retrieved once with the WebFetch tool (bi.go.id resets plain python connections), not by this script.
    seki = os.path.join(RAW_MACRO, "BI_SEKI_TABEL1_25_2.xls")
    if os.path.exists(seki):
        manifest.append(dict(url="https://www.bi.go.id/SEKI/tabel/TABEL1_25_2.xls", file=os.path.relpath(seki, ROOT),
                             status="WebFetch 2026-10-29 (manual)", utc="2026-10-29", bytes=os.path.getsize(seki),
                             sha256=sha(seki)))
    mpath = os.path.join(RAW_MACRO, "download_manifest_shocks_macro.csv")
    new = pd.DataFrame(manifest)
    if os.path.exists(mpath):  # keep first-download timestamps for cached files
        old = pd.read_csv(mpath)
        old = old[old["file"].notna() & (old["status"].astype(str) != "cached")]
        cached = new["status"] == "cached"
        keep = old[old["url"].isin(new.loc[cached, "url"])]
        missing = new[cached & ~new["url"].isin(keep["url"])]
        new = pd.concat([keep, missing, new[~cached]], ignore_index=True).drop_duplicates("url", keep="last")
    new.to_csv(mpath, index=False)
    print("manifest:", mpath)
