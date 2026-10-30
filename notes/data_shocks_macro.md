# Data note: US monetary policy shocks, macro controls, Bank Indonesia policy-shock candidates

Builder: `shocks_macro`. Built on 2026-10-29.

## Outputs

All outputs are in `data/clean/`.

| file | shape | layout |
|---|---|---|
| `us_shocks_events.csv` | 4,102 rows | Long. `date` is the **event day** (YYYY-MM-DD, not a month start). Other columns: `time_et`, `shock`, `value`, `unit`, `source`, `unscheduled`. |
| `us_shocks_monthly.csv` | 6,615 rows = 15 shocks x 441 months, 1990-01 to 2026-09 | Long. Columns: `date` (month start), `shock`, `value`, `unit`, `n_events`, `in_coverage`, `source`, `description`. |
| `macro_monthly.csv` | 261 months (2005-01 to 2026-09) x 38 series | Wide. One column per series, with the unit in the column name. |
| `bi_policy_candidates.csv` | 261 months (2005-01 to 2026-09) x 21 columns | Wide. Candidate domestic shocks for Bank Indonesia (BI). |

### How to rebuild
Run both commands from the project root. Each script that reads raw files runs with `-I` and starts with the required `sys.path` line.
```
python -I code/py/shocks_macro_download.py   # downloads only the files that are missing; --force re-downloads everything
python -I code/py/build_shocks_macro.py      # builds the 4 outputs and prints every validation number quoted below
```
`build_shocks_macro.py` asserts the checks that must hold:
- the SEKI year-block alignment;
- the SEKI row identity;
- the BIS Nov-2014 pattern that the correction relies on;
- the break-adjusted level equals the 7DRR from 19-Aug-2016;
- the Swanson column F equals minus column E.

If BIS revises its data, the rerun fails loudly instead of silently changing a correction.

### Where the raw downloads went
New raw downloads, all plain GETs:
- `data/raw/fred/` holds 23 FRED series.
- `data/raw/macro/` holds the IMF, OECD and BIS SDMX files plus one BI SEKI file.

`data/raw/macro/download_manifest_shocks_macro.csv` lists, for each download, the URL, the saved file, the HTTP status, the UTC time, the size in bytes and the sha256. It also records the two FRED IDs that returned 404: `IDNPROINDMISMEI` and `IDNSLRTTO01IXOBM`.

Shock and policy-rate files placed by the earlier builder are read and never modified:
- `data/raw/shocks/` (see its `README.md`)
- `data/raw/bi/BI_SEKI_TABEL1_25_1.xls`

---

## 1. US monetary policy shocks

### Sources
| prefix | source and file | events |
|---|---|---|
| `jk_` | Jarocinski-Karadi update, https://github.com/marekjarocinski/jkshocks_update_fed (commit of 2026-10-11, "until September 2026"), CC BY 4.0. File: `data/raw/shocks/jk/shocks_fed_jk_t.csv`, which gives event-level values with an ET timestamp. | 334 events, 1990-02-08 to 2026-09-16 |
| `usmpd_` | SF Fed USMPD constructed surprises (Acosta, Ajello, Bauer, Loria and Miranda-Agrippino 2025). File: `data/raw/shocks/usmpd/mps_zip/mps.csv`, extracted from https://www.frbsf.org/wp-content/uploads/... `monetary-policy-surprises.zip`. The database README says "Last update: 17 September 2026". | 279 events, 1994-02-04 to 2026-09-16 |
| `bs_` | Bauer-Swanson (2023). File: `data/raw/shocks/bauer_swanson/monetary-policy-surprises-data.xlsx` (https://www.frbsf.org/wp-content/uploads/monetary-policy-surprises-data.xlsx). Sheet `FOMC (update 2023)` gives events; sheet `Monthly (update 2023)` gives the authors' monthly series. | 361 events, 1988-02-04 to 2023-12-13. **The data end in Dec 2023.** |
| `sw_` | Swanson (2021, JME) factors. File: `data/raw/shocks/swanson/pre-and-post-ZLB-factors-extended.xlsx`, sheet `Data`, columns B to E, data from row 3 (https://sites.socsci.uci.edu/~swanson2/papers/pre-and-post-ZLB-factors-extended.xlsx). | 241 events, 1991-07-05 to 2019-06-19. **Not updated since 2019.** |

### Shocks kept, with units
| `shock` | definition | unit |
|---|---|---|
| `jk_pc1` | first principal component of MP1, FF4, ED2, ED3 and ED4 | pp. Scaled to the s.d. of the ED4 surprise, in % p.a. |
| `jk_mp_median`, `jk_cbi_median` | pure monetary policy (MP) and central bank information (CBI) shocks from the median-rotation sign restriction. Both can be present at one event. | same as pc1 |
| `jk_mp_pm`, `jk_cbi_pm` | "poor man's" split. Each event is assigned wholly to MP or wholly to CBI by the sign of the stock-rate comovement. | same as pc1 |
| `jk_sp500` | S&P 500 surprise, 100 x log change over the 30-minute window | percent |
| `usmpd_stmt` | statement surprise, 30-minute window | pp. Normalised to move the 1-year Treasury yield one-for-one. |
| `usmpd_pc` | press-conference surprise, 70-minute window. Exists only for the 95 press conferences, 2011-04-27 to 2026-09-16. In `mps.csv` an NA means "no press conference", so it is treated as no event. | same as stmt |
| `usmpd_me` | monetary event = statement plus press conference, 100-minute window | same as stmt |
| `bs_mps` | MPS: first principal component of ED1 to ED4, scaled to a unit effect on ED4 | pp |
| `bs_mps_orth` | MPS orthogonalised to the six pre-announcement news variables. Event-level values, summed by month. | pp |
| `bs_mps_orth_authors_m` | **the authors' own monthly MPS_ORTH**, which they re-orthogonalise at monthly frequency. It is not a sum of events. It is kept because Bauer-Swanson recommend it for monthly work. | pp |
| `sw_ffr`, `sw_fg`, `sw_lsap` | Swanson federal funds rate, forward guidance and LSAP factors | standard deviations (unit variance, 1991-2019) |

### Monthly aggregation (`us_shocks_monthly.csv`)
- **Sum within the month.** The value is the sum of the event values in the calendar month, using the event's ET date.
- **Months without an event.** Inside a source's coverage window, a month with no event has value 0 and `n_events` = 0.
- **Outside coverage.** The value is NaN and `in_coverage` = 0. The coverage windows are:

| source | coverage window |
|---|---|
| JK | 1990-02 to 2026-09. 1990-01 is NaN. |
| USMPD stmt and me | 1994-02 to 2026-09 |
| USMPD pc | 2011-04 to 2026-09 |
| BS | to 2023-12. 2024-01 onward is NaN. |
| SW | 1991-07 to 2019-06 |

- **Missing events.** If any event in a month has a missing value, the whole month is NaN; it is not a partial sum. This happens in:
  - `bs_mps` 2001-09: the 17-Sep-2001 unscheduled cut, when markets were closed.
  - `bs_mps_orth` 2001-09 and 2020-03, 04, 06, 07, 08, 09, 11 and 12: the authors leave MPS_ORTH as NA for Mar to Dec 2020.
  - `jk_sp500` 2008-01, 2008-10, 2010-05 and 2020-03.

  **The authors' own monthly sheet writes 0 for 2001-09 instead.** This is the only difference from their monthly MPS, and it falls outside the 2009-2025 window.

**The JK files end at 2026-09.** The USMPD events end at 2026-09-16; no FOMC event followed in September 2026.

### Event file (`us_shocks_events.csv`)
- The file has one row per source event and shock.
- **Same-day events are kept as separate rows** and are distinguished by `time_et`. JK has two events on 1991-02-01, 1991-04-30, 1991-09-13, 1991-11-06, 1991-12-20 and 2005-05-03.
- `time_et` comes from different places:
  - for JK, the start time in the JK file;
  - for BS, the `Time` column, converted to 24-hour HH:MM;
  - for USMPD and SW it is empty, because those files give no time.
- `unscheduled` (1 or 0) is filled for BS only.

### Caveats on the US shocks
1. **JK MP/CBI identity fails on 5 events.** On 5 JK events the S&P 500 surprise is missing:
   - 2008-01-22 08:20, with pc1 = -0.163
   - 2008-10-08 07:00
   - 2010-05-09 21:15
   - 2020-03-15 17:00
   - 2020-03-23 08:00

   On those events the authors set MP and CBI to 0 while pc1 stays nonzero. So `MP + CBI = pc1` holds on 329 of the 334 events. The largest violation is 0.1628, on 2008-01-22. The monthly MP and CBI series inherit this, so in 2008-01, 2008-10, 2010-05 and 2020-03, MP + CBI differs from pc1.
2. **Swanson LSAP sign.** Column E is kept as `sw_lsap`; column F is exactly -E (asserted). At the event level, corr(sw_lsap, BS TNOTE10 surprise) = -0.457 on 241 events, while corr(fg, TNOTE10) = +0.816 and corr(ffr, TNOTE10) = +0.203. TNOTE10 moves like a yield: it rises with hawkish forward guidance. So **positive `sw_lsap` means 10-year yields fall (expansionary)**, and the opposite holds for FFR and FG.
3. **Bauer-Swanson stops at 2023-12** and **Swanson at 2019-06**. For 2024-2025 only JK and USMPD exist.
4. **Units differ by family.** JK is pp at the ED4 scale. USMPD is pp of the 1-year yield. BS is pp at the ED4 scale. Rescale before pooling.

### Validation (numbers printed by the build)
**JK monthly file.** The authors' `shocks_fed_jk_m.csv` matches our sums of `shocks_fed_jk_t.csv` over 440 months:

| series | max abs gap |
|---|---|
| pc1 | 2.8e-17 |
| MP_median | 2.8e-17 |
| CBI_median | 2.8e-17 |
| MP_pm | 2.8e-17 |
| CBI_pm | 1.7e-18 |
| SP500 | 4.4e-16, over 436 non-missing months |

**BS monthly sheet, 1990-01 to 2023-12:**
- **MPS:** the authors' monthly MPS against our event sum, over 407 months: max abs gap 1.4e-5, from rounding in the sheet, and correlation 1.0000. The only NaN difference is 2001-09: ours is NaN, theirs is 0.
- **MPS_ORTH:** the authors' monthly MPS_ORTH against our event-sum `bs_mps_orth`, over 399 months: correlation 0.957 and max abs gap 0.145. The two differ by construction, because the authors re-orthogonalise at monthly frequency. Both series are kept.

**USMPD.**
- 279 events; PC is non-missing for 95.
- On the PC events, STMT + PC differs from ME by at most 0.026 pp. ME uses its own 100-minute window, so it is not exactly the sum.

**Event-level cross-source correlations, on common dates:**

| pair | correlation | common dates |
|---|---|---|
| jk_pc1, usmpd_stmt | 0.981 | 276 |
| jk_pc1, bs_mps | 0.954 | 303 |
| usmpd_stmt, bs_mps | 0.955 | 254 |
| jk_pc1, usmpd_me | 0.909 | 276 |

### Standard deviations, 2009-01 to 2025-12 (204 months, monthly sums)
| shock | months in coverage | nonzero months | mean | s.d. | min | max |
|---|---|---|---|---|---|---|
| jk_pc1 | 204 | 133 | -0.0020 | 0.0382 | -0.2631 | 0.2432 |
| jk_mp_median | 204 | 136 | -0.0030 | 0.0346 | -0.1397 | 0.1562 |
| jk_cbi_median | 204 | 136 | 0.0014 | 0.0192 | -0.0761 | 0.0870 |
| jk_mp_pm | 204 | 85 | -0.0015 | 0.0349 | -0.1913 | 0.2432 |
| jk_cbi_pm | 204 | 49 | -0.0001 | 0.0089 | -0.0567 | 0.0367 |
| usmpd_stmt | 204 | 138 | 0.0022 | 0.0222 | -0.1991 | 0.0609 |
| usmpd_me | 204 | 138 | 0.0013 | 0.0268 | -0.1926 | 0.0728 |
| usmpd_pc (from 2011-04) | 177 | 88 | -0.0007 | 0.0226 | -0.1481 | 0.0960 |
| bs_mps (to 2023-12) | 180 | 121 | 0.0026 | 0.0443 | -0.4190 | 0.1381 |
| bs_mps_orth (2020 NaN) | 172 | 113 | 0.0042 | 0.0302 | -0.0964 | 0.1184 |
| bs_mps_orth_authors_m | 180 | 121 | 0.0038 | 0.0429 | -0.3780 | 0.1084 |
| sw_ffr (to 2019-06) | 126 | 84 | 0.0896 | 0.1391 | -0.5335 | 0.4958 |
| sw_fg | 126 | 84 | -0.0494 | 0.6701 | -2.4187 | 1.8037 |
| sw_lsap | 126 | 84 | 0.0232 | 0.6684 | -1.9618 | 5.6307 |

The "nonzero months" counts differ between the JK median and poor man's splits because the poor man's split assigns each event entirely to one shock.

### Correlations, 2009-01 to 2025-12, monthly, pairwise complete
|  | pc1 | MP_med | CBI_med | MP_pm | CBI_pm | stmt | me | bs_mps | bs_orth | bs_orth_m |
|---|---|---|---|---|---|---|---|---|---|---|
| jk_pc1 | 1 | 0.838 | 0.366 | 0.964 | 0.265 | 0.931 | 0.604 | 0.911 | 0.826 | 0.807 |
| jk_mp_median | | 1 | -0.189 | 0.887 | -0.003 | 0.765 | 0.521 | 0.739 | 0.752 | 0.656 |
| jk_cbi_median | | | 1 | 0.232 | 0.516 | 0.325 | 0.144 | 0.289 | 0.099 | 0.243 |
| jk_mp_pm | | | | 1 | 0.025 | 0.868 | 0.552 | 0.848 | 0.775 | 0.744 |
| jk_cbi_pm | | | | | 1 | 0.271 | 0.171 | 0.244 | 0.309 | 0.221 |
| usmpd_stmt | | | | | | 1 | 0.756 | 0.985 | 0.889 | 0.877 |
| usmpd_me | | | | | | | 1 | 0.742 | 0.560 | 0.651 |
| bs_mps | | | | | | | | 1 | 0.905 | 0.890 |
| bs_mps_orth | | | | | | | | | 1 | 0.952 |

Restricting to 2009-01 to 2023-12, where every series is available, changes these by less than 0.04. For example, corr(pc1, MP_median) = 0.831 and corr(MP_median, CBI_median) = -0.225.

**Press-conference surprises behave differently from statement surprises.** Over 2011-04 to 2025-12, corr(usmpd_pc, usmpd_stmt) = -0.107 and corr(usmpd_pc, jk_pc1) = -0.269. Over 2009-2025, monthly corr(jk_pc1, usmpd_me) = 0.604, well below the statement-only correlation of 0.931. **The choice between statement and full monetary-event windows therefore matters.**

---

## 2. Macro controls (`macro_monthly.csv`, wide, 2005-01 to 2026-09)

Daily series are aggregated as follows:
- `_avg` is the mean of the available daily observations in the month.
- `_eom` is the last available daily observation in the month.

| column | source and exact series | transformation | coverage in file |
|---|---|---|---|
| `us_vix_avg_index`, `us_vix_eom_index` | FRED `VIXCLS` (daily) | avg and eom | 2005-01 to 2026-09 |
| `brent_imf_usd_bbl` | FRED `POILBREUSDM` (IMF PCPS Brent, monthly average) | as published | 2005-01 to 2026-09 |
| `brent_spot_avg_usd_bbl` | FRED `DCOILBRENTEU` (EIA Brent spot, daily) | avg | 2005-01 to 2026-09 |
| `us_indpro_index_2017eq100_sa` | FRED `INDPRO` | as published | 2005-01 to 2026-09 |
| `us_cpi_index_1982_84eq100_sa`, `us_cpi_yoy_pct` | FRED `CPIAUCSL` | index, and 100 x (x_t / x_{t-12} - 1) | **2025-10 is missing** (BLS published no October 2025 CPI); 260 of 261 months |
| `us_core_cpi_index_1982_84eq100_sa` | FRED `CPILFESL` | as published | same gap in 2025-10 |
| `us_2y_yield_avg_pct` | FRED `GS2` (monthly average) | as published | 2005-01 to 2026-09 |
| `us_2y_yield_eom_pct` | FRED `DGS2` (daily) | eom | 2005-01 to 2026-09 |
| `us_fedfunds_eff_avg_pct` | FRED `FEDFUNDS` (`data/raw/shocks/fred/FEDFUNDS.csv`) | as published | 2005-01 to 2026-09 |
| `usd_broad_avg_index_2006jan_eq100`, `usd_broad_eom_index_2006jan_eq100` | FRED `DTWEXBGS` (nominal broad dollar, daily) | avg and eom | **starts 2006-01** |
| `usd_broad_old_avg_index_1997jan_eq100` | FRED `TWEXBMTH` (discontinued broad index) | as published | 2005-01 to 2019-12. Not spliced; included only to cover 2005. Monthly corr with DTWEXBGS is 0.996, but the levels differ. |
| `commodity_all_imf_index_2016eq100` | FRED `PALLFNFINDEXM` (IMF all-commodity index) | as published | 2005-01 to 2026-09 |
| `commodity_energy_imf_index_2016eq100` | FRED `PNRGINDEXM` | as published | 2005-01 to 2026-09 |
| `commodity_nonfuel_imf_index_2016eq100` | FRED `PNFUELINDEXM` | as published | 2005-01 to 2026-09 |
| `idr_per_usd_avg`, `idr_per_usd_eom` | **IMF ER** `IMF.STA,ER/IDN.XDC_USD.PA_RT+EOP_RT.M` (official rate) | as published | 2005-01 to 2026-09 |
| `idr_per_usd_avg_bis`, `idr_per_usd_eom_bis` | BIS `WS_XRU/M.ID.IDR.A` and `.E` | as published (alternative) | 2005-01 to 2026-09 |
| `idr_per_usd_avg_pct_chg_mom` | from the IMF average | 100 x log difference | 2005-02 to 2026-09 |
| `idn_neer_broad_index_2020eq100` | BIS `WS_EER/M.N.B.ID` (nominal, broad basket, 64 economies) | as published | 2005-01 to 2026-09 |
| `idn_cpi_index_2022eq100`, `idn_cpi_yoy_pct`, `idn_cpi_mom_pct` | IMF CPI `IMF.STA,CPI/IDN.CPI._T.IX+YOY_PCH_PA_PT+POP_PCH_PA_PT.M`. The index is chain-linked on a 2022=100 reference. | as published | 2005-01 to 2026-09 |
| `idn_mfg_prod_index_2015eq100_nsa_spliced` | OECD SDMX `DSD_STES@DF_INDSERV`, IDN.M.PRVM.IX.C (manufacturing production volume, NSA), back-cast before 2010 (see the break note below) | spliced | 2005-01 to **2026-06** |
| `idn_mfg_prod_index_2015eq100_sa` | same OECD dataflow, calendar and seasonally adjusted | as published, **from 2010-01 only** | 2010-01 to 2026-06 |
| `idn_mfg_prod_yoy_pct` | from the spliced NSA index | 100 x (x_t / x_{t-12} - 1) | 2006-01 to 2026-06 |
| `idn_policy_rate_eom_pct`, `idn_policy_rate_avg_pct` | BIS `WS_CBPOL/D.ID` (daily), with the Nov-2014 correction (section 3) | eom and avg, **as published levels**, which include the Aug-2016 level drop | 2005-07 to 2026-09 |
| `idn_policy_rate_eom_adj_pct`, `idn_policy_rate_avg_adj_pct` | as above, break-adjusted (section 3) | eom and avg | 2005-07 to 2026-09 |
| `idn_policy_instrument` | label: BI Rate before Aug-2016, the switch month, then BI 7-day (Reverse) Repo Rate | label | |
| `idn_jibor_1m_eom_pct` | BI SEKI Table I.25 (see section 3), JIBOR 1 month, end of period | as published | 2005-01 to **2025-12**. BI stopped publishing JIBOR on 1-Jan-2026. |
| `idn_indonia_eom_pct` | BI SEKI Table I.25, sheet 1.25B, INDONIA | as published, end of period | 2018-08 to 2026-09 |
| `idn_interbank_3m_oecd_pct` | OECD `DSD_STES@DF_FINMARK` IDN IR3TIB | as published | to 2025-12 |
| `idn_interbank_call_oecd_pct` | OECD IRSTCI ("immediate rate") | as published | to 2026-08. **Before 2017 this equals the BI policy rate** (in every month of 2006-2013 and 2015-2016). It is not a market rate until 2017. |

### Activity proxy for Indonesia
**No monthly industrial production index for Indonesia is openly downloadable through 2026.** I checked:
- FRED `IDNPROINDMISMEI`: 404.
- FRED `IDNSLRTTO01IXOBM` (retail): 404.
- IMF `PI`: manufacturing ends 2019-04.
- FRED `IDNPRMNTO01IXOBM`: ends 2023-12.

The best openly available proxy is the OECD SDMX **manufacturing production volume index** (BPS large and medium manufacturing), which runs to 2026-06. GDP is quarterly only and was not used.

### Breaks, revisions and choices
- **Manufacturing break, 2009-12 to 2010-01.** The OECD SDMX series as published jumps from 102.82 to 76.60 between 2009-12 and 2010-01. This is a base change, not a collapse. Before 2010 the published OECD level is about 34.5% above the consistently spliced FRED/OECD-MEI vintage (mean gap 34.51%, max 35.62% over 2005-2009). The fix:
  - for 2005-01 to 2009-12, the NSA index is back-cast with the month-on-month growth of FRED `IDNPRMNTO01IXOBM`, anchored at 2010-01. The spliced series goes 78.65 to 76.60 across the break.
  - the SA index is left missing before 2010.
- **Manufacturing vintages.** OECD SDMX and the FRED vintage agree over 2010-2022: max gap 0.005%. In 2023 the data were revised: mean gap 2.0%, max 5.3% in 2023-11. The current OECD vintage is used. Against IMF PI 'C' (to 2019-04), month-on-month log growth matches with mean abs gap 0.0012; IMF's own 2018-2019 data differ, with a max gap of 0.079 in 2018-03.
- **IDR/USD: why the IMF rate is the main series.** The IMF ER series is the official BI middle rate/JISDOR and matches OECD MEI end-of-month exactly (max gap 0.000% over 228 months to 2023-12). BIS XRU differs at times of stress: up to 2.5% for the monthly average (2013-10) and 3.2% for end of month (2013-08). In 2013, BI's official rate lagged the market quotes that BIS appears to use. Both are kept. The IMF and OECD monthly averages differ by up to 2.26%, in 2008-11.
- **Indonesian CPI: why the IMF series is used.** IMF y/y matches OECD `CPALTT01IDM659N` with a max gap of 0.26 pp (to 2025-04). It differs from BIS WS_LONG_CPI (771) by up to 1.53 pp in 2008, where BIS appears to splice the 2007-base change differently. The IMF y/y recomputed from the IMF index matches to 3e-14.
- **Brent.** IMF `POILBREUSDM` and the mean of EIA daily spot have mean gap 1.3% and correlation 0.998. They differ by 46% in 2020-04 (negative-price episode, different pricing basis) and by 10-12% in 2026-04 and 2026-09. Both are kept.
- **US 2-year yield.** GS2 and the mean of DGS2 differ by at most 0.005 pp.

---

## 3. Domestic shock candidates for Bank Indonesia (`bi_policy_candidates.csv`)

**These are candidates, not identified shocks.**
- None of them comes from high-frequency market data around BI announcements; no open intraday or daily market data around BI decisions were available.
- The policy rate responds systematically to domestic inflation, the rupiah, and the Fed. Monthly corr(d_policy_eom_adj, jk_mp_median) = 0.119 and corr(d_policy_eom_adj, usmpd_stmt) = 0.144 over 2009-2025.
- Treat (a) and (b) as **policy changes**, not surprises. Use them with controls, or as a first stage, and say so in the paper.

### Policy-rate source
- **Source:** BIS WS_CBPOL daily, Indonesia. https://stats.bis.org/api/v1/data/WS_CBPOL/D.ID/all?format=csv, saved as `data/raw/macro/bis_cbpol_D_ID.csv`. It is byte-identical to `data/raw/bi/BIS_CBPOL_ID_daily.csv`.
- **Coverage:** 5-Jul-2005 to 19-Oct-2026.
- **Gaps:** weekends and holidays are NA and are forward-filled.

**Checks against other sources:**
- The eom of the daily series equals BIS monthly (eop) in all 255 months (max gap 0).
- It equals IMF MFS166 in all 253 overlapping months.
- Against BI's own SEKI Table I.25 "Policy Rate"/"BI Rate" row (end of period) it differs in 11 of 252 months:
  - **2011-02 to 2011-09 and 2011-11 to 2011-12.** SEKI shows 6.50 throughout 2011 and does not reflect the 4-Feb-2011 hike to 6.75, the 11-Oct cut or the 10-Nov cut. **SEKI is judged wrong here** and BIS is kept.
  - **2014-11.** See the correction below.

**Correction applied: 25 to 30 Nov 2014 set to 7.75.**
- What BIS shows: 7.75 on 18 to 24 Nov 2014, 7.50 on 25 to 28 Nov, and 7.75 again from 1 Dec.
- Why it is an error: BI raised the BI Rate to 7.75% at its 18-Nov-2014 meeting and held it until the 17-Feb-2015 cut. No Board decision was taken on 25 Nov or 1 Dec 2014. SEKI I.25 shows 7.75 at end-Nov-2014.
- **IMF MFS166 and OECD IRSTCI also show 7.50 at end-Nov-2014.** They most likely inherit the same feed, so the correction rests on BI's own SEKI and the decision record.
- Effect: the +25 bp move is dated 2014-11 (decision 2014-11-18) instead of appearing at eom 2014-12. The correction is flagged in `data_note`.

**The 19-Aug-2016 switch** from BI Rate (6.50) to the BI 7-day Reverse Repo Rate (5.25) is a level drop of 1.25 that is **not an easing**. BI's August 2016 meeting held the 7DRR at 5.25.

### Columns
| column | definition |
|---|---|
| `policy_rate_eom_raw_pct`, `policy_rate_avg_raw_pct` | published level (after the Nov-2014 correction), eom and monthly mean of daily values |
| `policy_rate_eom_adj_pct`, `policy_rate_avg_adj_pct` | **break-adjusted level.** Daily changes are cumulated with the 19-Aug-2016 jump set to 0, and the series is anchored to equal the 7DRR from 19-Aug-2016. This is equivalent to the pre-switch BI Rate minus 1.25 pp; both properties are asserted. **Only changes are meaningful before Aug 2016.** |
| `policy_instrument`, `data_note` | labels and flags for 2014-11 and 2016-08 |
| `d_policy_eom_raw_pp` | first difference of the raw eom level. It contains -1.25 in 2016-08. **Do not use this as a shock.** |
| **(a)** `d_policy_eom_adj_pp` | first difference of the break-adjusted eom level. It is 0 in 2016-08. |
| `d_policy_avg_adj_pp` | first difference of the break-adjusted monthly average. It spreads a decision across two months depending on the day of the decision. |
| **(b)** `decision_month`, `n_rate_changes`, `decision_size_pp`, `decision_sign`, `decision_dates` | from the daily series: days on which the rate changed, excluding 19-Aug-2016. The first observation, 5-Jul-2005, is the start of the series, so these columns are NaN for 2005-07. `decision_size_pp` is the sum of the changes in the month, and `decision_dates` lists `YYYY-MM-DD(+x.xx)`. |
| **(c)** `jibor_1m_eom_pct`, `d_jibor_1m_pp` | JIBOR 1 month, end of period, from SEKI Table I.25, and its monthly change |
| `d_jibor_1m_decision_pp` | `d_jibor_1m_pp` in decision months, 0 in months without a rate change, NaN where JIBOR is missing |
| `d_jibor_1m_minus_d_policy_pp` | `d_jibor_1m_pp` minus (a) |
| `indonia_eom_pct`, `d_indonia_pp`, `d_indonia_decision_pp` | the same for INDONIA, the overnight rate. Available from 2018-08. It is the only interbank alternative after JIBOR stopped in 2026. |

### Decisions found (from the BIS daily series)
- **Whole series, Jul-2005 to Oct-2026:** 86 change days, 35 hikes and 51 cuts.
- **2009-01 to 2025-12:** 56 decision months out of 204, with 20 hike months and 36 cut months. Only one month has two changes: 2018-05 (17 May and the extra meeting on 30 May).
- **Decision months per year, 2009 to 2025:**

| year | 2009 | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| decision months | 8 | 0 | 3 | 1 | 5 | 1 | 1 | 6 | 2 | 5 | 4 | 5 | 1 | 5 | 2 | 2 | 5 |

- **Hold decisions are invisible.** BI's Board meets monthly, so holds cannot be told apart from "no meeting" with this series. Treat `decision_month` = 0 as "no change", not as "no meeting".
- **Dates are effective dates as recorded by BIS.** They coincide with the announcement day in every case checked, for example 2016-06-16, 2018-05-30 and 2022-08-23.

### JIBOR source detail
**SEKI Table I.25 file.** https://www.bi.go.id/SEKI/tabel/TABEL1_25_2.xls was retrieved with the WebFetch tool on 2026-10-29 and saved as `data/raw/macro/BI_SEKI_TABEL1_25_2.xls`, sha256 `ddd69293...a59a79`. TABEL1_27 and TABEL1_28 were also tried: they hold US-dollar lending rates and rupiah deposit rates, contain no interbank rates, and were not kept.

**Sheets and rows used:**

| series | period | sheet and row |
|---|---|---|
| JIBOR 1M | 2003-12 to 2009-12 (the cells before 2003-12 are "-") | `Th 2002-2009` (old table 1.30), row "JIBOR > 1 Bulan" (sheet row 35). Column dates are read from the datetime header row. |
| JIBOR 1M | 2010 to 2017 | `Th 2010-2017`, row 17 |
| JIBOR 1M | 2018 to 2026-09 | `1.25B`, row 17 "1 Bulan 5)" |
| INDONIA | | `1.25B`, row 19. INDONIA is published from 1-Aug-2018. |
| policy-rate cross-check | | `data/raw/bi/BI_SEKI_TABEL1_25_1.xls` sheets `Th 2002-2009` (BI Rate), `Th 2010-2016` and `1.25A_1` ("Policy Rate") |

**Parsing.**
- The year labels in the header row are misplaced in places. In `1.25B`, "2025" and "2026" sit on the last column of their blocks; in `Th 2010-2017`, a blank column falls between Sep and Oct 2010.
- Years are therefore assigned by Jan-to-Dec blocks, and the build asserts that every year label falls inside its block.

**Coding of zeros.**
- SEKI writes 0 for "not published". This covers JIBOR from Jan-2026 (footnote 5: "Sejak 1 Januari 2026, JIBOR seluruh tenor tidak lagi dipublikasikan") and INDONIA before Aug-2018. These zeros are set to NaN.
- The SEKI footnote "Data transaksi per akhir periode" means **every value is end of month.**

**Cross-check.** JIBOR 1M for 2005-2009 equals `data/clean/bi_money_market_rates.csv` (series `jibor_1m`, another builder's file, read only) exactly: max gap 0.00 over 60 months.

### Validation and diagnostics, 2009-01 to 2025-12
- **Break adjustment.** The sum of daily decision sizes equals the monthly change of the adjusted eom level in every month: max gap 0.0. In Aug-2016 the raw change is -1.25 and the adjusted change is 0.00.
- **Standard deviations:**

| series | s.d. (pp) |
|---|---|
| `d_policy_eom_adj_pp` | 0.165 |
| `d_jibor_1m_pp` | 0.387 |
| `d_jibor_1m_decision_pp` | 0.265 |

- **JIBOR and decisions.**
  - In decision months, corr(d_jibor_1m, decision_size) = 0.827 (n = 56), and the OLS slope of the JIBOR change on decision size is 1.33.
  - Over all months, corr(d_jibor_1m, d_policy_eom_adj) = 0.568.
- **JIBOR noise.** The s.d. of the JIBOR change in **non-decision** months is 0.333 pp, about as large as in decision months. End-of-month JIBOR has large year-end and pre-Eid liquidity spikes that are not related to policy:

| month | JIBOR 1M change (pp) |
|---|---|
| 2016-12 | +1.69 |
| 2017-01 | -1.99 |
| 2017-06 | +1.08 |
| 2017-07 | -0.98 |
| 2019-01 | -1.18 |

  Outside the sample, Nov-2006 = 6.69 (Oct 10.79, Dec 9.49) also looks anomalous in the source. **(c) is therefore a noisy measure.** An end-of-month to end-of-month change mixes pre-decision anticipation, the decision and liquidity noise. It is not a surprise measure. If you use it, consider dropping or dummying December and the Eid months, or using it only as a robustness check.
- **Correlation with US shocks**, monthly 2009-2025: d_jibor_1m with jk_mp_median 0.051, jk_pc1 0.051, usmpd_stmt 0.055.

---

## Unresolved items and flags for downstream users
1. **The study period only partly overlaps the BS and Swanson shocks.** Bauer-Swanson ends 2023-12 and Swanson 2019-06. For the full 2009-2025 window use JK (`jk_mp_median`, `jk_pc1`) or USMPD (`usmpd_stmt`).
2. **JK MP and CBI are 0 on the 5 events with a missing S&P 500 surprise**, while pc1 is not. This affects 2008-01, 2008-10, 2010-05 and 2020-03.
3. **US CPI 2025-10 is missing** because the October 2025 CPI was not published. It was not interpolated.
4. **Indonesian manufacturing production:**
   - It ends 2026-06.
   - Before 2010 it is a splice; the SA index is missing before 2010.
   - No total-industry index exists.
5. **The JIBOR 1M series:**
   - It stops at 2025-12. For 2026, only INDONIA (overnight) is available.
   - It is end of month, with seasonal liquidity spikes.
6. **The Nov-2014 policy-rate correction is a judgment.** BIS, IMF and OECD all report 7.50 at end-Nov-2014; BI's SEKI and the decision record support 7.75.
7. **The broad dollar index (`DTWEXBGS`) starts 2006-01.** For 2005, only the discontinued, unspliced `TWEXBMTH` is available.
8. **No BI monetary policy surprise based on market data could be built from open data.** No open intraday or daily market-rate data around BI announcements were found.
