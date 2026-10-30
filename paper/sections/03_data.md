## 3. Data

Every input is publicly available online without registration. Appendix A gives each file's provenance, including the Internet Archive copies used for OJK statistics that are no longer on OJK's website. All construction code reruns end to end from the raw files.

### 3.1 Credit by sector and bank type

**Islamic financing by sector.** OJK's *Statistik Perbankan Syariah* (SPS) reports Islamic financing and non-performing financing (NPF) by economic sector every month. BUS and UUS are combined from January 2009 to May 2014 and reported separately from June 2014. The series is assembled from five archived editions (December 2014, June 2015, December 2018, December 2024 and June 2025). Where they overlap (12,582 sector x bank-type x month cells), the editions report identical financing in every cell; the only difference is one NPF total cell (January 2018), an error in the later editions that is corrected. The old and new sector classifications agree exactly on 12 overlap months once aggregated. No edition with January-November 2023 data is archived, so those 11 months are missing for all Islamic series.

**Total credit by sector.** Table I.4 of Bank Indonesia's Indonesian Economic and Financial Statistics (SEKI) reports credit, in rupiah and foreign currency, by economic sector and bank group, covering all banks including rural banks (BPR). Commercial-bank credit is the SEKI total minus the BPR group.

**Conventional credit** is commercial-bank credit minus Islamic financing. This requires SEKI to include Islamic financing, which its documentation does not state, so the paper tests it (Appendix A.2):
- **Stand-alone Islamic banks (BUS): the evidence is decisive.**
  - Commercial-bank credit shows no jump at the footnoted May 2014 coverage change. If BUS had entered then, underlying credit growth that month would have been -3.1 percent, below every other month of 2009-2025.
  - When OJK reclassified Islamic shop-house financing in July 2014, SEKI's shop-house line moved by almost exactly the same amount (-11.0 tn against -11.2 tn).
  - When two whole regional banks converted to Islamic banks (Bank Aceh, Bank Riau Kepri), SEKI's regional-bank group did not lose them.
- **Islamic windows (UUS): the evidence is strong but indirect.** OJK's all-bank statistics, which explicitly include Islamic windows, match SEKI's household credit within 0.15 percent, while UUS household financing alone is about 120 tn.

**Two sector panels.** Sectors are harmonised into two panels with an explicit crosswalk:
- **H9** covers 2009-01 to 2025-06 and has eight consistent sectors: agriculture, mining, manufacturing, utilities, construction, trade, transport, and services-plus-households. Households cannot be separated from business services consistently before 2014 because OJK's old "business services" line contains household property financing. The plan named this panel H9 before the households-services merge reduced it to eight sectors, and the paper keeps that name.
- **H15** covers 2016-06 to 2025-06 and has 15 sectors, including four household sectors (housing, shop-house, vehicles, other).

Table 1 describes both panels.

**Contamination flags.** Each sector x bank-type monthly change gets a flag, `adj_growth_ok`. It is false when the change is contaminated by any of the following:
- a reporting or classification break, either footnoted by the publisher (BI: 2014-05, 2024-03, 2025-01; OJK: 2014-05) or identified in the data (BI: 2010-01/02; OJK: 2014-07, 2015-03), or the 2017-07 splice of the old and new SEKI sector classifications in H9;
- a bank conversion (all sectors, all Islamic and conventional series);
- a merger;
- a one-month spike that fully reverses, identified with a noise-scaled rule;
- a missing neighbouring month.

About 6 percent of monthly changes are flagged. Several of the flagged events hit every unit at once: the three conversions, three classification changes and the 2023 gap. This matters for estimation (Section 4.3).

Two independent audits re-derived every one of the 16,095 panel cells from the raw workbooks with their own parsers. All differences were documented corrections of OJK source errors. One example: January 2018, where the published UUS block is exactly twice the correct value.

### 3.2 Monetary policy shocks

**US shocks.** The primary international shock is the **pure monetary policy** component of the Jarociński-Karadi (2020) decomposition of FOMC surprises (median rotation, updated to 2026). It removes the central-bank-information component that moves interest rates and stock prices in the same direction. Robustness uses four alternatives:
- the "poor man's" sign-restriction version (MP_pm);
- the statement and monetary-event surprises from the San Francisco Fed's US Monetary Policy Event-Study Database (USMPD; Acosta et al., 2025);
- the orthogonalised surprise of Bauer and Swanson (2023), available to 2023.

The information component (CBI) is reported as a contrast. Event-level surprises are summed within the calendar month. Over 2009-2025 the monthly JK pure-policy shock has a standard deviation of 3.5 bp, so the pre-registered reporting unit of 25 bp is about seven standard deviations (Table 2). Every estimate is linear in the shock, so this choice only rescales point estimates and standard errors; per-standard-deviation magnitudes are reported alongside.

**Domestic shock.** The domestic shock is the residual of a monthly BI policy rule. The change in the policy rate is regressed on:
- three of its own lags;
- lagged CPI inflation and manufacturing-production growth;
- two lags of the change in the IDR/USD rate;
- the lagged change in the VIX, the US 2-year yield and Brent;
- the contemporaneous US shock.

The policy rate is adjusted for the August 2016 switch from the BI Rate to the BI-7DRR, which lowered the headline rate by 125 bp without any easing. Over 2006-2026 the rule has R² = 0.48. The residual has a standard deviation of 13 bp, and 72 percent of its variance falls in months in which BI actually changed its rate. Identification here rests on selection on observables. The plan graded this shock as less credible than the US shock before any outcome was estimated.

### 3.3 Mechanism data

- **Islamic rates.** OJK reports Islamic deposit returns by contract and tenor and equivalent financing rates by contract, use and sector. Use and sector rates start in 2014-06.
- **Conventional rates.** SEKI reports commercial banks' rupiah time-deposit rates by tenor (I.28) and lending rates by use (I.26). The tables do not say whether Islamic banks' equivalent rates are included. They are treated as conventional rates; any inclusion of Islamic rates would bias the Islamic-minus-conventional spreads slightly towards zero.
- **Funding volumes.** OJK reports Islamic third-party funds (DPK) by instrument. Conventional deposits are SEKI table I.17's private deposits at commercial banks minus Islamic DPK. As on the credit side, this requires SEKI to include Islamic deposits. A level comparison with OJK's all-bank statistics shows it includes BUS deposits: the two totals differ by 0.3 to 0.4 percent, against a BUS deposit base of 5.5 to 5.8 percent of the total. UUS inclusion is assumed.
- **Government bond holdings.** The Ministry of Finance's Directorate General of Budget Financing and Risk Management (DJPPR) published daily holdings of tradable government bonds by holder and instrument, separately for conventional bonds (SUN) and sovereign sukuk (SBSN). The archived files cover 2015-12 to 2022-06.
