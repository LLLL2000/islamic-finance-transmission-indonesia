## Appendix A. Data sources and construction

### A.1 Sources

Every source is a public file obtained with a plain download. None required registration or a login. Files that are no longer served by their publisher were taken from the Internet Archive (web.archive.org). In each such case the archived file's SHA-1 digest matches the archive's record of the original, so the files are byte-identical to what the publisher served.

| Data | Publisher | File(s) | Access |
|---|---|---|---|
| Credit by economic sector and bank group (SEKI I.4) | Bank Indonesia | TABEL1_4.xls | bi.go.id/SEKI/tabel, direct |
| Lending rates by bank group and use (I.26) | Bank Indonesia | TABEL1_26.xls | direct |
| Time-deposit rates by bank group and tenor (I.28) | Bank Indonesia | TABEL1_28.xls | direct |
| Private deposits by bank group and type (I.17) | Bank Indonesia | TABEL1_17.xls | direct |
| Money-market rates incl. BI rate, JIBOR, INDONIA (I.25) | Bank Indonesia | TABEL1_25_1.xls | direct |
| Islamic banking statistics (SPS): financing and NPF by sector, contract, use; deposits; returns; margins; aggregates | OJK | SPS editions Dec-2014, Jun-2015, Dec-2018, Dec-2024, Jun-2025 | Internet Archive copies of ojk.go.id open downloads |
| Commercial-bank statistics (SPI), validation only | OJK | SPI Feb-2025 | Internet Archive copy |
| Holdings of tradable government bonds by holder, SUN and SBSN, daily | Ministry of Finance (DJPPR) | yearly workbooks 2015-2022 | Internet Archive copies of djppr.kemenkeu.go.id open downloads |
| Jarociński-Karadi shocks (update to Sep-2026) | Jarociński and Karadi | shocks_fed_jk_t.csv | github.com/marekjarocinski/jkshocks_update_fed |
| US Monetary Policy Event-Study Database | Federal Reserve Bank of San Francisco | monetary-policy-surprises.zip | frbsf.org |
| Bauer-Swanson surprises (to Dec-2023) | Federal Reserve Bank of San Francisco | monetary-policy-surprises-data.xlsx | frbsf.org |
| BI policy rate, daily | Bank for International Settlements | CBPOL | BIS data portal |
| VIX, US 2-year yield, Brent, US macro | FRED, IMF, OECD | various | public APIs |

### A.2 Does Bank Indonesia's credit total include Islamic financing?

Conventional credit is constructed as SEKI commercial-bank credit minus OJK Islamic financing. This is valid only if SEKI includes Islamic financing. The note `notes/data_panel.md` gives nine tests. The main ones are summarised in Section 3.1. If SEKI nevertheless excluded the Islamic windows (UUS), conventional credit would be understated by UUS/CONV:
- 0.7 to 3.0 percent in business sectors;
- up to 15 percent in household housing and shop-house finance in 2025.

The differential design absorbs any constant level error in the sector x bank-type fixed effects. It is not robust to a time-varying one.

### A.3 Contamination flags and corrections

Two independent audits re-derived every panel cell from the raw workbooks. All differences between the panel and the as-published cells are documented corrections of source errors:
- **December 2012:** the December column repeats November, so the year-end column is used instead.
- **January 2018:** UUS is published at exactly twice its correct value.
- **August 2020:** provisional cells are published as text.

The OJK files used in Section 7 carry 61 further corrections: 36 volume cells re-derived from accounting identities (BUS + UUS = total, or components = total) and 25 implausible rate cells set to missing. The OJK rate files have two further problems, and both are set to missing, never interpolated:
- **Copied blocks.** An audit found eight blocks in which one bank type's rates repeat another's (for example, UUS deposit returns in November 2015 equal BUS returns cell for cell). Each claim was verified against the data before acting, and 389 cells were set to missing. Only 20 of them fall in the series the paper estimates.
- **Spikes.** A one-month spike rule (a jump of more than 5 pp that reverses the next month) removes 82 further cells: 81 in the OJK rate files and one 1999 cell in Bank Indonesia's lending rates. None falls in a series used.

Months contaminated by conversions, mergers, classification breaks or reporting spikes are flagged rather than adjusted, and every estimator excludes them. For the Section 7 series, a noise-based rule also flags the months just after each conversion and the months with unexplained jumps found by a scan (36 of 405 series-months checked).

### A.4 Known gaps

- Islamic statistics for January-November 2023 are not available from archived open sources.
- A BUS/UUS split by sector does not exist before June 2014.
- Daily government-bond holdings end in June 2022.
- The Bauer-Swanson series ends in December 2023.

## Appendix B. Deviations from the pre-analysis plan and corrections

The plan (notes/pre_analysis_plan.md) was written before any outcome regression was run. The paper deviates from it as follows. Every pre-specified estimate is still reported.

1. **H9 has eight sectors, not nine.** Households can be separated from business services consistently only from 2014, so they are merged with services in the 2009-2025 panel. This was decided while building the data, before any outcome regression. H15 covers 2016-06 to 2025-06, as planned.
2. **Distributed-lag estimator (added after the first LP results).** The plan's rule of dropping windows that touch a contaminated month leaves about 92 usable months at 12 months, and fewer at longer horizons, because seven contamination events hit every unit. The DL estimator uses every clean month. A Monte Carlo on the actual design shows the DL is unbiased, about three times more precise for the US shock, and, for the domestic shock, free of the LP's attenuation (Section 6.3).
3. **No Islamic x macro controls in the DL (correction after review).** The first draft's DL included Islamic x macro controls dated one month before the outcome month. For shock lags of one month or more these controls are post-treatment. The DL baseline now omits them, as the Monte Carlo design already did; the first draft's version and a version with controls dated t-25 are reported in Table 6. The correction moved the H9 US estimate from -1.0 to -2.9 and the domestic one from -3.3 to -2.1.
4. **Joint test by permutation (added).** A Driscoll-Kraay Wald test of all DL lags was computed first. It rejected for every shock, and the Monte Carlo shows it rejects a true null in all but one of 600 draws. It is replaced by a block-permutation test.
5. **Minimum sample for the LP (added).** LP estimates resting on fewer than 36 usable months are reported as not estimable and are not plotted.
6. **Robustness checks added after seeing the data:**
    - dropping the 12 months after each conversion and the 2021 merger, motivated by the coincidence of conversions with BI tightening cycles;
    - dropping 2013-2015, the slowdown in Islamic finance;
    - a DL with three own lags;
    - leave one calendar year out and later start dates (Table 10), added after the mechanism results showed that the DL's use of 2007-08 shock lags can matter;
    - checks on the sector-exposure coefficient (a household x shock control, leave one sector out).
7. **Reporting units.** The pre-specified 25 bp unit is about seven standard deviations of the monthly JK shock, so per-standard-deviation magnitudes are added.
8. **Estimators by table.** Both estimators are reported for the headline differential and its robustness checks (Tables 4-6 and the leave-one-sector-out ranges in Table 10) and for the mechanism outcomes in Tables 13 and 14. The leave-one-year-out and later-start results (Table 10), the specification chart (Figure 6), the BUS/UUS split (Table 7), sector exposure (Table 8), pass-through ratios (Table 12) and levels by bank type (Figure 3) are shown with the DL only; the sector-exposure coefficient is therefore estimated with the DL, not the plan's LP. NPF by sector (Table 9) is shown with the LP only. Time-series LPs for macro and rate outcomes (Table 3) are added as the first stage.
9. **Minimum detectable effects.** They use 2.80 x the panel DL Driscoll-Kraay standard error rather than the residual variance of the cross-sector average differential named in the plan. Computed the plan's way, the H9 MDE at 12 months is 6.3 percent per 25 bp for the DL on the average differential and 6.9 for the plan's time-series LP, against 5.8 in Table 5.
10. **BI policy rule.** It adds the lagged changes in the US 2-year yield and Brent to the plan's regressors.
11. **Mechanisms (Section 7).** Estimated as specified, with LP and DL versions. The source copy errors in the OJK rate files that an audit identified are neutralised before estimation (Appendix A.3). Added after the first results: calendar-month dummies for the unadjusted volume series, a noise-based rule for months just after conversions, same-month comparators for pass-through ratios, and sample variants (outcomes from 2010 or 2011, from 2014-07, leave one year out). An independent verification of the first draft asked for the sample variants, and they changed the reading of the main deposit-spread result.
12. **Sovereign investor base (Section 8).** This is a supplementary module that the plan does not mention, so its results should be read as exploratory. Within it, the events-only check was chosen before any results were seen.
13. **Bauer-Swanson.** The shock is the monthly sum of event-level orthogonalised surprises, not the authors' own monthly series. It covers 2009-2023 only and is estimated for H9 only.
14. **Other corrections after review.** The first draft's LP placebo kept the own-growth lags, which made it a test of growth in month t-4 alone; it now uses four clean months and no own lags (H9: 0.7, s.e. 1.1 became 1.3, s.e. 1.8). The LP permutation test now permutes blocks of 12 calendar months rather than blocks of 12 usable rows.
