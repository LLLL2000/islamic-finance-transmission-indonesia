# Shock-side data: US monetary policy shocks, policy rates, exchange-rate regimes

Downloaded 2026-10-29. Each source file was fetched with a plain GET from a documented public link or API. No login, key or bot-challenge bypass was used.
The scripts that read these files are in `../scripts/` and are run with `python -I`.

## 1. US high-frequency monetary policy shocks

### 1a. Jarocinski-Karadi (2020) update, `jk/`
Source: https://github.com/marekjarocinski/jkshocks_update_fed. The latest commit is dated 2026-10-11, with the message "update Fed shocks until September 2026". Licence: CC BY 4.0.

| file | content |
|---|---|
| `shocks_fed_jk_t.csv` | 334 FOMC announcements, indexed by `start` (date-time ET). Coverage: 1990-02-08 11:30 to 2026-09-16 14:00. On 1991-02-01 and 2005-05-03 there are 2 events in a single day. |
| `shocks_fed_jk_m.csv` | Monthly, 1990-02 to 2026-09 (440 months). Equals the sum within each month, and is 0 when the month has no FOMC event. The columns are `year, month, pc1_hf, SP500_hf, MP_pm, CBI_pm, MP_median, CBI_median`. |
| `fomc_surprises_jk.csv` | Raw 30-minute surprises, 385 events from 1987-11-04 to 2026-09-16. The columns are `start, Event, FF1-FF4, MP1, ED1-ED4, TFUT02/05/10/30, SP500, SP500FUT, EUR`. ED is the SOFR futures rate from 2022 on. |
| `README.md` | Authors' README with the full definitions. |

Columns:
- `pc1`: the first principal component of the MP1, FF4, ED2, ED3 and ED4 surprises. It is scaled to the standard deviation of ED4, in % p.a.
- `SP500`: 100 x the log change in the S&P 500.
- `MP_pm` and `CBI_pm`: the "poor man's" sign-restriction split, where only one shock is present per event. `MP_pm + CBI_pm = pc1`.
- `MP_median` and `CBI_median`: the median-rotation split, where both shocks can be present. `MP_median + CBI_median = pc1`.
- MP is the **pure monetary policy** shock: rates and stocks move in opposite directions.
- CBI is the **central bank information** shock: rates and stocks move in the same direction.

### 1b. Acosta, Ajello, Bauer, Loria and Miranda-Agrippino (2025), the SF Fed "USMPD", `usmpd/`
Sources: https://www.frbsf.org/research-and-insights/data-and-indicators/us-monetary-policy-event-study-database/ and https://www.frbsf.org/wp-content/uploads/USMPD.xlsx. The README sheet says "Last update: 17 September 2026".

`USMPD.xlsx` sheets:
- **Statements**: 279 events, 1994-02-04 to 2026-09-16. Window is 30 minutes (-10 to +20).
- **Press Conferences**: 95 events, 2011-04-27 to 2026-09-16. Window is 70 minutes.
- **Monetary Events**: 279 events, 1994-02-04 to 2026-09-16. Window is 100 minutes and covers statement plus press conference.
- **Minutes**: 206 events, 2001-02-01 to 2026-08-19.

Columns:
- Indicator dummies: `SEP`, `Unscheduled`, `PC`.
- Futures surprises: `MP1`, `MP2`, `FF1-FF6`, `ED1-ED8` (Eurodollar to 2021, SOFR from 2022).
- Yield changes: `OIS1Y`, `OIS2Y`, `UST3M/6M/2Y/5Y/10Y/30Y`, `TIPS5Y/10Y/30Y`.
- Returns: `SP500`, `SPFUT`, `DXY`, `EURUSD`, `USDJPY`.
- Units: rates are in percentage points and returns in percent.

`monetary-policy-surprises.zip` was extracted to `mps_zip/`. It contains the authors' constructed surprise series:
- `mps.csv`: `Date, STMT, PC, ME`. 279 rows, 1994-02-04 to 2026-09-16. The surprises are normalised to move the 1-year Treasury yield one-for-one, in pp. PC is NA before 2011.
- `mps_minutes.csv`: `Date, MIN`. 174 rows, 2005-01-04 to 2026-08-19.
- `y1.csv`: the daily 1-year GSW yield `SVENY01` used for the normalisation.
- `mps.R` and `gss.R`: the authors' R code, including GSS target and path factors. **They were not executed.**

`usmpd-chart*.csv` hold only the web-chart data.

### 1c. Bauer-Swanson (2023) "Reassessment", `bauer_swanson/`
Source: https://www.frbsf.org/research-and-insights/data-and-indicators/monetary-policy-surprises/ and the file https://www.frbsf.org/wp-content/uploads/monetary-policy-surprises-data.xlsx. **This update stops in Dec 2023.** The change log's last entry is 10/11/2024.

`monetary-policy-surprises-data.xlsx` sheets:
- `FOMC (update 2023)`: 361 announcements, 1988-02-04 to 2023-12-13. Contains `Unscheduled`, `FF1, FF2`, `ED1-ED4` (SOFR SFR2-5 from 2023), `SP500`, `TNOTE02/05/10`, `TBOND`, `MPS`, `MPS_ORTH`, and the six orthogonalisation regressors `NFP_SURP, NFP_12M, SP500_3M, SLOPE_3M, BCOM_3M, TR_SKEW`.
- `Monthly (update 2023)`: 1988-02 to 2023-12.
- `FOMC (original)`: to 2019-12-11.
- `Monthly (original)`: 1973-01 to 2020-02.

Variables:
- `MPS` is the first principal component of ED1-ED4, scaled so that it has a unit effect on ED4.
- `MPS_ORTH` is the residual of MPS on the six macro and financial news variables. It is NA for Mar-Dec 2020.

The remaining files:
- `FOMC_Bauer_Swanson_original.xlsx` is the originally published file, from https://www.michaeldbauer.com/files/FOMC_Bauer_Swanson.xlsx.
- `chart1-monetary-policy-surprises.csv` holds the web-chart data in basis points, 2012-01-25 to 2023-12-13.

### 1d. Swanson (2021, JME) three factors, `swanson/`
Source: https://sites.socsci.uci.edu/~swanson2/papers/pre-and-post-ZLB-factors-extended.xlsx. The file covers 241 FOMC announcements from 1991-07-05 to 2019-06-19, and it has **not been updated since 2019**. The data sit in rows 3 onward of the sheet.

| column | content |
|---|---|
| col B | date |
| col C | Federal Funds Rate factor |
| col D | Forward Guidance factor |
| col E | LSAP factor |
| col F | minus the LSAP factor (sign-flipped) |

The factors are standardised to unit variance.

### 1e. Harmonised files I built, `derived/`
These come from `../scripts/build_shock_panel.py`.

- `us_mp_shocks_event_level.csv`: one row per calendar day with any event, 380 days from 1988-02-04 to 2026-09-16. When a source has two events on the same day, they are summed.
  - Prefixes: `jk_` is Jarocinski-Karadi, `abblm_` is Acosta et al. 2025, `bs_` is Bauer-Swanson, `sw_` is Swanson factors.
- `us_mp_shocks_monthly.csv`: the calendar-month sum, 1988-02 to 2026-09.
  - A month with no event is 0 inside each source's coverage.
  - Event months with a missing value stay NaN, for example `bs_mps_orth` in 2020.
  - Outside each source's coverage the value is blank.
  - For BS, the authors' own monthly `MPS_ORTH`, which is re-orthogonalised at monthly frequency, is preferable to my summed version.

Consistency check on the 253 common events: corr(jk_pc1, abblm_stmt) = 0.98, corr(jk_pc1, bs_mps) = 0.95, corr(abblm_stmt, bs_mps) = 0.96. For 2024-2026 (22 events), corr(jk_pc1, abblm_stmt) = 0.998.

## 2. Policy rates

### 2a. BIS central bank policy rates (WS_CBPOL), `bis_cbpol/`
The documented SDMX API is at `https://stats.bis.org/api/v1/data/WS_CBPOL/{FREQ}.{ISO2}/all?format=csv`. The columns are `FREQ, REF_AREA, ..., TITLE, TIME_PERIOD, OBS_VALUE`. Monthly values are end of period.

| country | daily | monthly | definition (COMPILATION) |
|---|---|---|---|
| US | 1954-07-01 to 2026-10-27 | 1954-07 to 2026-09 | midpoint of the fed funds target from 19 Dec 1985 |
| MY | 1995-11-03 to 2026-10-26 | 1995-11 to 2026-09 | OPR from 26 Apr 2004; before that the 3-month intervention rate, and the 3-month interbank rate before 1998 |
| ID | 2005-07-05 to 2026-10-19 | 2005-07 to 2026-09 | BI rate, then the 7-day reverse repo from 19 Aug 2016 |
| TR | 2002-02-20 to 2026-10-23 | 2002-02 to 2026-09 | overnight borrowing rate, then the 1-week repo from 20 May 2010 |
| SA | 2000-01-31 to 2026-10-13 | 2000-01 to 2026-09 | official repo rate |
| KW | 2002-06-03 to 2026-10-27 | 2002-06 to 2026-09 | CBK discount rate |

PK, AE, QA, BH, OM and JO are **not in BIS CBPOL**: the API returns 404.

### 2b. IMF MFS_IR (monetary statistics, interest rates), `imf/`
The documented SDMX 2.1 API, with no key needed, is `https://api.imf.org/external/sdmx/2.1/data/IMF.STA,MFS_IR/{ISO3}..M`, requested with the header `Accept: application/vnd.sdmx.data+csv;version=1.0.0`. The structure is in `mfs_ir_dsd*.xml`. Indicator codes:

| code | meaning |
|---|---|
| MFS166 | monetary-policy-related rate |
| DISR | discount rate |
| MMRT | money market rate |
| MFS135 | deposit rate |
| MFS162 | lending rate |
| MFS174 | savings rate |
| MFS135_OVNGT | overnight deposit rate (for Qatar this is the QCB deposit rate) |

Policy-relevant coverage:

| country | series and coverage |
|---|---|
| PAK | DISR 1964-01 to 2021-12; MMRT to 2021-11. The IMF series stops at 2021-12. |
| QAT | MFS166 2002-06 to 2026-08; overnight deposit 2002-06 to 2026-08; MMRT 2004-07 to 2026-08 |
| KWT | DISR 1975-01 to 2026-08; MMRT 1979-01 to 2026-08 |
| OMN | DISR 1980-01 to 2018-10; MMRT 2004-01 to 2022-04. The IMF series stops in 2022. |
| JOR | MFS166 2004-02 to 2026-08; DISR 1966-01 to 2026-08; MMRT 1999-01 to 2026-08 |
| MYS | MFS166 2001-12 to 2026-05; MMRT 1971-01 to 2026-08; deposit and lending rates to 2026-08 |
| IDN | MFS166 1990-01 to 2026-07; deposit and lending rates to 2026-07 |
| TUR | MFS166 1986-04 to 2026-08; DISR to 2026-08 |
| USA | MFS166 1982-09 to 2025-10 |
| SAU, ARE, BHR | **no observations** in MFS_IR at M, Q or A frequency |

### 2c. FRED, `fred/`
Each file comes from `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<ID>`.

| series | coverage |
|---|---|
| FEDFUNDS | 1954-07 to 2026-09 |
| DFF | 1954-07-01 to 2026-10-27 |
| DFEDTAR | 1982-09-27 to 2008-12-15 |
| DFEDTARU and DFEDTARL | 2008-12-16 to 2026-10-29 |
| GS1 and DGS1 | 1-year Treasury yield, to 2026-09 and 2026-10-27 |
| DGS2 | 2-year Treasury yield, to 2026-10-27 |
| INTDSRSAM193N | IMF discount rate for Saudi Arabia, 1999-01 to 2013-03, discontinued |
| INTDSRIDM193N | IMF discount rate for Indonesia, 1990-01 to 2013-04, discontinued |
| INTDSRTRM193N | IMF discount rate for Turkey, 1964-01 to 2026-08 |

FRED has no discount-rate series (`INTDSR..M193N`) for PK, AE, QA, BH, OM, JO, KW or MY.

### 2d. `derived/policy_rates_monthly_panel.csv`
Built by `../scripts/build_rate_panel.py`. It is a wide monthly panel, 1985-01 to 2026-09, combining the BIS and IMF series above. Columns are named `<ISO3>_<source>`.

### Blocked or unavailable central-bank sites
| site | result |
|---|---|
| centralbank.ae (UAE) | Cloudflare "Just a moment" (403): BLOCKED |
| sbp.org.pk (Pakistan) | Cloudflare "Attention Required" (403): BLOCKED |
| cbb.gov.bh (Bahrain) | HTTP 403: BLOCKED |
| cbo.gov.om (Oman) | Reachable, but its rate history is served only through an internal SharePoint `_api` list, so it is off limits |
| cbj.gov.jo | Timed out |
| sama.gov.sa | Connection reset |

**UAE and Bahrain therefore have no openly downloadable policy-rate series** from BIS, IMF, FRED or the central-bank sites. For pegged GCC members the official rates move with IORB/fed funds, but I did not construct a series from announcements.

## 3. Exchange-rate regimes: Ilzetzki, Reinhart and Rogoff, `irr/`
The page is https://www.ilzetzki.com/irr-data. It offers a "Beta Version: October 2026", which covers 1946-2025, and a "Stable Version: November 2021", which covers 1946-2019.

| file | content |
|---|---|
| `ERA_Classification_Monthly_1940-2025_beta_Oct2026.xlsx` | Sheets `Cover`, `Classification` (legend), `Fine` (codes 1-15, 1940M1 to 2025M12) and `Coarse` (codes 1-6, 1946M1 to 2025M12). The layout is wide: one column per country. Rows 3-4 hold start and end years, rows 5-6 the country name (UAE is labelled "UAE"), and data start at row 8 with dates such as "1940M1". |
| `Anchor_monthly_1946-2025_beta_Oct2026.xlsx` | Sheets `Contents`, `Master` (anchor currency by country and month, with ISO3 in row 6), then `USD`, `GBP`, `FRF`, `DEM`, `YEN`, `EUR`, `CNY` and `Basket` (anchor indicator sheets). |
| the two `..._stable_Nov2021.xlsx` files | The earlier vintage, ending 2019. |
| `IRR_Appendix.pdf` | Appendix (55 pages). |
| `extracted/irr_fine_monthly_selected.csv`, `irr_coarse_monthly_selected.csv`, `irr_anchor_master_monthly_selected.csv` | The 12 candidate countries only. Built by `../scripts/extract_irr2.py`. |

Fine codes:

| code | meaning |
|---|---|
| 1 | no separate legal tender |
| 2 | pre-announced peg or currency board |
| 3 | pre-announced band of ±2% or less |
| 4 | de facto peg |
| 5 | pre-announced crawling peg |
| 6 | pre-announced crawling band of ±2% or less, or de facto horizontal band of ±2% or less |
| 7 | de facto crawling peg |
| 8 | de facto crawling band of ±2% or less |
| 9 | pre-announced crawling band of ±2% or more |
| 10 | de facto crawling band of ±5% or less |
| 11 | moving band of ±2% or less |
| 12 | de facto moving band of ±5% / managed float |
| 13 | free float |
| 14 | freely falling |
| 15 | dual market with parallel-market data missing |

Coarse codes:

| code | meaning |
|---|---|
| 1 | hard peg (fine 1-4) |
| 2 | crawling peg or narrow band (fine 5-8) |
| 3 | managed float (fine 9-12) |
| 4 | free float (fine 13) |
| 5 | freely falling (fine 14) |
| 6 | dual market (fine 15) |

Fine-code spells since 1995 for the candidate countries:

| country | fine-code spells | anchor |
|---|---|---|
| SAU | 4 to 2019M12, then 2 | USD |
| ARE | 2 from 1997M11, except 4 in 2020M1-M7 | USD |
| QAT | 2 throughout | USD |
| BHR | 2 throughout | USD |
| OMN | 2 throughout | USD |
| KWT | 7 to 2002M12, 2 in 2003M1-2007M5, then 4 in 2007M6-2019M12, then 2 | USD (Kuwait officially uses a basket peg from May 2007) |
| JOR | 4 from 1995M9, 2 from 2020M6 | USD |
| MYS | 2 in 1998M10-2005M6, then 11 (2005M7-2015M12), 12 in 2016, 11 from 2017M1 | USD to about 2016, then CNY |
| IDN | 12 in 1999M5-2007M6, then 8 in 2007M7-2019M12, then 11 | USD, then CNY |
| PAK | 7 to 2019M12, then 12, 4 in 2024M3-2025M2, 12 in 2025M3-2025M8, 4 from 2025M9 | USD |
| TUR | alternates between 12, 13 and 14 (freely falling 2018M8-2019M5 and 2021M12-2025M1) | |
| USA | 13 | |

## Quick first-stage evidence (trilemma check)
From `../scripts/first_stage.py`: monthly data 2000-2026, regressing the change in the policy rate from t-1 to t on the monthly JK `MP_median`, with Newey-West t-statistics.

| policy rate | beta | t |
|---|---|---|
| US | 1.89 | 4.8 |
| Saudi Arabia | 1.85 | 4.0 |
| Kuwait | 1.06 | 2.8 |
| Jordan | 1.46 | 3.0 |
| Qatar (deposit rate) | 1.16 | 2.3 |
| Malaysia | 0.11 | 1.2 |
| Indonesia | 0.45 | 1.4 |

US shocks are therefore near one-for-one domestic shocks for the USD peggers, but not for Malaysia or Indonesia.
