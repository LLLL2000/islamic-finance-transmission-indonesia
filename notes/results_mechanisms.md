# Results note: module M, price and funding mechanisms (pre-analysis plan 5.4 and 5.5)

Script: `code/R/13_mechanisms.R` (sources `00_common.R`, which it does not modify). New builder for the conventional
deposit data: `code/py/build_bi_deposits.py`. Rerun from the project root, in this order:

```
python -I code/py/build_bi_deposits.py                                   # SEKI I.17 -> data/clean/bi_deposits_by_group.csv
"C:/Program Files/R/R-4.4.1/bin/Rscript.exe" --vanilla code/R/13_mechanisms.R   # about 7 minutes
```

**Revised 2026-10-30 after an independent verification.** Section 10 lists every issue the verifier raised and
what was done about it. The main changes: a sample-robustness block (drop 2009, leave one year out, the plan's
section-6 checks), a block permutation test, same-sample comparators for the pass-through ratios, a rule for the
conversion follow-up and scan months, and a rewritten interpretation that no longer claims more than the estimates
show.

The revised builder and script ran end to end from a fresh session on 2026-10-30: exit 0, about 7 minutes for the R
script, and the only warnings say packages were built under R 4.4.3. Consecutive fresh-session runs (the later ones
changed only the pre-sample shock table and the figure captions) gave byte-identical copies of all 26 estimation
table and data files they share. The clean SEKI file kept its SHA-256 (`f3bd6c04…92e6`). `00_common.R` was not modified.

Every number below comes from the output files listed in section 9. The auto-generated
`output/tables/mech_results_tables.md` has the full tables: every shock, every estimator, h = 0, 3, 6, 12, 24, the
sample-robustness table, the permutation table and the event-month flags.

## 0. Summary

The question is whether Islamic deposit returns and financing margins adjust more slowly than conventional rates
after a monetary tightening, and whether that moves funding, the contract mix or credit risk. Per 25 bp (b25, s.e.),
DL = distributed lag, LP = local projection; a 25 bp US surprise is a 7-13 s.d. event, so read magnitudes per s.d.

1. **Deposit pricing after US shocks: the Islamic-minus-conventional 1-month spread falls in the DL, but the
   result is fragile.**
   - DL, JK `MP_median`: -1.41 (0.60) at 12 months and -1.58 (0.59) at 24, or -0.20 (0.08) pp per s.d. at 12
     months. The other US series have the same sign: `MP_pm` -1.47 (0.48), USMPD statement -2.20 (0.67).
   - The LP has the same sign but is **not significant at 12 months for any US shock**: -1.15 (1.11), -1.59 (1.08),
     -1.74 (1.08), on 88 months. It is significant only for `MP_median` at 24 months, -3.44 (1.39), on 55 months.
   - **The significance of the pre-registered primary shock rests on 2009.** Without the 2009 outcome months the DL
     gives -0.58 (0.48); starting in 2011, so that every DL shock lag is from 2009 or later, -0.58 (0.50).
     Leaving out one calendar year at a time, the estimate ranges from -1.68 (2011 out) to -0.58 (2009 out).
   - Why: the DL regresses the 2009 outcome months on shock lags back to 2007-02, and 2007-08 contains large Fed
     surprises. Those 23 months (2007-02..2008-12) carry 67% as much `MP_median` variance (sum of squares) as the
     198 months of 2009-2025. The LP never uses a shock before 2009-05. The three largest of these surprises are negative
     (easing surprises in 2008-12, 2007-09 and 2008-11), so the full-sample DL is not a "tightening-phase" estimate: the
     linear model treats easing and tightening symmetrically.
   - `MP_pm` and the statement surprise are less sensitive. Without 2009 they give -0.78 (0.38) and -1.42 (0.54),
     about -0.11 and -0.13 pp per s.d., half the full-sample -0.20. From 2014-07 the spliced spread gives -0.87
     (0.51), -0.71 (0.40) and -1.41 (0.44), and the Rupiah-only 2014+ series gives -0.99 (0.52), -0.68 (0.38)
     and -1.40 (0.41).
   - The lead tests pass for the three pure US series. Block permutation: p = 0.018 (DL) and 0.14 (LP) for
     `MP_median`.
   - **Reading.** The sign is negative for every US shock and every h = 12 sample variant, except one insignificant
     LP estimate (`MP_median`, 2009-2014 only: 0.31 (1.76)). The size is about half the headline
     outside 2009 (about -0.1 pp per s.d.). The primary shock's significance depends on one year, which by the
     logic of plan section 7 undermines it, and the LP is never significant at the pre-registered 12-month horizon.
   - After a domestic BI shock, the spread dips by -0.30 (0.12) at 3 months (DL) and closes by 12 months, with a
     pre-trend (LP -0.18 (0.09)).
   - The Fed information shock (CBI) gives the same spread response, but fails the lead tests and flips sign in the
     LP at 24 months (section 3.5). It is a warning about identification, not corroboration.
2. **Conventional pass-through.** The conventional 1-month rate follows the BI rate in the full sample (DL pass-through
   0.8-1.1). Its response to `MP_median`, 1.30 (0.43) at 12 months, halves without 2009 to 0.68 (0.49). For
   `MP_pm` and the statement surprise it is stable (1.44 to 1.10; 2.53 to 2.12).
3. **Stand-alone banks (BUS) vs windows (UUS).**
   - The **BUS-minus-conventional** 1-month spread (2014-06+) is the one deposit-pricing result that is significant
     in both estimators at 12 months for the three pure US shocks: LP -0.68 (0.41), -0.65 (0.35), -0.79 (0.33) on
     49 months; DL -1.11 (0.65), -0.83 (0.50), -1.72 (0.46) (`MP_median`, `MP_pm`, statement), about -0.07 to
     -0.16 pp per s.d. Its lead tests pass, and the 2009 problem does not apply. But it is short-sample and fragile:
     dropping the pandemic months or the plan's break years leaves only the statement surprise significant, and the
     LP permutation p is 0.18 for `MP_median`.
   - Whether BUS differ from UUS is **suggestive at 3-6 months in the DL only, not robust**:
     - The direct BUS-minus-UUS return gap after `MP_median`: DL -0.83 (0.39) at 3 months, -1.15 (0.43) at 6, -0.49
       (0.76) at 12. LP: -0.14 (0.36) at 12.
     - The UUS level rises in the DL, 1.89 (0.51) at 12 months, but not in the LP, -0.55 (0.59), on 42 months. By
       the module's own rule (LP and DL disagree, so not robust), the "windows track their parents" reading is not
       established.
4. **Deposit flows: uninformative.** The Islamic-minus-conventional DPK growth differential rises on impact after
   US shocks (DL +2.79 (1.56)% per 25 bp), the wrong sign for an outflow. From 6 months on, LP and DL disagree in
   sign. The 12-month MDE is 9.3% per 25 bp (DL), 1.3% per s.d., so the data cannot tell whether depositors react.
5. **Financing rates: no evidence that Islamic financing becomes cheaper than comparable conventional credit.**
   - The murabahah minus conventional working-capital spread is -1.41 (0.43) at 12 months after `MP_median` (DL).
     Without 2009 it is -0.75 (0.43); in 2009-2014 alone -2.15 (0.75), when the murabahah rate itself fell.
   - From 2014-07 the murabahah rate is flat: 0.02 (0.40), 0.05 (0.35), 0.13 (0.46) for `MP_median`, `MP_pm` and the
     statement surprise. The spread against working capital stays negative, -0.53 (0.39), -0.52 (0.30), -0.78
     (0.37), only because conventional working-capital rates rise. Against conventional consumption loans, which do
     not move either, it is about zero: 0.18 (0.49), 0.14 (0.42), 0.11 (0.52).
   - On the same months the use-matched Islamic working-capital rate rises at least as much as the conventional one
     (spread +1.03 (0.77)).
   - So after 2014 the murabahah rate behaves like the conventional consumer-loan rate, which also does not move.
     That is not an Islamic-specific cheapening.
6. **Contract mix, FDR, NPF.** Nothing robust: LP and DL disagree, or the lead placebo fails.
7. **No mechanism is established.** Nothing here measures bank margins or funding costs, so the data cannot say
   whether sticky Islamic returns were a cost advantage. Section 7 gives the competing readings.

## 1. Data construction

### 1.1 Inputs (all `data/clean/`, read only)

| file | use |
|---|---|
| `ojk_deposit_returns.csv` | Islamic mudharabah time-deposit returns by tenor (BUS_UUS from 2009; BUS and UUS from 2014-06) |
| `ojk_margins.csv` | equivalent financing rates by contract (2009+) and by use (Tabel 18, 2014-06+) |
| `ojk_deposits.csv` (series `harmonised`) | Islamic DPK: `h_total`, `h_demand`, `h_sav`, `h_time` |
| `ojk_contracts.csv` (currency `all`) | murabahah and profit-sharing shares of financing |
| `ojk_aggregates.csv` | `fdr_pct_computed`, `npf_gross_pct_computed`, `dpk_rp_bn` (BUS, for one check) |
| `ojk_conversion_events.csv` | candidate event months for the rule in 1.6 |
| `bi_deposit_rates.csv` (`commercial_banks`) | conventional Rupiah time-deposit rates, 1m/3m/6m/12m (SEKI I.28) |
| `bi_lending_rates.csv` (`commercial_banks`) | conventional Rupiah lending rates: working capital, investment, consumption (SEKI I.26) |
| `macro_monthly.csv` | BI policy rate, `idn_policy_rate_avg_adj_pct`, as in `11_macro_first_stage.R` |
| `us_shocks_events.csv` | event dates, for the month-end timing count (2.6) |
| `bi_deposits_by_group.csv` | **new**, see 1.2 |

All outcome data are restricted to 2009-01..2025-06 at both ends. Shock lags before 2009 come from `load_shocks()`
and are used only by the DL (section 2.2).

### 1.2 New download: conventional deposit volumes (SEKI I.17)

**Requests.** I made five plain GETs with the WebFetch tool (default headers, no login, no spoofing) to the
documented pattern `https://www.bi.go.id/SEKI/tabel/TABEL1_<n>.xls`. I checked each sheet title.

| n | title found |
|---|---|
| 1 | I.1 money supply and its determinants |
| 9 | I.9 working-capital credit by group and sector |
| 20 | I.20 private Rupiah deposits by province |
| 15 | I.15/I.16 property loans |
| 17 | **I.17 "Posisi simpanan masyarakat pada bank umum dan BPR menurut kelompok bank dan jenis simpanan"** |

The I.17 title translates as: outstanding private deposits of commercial and rural banks, by bank group and deposit
type (giro, tabungan, deposito), Rp bn, end of month.

**Provenance of the file kept.**
- URL: `https://www.bi.go.id/SEKI/tabel/TABEL1_17.xls`.
- Fetched 2026-10-29 23:07 local time (2026-10-30 02:07 UTC).
- 515,584 bytes. SHA-256 `bfc69eb14d7c0587456c355cd3c620f19b1628776d272ead20c47001cdc50383`.
- Copied unchanged into the new folder `data/raw/bi_seki_deposits/BI_SEKI_TABEL1_17.xls`.
- The four probe files that did not match were not kept in the project.

**Builder.** `code/py/build_bi_deposits.py` reads the file with `python -I` and executes nothing from it.
- It writes `data/clean/bi_deposits_by_group.csv`: 25,456 rows, 2002-01..2026-08. Columns: currency IDR/FX/all,
  bank group, deposit type total/demand/savings/time.
- It adds a derived `commercial_banks` group: persero + BPD + BSN + foreign. Foreign is the joint/foreign group to
  2024-12 and foreign branches from 2025-01.
- Sheets used, newest wins: 'Th 2002-2009' for months up to 2009-12; 'Th 2010-2024' for 2010-01..2024-12; '1.17_1'
  and '1.17_2' (LBUT vintage) from 2025-01.
- Validation, all in `output/tables/mech_bi_deposits_validation.csv`: deposit types vs group totals, max |gap| 0.04
  Rp bn; groups vs block totals 0.02; Rp + FX vs all 0.03.
- Two older sheets were revised by later ones. 'Th 2010-2012' vs 'Th 2010-2024': cells differ only in
  2016-03..2017-06, max 6.0% relative. The LBUT vintage in 2025-01..03 reclassified groups, but the total moved by
  only -1,422.5 Rp bn in 2025-01.
- The revised run reproduced the clean file's SHA-256 (`f3bd6c04…92e6`).

**Does SEKI I.17 already contain Islamic deposits?** Yes, at least for BUS. The tests (`mech_dpk_inclusion_tests.csv`)
follow `notes/data_panel.md` section 2.

| test | result |
|---|---|
| T1, 2014-05 (the LBUS footnote month) | Islamic DPK was 5.23% of SEKI commercial deposits in 2014-04. SEKI commercial deposits grew 1.41% in 2014-05 (median absolute monthly change 0.89%), so there is no 5% jump. If Islamic deposits had been first included that month (hypothesis B), conventional growth in 2014-05 would have been -4.03%. Under A (included throughout) it was 1.33%. The minimum of the A series over 2009-2025, excluding break months, is -2.12% (sd 1.29, 180 months). |
| T-level, OJK SPI | SPI commercial-bank DPK, which includes BUS: 8,457,929 (2023-12) and 8,837,242 (2024-12). SEKI private commercial deposits plus memo items (central government and non-residents): 8,431,802 and 8,798,873. The gap under A is 26,127 and 38,369 (0.3-0.4%). Under B, SEKI would have to equal SPI minus BUS DPK (465,932 and 511,374); it exceeds that by 439,804 and 473,005. |
| T4, conversions of conventional regional banks (BPD) to BUS | The abnormal BUS DPK jump was +19,268 (2016-09), +11,730 (2018-09) and +23,555 (2022-08). Under B, BPD deposits would fall by roughly that much. The abnormal BPD change was -11,707, +19,866 and -948: clearly against B in 2018-09 and 2022-08, ambiguous in 2016-09. BPD deposits are noisy. |

**Conventional DPK.**
- Definition: SEKI I.17 commercial banks (Rp + FX) minus OJK BUS+UUS harmonised DPK, by type. Total = total;
  demand = giro − `h_demand`; savings = tabungan − `h_sav`; time = deposito − `h_time`.
- UUS deposits sit inside the parent banks' reports. Their inclusion cannot be tested directly; it is assumed, as on
  the credit side.
- Concept mismatch: SEKI counts private deposits only. Central-government and non-resident deposits are memo items
  and are not split by bank group. OJK DPK includes all third-party funds. Robustness series `dpk_convmemo_total`
  adds the memo items.
- Islamic share of commercial private deposits: 2.30% in 2009-01, 8.17% in 2025-06.
- Conventional DPK covers 2009-01..2025-06: 187 monthly levels; 179 clean monthly changes for total and time
  deposits, 180 for demand and 178 for savings. It inherits every break and event flag of the Islamic series of the
  same type (`mech_series_coverage.csv`).

### 1.3 Rate series and splices

**Conventional rates.** SEKI I.28 time-deposit rates and I.26 lending rates for `commercial_banks`, Rupiah. Whether
BUS equivalent returns enter these averages is not documented. If they do, their weight would be roughly the
Islamic share of deposits (2.30% in 2009-01, 8.17% in 2025-06), which pulls spread responses slightly towards zero.

**Islamic deposit return, BUS_UUS (`dep_isl_<tenor>`).**
- Old-format Tabel 36 (currency unstated) for 2009-01..2014-05, then the new-format **Rupiah** tenor rate from 2014-06.
- Why Rupiah: the conventional comparator (I.28) is Rupiah only, and Rupiah is 91.9% of BUS_UUS mudharabah time
  deposits in 2014-06, 94.2% in 2025-06 and 94.3% on average (`mech_descriptives.csv`).
- The data note documents that old tenor rates track a deposit-weighted Rupiah+FX average better than Rupiah alone,
  so the old segment is probably an all-currency average.
- **The change into 2014-06 is always dropped.** The level jump across the splice is +1.19 pp at 1m, +1.57 (3m),
  +0.86 (6m) and +0.56 (12m). Median absolute clean monthly changes are about 0.18-0.25 pp (`mech_splice_jumps.csv`).
- Two robustness series: Rupiah only, 2014-06+ (`dep_isl_1m_post14`, `spread_1m_post14`); breaks only at the format
  switch (`*_minbrk`).
- The 1-month tenor is primary. 1-month deposits are on average 67.9% of BUS_UUS Rupiah time deposits (minimum 43.1%).

**BUS and UUS deposit returns.** New-format Rupiah, 2014-06+.

**Financing rates by contract.** Murabahah, mudharabah and musyarakah, BUS_UUS: old Tabel 36 to 2014-05, Rupiah from
2014-06, change into 2014-06 dropped. Also BUS and UUS murabahah from 2014-06.
- The old-format mudharabah rate is 21.32% in 2014-05 against 12.93% in 2014-06: **a -8.39 pp splice jump**, the
  definitional gap noted in the data note. The change is dropped, so it does not enter the estimates.
- Murabahah jumps -0.75 and musyarakah -0.54 at the splice.
- **Ijarah is not used.** The old ijarah rate changes method in Oct 2012 (Tabel 36 footnote) and is about 0.1-1%
  before that.

**Use-matched Islamic financing rates.** Tabel 18 working capital, investment and consumption; all debtor sizes,
all currencies; BUS_UUS; 2014-06+. They are compared with the conventional rate for the same use.

**Same-sample conventional comparators (new).** `dep_conv_1m_on_post14`, `_on_bus`, `_on_uus` and
`lend_conv_<use>_on_use` are the conventional series restricted to exactly the clean months of the matching Islamic
2014+ series. They are used only to compare pass-through ratios on the same months (section 4).

**Volumes and ratios.** `h_*` DPK in 100 × log. FDR = computed FDR (rule G). NPF = `npf_gross_pct_computed`.
Shares = 100 × murabahah / total and 100 × (mudharabah + musyarakah + other profit-sharing) / total. Old-format
musyarakah already includes other profit-sharing, so those months add 0.

### 1.4 Neutralising the known source copy errors

Every rule below is applied in the script, flagged in `data/clean/mech_monthly_series.csv` (via `change_clean`) and
listed cell by cell in `output/tables/mech_cleaning_cells.csv`. Counts come from `mech_cleaning_log.csv`, which also
verifies each audit claim before acting on it. Nothing is interpolated.

| rule | action | cells set to NA (verification) |
|---|---|---|
| 0 | rates published as exactly 0 (`zero_published`) mean "not applicable" | returns 479; margins 11,127 |
| A | deposit returns 2015-11: UUS and BUS_UUS → NA | 51 (UUS == BUS in 25 of 25 cell pairs) |
| B | contract margins 2024-09: BUS, UUS, BUS_UUS → NA | 74 (BUS == UUS in 23 of 23) |
| C | BUS_UUS → NA: contract 2015-08; sector 2018-09, 2018-10, 2020-04 | 23, 59, 59, 55 (BUS_UUS == BUS in 19/19, 55/55, 55/55, 52/53) |
| D | sector margins 2020-05, BUS_UUS cells equal to 3.888789 → NA | 42 (42 of 64 non-missing cells equal 3.888789) |
| E | deposit returns 2024-09 BUS_UUS → NA | 26 (BUS_UUS == BUS in 16 of 25) |
| F | one-month spike rule, applied once to all OJK rate series and to the BI rate series used: \|x_t − x_{t−1}\| > 5 and \|x_{t+1} − x_t\| > 5 with opposite signs; neighbours must be adjacent, non-missing months | returns 3 (>12m tenor: BUS_UUS 2009-02 and 2010-10, BUS Rupiah 2015-12); margins 78 (mostly tiny sector categories; clusters include 2015-10 and 2024-09); BI lending 1 (1999-12, outside the sample); BI deposit rates 0; policy rate 0 |
| G | FDR | computed FDR used everywhere; reported FDR never used |
| I | 2023-01..11 absent | every series is put on the complete 2009-01..2025-06 grid with NA there, so no change is computed across the gap; the change into 2023-12 is missing too |

Rule D was revised: the first version set the whole 64-cell BUS_UUS 2020-05 sector block to NA. The other 22 cells
have plausible, category-specific values and are now kept. Sector margins are not estimated, so no result changes.

**Cells hit inside the series actually used** (`mech_cleaning_used_series.csv`): rule A 8 cells (2015-11); rule E 4
cells (2024-09); rule B 5 contract cells (2024-09); rule C 3 contract cells (2015-08). None of the F spikes fell in a
series used. A UUS working-capital use-rate spike in 2024-09 was removed, but only the BUS_UUS use rates are used.
`mech_spike_cells.csv` lists the 82 spike cells (the first version had a spurious empty row, now dropped).

A scan of the OJK rate files for other cross-block copies found exactly the audit list. It also found UUS FX deposit
returns equal to 1.000000 in 2017-09..11; these are a plausible 1% floor, and FX rates are not used.

### 1.5 Contaminated changes (break months)

The change *into* a month is treated as contaminated, and any LP window containing it is dropped, in these cases:

| series | break months |
|---|---|
| Islamic rates, BUS_UUS spliced | 2014-05 (LSMK revision), 2014-06 (format switch), 2016-09 / 2018-09 / 2022-08 (whole conventional banks convert to BUS) |
| BUS / UUS series | 2014-07 (BTPN Syariah spin-off) and the three conversions |
| Islamic volumes and ratios, BUS_UUS | 2014-05 and the three conversions |
| conventional rates (I.26 / I.28) | 2025-01 (LBUT vintage switch) |
| SEKI deposits | 2014-05 and 2025-01 |
| conventional DPK and differentials | the union of the SEKI breaks and every break or event flag of the Islamic series |

All OJK Islamic series also get the event flags of 1.6. Spreads use the union of their components' breaks.
Per-series break lists and counts of clean changes are in `mech_series_coverage.csv`.

### 1.6 Conversion follow-up, merger and scan months (new)

`ojk_conversion_events.csv` lists, besides the three conversion months, the follow-up months 2016-10, 2018-10 and
2022-09, the BSI merger (2021-02) and five months with unattributed jumps found by a scan (S1 2015-06, S2
2021-10..12, S3 2016-12). The first version ignored them. The revision applies the house rule R3 of
`notes/data_panel.md` to every OJK-based Islamic series at these nine months:
- abnormal change = the change into the month minus the median of the previous 12 clean changes (at least 6);
- noise scale = 1.4826 × median |abnormal change| over 2014-06..2025-06, excluding break and candidate months;
- the change is flagged (treated as a break) if |abnormal| ≥ 3 × noise and, for log volumes, also ≥ 1%.

Of 405 series-months checked, 36 are flagged (`mech_event_flags.csv`; all z-scores listed). The flags that matter
for the results below:
- murabahah rate (BUS_UUS) 2016-10 (z = 5.2) and 2021-02 (z = -7.9); BUS murabahah 2016-10 and 2021-02; UUS
  murabahah 2021-10 and 2021-11;
- UUS 1-month return 2015-06 (z = -5.3), and the Rupiah-only 2014+ BUS_UUS return 2015-06 (z = -3.1). The spliced
  BUS_UUS 1-month return is not flagged there (z = -2.9), so the headline spread series is unchanged;
- Islamic total DPK 2021-12 (z = 3.3), time deposits 2021-11, savings 2016-12 and 2021-12; UUS time deposits
  2021-11 and 2022-09; FDR (BUS_UUS) 2021-11, UUS FDR 2022-09; murabahah and profit-sharing shares 2016-12.

**UUS DPK in 2022-09.** The verifier flagged a -5.66% fall in UUS total DPK in 2022-09 as a possible leftover of the
Bank Riau Kepri conversion. The rule does not flag the UUS total (abnormal -6.50%, z = -2.5), although it flags UUS
time deposits (z = -3.6). The levels (`mech_event_levels.csv`) show no reclassification signature: in 2022-09 UUS
fell by 9,482 Rp bn while BUS rose by only 773 (abnormal -1,942) and the Islamic total fell by 8,710. A UUS-to-BUS
transfer would show a mirrored BUS rise, as it does in the conversion month 2022-08 itself (BUS +25,036, UUS -5,452).
So the total is kept, as the rule says.

**Effect on results.** The headline deposit-spread series has no flag, so its results are unchanged. The flags change
the murabahah, DPK and UUS results; the main ones are reported both ways ("event rule off", series `*_noevt`).

## 2. Estimation

### 2.1 Estimators

**Local projections (`lp`)**, as in `11_macro_first_stage.R`: y_{t+h} − y_{t−1} on ε_t plus 3 lags of the
outcome's clean monthly change, OLS, Newey-West lag h+1. A horizon is reported only if at least 40 months remain.
Units: pp for rates and ratios, percent (100 log) for volumes.

**Robustness estimators:** `lp_ctrl` adds X_{t−1} = `CONTROLS` from `00_common.R` (VIX, Δlog Brent, Δlog IDR, BI
rate), lagged one month. `lp_seas` adds 11 calendar-month dummies for t (**an addition to the plan**: the volumes are
not seasonally adjusted, and FOMC meetings fall in fixed calendar months).

**Distributed lag (`dl`)**, `dl_ts` from `00_common.R`: the clean monthly change on ε_{t−k}, k = 0..24, cumulated,
NW(12); `dl_seas` adds the month dummies.

### 2.2 The DL and the LP use different samples

- The LP loses every window that touches a break. For the BUS_UUS rate series it keeps 88 months at h = 12 and 55
  at h = 24, against 175-176 months in the DL. For the BUS/UUS 1-month return and spread series, LP horizons beyond
  11-15 months have fewer than 40 months and are not reported.
- **The DL also uses shocks the LP never sees.** The DL outcome months start in 2009-02, and each is regressed on 25
  shock lags, so the DL uses shocks from 2007-02. The LP needs three own lags, so its first shock month is 2009-05.
  For the US shocks, 2007-02..2008-12 carries 67% (`MP_median`), 70% (`MP_pm`), 94% (statement) and 64% (CBI) as
  much shock variance as all of 2009-2025 (`mech_presample_shocks_summary.csv`). The largest `MP_median` values are -6.4 s.d.
  (2008-12), -5.3 s.d. (2007-09) and -4.2 s.d. (2008-11).
- This is part of why the two estimators disagree. Section 3.3 reports the DL with outcomes from 2011, where every
  shock lag is from 2009 or later.
- The DL also assumes exogenous, serially uncorrelated shocks and has no own-lag dynamics.

### 2.3 Shocks and scaling

`bi_rule_resid` (domestic, selection on observables); `jk_mp_median` (primary US, as pre-registered), `jk_mp_pm`,
`usmpd_stmt`; `jk_cbi_median` (information contrast). Results are per 25 bp (b25 = 0.25 b) and per 1 s.d. over
2009-01..2025-06 (`mech_shock_sd.csv`).

| shock | 1 s.d. (pp) | 25 bp in s.d. |
|---|---|---|
| bi_rule_resid | 0.1266 | 2.0 |
| jk_mp_median | 0.0350 | 7.1 |
| jk_mp_pm | 0.0354 | 7.1 |
| usmpd_stmt | 0.0224 | 11.2 |
| jk_cbi_median | 0.0194 | 12.9 |

**A 25 bp US surprise is a 7-13 s.d. event, so per-25 bp numbers are linear extrapolations far outside the data.**

### 2.4 Pass-through ratios, lead placebo

**Pass-through ratios** (`mech_passthrough.csv`): the cumulative response of the rate divided by the cumulative
response of the BI policy rate, both estimated on the same months, joint Newey-West covariance (lag h+1 for the LP,
12 for the DL), delta-method s.e. For a spread or gap the ratio is the difference in pass-through, with its own s.e.
Rows where the denominator has |t| < 2 are flagged "weak": 71% of the LP ratios for US shocks.

**Lead placebo** (`mech_pretrend.csv`, plan section 6): (i) LP: y_{t−1} − y_{t−5} on ε_t, NW(5), clean windows only;
(ii) DL: the sum of 6 lead coefficients ε_{t+1..t+6}.

### 2.5 Sample robustness and permutation (new)

- **Sample variants** (`mech_robustness.csv`, h = 0, 3, 6, 12, 24; h = 12 summary in `mech_robustness_h12.csv`).
  Each variant restricts the outcome months. The DL keeps month t's change if t is kept; the LP keeps the window t if
  every month of [t−1, t+h] is kept. Variants: full; from 2010-01 (no 2009 outcome months); from 2011-01; from
  2014-07; to 2014-04; the plan's section-6 checks (drop 2014, 2016, 2017 and 2021; drop 2020-03..2021-12); and
  leave one calendar year out, 2009..2025. Run for 24 outcomes × 5 shocks × {LP, DL}. All variants run are reported.
- **Block permutation** (`mech_permutation.csv`, plan sections 4 and 6): the monthly shock series over 2007-01..2025-06
  (which covers every month the DL uses) is permuted in 12-month blocks, 2,000 draws, and the DL and LP at h = 12 are re-estimated on the same rows; p is the
  share of draws with |b*| ≥ |b|. Run for 6 outcomes × 5 shocks.

### 2.6 Timing

Monthly US shocks sum events by their ET date. An FOMC statement at 14:00 ET is after midnight in Jakarta, so an
event on the last calendar day of a month reaches Indonesian markets on day 1 of the next month but is dated in the
earlier month. In 2009-01..2025-06 this affects 7 of 136 non-zero `MP_median` events (2013-07-31, 2014-04-30,
2018-01-31, 2019-07-31, 2020-03-31, 2024-01-31, 2024-07-31), 1.2% of its sum of squares (statement 2.5%, CBI 3.1%;
`mech_timing.csv`). It mainly attenuates h = 0.

## 3. Results: deposit-rate pass-through (1-month tenor)

### 3.1 Main estimates

Per 25 bp, b25 (s.e.); * = 90% band excludes 0. n = months at h = 0 / 12 / 24. Source: `mech_key_results.csv`.

**Domestic shock, `bi_rule_resid`** (25 bp = 2.0 s.d.)

<!-- chk res shock=bi_rule_resid -->
| outcome | est | h=0 | h=3 | h=6 | h=12 | h=24 | n |
|---|---|---|---|---|---|---|---|
| BI policy rate | lp | 0.10 (0.02)* | 0.42 (0.08)* | 0.51 (0.10)* | 0.45 (0.11)* | 0.26 (0.16) | 194/182/170 |
| | dl | 0.12 (0.02)* | 0.51 (0.03)* | 0.64 (0.05)* | 0.63 (0.10)* | 0.52 (0.15)* | 197 |
| conventional 1m | lp | 0.02 (0.02) | 0.28 (0.08)* | 0.42 (0.12)* | 0.43 (0.14)* | 0.34 (0.18)* | 190/176/164 |
| | dl | 0.05 (0.01)* | 0.40 (0.06)* | 0.58 (0.11)* | 0.66 (0.17)* | 0.56 (0.28)* | 196 |
| Islamic 1m (BUS_UUS) | lp | -0.11 (0.07)* | -0.03 (0.07) | 0.14 (0.15) | 0.11 (0.13) | 0.50 (0.18)* | 152/88/55 |
| | dl | -0.04 (0.06) | 0.08 (0.10) | 0.35 (0.11)* | 0.51 (0.19)* | 0.65 (0.34)* | 176 |
| spread Isl − conv | lp | -0.10 (0.06)* | -0.26 (0.09)* | -0.27 (0.16)* | 0.08 (0.15) | 0.43 (0.30) | 149/88/55 |
| | dl | -0.08 (0.06) | -0.30 (0.12)* | -0.23 (0.13)* | -0.11 (0.22) | 0.18 (0.33) | 175 |
| spread BUS − conv | lp | -0.06 (0.05) | -0.15 (0.09)* | 0.04 (0.08) | 0.16 (0.12) | | 97/49/- |
| | dl | -0.06 (0.06) | -0.20 (0.11)* | -0.12 (0.15) | -0.16 (0.22) | -0.10 (0.31) | 115 |
| spread UUS − conv | lp | -0.03 (0.06) | -0.20 (0.10)* | 0.06 (0.09) | | | 88/-/- |
| | dl | -0.04 (0.07) | -0.18 (0.08)* | -0.18 (0.15) | -0.09 (0.23) | 0.13 (0.32) | 112 |
| gap BUS − UUS | lp | -0.02 (0.07) | -0.01 (0.11) | -0.05 (0.12) | 0.11 (0.07) | | 92/42/- |
| | dl | -0.01 (0.09) | 0.01 (0.13) | 0.07 (0.17) | -0.04 (0.36) | -0.16 (0.48) | 113 |

**US pure monetary policy shock, `jk_mp_median`** (25 bp = 7.1 s.d.)

<!-- chk res shock=jk_mp_median -->
| outcome | est | h=0 | h=3 | h=6 | h=12 | h=24 | n |
|---|---|---|---|---|---|---|---|
| BI policy rate | lp | 0.03 (0.07) | 0.21 (0.27) | 0.65 (0.46) | 1.27 (0.58)* | 2.25 (0.47)* | 194/182/170 |
| | dl | 0.04 (0.07) | 0.45 (0.24)* | 0.87 (0.34)* | 1.15 (0.36)* | 1.38 (0.40)* | 197 |
| conventional 1m | lp | -0.04 (0.08) | 0.07 (0.24) | 0.35 (0.43) | 0.82 (0.60) | 2.31 (0.57)* | 190/176/164 |
| | dl | -0.05 (0.09) | 0.44 (0.23)* | 0.81 (0.32)* | 1.30 (0.43)* | 1.69 (0.47)* | 196 |
| Islamic 1m (BUS_UUS) | lp | -0.11 (0.25) | -0.66 (0.53) | -0.27 (0.51) | -1.08 (0.73) | -0.42 (0.92) | 152/88/55 |
| | dl | 0.04 (0.20) | -0.28 (0.35) | 0.25 (0.31) | 0.22 (0.39) | 0.45 (0.49) | 176 |
| spread Isl − conv | lp | -0.09 (0.21) | -0.28 (0.50) | 0.07 (0.77) | -1.15 (1.11) | -3.44 (1.39)* | 149/88/55 |
| | dl | 0.06 (0.21) | -0.82 (0.53) | -0.68 (0.54) | -1.41 (0.60)* | -1.58 (0.59)* | 175 |
| BUS 1m | lp | 0.01 (0.17) | -0.31 (0.18)* | -0.64 (0.38)* | -0.31 (0.32) | | 101/52/- |
| | dl | -0.18 (0.14) | -0.38 (0.24) | 0.12 (0.31) | 0.97 (0.70) | 1.61 (0.52)* | 116 |
| UUS 1m | lp | -0.07 (0.18) | -0.19 (0.27) | -0.33 (0.49) | -0.55 (0.59) | | 92/42/- |
| | dl | -0.00 (0.32) | 0.34 (0.31) | 1.21 (0.49)* | 1.89 (0.51)* | 2.58 (0.50)* | 113 |
| spread BUS − conv | lp | -0.15 (0.10) | -0.38 (0.23)* | -1.05 (0.27)* | -0.68 (0.41)* | | 97/49/- |
| | dl | -0.19 (0.14) | -0.80 (0.27)* | -0.91 (0.27)* | -1.11 (0.65)* | -1.01 (0.70) | 115 |
| spread UUS − conv | lp | -0.21 (0.12)* | 0.25 (0.54) | -0.17 (0.46) | | | 88/-/- |
| | dl | -0.02 (0.29) | -0.26 (0.40) | 0.10 (0.55) | -0.52 (0.61) | -0.36 (0.77) | 112 |
| gap BUS − UUS | lp | 0.07 (0.15) | -0.19 (0.36) | -0.44 (0.42) | -0.14 (0.36) | | 92/42/- |
| | dl | -0.24 (0.43) | -0.83 (0.39)* | -1.15 (0.43)* | -0.49 (0.76) | -0.71 (0.66) | 113 |
| gap BUS − UUS, event rule off | lp | -0.07 (0.19) | -0.64 (0.39) | -1.09 (0.57)* | -0.14 (0.36) | | 96/42/- |
| | dl | -0.25 (0.46) | -1.00 (0.45)* | -1.41 (0.48)* | -0.62 (0.80) | -0.89 (0.62) | 114 |

The UUS rows changed slightly from the first version because the UUS 1-month return is now flagged in 2015-06
(1.6); the event-rule-off gap row reproduces the first version's series.

### 3.2 The 1-month spread by estimator, h = 12 and 24

<!-- chk spreadrob -->
| shock | lp h12 | lp_ctrl h12 | lp_seas h12 | dl h12 | dl_seas h12 | lp h24 | dl h24 |
|---|---|---|---|---|---|---|---|
| bi_rule_resid | 0.08 (0.15) | 0.13 (0.14) | 0.06 (0.16) | -0.11 (0.22) | -0.11 (0.21) | 0.43 (0.30) | 0.18 (0.33) |
| jk_mp_median | -1.15 (1.11) | -1.19 (1.04) | -1.19 (1.36) | -1.41 (0.60)* | -1.33 (0.50)* | -3.44 (1.39)* | -1.58 (0.59)* |
| jk_mp_pm | -1.59 (1.08) | -1.60 (0.98) | -1.83 (1.32) | -1.47 (0.48)* | -1.49 (0.38)* | -2.05 (1.38) | -1.72 (0.58)* |
| usmpd_stmt | -1.74 (1.08) | -1.73 (0.93)* | -1.99 (1.19)* | -2.20 (0.67)* | -2.12 (0.63)* | -1.52 (1.27) | -2.48 (0.89)* |
| jk_cbi_median | -2.36 (1.23)* | -1.94 (0.90)* | -2.76 (1.44)* | -2.50 (1.09)* | -2.74 (1.12)* | 2.26 (1.18)* | -3.17 (1.61)* |

- For the three pure US shocks the LP has the same sign as the DL but is significant at 12 months only with controls
  or month dummies for the statement surprise. The LP MDE at h = 12 is 3.11 per 25 bp for `MP_median` (DL 1.67).
- **Splice robustness** (Rupiah only, 2014-06+, DL h = 12): `MP_median` -0.99 (0.52), `MP_pm` -0.68 (0.38),
  `usmpd_stmt` -1.40 (0.41), `bi_rule_resid` -0.10 (0.19). (The first version reported -0.94 (0.51) for `MP_median`;
  the change comes from the 2015-06 event flag on this series.)
- **Minimal-break robustness** (DL h = 12): `MP_median` -1.31 (0.57), `MP_pm` -1.26 (0.45), `bi_rule_resid` 0.02 (0.19).
- **Other tenors** (DL h = 12, `MP_median`): 3m -0.76 (0.45), 6m -0.86 (0.91), 12m -1.18 (0.44).
- **Per 1 s.d.** (DL, h = 12): -0.20 (0.08) for `MP_median`, -0.21 (0.07) `MP_pm`, -0.20 (0.06) `usmpd_stmt`, -0.19
  (0.08) `jk_cbi_median`, -0.05 (0.11) `bi_rule_resid`.

### 3.3 Sample robustness at h = 12 (new)

Columns restrict the outcome months (2.5). "LOYO" = leave one calendar year out (17 years): the range of b25, with the
year left out in brackets, and the smallest |t| with its year.

**Spread Islamic − conventional, 1m**

<!-- chk rob outcome=spread_1m -->
| shock | est | full | from 2010 | from 2011 | from 2014-07 | to 2014-04 | drop 2014, 2016-17, 2021 | drop 2020-03..2021-12 | LOYO range | min \|t\| (year) |
|---|---|---|---|---|---|---|---|---|---|---|
| bi_rule_resid | dl | -0.11 (0.22) | -0.11 (0.20) | -0.16 (0.19) | -0.22 (0.21) | 0.09 (0.60) | 0.30 (0.24) | -0.10 (0.22) | -0.23 (2022) .. 0.16 (2014) | 0.11 (2017) |
| bi_rule_resid | lp | 0.08 (0.15) | 0.07 (0.16) | 0.04 (0.18) | 0.28 (0.09)* | 0.10 (0.28) | -0.09 (0.16) | 0.12 (0.25) | 0.02 (2011) .. 0.23 (2012) | 0.11 (2011) |
| jk_mp_median | dl | -1.41 (0.60)* | -0.58 (0.48) | -0.58 (0.50) | -0.87 (0.51)* | -1.83 (1.44) | -1.50 (0.61)* | -1.35 (0.67)* | -1.68 (2011) .. -0.58 (2009) | 1.20 (2009) |
| jk_mp_median | lp | -1.15 (1.11) | -1.12 (1.18) | -1.55 (1.27) | -1.00 (0.52)* | 0.31 (1.76) | -0.11 (1.29) | -0.29 (1.63) | -3.20 (2011) .. -0.06 (2020) | 0.04 (2020) |
| jk_mp_pm | dl | -1.47 (0.48)* | -0.78 (0.38)* | -0.76 (0.42)* | -0.71 (0.40)* | -0.90 (2.93) | -1.59 (0.49)* | -1.58 (0.56)* | -1.91 (2022) .. -0.78 (2009) | 2.03 (2009) |
| jk_mp_pm | lp | -1.59 (1.08) | -1.52 (1.02) | -1.62 (0.98)* | -0.64 (0.38)* | -2.16 (3.01) | -1.40 (1.82) | -2.26 (2.63) | -2.64 (2011) .. -0.18 (2013) | 0.51 (2013) |
| usmpd_stmt | dl | -2.20 (0.67)* | -1.42 (0.54)* | -1.55 (0.57)* | -1.41 (0.44)* | -0.19 (2.98) | -2.50 (0.64)* | -1.91 (0.86)* | -2.48 (2020) .. -1.42 (2009) | 2.61 (2009) |
| usmpd_stmt | lp | -1.74 (1.08) | -1.55 (0.91)* | -1.67 (0.87)* | -0.68 (0.35)* | -4.10 (4.03) | -2.54 (2.73) | -4.03 (3.57) | -3.79 (2020) .. -0.37 (2013) | 1.05 (2021) |
| jk_cbi_median | dl | -2.50 (1.09)* | -1.73 (0.89)* | -1.88 (0.96)* | -1.57 (1.12) | -3.45 (3.32) | -2.39 (1.44)* | -2.35 (1.17)* | -3.16 (2015) .. -1.73 (2009) | 1.65 (2014) |
| jk_cbi_median | lp | -2.36 (1.23)* | -1.93 (1.03)* | -1.83 (1.31) | -0.42 (0.47) | -4.22 (2.08)* | -3.30 (1.37)* | -3.45 (1.72)* | -3.70 (2020) .. -0.69 (2013) | 1.14 (2013) |

- Months used, DL: 175 full, 164 from 2010, 152 from 2011, 112 from 2014-07. LP: 88, 79, 67, 40.
- Per 1 s.d. without 2009 (DL, from 2010): `MP_median` -0.08 (0.07), `MP_pm` -0.11 (0.05), `usmpd_stmt` -0.13 (0.05).
  From 2014-07: -0.12 (0.07), -0.10 (0.06), -0.13 (0.04).
- The plan's two section-6 checks (drop the break and merger years; drop the pandemic) leave the DL estimate
  unchanged in size and significance for all four US series. Dropping 2009 is what matters.
- Plan section 7 lists "a significant β_12 driven by a single sector" as undermining a result. A significant
  `MP_median` estimate that disappears when one year (2009) is dropped is the time-series analogue, and is reported
  here as undermining the primary-shock result.

**Spread BUS − conventional, 1m (2014-06+, so the first four columns coincide)**

<!-- chk rob outcome=spread_bus_1m -->
| shock | est | full | from 2010 | from 2011 | from 2014-07 | to 2014-04 | drop 2014, 2016-17, 2021 | drop 2020-03..2021-12 | LOYO range | min \|t\| (year) |
|---|---|---|---|---|---|---|---|---|---|---|
| jk_mp_median | dl | -1.11 (0.65)* | -1.11 (0.65)* | -1.11 (0.65)* | -1.11 (0.65)* | | -1.58 (0.99) | -0.93 (0.69) | -1.97 (2022) .. -0.74 (2018) | 1.25 (2021) |
| jk_mp_median | lp | -0.68 (0.41)* | -0.68 (0.41)* | -0.68 (0.41)* | -0.68 (0.41)* | | | | -0.82 (2016) .. -0.36 (2022) | 1.18 (2017) |
| jk_mp_pm | dl | -0.83 (0.50)* | -0.83 (0.50)* | -0.83 (0.50)* | -0.83 (0.50)* | | -1.00 (0.77) | -0.67 (0.64) | -1.66 (2022) .. -0.57 (2018) | 1.07 (2021) |
| jk_mp_pm | lp | -0.65 (0.35)* | -0.65 (0.35)* | -0.65 (0.35)* | -0.65 (0.35)* | | | | -0.65 (2009) .. -0.35 (2022) | 1.35 (2016) |
| usmpd_stmt | dl | -1.72 (0.46)* | -1.72 (0.46)* | -1.72 (0.46)* | -1.72 (0.46)* | | -2.37 (0.88)* | -1.85 (0.80)* | -2.02 (2020) .. -1.39 (2021) | 1.68 (2021) |
| usmpd_stmt | lp | -0.79 (0.33)* | -0.79 (0.33)* | -0.79 (0.33)* | -0.79 (0.33)* | | | | -0.79 (2009) .. -0.53 (2022) | 1.82 (2016) |

- Months: DL 115 (75 without 2014, 2016-17 and 2021; 93 without the pandemic); LP 49 at h = 12, too few for the
  plan's checks. Lead tests pass for all three (`mech_pretrend.csv`). Per s.d., LP -0.10, -0.09, -0.07 and DL -0.16,
  -0.12, -0.15 pp. Block permutation, `MP_median`: DL p = 0.0355, LP p = 0.1775.

**Conventional 1m and BI rate, DL, h = 12** (same variants; full table in `mech_results_tables.md`)

<!-- chk rob outcome=dep_conv_1m -->
| shock | est | full | from 2010 | from 2011 | from 2014-07 | to 2014-04 | drop 2014, 2016-17, 2021 | drop 2020-03..2021-12 | LOYO range | min \|t\| (year) |
|---|---|---|---|---|---|---|---|---|---|---|
| jk_mp_median | dl | 1.30 (0.43)* | 0.68 (0.49) | 0.72 (0.46) | 1.32 (0.26)* | 1.14 (1.21) | 1.32 (0.45)* | 1.20 (0.49)* | 0.68 (2009) .. 1.50 (2023) | 1.38 (2009) |
| jk_mp_pm | dl | 1.44 (0.33)* | 1.10 (0.28)* | 1.12 (0.26)* | 1.23 (0.23)* | 1.17 (1.10) | 1.44 (0.36)* | 1.36 (0.38)* | 1.10 (2009) .. 1.76 (2023) | 3.06 (2022) |
| usmpd_stmt | dl | 2.53 (0.42)* | 2.12 (0.48)* | 2.22 (0.44)* | 2.38 (0.36)* | 0.67 (2.97) | 2.58 (0.52)* | 2.47 (0.70)* | 2.12 (2009) .. 2.73 (2023) | 4.04 (2020) |

<!-- chk rob outcome=bi_policy -->
| shock | est | full | from 2010 | from 2011 | from 2014-07 | to 2014-04 | drop 2014, 2016-17, 2021 | drop 2020-03..2021-12 | LOYO range | min \|t\| (year) |
|---|---|---|---|---|---|---|---|---|---|---|
| jk_mp_median | dl | 1.15 (0.36)* | 0.97 (0.54)* | 0.99 (0.53)* | 1.60 (0.38)* | 0.48 (0.88) | 1.09 (0.38)* | 1.06 (0.37)* | 0.86 (2022) .. 1.33 (2011) | 1.79 (2009) |

- The Islamic 1-month return after `MP_median` from 2014-07 rises in the DL, 1.54 (0.48) (Rupiah-only series 1.45
  (0.52), `mech_deposit_rates.csv`), but not in the LP, -0.54 (0.37) (`mech_robustness_h12.csv`). In the full sample
  it is 0.22 (0.39) (DL) and -1.08 (0.73) (LP).

### 3.4 Block permutation, h = 12

<!-- chk perm -->
| outcome | shock | est | b25 | n | p (k/2000) |
|---|---|---|---|---|---|
| spread_1m | jk_mp_median | dl | -1.41 | 175 | 0.0180 |
| spread_1m | jk_mp_median | lp | -1.15 | 88 | 0.1415 |
| spread_1m | jk_mp_pm | dl | -1.47 | 175 | 0.0130 |
| spread_1m | jk_mp_pm | lp | -1.59 | 88 | 0.0560 |
| spread_1m | usmpd_stmt | dl | -2.20 | 175 | 0.0205 |
| spread_1m | usmpd_stmt | lp | -1.74 | 88 | 0.1275 |
| spread_1m | jk_cbi_median | dl | -2.50 | 175 | 0.0240 |
| spread_1m | bi_rule_resid | dl | -0.11 | 175 | 0.5930 |
| spread_1m_post14 | jk_mp_median | dl | -0.99 | 110 | 0.0495 |
| spread_bus_1m | jk_mp_median | dl | -1.11 | 115 | 0.0355 |
| gap_bus_uus_1m | jk_mp_median | dl | -0.49 | 113 | 0.3190 |
| gap_bus_uus_1m | jk_mp_median | lp | -0.14 | 42 | 0.6630 |
| fspread_isl_murabahah_wc | jk_mp_median | dl | -1.41 | 169 | 0.0065 |
| fspread_isl_murabahah_wc | jk_mp_median | lp | -1.37 | 52 | 0.0890 |
| dpk_diff_total | jk_mp_median | dl | -3.71 | 179 | 0.4115 |
| dpk_diff_total | jk_mp_median | lp | 7.95 | 91 | 0.1790 |

The permutation p-values agree with the Newey-West inference: the full-sample DL spread rejects, the LP does not.
The permutation keeps the 2007-08 shocks in the pool, so it does not address the 2009 dependence.

### 3.5 The CBI information shock: a caution, not corroboration

- The CBI spread response has the same sign as the pure policy shocks: -2.50 (1.09) at 12 months (DL), -0.19 (0.08)
  per s.d.
- But the CBI spread **fails the DL lead test**: -1.00 (0.60), p = 0.094. The BI rate's CBI lead test gives 0.83
  (0.43), p = 0.055.
- The LP **flips sign at 24 months**: +2.26 (1.18) against -3.17 (1.61) in the DL.
- CBI moves the BI rate by 4.05 (1.00) per 25 bp at 12 months (DL), 0.31 pp per s.d., about twice the 0.16 per s.d.
  for `MP_median`. The conventional 1m rate moves 0.32 per s.d. (CBI) against 0.18 (`MP_median`).
- A Fed "information" surprise that moves Indonesian rates more than a pure policy surprise, with leads, points to
  common global-cycle co-movement picked up by the aggregate DL. That weakens the causal reading of every US-shock
  DL result here, not only the CBI one.

## 4. Pass-through ratios (rate / BI policy rate, cumulative, same months)

DL estimates, ratio (s.e.); the LP versions are in `mech_passthrough.csv`. Rows marked "same months" restrict the
conventional rate to the clean months of the Islamic 2014+ series above them, so those pairs are comparable.

<!-- chk pt -->
| rate | bi_rule_resid h6 | bi_rule_resid h12 | jk_mp_median h6 | jk_mp_median h12 | jk_mp_pm h6 | jk_mp_pm h12 |
|---|---|---|---|---|---|---|
| conventional deposit 1m | 0.91 (0.16) | 1.04 (0.24) | 0.92 (0.21) | 1.12 (0.29) | 0.82 (0.13) | 0.92 (0.18) |
| Islamic deposit 1m (BUS_UUS, 2009+) | 0.56 (0.18) | 0.82 (0.34) | 0.29 (0.39) | 0.17 (0.29) | 0.16 (0.27) | 0.24 (0.21) |
| difference: spread 1m | -0.37 (0.19) | -0.17 (0.34) | -0.78 (0.48) | -1.11 (0.51) | -0.81 (0.36) | -0.81 (0.32) |
| Islamic 1m, Rupiah 2014-06+ | 0.39 (0.20) | 0.37 (0.31) | 0.30 (0.19) | 0.50 (0.16) | 0.23 (0.19) | 0.51 (0.13) |
| conventional 1m, same months as Rupiah 2014-06+ | 0.61 (0.14) | 0.53 (0.23) | 0.93 (0.19) | 0.84 (0.14) | 0.86 (0.14) | 0.79 (0.12) |
| BUS 1m (2014-06+) | 0.42 (0.23) | 0.29 (0.41) | 0.10 (0.26) | 0.37 (0.23) | 0.04 (0.24) | 0.40 (0.18) |
| conventional 1m, same months as BUS | 0.61 (0.13) | 0.54 (0.21) | 0.92 (0.19) | 0.79 (0.13) | 0.82 (0.13) | 0.74 (0.13) |
| UUS 1m (2014-06+) | 0.26 (0.17) | 0.38 (0.27) | 1.04 (0.39) | 0.65 (0.16) | 0.94 (0.42) | 0.70 (0.15) |
| conventional 1m, same months as UUS | 0.60 (0.14) | 0.54 (0.22) | 0.89 (0.16) | 0.81 (0.14) | 0.81 (0.13) | 0.76 (0.13) |
| difference: BUS − UUS | 0.12 (0.28) | -0.07 (0.57) | -0.98 (0.41) | -0.17 (0.26) | -0.93 (0.40) | -0.24 (0.23) |
| conventional deposit 3m | 0.92 (0.18) | 1.12 (0.29) | 1.15 (0.32) | 1.27 (0.40) | 0.90 (0.18) | 1.00 (0.23) |
| Islamic deposit 3m | 0.74 (0.24) | 1.00 (0.55) | 0.99 (0.43) | 0.81 (0.34) | 0.74 (0.32) | 0.74 (0.25) |
| conventional lending, working capital | 0.40 (0.08) | 0.57 (0.13) | 0.32 (0.08) | 0.47 (0.11) | 0.25 (0.07) | 0.40 (0.05) |
| conventional lending, consumption | 0.09 (0.06) | 0.30 (0.10) | -0.07 (0.14) | -0.06 (0.14) | -0.09 (0.14) | -0.11 (0.14) |
| Islamic murabahah | 0.17 (0.23) | 0.50 (0.40) | -0.52 (0.31) | -0.71 (0.44) | -0.10 (0.18) | -0.28 (0.23) |
| Islamic use-matched consumption (2014-06+) | 0.50 (0.28) | 0.63 (0.31) | -0.24 (0.20) | -0.28 (0.21) | 0.04 (0.24) | -0.15 (0.20) |
| conventional consumption, same months | 0.09 (0.11) | 0.28 (0.15) | -0.03 (0.16) | -0.07 (0.11) | 0.01 (0.10) | -0.03 (0.10) |
| Islamic use-matched working capital (2014-06+) | 0.47 (0.22) | 0.01 (0.47) | 0.89 (0.62) | 0.60 (0.34) | 0.81 (0.49) | 0.62 (0.32) |
| conventional working capital, same months | 0.23 (0.08) | 0.35 (0.07) | 0.23 (0.06) | 0.21 (0.04) | 0.23 (0.07) | 0.25 (0.05) |
| difference: use-matched WC spread | 0.22 (0.23) | -0.36 (0.47) | 0.66 (0.63) | 0.39 (0.32) | 0.59 (0.48) | 0.36 (0.28) |

- The BI-rate denominators of the DL ratios have |t| between 2.3 and 12.5 across all DL rows.
- **On the same 2014+ months**, the Islamic 1-month pass-through after `MP_median` is 0.50 (0.16) against 0.84
  (0.14) for conventional; the gap is the spread ratio -0.34 (0.20).
- **BUS vs UUS.** BUS 0.37 (0.23) and UUS 0.65 (0.16) at 12 months (the first version reported 0.71 for UUS,
  before the 2015-06 flag). The direct difference is -0.17 (0.26) at 12 months and -0.98 (0.41) at 6 months.
- **Use-matched working capital.** On the same months the conventional working-capital ratio is 0.21 (0.04), not the
  full-sample 0.47 (0.11) the first version compared against. The Islamic ratio is 0.60 (0.34); the difference is
  0.39 (0.32). So the Islamic working-capital rate passes through at least as much as the conventional one.
- LP versions: `bi_rule_resid` h = 12, conventional 1m 0.91 (0.22), Islamic 1m 0.35 (0.50), weak; `jk_mp_pm` h = 12,
  conventional 1m 0.79 (0.13).

## 5. Results: financing rates

Per 25 bp, DL (LP in `mech_financing_rates.csv`).

<!-- chk res5 -->
| outcome | shock | h=0 | h=3 | h=6 | h=12 | h=24 |
|---|---|---|---|---|---|---|
| murabahah rate | bi_rule_resid | 0.10 (0.07) | 0.21 (0.18) | 0.10 (0.14) | 0.31 (0.25) | 0.61 (0.34)* |
| conv. working-capital rate | bi_rule_resid | 0.03 (0.01)* | 0.14 (0.03)* | 0.25 (0.05)* | 0.36 (0.09)* | 0.37 (0.12)* |
| spread murabahah − conv. WC | bi_rule_resid | 0.06 (0.07) | 0.07 (0.16) | -0.13 (0.13) | -0.01 (0.22) | 0.26 (0.30) |
| murabahah rate | jk_mp_median | -0.31 (0.40) | -0.13 (0.22) | -0.47 (0.22)* | -0.89 (0.35)* | -0.36 (0.39) |
| conv. working-capital rate | jk_mp_median | -0.00 (0.04) | 0.22 (0.09)* | 0.28 (0.12)* | 0.55 (0.16)* | 0.86 (0.17)* |
| spread murabahah − conv. WC | jk_mp_median | -0.28 (0.39) | -0.32 (0.26) | -0.74 (0.28)* | -1.41 (0.43)* | -1.32 (0.45)* |
| spread murabahah − conv. WC, event rule off | jk_mp_median | -0.28 (0.39) | -0.39 (0.25) | -0.78 (0.28)* | -1.36 (0.46)* | -1.40 (0.47)* |
| spread murabahah − conv. consumption | jk_mp_median | -0.36 (0.40) | -0.09 (0.24) | -0.40 (0.18)* | -0.84 (0.37)* | -0.89 (0.64) |
| spread mudharabah − conv. WC | jk_mp_median | 0.26 (0.14)* | 0.07 (0.34) | -0.22 (0.34) | -0.48 (0.35) | -0.90 (0.50)* |
| spread musyarakah − conv. investment | jk_mp_median | 0.34 (0.34) | -0.18 (0.48) | -0.23 (0.32) | -0.79 (0.53) | -1.63 (0.84)* |
| BUS murabahah | jk_mp_median | 0.15 (0.09)* | 0.05 (0.14) | -0.08 (0.13) | -0.28 (0.21) | -0.22 (0.20) |
| UUS murabahah | jk_mp_median | -0.02 (0.06) | -0.21 (0.09)* | -0.16 (0.09)* | -0.07 (0.19) | 0.15 (0.22) |
| Islamic use-matched WC rate | jk_mp_median | 0.51 (0.30)* | 0.76 (0.49) | 1.00 (0.55)* | 1.58 (0.78)* | 1.23 (0.92) |
| spread use-matched consumption | jk_mp_median | -0.08 (0.17) | -0.04 (0.31) | -0.24 (0.26) | -0.54 (0.57) | -0.41 (0.91) |
| spread use-matched WC | jk_mp_median | 0.52 (0.28)* | 0.62 (0.57) | 0.75 (0.60) | 1.03 (0.77) | 0.32 (0.91) |

**Sample robustness of the murabahah − working-capital spread, h = 12**

<!-- chk rob outcome=fspread_isl_murabahah_wc -->
| shock | est | full | from 2010 | from 2011 | from 2014-07 | to 2014-04 | drop 2014, 2016-17, 2021 | drop 2020-03..2021-12 | LOYO range | min \|t\| (year) |
|---|---|---|---|---|---|---|---|---|---|---|
| jk_mp_median | dl | -1.41 (0.43)* | -0.75 (0.43)* | -0.66 (0.39)* | -0.53 (0.39) | -2.15 (0.75)* | -1.50 (0.49)* | -1.50 (0.49)* | -1.66 (2022) .. -0.75 (2009) | 1.77 (2009) |
| jk_mp_median | lp | -1.37 (1.17) | -1.37 (1.17) | -1.43 (1.25) | | | | | -1.69 (2021) .. -1.33 (2017) | 1.13 (2014) |
| jk_mp_pm | dl | -1.06 (0.34)* | -0.61 (0.33)* | -0.64 (0.32)* | -0.52 (0.30)* | -1.95 (1.62) | -0.98 (0.34)* | -1.03 (0.39)* | -1.28 (2022) .. -0.61 (2009) | 1.87 (2009) |
| usmpd_stmt | dl | -1.43 (0.61)* | -0.58 (0.55) | -0.54 (0.55) | -0.78 (0.37)* | -0.61 (3.93) | -0.93 (0.83) | -1.09 (1.01) | -1.79 (2020) .. -0.58 (2009) | 1.06 (2009) |

<!-- chk rob outcome=fspread_isl_murabahah_wc_noevt -->
| shock | est | full | from 2010 | from 2011 | from 2014-07 | to 2014-04 | drop 2014, 2016-17, 2021 | drop 2020-03..2021-12 | LOYO range | min \|t\| (year) |
|---|---|---|---|---|---|---|---|---|---|---|
| jk_mp_median | dl | -1.36 (0.46)* | -0.62 (0.40) | -0.52 (0.36) | -0.27 (0.31) | -2.15 (0.75)* | -1.50 (0.49)* | -1.47 (0.48)* | -1.64 (2022) .. -0.62 (2009) | 1.54 (2009) |
| jk_mp_median | lp | -1.12 (0.72) | -1.12 (0.72) | -1.15 (0.75) | | | | -3.06 (1.83)* | -2.29 (2020) .. -0.17 (2012) | 0.51 (2012) |

- **After 2014** (DL, h = 12, `MP_median` / `MP_pm` / statement; `mech_robustness_h12.csv`): murabahah rate 0.02
  (0.40), 0.05 (0.35), 0.13 (0.46); conventional working-capital rate 0.54 (0.15), 0.58 (0.10), 0.93 (0.23);
  conventional consumption rate -0.04 (0.22), -0.03 (0.17), -0.06 (0.26); murabahah − consumption spread 0.18 (0.49),
  0.14 (0.42), 0.11 (0.52). The post-2014 murabahah − WC spread is negative because WC rates move, not because
  murabahah moves; against the consumption comparator there is nothing.
- The second block is the event-rule-off series (the first version's breaks). The verifier's numbers, -0.62 (0.40)
  without 2009 and -0.27 (0.31) from 2014-07, are reproduced there. With the 2016-10 and 2021-02 flags, the 2014-07+
  estimate becomes -0.53 (0.39): still not significant. The 2009-2014 sub-sample gives -2.15 (0.75) either way.
- LP months at h = 12: 52 (event rule on) and 69 (off); the event-rule-off LP without the pandemic uses 40. Blank
  cells: fewer than 40 months.
- Block permutation (h = 12, `MP_median`): DL p = 0.0065; LP p = 0.0890.

## 6. Results: funding volumes, FDR, contract mix, NPF

Per 25 bp, percent (DPK) or pp (FDR, shares, NPF).

<!-- chk res6 -->
| outcome | shock | est | h=0 | h=3 | h=6 | h=12 | h=24 | n (h0/h12/h24) |
|---|---|---|---|---|---|---|---|---|
| Islamic DPK | bi_rule_resid | lp | 0.08 (0.31) | 0.08 (0.65) | 0.67 (0.71) | 2.59 (1.45)* | 5.33 (2.78)* | 159/94/47 |
| | | dl | 0.04 (0.34) | -0.03 (0.63) | 0.21 (0.89) | -0.28 (1.50) | -0.82 (2.52) | 180 |
| Isl − conv DPK, total | bi_rule_resid | lp | 0.04 (0.23) | -0.14 (0.57) | 0.70 (0.86) | 3.36 (1.26)* | 3.95 (2.03)* | 155/91/47 |
| | | dl | -0.11 (0.30) | -0.49 (0.66) | -0.56 (0.95) | -0.81 (1.49) | -1.27 (2.38) | 179 |
| Isl − conv DPK, time deposits | bi_rule_resid | lp | -0.10 (0.34) | -1.01 (0.79) | -0.01 (1.29) | 3.80 (2.18)* | 6.67 (4.26) | 155/90/46 |
| | | dl | -0.44 (0.28) | -0.63 (0.88) | -0.96 (1.39) | -1.53 (2.15) | -3.32 (3.25) | 179 |
| Islamic DPK | jk_mp_median | lp | 2.22 (1.29)* | 1.22 (4.59) | 4.65 (5.05) | 10.99 (6.43)* | 7.95 (17.18) | 159/94/47 |
| | | dl | 2.24 (1.40) | 1.43 (3.05) | 2.00 (2.75) | -2.14 (4.91) | -9.11 (6.31) | 180 |
| conventional DPK | jk_mp_median | lp | -0.40 (0.91) | -0.19 (2.41) | 0.73 (3.20) | 9.48 (4.03)* | 4.78 (7.56) | 155/91/47 |
| | | dl | -0.39 (0.90) | -1.24 (1.06) | 0.81 (1.40) | 1.97 (2.61) | -2.52 (2.19) | 179 |
| Isl − conv DPK, total | jk_mp_median | lp | 3.51 (1.25)* | 5.62 (2.89)* | 8.83 (3.24)* | 7.95 (5.64) | 4.57 (12.50) | 155/91/47 |
| | | dl | 2.79 (1.56)* | 3.42 (2.90) | 1.57 (2.56) | -3.71 (3.34) | -5.93 (5.04) | 179 |
| Isl − conv DPK, total, event rule off | jk_mp_median | lp | 2.86 (1.31)* | 4.73 (2.90) | 7.94 (3.37)* | 5.59 (6.01) | 13.84 (9.73) | 159/99/55 |
| | | dl | 2.72 (1.58)* | 3.30 (2.93) | 1.59 (2.55) | -3.59 (3.31) | -6.03 (4.99) | 180 |
| Isl − conv DPK, time deposits | jk_mp_median | lp | 2.98 (1.60)* | 7.48 (4.70) | 8.55 (5.89) | 3.78 (8.65) | 10.13 (18.88) | 155/90/46 |
| | | dl | 4.00 (1.54)* | 7.34 (3.95)* | 2.16 (2.99) | -4.47 (4.14) | -7.41 (6.60) | 179 |
| BUS − UUS DPK | jk_mp_median | lp | -0.21 (1.25) | 3.25 (4.01) | 3.10 (5.02) | 0.44 (8.70) | | 101/52/- |
| | | dl | 1.60 (2.24) | 3.31 (2.87) | 4.94 (2.62)* | -1.23 (4.48) | 12.06 (5.96)* | 116 |
| FDR (BUS_UUS) | jk_mp_median | lp | -1.01 (1.24) | -0.23 (2.86) | -2.43 (2.71) | 5.89 (4.35) | 7.02 (6.36) | 159/93/46 |
| | | dl | -1.15 (1.26) | -0.71 (2.08) | -0.76 (1.79) | 5.67 (2.33)* | 5.35 (2.47)* | 180 |
| murabahah share | jk_mp_median | dl | -0.25 (0.29) | 0.34 (0.40) | 0.62 (0.52) | 1.22 (1.11) | 0.65 (1.15) | 180 |
| profit-sharing share | bi_rule_resid | lp | 0.09 (0.05)* | -0.05 (0.17) | -0.37 (0.19)* | -0.64 (0.34)* | -2.01 (0.58)* | 160/99/55 |
| | | dl | 0.08 (0.05) | 0.04 (0.21) | -0.03 (0.30) | 0.17 (0.51) | 0.35 (0.66) | 180 |
| NPF (BUS_UUS) | bi_rule_resid | lp | 0.01 (0.04) | -0.04 (0.08) | 0.01 (0.06) | 0.01 (0.08) | -0.29 (0.13)* | 163/102/55 |
| | | dl | 0.01 (0.04) | 0.00 (0.08) | 0.02 (0.09) | 0.27 (0.13)* | 0.44 (0.19)* | 181 |
| NPF (BUS_UUS) | jk_mp_median | dl | -0.25 (0.15) | -0.20 (0.20) | -0.33 (0.16)* | -0.29 (0.36) | 0.14 (0.29) | 181 |

The 2021-12 flag on Islamic total DPK (1.6) costs the LP 8 months at h = 12 and 24; the event-rule-off rows give the
first version's series.

**Robustness of the Islamic − conventional DPK differential at h = 12** (lp / lp_ctrl / lp_seas / dl / dl_seas):
- `bi_rule_resid`: 3.36 (1.26) / 3.78 (1.51) / 3.78 (1.23) / -0.81 (1.49) / -0.72 (1.65).
- `jk_mp_pm`: 12.56 (4.22) / 9.86 (4.66) / 11.10 (6.98) / -3.02 (3.49) / -3.78 (3.59).
- `usmpd_stmt`: 14.45 (3.47) / 11.82 (3.83) / 12.73 (5.64) / -0.82 (7.10) / -1.61 (7.39).
- Including the SEKI memo items in conventional deposits changes little: `jk_mp_median` LP h = 12 6.89 (5.79),
  DL -4.16 (3.34).
- At h = 0 the US-shock effect survives the month dummies for the statement surprise (`usmpd_stmt` lp_seas 5.88
  (1.19)) and is smaller for `jk_mp_median` (lp_seas 2.73 (1.13)).
- The LP's positive h = 12 estimates for `MP_pm` and the statement surprise survive dropping 2009 (15.38 (3.76),
  15.99 (3.40)) and the 2014-07+ sample (4.04 (2.41), 5.99 (1.78)), but not the plan's two section-6 checks: dropping
  2014, 2016-17 and 2021 gives 6.00 (12.84) and 1.04 (17.09); dropping the pandemic gives 7.24 (8.57) and 9.15
  (13.20). In 2009-2014 alone they flip sign: -13.98 (5.51) and -13.66 (3.32). Under the permutation test the LP h = 12 p-values are 0.0365 (`MP_pm`) and 0.0745 (statement); the DL
  ones 0.4855 and 0.9270 (`mech_permutation.csv`).

**MDE (2.80 × s.e., per 25 bp) for the DPK differential at h = 12:**

| shock | LP | DL |
|---|---|---|
| bi_rule_resid | 3.54 | 4.18 |
| jk_mp_median | 15.79 | 9.34 |
| jk_mp_pm | 11.81 | 9.78 |
| usmpd_stmt | 9.72 | 19.89 |

Per s.d. of `jk_mp_median`, the DL MDE is 1.31%.

**Pre-trend and lead placebo** (`mech_pretrend.csv`). 27 of 210 tests reject at 10% (13 at 5%); about 21 and 10
are expected by chance. The rejections cluster where it matters:
- **1m spread, domestic shock:** LP pre-trend -0.18 (0.09).
- **1m spread and BI rate, CBI:** DL leads -1.00 (0.60) and 0.83 (0.43) (section 3.5).
- **FDR, US shocks:** `MP_median` LP 3.03 (1.38); `MP_pm` LP 4.12 (1.20) and DL 3.09 (1.41); `usmpd_stmt` LP 4.56
  (2.47) and DL 5.20 (2.86).
- **Contract shares:** murabahah share DL leads under `usmpd_stmt` 1.77 (0.79) and `jk_cbi_median` 2.82 (1.15);
  profit-sharing share under `usmpd_stmt` (LP -1.07 (0.54), DL -1.63 (0.93)).
- **NPF, LP pre-trends:** `MP_median` -0.35 (0.16), `MP_pm` -0.24 (0.13), `usmpd_stmt` -0.52 (0.25).
- **DPK:** CBI on the total differential (LP -7.99 (3.68), DL -9.32 (5.49)) and on time deposits (DL -16.94 (6.13)).
- **BUS − UUS gap, domestic shock:** DL -0.38 (0.19).
- **The headline US spread passes** for the three pure series: `MP_median` LP 0.53 (0.51), DL 0.40 (0.32); `MP_pm`
  0.15 (0.34), 0.03 (0.33); `usmpd_stmt` 0.52 (0.41), -0.09 (0.55).

## 7. Interpretation against the hypothesis

| link in the hypothesised chain | verdict | evidence |
|---|---|---|
| (1) Islamic deposit returns adjust more slowly than conventional deposit rates, so the spread falls after tightening | **US shocks: right sign throughout, significant only in the DL, and the primary shock's significance depends on 2009. Domestic: transitory, with a pre-trend.** | DL h12 spread -1.41 (0.60) (`MP_median`), -1.47 (0.48), -2.20 (0.67); LP -1.15 (1.11), -1.59 (1.08), -1.74 (1.08). Without 2009: -0.58 (0.48), -0.78 (0.38), -1.42 (0.54), about -0.08 to -0.13 pp per s.d. 2014-07+: about -0.1 pp per s.d. for all three. On the same 2014+ months, Islamic pass-through 0.50 (0.16) vs conventional 0.84 (0.14). BUS − conventional (2014+): LP -0.68 (0.41), -0.65 (0.35), -0.79 (0.33), DL -1.11 (0.65), -0.83 (0.50), -1.72 (0.46), no lead, not robust to dropping the pandemic or break years except for the statement surprise. Domestic: the spread dips -0.30 (0.12) at 3 months and closes; LP pre-trend -0.18 (0.09). The CBI information shock is not corroboration (3.5). |
| (2) Rate-sensitive depositors move to conventional banks, so Islamic DPK growth falls relative to conventional | **not supported; uninformative** | On impact the differential moves the wrong way (+2.79 (1.56) DL, +3.51 (1.25) LP per 25 bp after `MP_median`). From h = 6 the LP is positive and the DL negative, both mostly insignificant; the LP results fail the plan's section-6 checks and flip sign in 2009-2014. MDE at 12 months 9.3% per 25 bp (DL), 1.3% per s.d. |
| (3) This squeezes Islamic funding and credit | **not tested in a usable way** | The FDR rises after US shocks in the DL (+5.67 (2.33) at 12 months), but its lead tests fail, so it is not interpretable. |
| (4) Fixed murabahah margins adjust slowly, making Islamic financing relatively cheap | **slow repricing yes, Islamic-specific cheapening no** | Full sample: murabahah − WC spread -1.41 (0.43). Without 2009 -0.75 (0.43), 2009-2014 only -2.15 (0.75). From 2014-07 the murabahah rate is flat (0.02 (0.40)) and the spread against WC is -0.53 (0.39), -0.52 (0.30), -0.78 (0.37) for the three US series (event rule off, `MP_median`: -0.27 (0.31)) because WC rates rise; against conventional consumption loans, which are also flat, it is 0.18 (0.49), 0.14 (0.42), 0.11 (0.52). Post-2014 BUS and UUS murabahah rates are flat (-0.28 (0.21), -0.07 (0.19) at 12 months). The use-matched Islamic WC rate rises 1.58 (0.78), more than the conventional WC rate on the same months (pass-through 0.60 (0.34) vs 0.21 (0.04)). The full-sample fall in the murabahah rate itself comes from the old-format (Tabel 36) period. |
| (5) UUS can draw on parent funding, BUS cannot | **suggestive at 3-6 months in the DL only; not robust** | BUS − UUS gap: DL -0.83 (0.39) at 3 months and -1.15 (0.43) at 6, -0.49 (0.76) at 12 (permutation p = 0.319); LP -0.14 (0.36). UUS level: DL 1.89 (0.51), LP -0.55 (0.59) at 12 months. Pass-through difference -0.17 (0.26) at 12 months. Samples of 113-116 months (DL), 42 (LP). BUS DPK does not fall relative to UUS. |
| 5.4 contract mix | **nothing robust** | Murabahah share: no significant DL response; its leads fail for two US series. The profit-sharing share falls after the domestic shock in the LP (-2.01 (0.58) at 24 months) but not in the DL (0.35 (0.66)). |
| 5.5 NPF | **nothing robust** | Domestic: DL +0.27 (0.13) at 12 months but LP -0.29 (0.13) at 24 (opposite signs). US: insignificant, with LP pre-trends. |

**Reading.** There is some evidence that Islamic 1-month returns move less than conventional deposit rates after US
shocks. The sign is stable, but the size is about half the headline outside 2009, and for BUS_UUS only the DL is
significant. The cleanest version is the stand-alone banks' spread after 2014, significant in both estimators but on
49-115 months and not robust to the plan's section-6 checks.
The module does **not** establish why, or what it does to banks:
- **Sticky pricing with a cost advantage** (the first version's reading): Islamic banks pay depositors less than
  conventional banks after a tightening. That would be a cost advantage only if their asset yields held up, and
  bank margins are not measured here. "Rate-insensitive depositors" is not shown either: the DPK step is
  uninformative (MDE 1.3% per s.d.), so the data cannot distinguish rate-insensitive depositors from moderate outflows.
- **Profit-sharing pass-through of asset income** fits the same numbers at least as well. Mudharabah returns are set
  from realised income. In the full sample the murabahah equivalent rate falls after US tightening (DL -0.89 (0.35)
  at 12 months) and the LP Islamic 1-month return falls too (-1.08 (0.73)). Lower realised yields would then pass
  into lower returns. But this rests on the same pre-2014 period: after 2014 BUS and UUS murabahah rates are flat, and
  the Islamic return rises in the DL (1.45 (0.52), Rupiah 2014+) though not in the LP (-0.54 (0.37) from 2014-07).
- **Common global-cycle co-movement** in the aggregate DL is a third possibility, given the CBI diagnostics (3.5) and
  the weight of the 2007-08 shocks.

None of these is tested here. In particular, nothing links the spread result to the core module's null credit
differential after US shocks, and that null is itself imprecise (s.e. about 2% per 25 bp at 12 months).

The domestic-shock credit result (Islamic credit falls relative to conventional, with a pre-trend) gets **no** funding
or price explanation here. After domestic shocks deposit spreads close within about a year, DPK differentials depend
on the estimator, and there is no FDR response.

## 8. Caveats

1. **Few independent episodes.** These are aggregate monthly series: 110-197 months in the DL (175-197 for the series that start in 2009) and
   as few as 42-102 in the LP at long horizons. In 2009-2025 the tightening phases are few (2013, 2018, 2022-23, the last partly
   inside the 2023 data gap). The DL also leans on the 2007-08 Fed surprises (2.2). Everything here is descriptive
   time-series evidence (plan 5.4), not Khwaja-Mian-style identification.
2. **Multiple testing.** About 110 outcome series × 5 shocks × 5 estimators × 25 horizons, plus 24 sample variants for
   24 outcomes. Isolated stars mean little. The US deposit-spread result has the same sign across the US shocks,
   estimators and samples and passes the lead test for the three pure series. But it is significant only in the
   DL, and for the primary shock not without 2009. The BUS-minus-conventional spread (2014+) is the only
   deposit-pricing result significant in both LP and DL at 12 months for the three pure US shocks, with no lead; it
   fails the plan's section-6 checks for two of the three. Nothing else comes close.
3. **LP vs DL.** Break-dropping leaves the LP on short, period-specific samples for every Islamic series. The DL uses
   all clean months and the 2007-08 shock lags, and assumes exogenous, serially uncorrelated shocks with no own-lag
   dynamics. Where the two disagree (DPK, NPF, contract mix, UUS level), the result is not robust.
4. **Shock scale.** A 25 bp US surprise is 7-13 s.d.; read the per-s.d. numbers for magnitudes.
5. **Identification of the US shocks in an aggregate DL.** CBI moves Indonesian rates more than the pure policy shock
   and fails lead tests (3.5). Some of the US-shock DL responses may reflect global co-movement rather than the
   causal effect of Fed news.
6. **Domestic shock.** A policy-rule residual (selection on observables). Its 1m-spread pre-trend and the core
   module's credit pre-trend both suggest it is partly anticipated or endogenous.
7. **Timing.** 7 of 136 non-zero `MP_median` events fall on the last day of a month and reach Jakarta the next
   month (2.6); this mainly attenuates h = 0.
8. **Concepts.**
   - OJK returns and margins are "equivalent rates", probably weighted over outstanding stocks. SEKI rates may weight
     differently (new versus outstanding business is undocumented). Part of the Islamic sluggishness could be a
     stock-versus-flow artefact, particularly for murabahah, where margins are fixed for the life of the contract.
   - SEKI I.26/I.28 may contain BUS, which biases spread responses slightly towards zero.
   - Conventional DPK uses SEKI private deposits minus OJK DPK, a small concept mismatch; the memo-item variant
     changes little. The SEKI inclusion of UUS deposits is assumed, not tested.
9. **Seasonality.** Volumes are not seasonally adjusted. The month-dummy variants are an addition to the plan;
   moving holidays such as Lebaran are not modelled.
10. **Splices and events.** The 2014-06 splice (+1.19 pp for the 1-month return) and the old-format mudharabah gap
    (-8.39 pp) are handled by dropping the change. The pre-2014 Islamic deposit series is of unstated currency; the
    Rupiah-only 2014+ variant gives the same sign at about half the size. The event-month rule (1.6) is an addition
    after the verification; the affected results are reported both ways.
11. **Not done.** No BUS/UUS split before 2014-06; no ijarah (method change); no sector-level margins (cleaned but
    not estimated); no asymmetry test (tightening vs easing); no measure of bank margins or funding costs; no
    pass-through ratio inference beyond the delta method (weak denominators are flagged, not fixed).

## 9. Files

**Code**
- `code/R/13_mechanisms.R`
- `code/py/build_bi_deposits.py`

**Data**
- `data/raw/bi_seki_deposits/BI_SEKI_TABEL1_17.xls` (new raw folder)
- `data/clean/bi_deposits_by_group.csv` (new)
- `data/clean/mech_monthly_series.csv` (new; every derived monthly series with its `change_clean` flag)

**Results tables, long format** (columns: outcome, shock, estimator, h, b, se, b25, se25, bsd, sesd, n, t_first,
t_last, shock_sd, block, unit, bank_type)
- `output/tables/mech_deposit_rates.csv`
- `output/tables/mech_financing_rates.csv`
- `output/tables/mech_funding.csv`
- `output/tables/mech_contract_mix.csv`
- `output/tables/mech_npf.csv`

**Summaries and tests**
- `output/tables/mech_key_results.csv`
- `output/tables/mech_passthrough.csv`
- `output/tables/mech_pretrend.csv`
- `output/tables/mech_robustness.csv` and `mech_robustness_h12.csv` (new)
- `output/tables/mech_permutation.csv` (new)
- `output/tables/mech_results_tables.md`

**Data checks**
- `output/tables/mech_dpk_inclusion_tests.csv`
- `output/tables/mech_bi_deposits_validation.csv`
- `output/tables/mech_descriptives.csv`
- `output/tables/mech_shock_sd.csv`
- `output/tables/mech_series_coverage.csv`
- `output/tables/mech_splice_jumps.csv`
- `output/tables/mech_event_flags.csv` and `mech_event_levels.csv` (new)
- `output/tables/mech_presample_shocks.csv` and `mech_presample_shocks_summary.csv` (new)
- `output/tables/mech_timing.csv` (new)

**Cleaning records**
- `output/tables/mech_cleaning_log.csv`
- `output/tables/mech_cleaning_cells.csv`
- `output/tables/mech_cleaning_used_series.csv`
- `output/tables/mech_spike_cells.csv`

**Figures** (7 × 4.5 in, 200 dpi; LP and DL with 90% bands; rows `bi_rule_resid` and `jk_mp_median`)
- `output/figures/mech_fig1_deposit_passthrough.png`
- `output/figures/mech_fig2_bus_uus_returns.png` (now shows the direct BUS − UUS gap instead of the UUS spread)
- `output/figures/mech_fig3_financing_rates.png`
- `output/figures/mech_fig4_funding.png`
- `output/figures/mech_fig5_mix_fdr_npf.png`

## 10. Response to the verification (2026-10-30)

The verifier reproduced every output byte for byte and found no coding error. All issues concerned what the notes
claimed. Each is listed with what changed.

| # | issue | response |
|---|---|---|
| 1 | Headline depends on 2009; not disclosed | **Fixed.** Sample-robustness block (drop 2009, from 2011, LOYO, 2014+, plan checks) for 24 outcomes; results in 0, 3.3 and 7. The pre-2009 shock lags are documented (2.2, `mech_presample_shocks*.csv`) and in the figure captions. "In tightening phases" removed. MP_median stays the primary shock because the plan pre-registers it; `MP_pm` and the statement surprise are reported next to it, not instead of it. No asymmetry test was added (it would be a new, unregistered specification); the text now says the linear model is symmetric. |
| 2 | Murabahah "relatively cheap" driven by 2009 and pre-2014 data | **Fixed.** The drop-2009, 2014+ and 2009-2014 spreads are reported (section 5). With the event flags, the 2014+ spread against working capital is still significant at 10% for `MP_pm` and the statement surprise, so the verdict is "slow repricing, not Islamic-specific cheapening": after 2014 the murabahah rate is flat and so is the conventional consumption rate. |
| 3 | BUS vs UUS overstated | **Fixed.** `gap_bus_uus_1m` and the LP rows for the BUS and UUS levels are reported (3.1), with its pass-through difference (4) and permutation (3.4). The BUS-minus-conventional spread, which does hold in both estimators, now has its own robustness table (3.3). Claim downgraded to "suggestive at 3-6 months in the DL only; not robust". Figure 2 now shows the gap. |
| 4 | Cost-advantage reading not tested | **Fixed.** The narrative is removed from the findings. Section 7 lists it with profit-sharing pass-through and global co-movement as untested readings, and no longer claims to explain the core module's credit null. |
| 5 | CBI offered as corroboration despite poor diagnostics | **Fixed.** Section 3.5 reports the lead failures, the LP sign flip and the size of the BI-rate response, and treats CBI as a caution (caveat 5). |
| 6 | "Consistent across shocks and estimators" overstated | **Fixed.** Now "same sign in the LP, significant only in the DL" (0, 7, caveat 2). |
| 7 | Plan section-6 checks not run | **Fixed.** Drop 2014/2016-17/2021, drop 2020-03..2021-12 and the block permutation (2,000 draws, as in the plan) are in the script (3.3, 3.4, 5, 6). |
| 8 | Use-matched pass-through compared across samples | **Fixed.** Same-month conventional comparators added for the use-matched rates and the 2014+ deposit returns (section 4). |
| 9 | Month-end FOMC timing undisclosed | **Fixed.** Counted in `mech_timing.csv`; caveat 7. |
| 10 | Conversion follow-up and scan months not treated | **Fixed by a general rule** (1.6), the house rule R3, rather than a one-off break. It does not flag UUS total DPK in 2022-09; the levels show no UUS-to-BUS transfer that month, so it is kept (1.6). The S1-S3 jumps are documented in `mech_event_levels.csv` and `mech_event_flags.csv`. |
| 11 | Empty spike row; rule D wider than the audit | **Fixed.** The empty row is gone; rule D now sets only the 42 audited cells to NA. |
