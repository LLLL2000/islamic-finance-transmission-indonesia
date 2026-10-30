# Module S (supplementary): the sovereign investor base, sukuk (SBSN) vs conventional bonds (SUN)

Script: `code/R/14_sovereign.R`. It runs from a fresh R session (`Rscript --vanilla`) in about 11 to 15 minutes; the run
used for these notes finished with exit code 0. Tables are in `output/tables/sov_*.csv` and figures in
`output/figures/sov_fig1..5_*.png`. Every number below is copied from those tables. Table names are given in brackets.

**Revision of 2026-10-30.** An independent verification reproduced every number of the first version and found no
coding error, but showed that the write-up overstated robustness. This version adds the checks it asked for
(section 1.3), corrects the permutation test, and tones down the interpretation. Point estimates and NW standard
errors of the specifications that existed before are unchanged; permutation p-values changed because of the
correction (section 1.3).

## 0. Bottom line

1. **There is suggestive but fragile evidence that non-residents sell SUN in the first week after a US pure-policy
   tightening.**
   - Primary specification, JK `MP_median`, per 1 s.d. of the event shock (3.68 bp): non-resident SUN holdings fall
     by 0.080 pp of SUN outstanding by day 2 (s.e. 0.033) and 0.142 pp by day 5 (s.e. 0.059), about Rp 3.06 tn
     (s.e. 1.22). NW p 0.015 and 0.017; permutation p 0.007 and 0.008.
   - Per 25 bp, which is 6.8 s.d. and far outside the data: −0.963 pp (0.403) by day 5, or Rp −20.8 tn (8.3).
   - **It is not significant in the events-only cross-section** (56 events, HC1): −0.061 (0.041) at day 2, p 0.132;
     −0.106 (0.084) at day 5, p 0.209; with settlement counts −0.094 (0.084), p 0.260.
   - **The full-sample pre-announcement placebo is uninformative, not clean**: 0.010 (0.064) per s.d., with an MDE of
     0.181, larger than the 0.142 effect it should rule out. Once March–April 2020 or only the 2020-03-03 event is
     dropped, the placebo moves in the same direction as the post-event responses (section 4.5).
   - **The day-5 estimate survives leave-one-event-out** (t between −2.88 and −2.04 over all 58 drops) and a fixed
     event sample (−0.144 (0.072), p 0.046).
   - **The shape after day 5 hinges on one event**, the 2020-03-03 emergency cut (−12.4 bp, 3.4 s.d.). Dropping only
     that event turns the day-20 response from −0.059 (0.213) into −0.371 (0.138), p 0.007. Dropping any other single
     event leaves it between −0.074 and +0.006. "The response fades by day 10–20" is therefore not a finding.
   - **Settlement timing.** The positions are settled holdings. If secondary trades settle T+2 (not verified), the
     day 0–1 positions predate the announcement. Measured from day +1, the day-5 response is −0.092 (0.046), p 0.042.
2. **The SBSN-minus-SUN differential in pp of outstanding is uninformative.**
   - It is +0.036 per s.d. at day 5 (s.e. 0.044, MDE 0.122) and insignificant at every horizon after day 0.
   - The day-0 value, +0.039 (0.020), NW p 0.050, is not a result. Under T+2 settlement day 0 is pre-event, and the
     T+2-aligned differential at day 5 is −0.001 (0.031).
   - Its positive sign is what a pure composition effect produces. Non-residents held 4.7% of SBSN but 38.6% of SUN
     on the eve of the events, so equal *proportional* selling would give +0.124 at day 5. The SBSN response itself,
     −0.085 pp per s.d. (90% CI −0.196 to 0.027), cannot distinguish "no selling of SBSN" (0) from "selling like SUN
     holders" (−0.018). "Sukuk lose less foreign funding relative to their size" follows from the ownership shares,
     not from these estimates.
3. **The proportional (log) comparison is also uninformative.**
   - The log differential is −1.99% per s.d. at day 5 (s.e. 1.16; NW p 0.088; permutation p 0.084); NW p is 0.043
     and 0.042 at days 6 and 7 and above 0.18 from day 8 on [sov_daily_lp_all.csv]. Its minimum detectable effect at
     day 5, 3.26%, is about 8.5 times the SUN log response itself (−0.383%).
   - The point estimate is negative at day 5 in all 13 specifications, with NW/HC1 p between 0.017 and 0.245 (below
     0.05 in 5: the two samples without 2020, the two variants dropping 2020-03-03, and the possibly-bad issuance
     control). This does not establish a direction. All specifications reuse the same 56 events, and four of the five
     significant ones are samples without the March 2020 events, in which the pre-announcement log differential has
     the *opposite* sign: +2.305 (1.003), p 0.022 excluding March–April 2020; +2.393 (0.982), p 0.015 dropping only
     2020-03-03. A rise before the event followed by a fall is what mean reversion in a tiny, noisy series looks
     like (non-resident SBSN holdings: daily log s.d. 3.1%).
   - The composition gap (observed pp differential minus the equal-proportional benchmark) is −0.087 (0.051) per s.d.
     at day 5, p 0.087. It is close to the log differential times the SBSN non-resident share and carries the same
     caveats (section 4.6).
4. **Pre-announcement drift.** Excluding March–April 2020, the shock "predicts" SUN selling (−0.072 (0.033), NW
   p 0.028) and a positive pp differential (+0.113 (0.053), p 0.033) in the five days *before* the FOMC. With the
   corrected permutation test these are weaker (permutation p 0.139 and 0.061), but the design is not clean.
5. **Verdict.** Nothing here supports the hypothesis that the Islamic (SBSN) foreign investor base is less flighty.
   The SBSN-versus-SUN comparison is uninformative in both metrics; it does not show the opposite either. The SUN
   outflow is suggestive and fragile.

## 1. Design

- **Comparison.** SUN and SBSN are tradable Rupiah government bonds from the same issuer, with the same credit
  risk, currency and trading calendar. Comparing non-resident holdings of the two on the same days holds macro
  news and the exchange rate fixed.
- **Hypothesis.** If the Islamic investor base is less flighty, non-resident SBSN holdings fall less than SUN
  holdings after a US tightening.
- **Outcome.** For holder H and instrument I, the outcome is
  (H_{I,t+h} − H_{I,t−1}) / Outstanding_{I,t−1} × 100, i.e. pp of the instrument's outstanding, which is robust to
  issuance.
  - Alternative scalings for non-residents: 100 × log change (percent of the holder's own position), and Rp tn.
  - The differential is the difference series SBSN − SUN, with its own lags.
- **All-trading-day local projection**, h = 0..20 trading days:
  `Δ^h y_t = b_h e_t + Σ_{l=1..5} g_l Δy_{t−l} + c_SUN C^SUN_{t,h} + c_SBSN C^SBSN_{t,h} + u`.
  - e_t is the event shock on day 0 and 0 on every other trading day. NA shock values (Bauer–Swanson 2020) drop the
    day; they are never set to 0.
  - C^I_{t,h} counts the settlement days of instrument I inside [t, t+h]. A settlement day is one where total
    outstanding of I moves by more than Rp 0.5 tn. The auction calendar is set in advance.
  - Newey–West errors with lag h+5; 90% bands.
- **Effective sample.** 1,576 trading days from 2015-12-31 to 2022-06-27. The regressions use 1,570 days at h=0 and
  1,550 at h=20, but identification comes from the **event days only**: 58 JK event days (56 with a non-zero JK
  value) at h=0, and 56 (54 non-zero) at h=20. The two June 2022 events (2022-06-13, +11.0 bp; 2022-06-15, +4.6 bp)
  enter only the short horizons, so the event set changes across horizons; the fixed-sample variant removes this.
- **Units.** b is per 1 pp of shock. Reported per 25 bp (b × 0.25), the pre-registered unit, and per 1 s.d. of the
  shock's event distribution over the in-sample events [sov_shock_sd.csv]:

  | shock | events | s.d. (bp) | 25 bp = ... s.d. |
  |---|---|---|---|
  | jk_mp_median | 56 | 3.68 | 6.80 |
  | jk_mp_pm | 56 | 4.31 | 5.80 |
  | usmpd_stmt | 58 | 2.50 | 9.99 |
  | jk_cbi_median | 56 | 2.15 | 11.64 |
  | bs_mps_orth | 46 | 3.47 | 7.20 |

  A 25 bp surprise is 6 to 12 s.d. of the event distribution. The largest JK MP event in the sample is 12.4 bp in
  absolute value. **Per-s.d. numbers are the realistic magnitudes; per-25 bp numbers are linear extrapolations.**

### 1.1 Timing convention (day 0)
- **Rule.** Event dates are ET. Jakarta (WIB, UTC+7) is 11 hours (EDT) or 12 hours (EST) ahead, so the Jakarta close
  of about 16:00 WIB is 04:00–05:00 ET.
  - Every in-sample JK event is at 08:00 ET or later [sov_events.csv]. Scheduled FOMC statements are at 14:00 ET.
    USMPD gives no times.
  - The 2020-03-15 event is a Sunday at 17:00 EDT, which is 04:00 WIB Monday, before the Jakarta open.
  - So the first Jakarta close that can reflect an announcement is the **next Jakarta trading date after the ET
    date**. That date is day 0, and day −1 is the last close before the announcement.
  - The trading calendar is the set of dates in the DJPPR daily file. The largest gap from ET date to day 0 is
    7 calendar days, caused by holidays.
- **Weekday.** Day 0 is a Thursday for 46 of the 56 non-zero JK MP events. Thursday is also the main settlement day:
  192 of the 350 SUN and 135 of the 257 SBSN settlement days are Thursdays [sov_desc_summary.csv]. That is why the
  settlement controls matter.
- **Alternative timing** (`allday_same_settle`): day 0 is the first trading date on or after the ET date, so day 0
  is mostly pre-event. As expected, its h=0 response is about zero (SUN +0.002, s.e. 0.010 per s.d.).

### 1.2 Settlement basis of the holdings
- **The positions are settled holdings.** The DJPPR ownership tables come from Bank Indonesia's BI-SSSS, which is
  both the SBN registry and the settlement system. The data agree: of the days on which total outstanding *rises* by
  more than Rp 0.5 tn, 132 of 188 (SUN) and 123 of 178 (SBSN) are Thursdays, and only 8 and 14 are Tuesdays
  [sov_desc_summary.csv]. SUN and SBSN auctions are normally held on Tuesdays (general market knowledge, not checked
  against an auction calendar here), so new issues enter the holdings at their T+2 settlement date, not the auction
  date.
- **Secondary-market settlement cycle: not verified.** One web search (2026-10-30) returned BI-SSSS regulations
  but no document stating the standard settlement cycle for secondary SBN trades. If it is T+2, then the day-0
  (Thursday) and day-1 positions reflect trades up to the Wednesday before the announcement, and **the h = 0 and
  h = 1 estimates are pre-event**.
  - Primary h=0 and h=1, per s.d.: SUN −0.029 (0.017) and −0.045 (0.025); pp differential +0.039 (0.020) and
    +0.037 (0.027); SBSN log +0.363 (0.192) and −0.062 (0.314). These are reported but not interpreted as responses.
  - `allday_t2aligned_settle` measures the response from the day +1 position, (y_{t+h} − y_{t+1}), for h ≥ 2, with
    settlement counts over [t+2, t+h] (section 4.3).

### 1.3 Specifications: what was fixed before results, after results, and after verification
- **Chosen before any result:**
  - `allday_settle`, the primary specification.
  - `allday_nosettle`.
  - `allday_same_settle`.
  - `allday_exCOVID_settle`: drops windows [t−1, t+h] that overlap 2020-03-01..04-30.
  - Events-only cross-sections with HC1 errors (`events_hc1`, `events_hc1_settle`). These exclude the two JK
    events whose MP and CBI the authors set to 0 because the S&P 500 surprise is missing (2020-03-15 and 03-23).
  - The permutation test (2,000 re-draws of the event dates among non-event trading days; the pool excludes day 0
    of any US event in the events file, under either timing).
  - The pre-event placebo: change over [−6, −1] on e_t, with lags dated t−6..t−10.
  - The log and Rp tn scalings, and the monthly maturity-bucket LPs.
- **Added after seeing the first results** (reported in full, never chosen by significance):
  1. `allday_exPandemic_settle`, which drops windows overlapping 2020-03..2021-12 (pre-analysis plan §6).
  2. `allday_issuance_settle`, which adds the window change in total outstanding of both instruments. For h ≥ 5 this
     is a possibly bad control: post-FOMC auction awards can respond to the shock.
  3. A weekday-stratified permutation (`p_perm_wday`).
  4. Permutation p-values for the ex-COVID and ex-pandemic specifications, and the ex-COVID placebo.
  5. The composition-only benchmark.
  6. The Bauer–Swanson `bs_mps_orth` shock (plan §3 robustness; orthogonalised to pre-FOMC news), added after the
     ex-COVID placebo failed. Its 12 events in 2020 are NA in the source and are dropped, never set to 0.
- **Added after the independent verification** (reported in full):
  1. `allday_fixedsample_settle`: only days with t ≤ T−21, so the same 56 event days enter every horizon.
  2. `allday_drop0303_settle`: drops the day-0 row of the 2020-03-03 event.
  3. `allday_dropMar20x2_settle` (2020-03-15 and 03-23) and `allday_dropMar20x3_settle` (also 2020-03-03), mainly
     for USMPD.
  4. `allday_t2aligned_settle` (section 1.2).
  5. Leave-one-event-out for the primary shock [sov_loeo_nonres.csv, sov_loeo_summary.csv].
  6. The pre-window placebo in every sample above and in the ex-pandemic sample.
  7. A joint Newey–West standard error for the composition gap, and the same gap on the placebo outcomes.
  8. **Permutation correction.** The permutation now re-draws only the event values that enter each regression,
     and only onto non-event days inside that regression's sample. Before, the ex-COVID, ex-pandemic and placebo
     tests re-drew all 56 values, including the excluded March–April 2020 ones, which made those p-values mildly
     anti-conservative. All permutation p-values were recomputed; in the primary specification they change only within
     simulation noise, while the ex-COVID placebo p-values rise (section 4.5).
  9. Monthly shocks assigned by the Jakarta day-0 month (section 5).

## 2. Data and descriptives

- **DJPPR daily holdings** of tradable Rupiah SBN, at face value. The common SUN/SBSN sample runs 2015-12-31 to
  2022-06-27. SBSN is missing on 2022-06-28, so that date is dropped. The eight holders add up to total
  outstanding, apart from the known 2018-04-05 SUN discrepancy of Rp 0.010 tn (check V4 in `notes/data_djppr.md`).

  [sov_desc_summary.csv]

  | | SUN | SBSN |
  |---|---|---|
  | outstanding, 2015-12-31 → 2022-06-27 (Rp tn) | 1,302.6 → 3,974.3 | 159.2 → 866.3 |
  | non-resident holdings, first → last (Rp tn) | 550.4 → 766.8 | 8.14 → 16.27 |
  | non-resident share of outstanding: mean (min–max) | 38.9% (19.3–47.7) | 4.67% (1.37–8.27) |
  | s.d. of daily non-resident change: pp of outstanding | 0.114 | 0.138 |
  | s.d. of daily non-resident change: log, % | 0.285 | 3.113 |
  | s.d. of daily non-resident change: Rp tn | 2.40 | 0.567 |

  Measured in pp of outstanding, SBSN non-resident holdings are as noisy as SUN's. In proportional terms they are
  about 11 times noisier, because the base is small: a mean of Rp 19.0 tn.

- **Figure 1** (`sov_fig1_nonres_share.png`). Before March 2020, the non-resident SUN share stays between 42.1% and
  47.7%; it then falls to 19.3% by June 2022. The SBSN share is 2.9–8.3% before March 2020 and 1.37–8.27% over the
  whole sample [sov_desc_nonres_share_daily.csv].

- **Holder composition** (`sov_fig2_holder_composition.png`), mean shares 2015-12-31..2022-06-27
  [sov_desc_composition.csv]:
  - **SBSN:** conventional banks 36.7%, insurance and pension 22.5%, others 9.6%, Islamic banks 9.3%,
    individuals 6.8%, mutual funds 5.4%, Bank Indonesia (net) 4.9%, non-residents 4.7%.
  - **SUN:** non-residents 38.9%, conventional banks 26.0%, insurance and pension 15.3%, Bank Indonesia 7.4%,
    others 5.4%, mutual funds 4.1%, individuals 2.8%.
  - **On 2022-06-27:** SUN non-residents 19.3% and BI 16.9%; SBSN non-residents 1.88%, BI 11.4%, Islamic banks
    9.0%.
  - SBSN is held mainly by domestic banks and insurers, and the foreign SBSN base is tiny.

- **Maturity mix** [sov_monthly_bucket_shares.csv], mean shares of non-resident holdings, 2017-01..2022-05:
  - **SBSN:** 34.7% in 0–1y, 29.0% in 1–2y, 22.7% in 2–5y, 3.9% in 5–10y, 9.7% in >10y.
  - **SUN:** 3.5%, 4.1%, 20.8%, 36.8%, 34.7%.
  - Foreign SBSN holdings are short-dated and foreign SUN holdings are long-dated. **The SBSN−SUN comparison
    therefore does not hold duration constant.**

## 3. Main results: non-residents, JK MP_median, primary specification

Primary specification: all trading days, settlement-count controls [sov_headline.csv, sov_key_nonres.csv].

- Each cell gives the estimate with its s.e. in parentheses.
- p-values are NW / permutation / weekday-stratified permutation (2,000 draws each).
- MDE is 2.80 × s.e.
- If secondary trades settle T+2 (section 1.2), the h=0 column is pre-event.

**Per 25 bp:**

| outcome | h=0 | h=2 | h=5 | h=10 | h=20 |
|---|---|---|---|---|---|
| SUN, pp of outstanding | −0.198 (0.113) | −0.546 (0.224) | −0.963 (0.403) | −0.654 (0.858) | −0.404 (1.452) |
| SUN, Rp tn | −3.35 (2.42) | −11.91 (4.67) | −20.83 (8.32) | −11.42 (17.49) | −5.28 (29.66) |
| SUN, log % | −0.424 (0.278) | −1.459 (0.545) | −2.602 (1.023) | −1.609 (2.070) | −1.003 (3.514) |
| SBSN, pp of outstanding | 0.097 (0.056) | −0.159 (0.169) | −0.577 (0.461) | −0.577 (0.729) | −0.854 (0.988) |
| SBSN, Rp tn | 0.52 (0.27) | −0.59 (0.80) | −2.03 (1.92) | −1.10 (2.90) | −1.99 (3.84) |
| SBSN, log % | 2.471 (1.308) | −4.376 (4.164) | −15.986 (9.043) | −14.398 (12.692) | −18.307 (17.067) |
| **SBSN − SUN, pp of outstanding** | 0.267 (0.136) | 0.305 (0.226) | 0.247 (0.297) | −0.127 (0.568) | −0.645 (0.969) |
| **SBSN − SUN, log %** | 2.877 (1.414) | −2.982 (3.967) | −13.516 (7.913) | −13.602 (10.823) | −18.473 (14.171) |

**Per 1 s.d. (3.68 bp):**

| outcome | h=0 | h=2 | h=5 | h=10 | h=20 |
|---|---|---|---|---|---|
| SUN, pp of outstanding | −0.029 (0.017) | −0.080 (0.033) | −0.142 (0.059) | −0.096 (0.126) | −0.059 (0.213) |
| p: NW / perm / perm-wday | 0.081 / 0.034 / 0.060 | 0.015 / 0.007 / 0.009 | 0.017 / 0.008 / 0.007 | 0.445 / 0.273 / 0.295 | 0.781 / 0.668 / 0.686 |
| SUN, Rp tn | −0.49 (0.36) | −1.75 (0.69) | −3.06 (1.22) | −1.68 (2.57) | −0.78 (4.36) |
| SUN, log % | −0.062 (0.041) | −0.215 (0.080) | −0.383 (0.151) | −0.237 (0.304) | −0.148 (0.517) |
| SBSN, pp of outstanding | 0.014 (0.008) | −0.023 (0.025) | −0.085 (0.068) | −0.085 (0.107) | −0.126 (0.145) |
| SBSN, Rp tn | 0.08 (0.04) | −0.09 (0.12) | −0.30 (0.28) | −0.16 (0.43) | −0.29 (0.56) |
| SBSN, log % | 0.363 (0.192) | −0.644 (0.612) | −2.351 (1.330) | −2.117 (1.866) | −2.692 (2.510) |
| **SBSN − SUN, pp of outstanding** | 0.039 (0.020) | 0.045 (0.033) | 0.036 (0.044) | −0.019 (0.083) | −0.095 (0.142) |
| p: NW / perm / perm-wday | 0.050 / 0.060 / 0.086 | 0.178 / 0.263 / 0.282 | 0.404 / 0.540 / 0.533 | 0.823 / 0.825 / 0.844 | 0.505 / 0.503 / 0.507 |
| MDE of the differential (per s.d.) | 0.056 | 0.093 | 0.122 | 0.234 | 0.399 |
| MDE of the differential (per 25 bp) | 0.382 | 0.634 | 0.831 | 1.589 | 2.712 |
| **SBSN − SUN, log %** | 0.423 (0.208) | −0.439 (0.583) | −1.988 (1.164) | −2.000 (1.592) | −2.717 (2.084) |
| p: NW / perm / perm-wday | 0.042 / 0.249 / 0.233 | 0.452 / 0.560 / 0.555 | 0.088 / 0.084 / 0.079 | 0.209 / 0.225 / 0.232 | 0.192 / 0.205 / 0.225 |
| MDE, log differential (per s.d.) | 0.582 | 1.634 | 3.258 | 4.456 | 5.835 |

Days in the regression: 1,570 at h=0 and 1,550 at h=20. Event days: 58 at h=0 and 56 at h=20.

**Reading the table:**

- **The SUN outflow is concentrated in days 2–6** (NW p < 0.05 at h = 2..6 [sov_daily_lp_all.csv]) and passes NW
  and both permutation tests at days 2 and 5 in the all-days design.
  It does not pass the events-only HC1 test (section 4.1), and its pre-window placebo is uninformative (section
  4.5). Treat it as suggestive.
- **After day 5 the SUN response is uninformative**, and its shape depends on the 2020-03-03 event (section 4.2).
- **The SBSN response is imprecise at every horizon.**
- **The day-0 positive SBSN reading is not a finding.** It is +0.014 pp per s.d. (Rp 0.08 tn), disappears under
  same-date timing, fails both permutation tests (p 0.368 in pp, 0.299 in log), and would be pre-event under T+2.
- **The pp differential** is insignificant at every horizon after day 0; its day-0 value (NW p 0.050, permutation
  p 0.060) falls under the same T+2 caveat.

Figure 3 (`sov_fig3_irf_nonresidents.png`) plots these responses per 25 bp, with the drop-2020-03-03 and
fixed-event-sample point estimates overlaid.

## 4. Robustness

### 4.1 Specifications, JK MP_median, per 1 s.d. [sov_key_nonres.csv]

| specification | SUN pp, h=5 | p (NW or HC1 / perm) | SUN pp, h=20 | diff pp, h=5 | diff pp, h=20 | diff log, h=5 | diff log, h=20 | event days (h=0) |
|---|---|---|---|---|---|---|---|---|
| all days, settlement counts (primary) | −0.142 (0.059) | 0.017 / 0.008 | −0.059 (0.213) | 0.036 (0.044) | −0.095 (0.142) | −1.988 (1.164) | −2.717 (2.084) | 58 |
| all days, no settlement control | −0.127 (0.059) | 0.032 / – | −0.012 (0.262) | 0.033 (0.046) | −0.092 (0.157) | −1.793 (1.146) | −1.951 (2.146) | 58 |
| all days, same-date timing | −0.122 (0.048) | 0.011 / – | 0.023 (0.229) | 0.051 (0.051) | −0.148 (0.169) | −1.109 (0.954) | −2.382 (1.869) | 58 |
| excl. Mar–Apr 2020 | −0.218 (0.061) | <0.001 / <0.001 | −0.394 (0.134) | 0.093 (0.039) | 0.107 (0.142) | −2.655 (1.195) | −4.016 (2.397) | 52 |
| excl. 2020-03..2021-12 (added after results) | −0.243 (0.068) | <0.001 / <0.001 | −0.473 (0.139) | 0.118 (0.041) | 0.175 (0.150) | −2.569 (1.204) | −4.003 (2.531) | 39 |
| + issuance amounts (added after results) | −0.119 (0.053) | 0.025 / – | −0.050 (0.183) | 0.028 (0.039) | −0.121 (0.137) | −1.886 (0.834) | −3.292 (1.762) | 58 |
| events only, HC1 | −0.106 (0.084) | 0.209 / – | 0.058 (0.338) | 0.036 (0.045) | −0.107 (0.208) | −1.649 (1.126) | −1.500 (2.225) | 56 |
| events only, HC1, settlement counts | −0.094 (0.084) | 0.260 / – | −0.044 (0.260) | 0.018 (0.048) | −0.077 (0.182) | −1.878 (1.102) | −2.628 (2.173) | 56 |
| fixed event sample, t ≤ T−21 (added after verification) | −0.144 (0.072) | 0.046 / 0.020 | −0.059 (0.213) | 0.015 (0.050) | −0.095 (0.142) | −2.243 (1.455) | −2.717 (2.084) | 56 |
| drop 2020-03-03 (added after verification) | −0.188 (0.065) | 0.004 / 0.002 | −0.371 (0.138) | 0.043 (0.057) | 0.071 (0.134) | −2.925 (1.221) | −4.060 (2.325) | 57 |
| drop 2020-03-15, 03-23 (added after verification) | −0.140 (0.059) | 0.018 / 0.010 | −0.057 (0.216) | 0.035 (0.045) | −0.096 (0.144) | −1.986 (1.164) | −2.702 (2.083) | 56 |
| drop 2020-03-03, 03-15, 03-23 (added after verification) | −0.188 (0.065) | 0.004 / 0.003 | −0.369 (0.138) | 0.043 (0.058) | 0.071 (0.134) | −2.922 (1.221) | −4.052 (2.320) | 55 |
| T+2-aligned, from day +1 (added after verification) | −0.092 (0.046) | 0.042 / 0.022 | −0.013 (0.203) | −0.001 (0.031) | −0.123 (0.135) | −1.963 (1.043) | −2.526 (2.029) | 58 |

- **Events-only.** The events-only cross-section, a robustness check chosen before the results, does not reject for
  SUN at any horizon: −0.061 (0.041), p 0.132 at h=2; −0.106 (0.084), p 0.209 at h=5. Its point estimates are about
  three quarters of the all-days ones, with larger standard errors.
- **Fixed event sample.** The two June 2022 events add precision only at short horizons. Holding the 56 event days
  fixed, SUN at h=5 is −0.144 (0.072), NW p 0.046, permutation p 0.020, against p 0.017 in the primary.
- **Signs.** Within the first week SUN falls in every specification, the pp differential is positive except T+2-aligned
  (−0.001), and the log differential is negative. These specifications share the same events, so their agreement
  is not independent evidence.
- **Ex-COVID and ex-pandemic samples.** Excluding 2020 makes the SUN outflow larger and more persistent (h=20:
  −0.394, NW p 0.003, permutation p 0.006). These are the samples in which the pre-window placebo fails (4.5), and
  most of the change comes from the single 2020-03-03 event (4.2).

Figure 5 (`sov_fig5_robustness_diff.png`) shows the pp differential for all shocks and the specifications chosen
before verification.

### 4.2 Leave-one-event-out, JK MP_median, primary specification, per 1 s.d. [sov_loeo_summary.csv]

Each row drops one of the 58 event days (day-0 row removed) and re-estimates. Event dates are ET.

| outcome | h | full sample | range over the 58 drops | drop 2020-03-03 only | range over the other 57 drops |
|---|---|---|---|---|---|
| SUN pp | 2 | −0.080 (0.033) | −0.093 to −0.063 (t −2.90 to −2.06) | −0.087 (0.042) | −0.093 to −0.063 |
| SUN pp | 5 | −0.142 (0.059) | −0.188 to −0.117 (t −2.88 to −2.04) | −0.188 (0.065), p 0.004 | −0.163 to −0.117 |
| SUN pp | 10 | −0.096 (0.126) | −0.269 to −0.052 | −0.269 (0.092), p 0.003 | −0.112 to −0.052 |
| SUN pp | 20 | −0.059 (0.213) | −0.371 to +0.006 | −0.371 (0.138), p 0.007 | −0.074 to +0.006 |
| diff pp | 0 | 0.039 (0.020) | 0.028 to 0.046 | 0.039 (0.025), p 0.122 | 0.028 to 0.046 |
| diff pp | 5 | 0.036 (0.044) | 0.016 to 0.059 | 0.043 (0.057) | 0.016 to 0.059 |
| diff log | 5 | −1.988 (1.164) | −2.925 to −1.431 (t −2.40 to −1.46) | −2.925 (1.221), p 0.017 | −2.390 to −1.431 |
| diff log | 20 | −2.717 (2.084) | −4.060 to −1.909 | −4.060 (2.325), p 0.081 | −3.500 to −1.909 |
| placebo SUN pp | [−6,−1] | 0.010 (0.064) | −0.056 to +0.029 | −0.056 (0.041), p 0.170 | −0.009 to +0.029 |
| placebo diff pp | [−6,−1] | −0.054 (0.140) | −0.080 to +0.108 | +0.108 (0.053), p 0.042 | −0.080 to −0.043 |
| placebo diff log | [−6,−1] | 0.748 (1.548) | 0.298 to 2.393 | +2.393 (0.982), p 0.015 | 0.298 to 1.001 |

- **SUN at h=2 and h=5** is significant at 5% after every single drop (58 of 58).
- **After day 5 one event decides the shape.** Without 2020-03-03 (a −12.4 bp emergency cut on a risk-off day,
  followed by heavy foreign selling of Indonesian bonds), the SUN outflow keeps building to −0.371 at h=20. With it,
  the outflow "fades". Neither shape is robust.
- **The full-sample placebo is clean only because of the same event.** Without it, the pp and log differential
  placebos are positive and significant (p 0.042 and 0.015) and the SUN placebo is −0.056 (p 0.170).
- Among the other events, dropping 2019-01-30 gives the smallest SUN outflow at h=5 (−0.117), and dropping
  2019-06-19 gives the least negative log differential at h=5 (−1.431).

### 4.3 T+2 alignment, JK MP_median, per 1 s.d. [sov_key_nonres.csv, sov_headline.csv]

`allday_t2aligned_settle` measures y_{t+h} − y_{t+1}: if secondary trades settle T+2, day +1 is the last position
built from pre-announcement trades only.

| outcome | h=2 | h=5 | h=10 | h=20 |
|---|---|---|---|---|
| SUN pp | −0.036 (0.013), p 0.005 | −0.092 (0.046), p 0.042 | −0.049 (0.121) | −0.013 (0.203) |
| SBSN − SUN, pp | 0.009 (0.012) | −0.001 (0.031) | −0.048 (0.082) | −0.123 (0.135) |
| SBSN − SUN, log % | −0.490 (0.359) | −1.963 (1.043), p 0.060 | −1.802 (1.527) | −2.526 (2.029) |

Permutation p for SUN at h=5: 0.022. The SUN outflow measured this way is about two thirds of the primary
estimate. The positive pp differential disappears entirely: it came from days 0–1.

### 4.4 Other shocks: per 1 s.d. [sov_key_nonres.csv]

Primary specification unless stated.

| shock | SUN pp, h=5 | SUN pp, h=20 | diff pp, h=5 | diff pp, h=20 | diff log, h=5 | diff log, h=20 |
|---|---|---|---|---|---|---|
| jk_mp_pm | −0.136 (0.061) | −0.003 (0.273) | 0.049 (0.029) | −0.089 (0.148) | −1.600 (1.225) | −1.712 (2.393) |
| jk_mp_pm, drop 2020-03-03 | −0.203 (0.072) | −0.538 (0.166) | 0.065 (0.038) | 0.209 (0.140) | −2.781 (1.465) | −3.724 (3.246) |
| usmpd_stmt | 0.019 (0.096) | 0.152 (0.228) | −0.074 (0.074) | −0.152 (0.132) | −0.742 (1.172) | 0.182 (2.047) |
| usmpd_stmt, drop 2020-03-15, 03-23 | −0.093 (0.066) | 0.013 (0.255) | 0.009 (0.037) | −0.088 (0.150) | −1.279 (1.386) | −1.096 (2.193) |
| usmpd_stmt, drop 2020-03-03 | 0.013 (0.144) | −0.107 (0.245) | −0.107 (0.106) | 0.002 (0.153) | −1.614 (1.439) | −0.229 (2.854) |
| usmpd_stmt, drop all three | −0.166 (0.079) | −0.447 (0.154) | 0.013 (0.060) | 0.172 (0.136) | −2.770 (1.660) | −2.522 (3.296) |
| usmpd_stmt, excl. Mar–Apr 2020 | −0.190 (0.075) | −0.482 (0.139) | 0.048 (0.055) | 0.219 (0.132) | −2.710 (1.657) | −2.619 (3.305) |
| jk_cbi_median (information) | −0.008 (0.057) | 0.041 (0.145) | −0.010 (0.066) | −0.041 (0.137) | −0.085 (1.321) | 0.477 (2.448) |
| bs_mps_orth (2020 events dropped) | −0.119 (0.064) | −0.298 (0.114) | 0.021 (0.056) | 0.059 (0.122) | −1.416 (1.266) | −2.147 (2.837) |

- **jk_mp_pm** reproduces the primary results, including the dependence on 2020-03-03.
- **usmpd_stmt** is null in the full sample. The three March 2020 easings drive that null *jointly*: USMPD codes
  2020-03-03, 03-15 and 03-23 as −10.2, −8.0 and −1.3 bp, and those weeks saw heavy foreign selling. Dropping 03-15
  and 03-23 (which JK codes as 0) leaves SUN at h=5 at −0.093 (0.066), p 0.159; dropping 2020-03-03 alone leaves
  0.013 (0.144), p 0.930. Only dropping all three gives −0.166 (0.079), p 0.035.
- **The CBI information shock** moves nothing.
- **The orthogonalised Bauer–Swanson shock** gives a SUN outflow that builds to −0.298 pp per s.d. at h=20
  (NW p 0.009). It has no 2020 events, so this is comparable to the drop-2020-03-03 and ex-COVID results, not to
  the primary. Its differentials are uninformative.

### 4.5 Pre-announcement placebo: change over [−6, −1] regressed on e_t, per 1 s.d. [sov_daily_pretrend.csv]

| shock, sample | SUN pp | MDE | p NW / perm | diff pp | p NW / perm | diff log | p NW / perm |
|---|---|---|---|---|---|---|---|
| jk_mp_median, full | 0.010 (0.064) | 0.181 | 0.878 / 0.822 | −0.054 (0.140) | 0.699 / 0.307 | 0.748 (1.548) | 0.629 / 0.427 |
| jk_mp_median, fixed event sample | 0.041 (0.070) | 0.195 | 0.551 / 0.373 | −0.093 (0.161) | 0.562 / 0.118 | 0.429 (1.824) | 0.814 / 0.697 |
| jk_mp_median, drop 2020-03-03 | −0.056 (0.041) | 0.115 | 0.170 / 0.243 | 0.108 (0.053) | 0.042 / 0.063 | 2.393 (0.982) | 0.015 / 0.038 |
| jk_mp_median, excl. Mar–Apr 2020 | −0.072 (0.033) | 0.092 | 0.028 / 0.139 | 0.113 (0.053) | 0.033 / 0.061 | 2.305 (1.003) | 0.022 / 0.055 |
| jk_mp_median, excl. 2020-03..2021-12 | −0.094 (0.035) | 0.098 | 0.007 / 0.097 | 0.117 (0.056) | 0.038 / 0.084 | 1.543 (0.943) | 0.102 / 0.172 |
| jk_mp_pm, excl. Mar–Apr 2020 | −0.083 (0.026) | 0.072 | 0.001 / 0.109 | 0.093 (0.046) | 0.045 / 0.127 | 1.611 (0.862) | 0.061 / 0.156 |
| usmpd_stmt, full | 0.084 (0.062) | 0.173 | 0.175 / 0.062 | −0.139 (0.140) | 0.322 / 0.012 | −0.177 (1.541) | 0.909 / 0.848 |
| usmpd_stmt, excl. Mar–Apr 2020 | −0.086 (0.042) | 0.118 | 0.041 / 0.121 | 0.160 (0.089) | 0.073 / 0.029 | 2.094 (1.331) | 0.116 / 0.127 |
| jk_cbi_median, excl. Mar–Apr 2020 | −0.061 (0.040) | 0.113 | 0.129 / 0.164 | 0.091 (0.076) | 0.231 / 0.105 | 0.277 (1.361) | 0.839 / 0.797 |
| bs_mps_orth (2020 dropped) | −0.056 (0.036) | 0.100 | 0.115 / 0.244 | 0.111 (0.077) | 0.151 / 0.058 | 1.466 (1.122) | 0.191 / 0.156 |

The weekday-stratified permutation gives the same picture (see the table file).

**What the placebo shows:**

- **The full-sample placebo is uninformative.** Its MDE (0.181 per s.d. for SUN) exceeds the h=5 effect (0.142), and
  section 4.2 shows that it looks clean only because of the 2020-03-03 event.
- **Outside the March 2020 events, the pre-announcement drift has the same sign as the post-event effects.**
  Hawkish surprises are preceded by non-resident SUN selling and a positive pp differential. The drift is not small:
  excluding March–April 2020, SUN −0.072 before against −0.218 by h=5 after; differential +0.113 before against
  +0.093 after.
- **The log differential has the opposite sign before the event.** It is about +2.3% per s.d. before hawkish
  surprises (excluding March–April 2020 or dropping 2020-03-03) and negative afterwards. This looks like mean
  reversion in a small, noisy series.
- **The corrected permutation test is weaker than NW on the placebo cells** (for example SUN ex-COVID: NW p 0.028,
  permutation p 0.139). With the March–April 2020 values no longer re-drawn, the permuted null is wider. Neither
  test is clean when a few events sit in a crisis; the NW p-values on these cells are the less favourable reading
  for the design, and I report both.
- **The orthogonalised BS shock does not remove the drift.** Its point estimates are of similar size (SUN −0.056,
  differential +0.111), only less precise.
- **Likely reading.** FOMC surprises in this period are correlated with pre-meeting conditions that already move
  EM portfolio flows. The post-event LPs condition on five lags of the daily change, which absorbs the linear link
  to pre-window flows, but not a persistent common drift.

### 4.6 Composition-only benchmark, per 1 s.d. [sov_composition_benchmark.csv, sov_composition_gap_pretrend.csv]

**The benchmark.** If non-residents cut SBSN by the same *proportion* as SUN, the pp-of-outstanding differential is
approximately b_log(SUN) × NR share(SBSN)/100 − b_pp(SUN). The non-resident shares at day −1 of the events are
SUN 38.63% and SBSN 4.67%. The gap, observed minus benchmark, equals b_diff − 0.0467 × b_log(SUN) + b_pp(SUN);
its standard error comes from a joint Newey–West over the three equations (lag h+5), which reproduces each
single-equation NW s.e. exactly.

**Check of the approximation.** b_log(SUN) × 38.63/100 reproduces b_pp(SUN): −0.148 against −0.142 at h=5, primary.

| specification | h | SBSN pp (90% CI) | SBSN pp under equal proportional selling | observed diff pp (s.e.) | benchmark diff | gap (s.e.), p |
|---|---|---|---|---|---|---|
| primary | 0 | 0.014 (0.001, 0.028) | −0.003 | 0.039 (0.020) | 0.026 | 0.013 (0.008), 0.120 |
| primary | 2 | −0.023 (−0.064, 0.018) | −0.010 | 0.045 (0.033) | 0.070 | −0.025 (0.022), 0.257 |
| primary | 5 | −0.085 (−0.196, 0.027) | −0.018 | 0.036 (0.044) | 0.124 | −0.087 (0.051), 0.087 |
| primary | 10 | −0.085 (−0.261, 0.092) | −0.011 | −0.019 (0.083) | 0.085 | −0.104 (0.090), 0.248 |
| primary | 20 | −0.126 (−0.365, 0.113) | −0.007 | −0.095 (0.142) | 0.053 | −0.147 (0.125), 0.238 |
| excl. Mar–Apr 2020 | 5 | −0.140 (−0.231, −0.048) | −0.027 | 0.093 (0.039) | 0.191 | −0.098 (0.054), 0.068 |
| drop 2020-03-03 | 5 | −0.154 (−0.250, −0.058) | −0.023 | 0.043 (0.057) | 0.165 | −0.122 (0.059), 0.037 |
| fixed event sample | 5 | −0.095 (−0.235, 0.045) | −0.015 | 0.015 (0.050) | 0.129 | −0.113 (0.063), 0.072 |
| T+2-aligned | 5 | −0.081 (−0.180, 0.019) | −0.012 | −0.001 (0.031) | 0.081 | −0.082 (0.047), 0.079 |

- **The positive pp differential is consistent with a pure composition effect.** Under equal proportional selling the
  SBSN response would be about −0.02 pp per s.d. In the primary specification the SBSN 90% interval contains both
  that value and zero, so the data cannot tell "SBSN non-residents do not sell" from "they sell like SUN
  non-residents".
- **The gap is negative at h=5 in all 11 all-day specifications** and at h=2 in 10 of 11 (same-date timing: +0.001).
  It has p < 0.10 in 8 of 11 at h=5 (smallest p 0.037), 5 of 11 at h=10, and 4 of 11 at h=20.
- **This is not independent evidence of proportional flight.** The gap is close to 0.0467 × the log differential
  (−0.0467 × 1.988 = −0.093 against −0.087), so it inherits the log differential's problems: the same 56 events in
  every specification, and a pre-event pattern of the opposite sign once the 2020-03-03 event is out.
  - The gap's own pre-window placebo [sov_composition_gap_pretrend.csv] is −0.043 (0.090), p 0.630, in the full
    sample, but positive without the March 2020 events: +0.060 (0.042), p 0.153, dropping 2020-03-03; +0.051
    (0.041), p 0.218, excluding March–April 2020; +0.036 (0.042), p 0.391, excluding 2020-03..2021-12.
  - In the same samples the log-differential placebo is positive and significant (section 4.5).
- The comparison is descriptive. It does not show stickier SBSN holders. The negative post-event gap is marginal
  and follows a positive (if insignificant) pre-event gap, so it is not credible evidence of flightier SBSN holders
  either.

### 4.7 Rp tn per event
Per 1 s.d. JK MP surprise, primary specification, by day 5:
- SUN: −Rp 3.06 tn (s.e. 1.22).
- SBSN: −Rp 0.30 tn (0.28).

Per 25 bp, by day 5:
- SUN: −Rp 20.8 tn (8.3).
- SBSN: −Rp 2.03 tn (1.92).

### 4.8 Other holders: JK MP_median, primary specification, per 25 bp, pp of own outstanding [sov_holders_primary.csv]

| holder | share at day −1, SUN / SBSN | SUN h=0 | SUN h=5 | SUN h=20 | SBSN h=0 | SBSN h=5 | SBSN h=20 |
|---|---|---|---|---|---|---|---|
| total outstanding | – | −0.680 (0.321) | −1.040 (0.342) | −0.930 (1.087) | −0.403 (0.797) | −1.680 (2.627) | 0.570 (4.918) |
| conventional banks | 25.85% / 36.22% | −0.166 (0.422) | −0.358 (1.441) | 3.438 (2.038) | −0.264 (0.355) | −0.149 (0.806) | 3.488 (2.343) |
| Islamic banks | – / 9.18% | n/a | n/a | n/a | −0.078 (0.158) | −0.123 (0.200) | 0.816 (0.625) |
| Bank Indonesia (net) | 7.73% / 5.20% | −0.275 (0.408) | 0.050 (1.372) | −4.343 (2.425) | 0.057 (0.280) | 0.329 (0.568) | −0.743 (1.367) |
| mutual funds (all funds) | 4.10% / 5.61% | −0.011 (0.013) | 0.039 (0.048) | 0.121 (0.111) | 0.029 (0.028) | −0.018 (0.087) | −0.689 (0.366) |
| insurance & pension | 15.35% / 22.65% | −0.088 (0.065) | −0.145 (0.106) | −0.357 (0.210) | −0.013 (0.102) | −0.165 (0.216) | −0.737 (0.489) |
| individuals | 2.90% / 6.74% | −0.010 (0.028) | 0.096 (0.051) | 0.351 (0.204) | −0.125 (0.227) | −0.937 (1.527) | −0.944 (1.299) |
| others | 5.44% / 9.73% | −0.016 (0.024) | −0.024 (0.051) | −0.055 (0.141) | −0.050 (0.054) | −0.316 (0.273) | −0.340 (0.683) |

To convert to per 1 s.d., divide by 6.8. Figure 4 (`sov_fig4_irf_holders.png`) plots these. These are 15 holder ×
instrument series × 21 horizons, so scattered p < 0.10 cells are expected by chance.

- **Total SUN outstanding falls on day 0 and day 5.**
  - **Day 0** (−0.680, s.e. 0.321) can only be a chance correlation: day-0 settlements come from auctions held
    before the FOMC.
  - **Day 5** (−1.040, s.e. 0.342) may be a real supply response. Post-FOMC auctions settle around day 5, and the
    government can cut awards when bids price in higher yields.
  - Either way, issuance noise loads onto holder responses. This is why the pp-of-outstanding scaling and the
    settlement controls are used.
- **Islamic banks (SBSN only; the DJPPR line may or may not include Islamic windows): uninformative, not zero.**
  - Near zero in the first week (h=5: −0.123 (0.200), i.e. −1.3% of their own position).
  - Positive and larger later: about +1 pp of SBSN outstanding per 25 bp at h=9–17, roughly 10–12% of their own
    position; the 90% band excludes 0 at h=15–17 (NW p 0.059–0.092).
  - The MDE at h=20 is 1.750 pp per 25 bp, about 19% of their holdings. Responses smaller than that cannot be ruled
    out.
- **Mutual funds.** DJPPR does not separate Shariah funds, so this line covers all funds. Their SBSN holdings fall
  at h=8–20 with NW p between 0.044 and 0.120 (h=20: −0.689 (0.366) per 25 bp, about 12% of their own position).
  This is marginal and one of many cells.
- **Conventional banks absorb SBSN** at h=9–15: +3.3 to +5.75 pp of SBSN outstanding per 25 bp (NW p 0.005–0.08),
  peaking at h=12 (5.751, s.e. 2.054), about 16% of their own position. This may partly reflect issuance absorbed by
  banks, but the SBSN investor base is not untouched by the US shock.
- **The other holder responses are imprecise.** BI net SUN falls at h=20 (−4.343 (2.425)); SBSN insurers drift down.

## 5. Monthly: non-resident holdings by maturity bucket (descriptive)

**Specification.** Monthly LP, h=0..12, with three lags of the monthly change and NW lag h+1 (house style). The
outcome is in pp of the instrument's total outstanding at the end of month t−1. Shocks are summed within the month.
Per-s.d. scaling uses the monthly s.d. over 2009-01..2025-06 (ET-month series); jk_mp_median 3.50 bp, so
25 bp = 7.14 s.d. [sov_shock_sd.csv].

**Month assignment.** `load_shocks()` assigns each event to its ET month. Three events have their Jakarta day 0 in
the next month: 2018-01-31, 2019-07-31 (FOMC, day 0 on the 1st) and 2020-03-31 (08:30 ET, day 0 2020-04-01), so in
the ET version their h=0 month-end position is pre-event. The `jakarta_day0_month` version moves them (and the
corresponding USMPD/BS events) to the following month; summing the event file by ET month reproduces
`load_shocks()` exactly for these shocks over 2016–2022. Both versions are reported; the Jakarta version is the
correct timing.

**Sample.** 61 months (2017-05..2022-05) at h=0 and 49 at h=12 [sov_monthly_maturity_lp.csv,
sov_monthly_diff_lp.csv].

| shock (per 1 monthly s.d.) | month | SUN total, h=0 | SUN total, h=12 | SBSN total, h=0 | SBSN total, h=12 | SBSN−SUN, h=0 | SBSN−SUN, h=12 |
|---|---|---|---|---|---|---|---|
| jk_mp_median | Jakarta | 0.366 (0.363) | 0.879 (0.387) | 0.068 (0.072) | 0.040 (0.232) | −0.277 (0.292) | −0.973 (0.463) |
| jk_mp_median | ET | 0.378 (0.391) | 1.009 (0.451) | 0.085 (0.084) | 0.090 (0.274) | −0.250 (0.307) | −1.078 (0.496) |
| usmpd_stmt | Jakarta | 0.424 (0.147) | 0.628 (0.285) | 0.102 (0.032) | 0.124 (0.102) | −0.301 (0.141) | −0.587 (0.401) |
| usmpd_stmt | ET | 0.465 (0.130) | 0.659 (0.274) | 0.111 (0.035) | 0.151 (0.091) | −0.324 (0.132) | −0.579 (0.376) |
| bi_rule_resid (domestic) | – | 0.040 (0.140) | 0.583 (0.306) | −0.150 (0.058) | −0.345 (0.152) | −0.190 (0.169) | −0.753 (0.352) |

- **The monthly SUN response has the wrong sign relative to the daily one.** Non-resident SUN holdings *rise* in the
  months after a US tightening, significantly so for usmpd_stmt at h=0 (+0.424 (0.147) Jakarta, +0.465 (0.130) ET;
  SBSN +0.102 (0.032) and +0.111 (0.035)). The negative monthly differential is driven by that rise, not by SBSN.
- JK MP_median per 25 bp, SBSN−SUN at h=12: −6.95 (3.30), p 0.035 (Jakarta); −7.69 (3.54), p 0.030 (ET).
- **I do not interpret these.**
  - Monthly sums of daily surprises discard the timing that identifies the daily design.
  - 49–61 months spanning the 2020 collapse in foreign SUN holdings leave room for any trend to load on a few
    shocks.
  - The maturity-bucket LPs are in the table file. Bucket shares also shift mechanically as bonds roll down,
    which adds noise.
- **The domestic BI rule residual is the less credible shock** (selection on observables). Per 25 bp, which is
  1.98 monthly s.d., its h=12 differential is −1.487 (0.696).
- **Why the sample starts in 2017-05.** The monthly file starts in 2017-01, and the first change plus three lags
  use up four months.

## 6. Interpretation

**What the module asks.** Whether Islamic finance changes the international transmission through the investor
base. Sovereign sukuk are the cleanest place in Indonesia to look: same issuer, same day, same exchange rate.

**What the data say:**
1. **Foreign portfolio investors may sell Indonesian government bonds in the week after US hawkish surprises.** In
   the primary all-days specification the effect is 0.080–0.142 pp of SUN outstanding per s.d. by days 2–5
   (Rp 1.75–3.06 tn). This is suggestive, not established: it is insignificant in the events-only cross-section, the
   full-sample placebo cannot rule out a pre-trend of that size, and outside March 2020 the pre-window drift has the
   same sign. What happens after day 5 depends on whether the 2020-03-03 emergency cut is in the sample.
2. **Foreigners hold so little SBSN (about 5% of the stock against about 39% of SUN) that, by arithmetic, any
   proportional foreign selling moves SBSN outstanding less.** That follows from the ownership shares; the estimated
   SBSN responses are too imprecise to confirm it.
3. **Whether SBSN's foreign holders are stickier per unit held cannot be answered with these data.** The proportional
   comparison has an MDE several times the SUN response, its point estimates are negative but marginal, and the
   pre-event pattern of the opposite sign points to mean reversion rather than flight. Neither "stickier" nor
   "flightier" is supported.
4. **Domestic Islamic holders.** The Islamic-bank SBSN response is uninformative (MDE about 19% of their position at
   h=20); Shariah funds are not identified in the data.

**Link to the credit module.** The credit module found no detectable differential Islamic-vs-conventional credit
response to US shocks. This module adds only that the sovereign investor base offers no evidence of a less flighty
Islamic investor base. It does not measure how Islamic banks are funded, so it says nothing about funding channels;
the earlier conjecture that Indonesian Islamic finance is "domestically funded and therefore insulated" was not
tested here and would apply equally to conventional banks, so it cannot explain a null *differential*.

**Credibility.** The design is **not** credible as clean causal evidence. In every JK MP_median sample without the
2020-03-03 event, at least one pre-window placebo (SUN, pp differential or log differential) is significant at 5%
under NW: the announcement-day shock predicts flows in the week *before* the announcement. In the full sample the
placebo is uninformative. Treat every number here as descriptive of the joint behaviour of surprises and flows
around FOMC meetings.

## 7. Caveats

- **Sample.** Only 2015-12-31 to 2022-06-27, the archived DJPPR daily files (see `notes/data_djppr.md`). That gives
  56–58 events per shock, 46 for Bauer–Swanson, and 39 in the ex-pandemic sample. Inference rests on these event
  counts, not on the roughly 1,550 trading days, and the all-days NW and events-only HC1 inferences disagree for SUN.
- **One influential event.** The 2020-03-03 emergency cut (−12.4 bp, 3.4 s.d.) decides the shape of every response
  after day 5 and the full-sample placebo (section 4.2).
- **Face values.** Holdings are face values, not market values, so price effects are excluded by construction.
  Non-tradable and FX SBN are excluded.
- **Settlement timing.** Positions are settled holdings (section 1.2). The secondary-market settlement cycle is not
  verified; under T+2 the h=0–1 estimates are pre-event and the T+2-aligned results (section 4.3) are the relevant
  ones.
- **Islamic banks line.** DJPPR's "Bank Syariah" line reports SBSN only, and the file does not say whether it
  includes Islamic windows (UUS). It cannot be matched to the OJK BUS/UUS split. Shariah mutual funds are not
  separated from other funds.
- **Small SBSN base.** Non-resident SBSN holdings average Rp 19.0 tn, with daily log changes of 3.1% s.d. A few
  large holders may drive them. DJPPR has a memo line for foreign governments and central banks, which could show
  how much of the base is official. I did not analyse it.
- **Maturity is not held fixed.** Foreign SBSN holdings are short-dated (34.7% at 0–1y and 29.0% at 1–2y) and
  foreign SUN holdings long-dated (36.8% at 5–10y and 34.7% at >10y); see section 2.
- **Shock problems.**
  - **JK `MP_median`/`MP_pm`** are 0 on 2020-03-15 and 2020-03-23 because the S&P 500 surprise is missing, even
    though these were major easings. They are excluded from the events-only regressions and the s.d., and enter
    the all-days LP as zero shocks (dropping them changes little: section 4.1).
  - **USMPD** codes those events as negative surprises; together with 2020-03-03 they drive its full-sample null
    (section 4.4).
  - **`bs_mps_orth`** is NA for the 2020 events, which are dropped.
- **Pre-window drift.** Without the March 2020 events the placebo fails under NW for the JK shocks and USMPD (the
  corrected permutation p-values are weaker), and is of similar size, but insignificant, for BS. The full-sample
  placebo is uninformative. See 4.5.
- **Multiple comparisons.** I report 5 shocks × 13 specifications × 3 scalings × up to 21 horizons, plus other
  holders and leave-one-out runs. With that many cells, scattered p < 0.05 results are expected by chance. The
  pre-specified headline is the primary specification with JK MP_median.
- **Per-25 bp numbers are extrapolations.** 25 bp is 6–12 s.d. of the event distribution.
- **Monthly block.** Descriptive only; its SUN responses have the opposite sign to the daily ones.

## 8. Files

- Script: `code/R/14_sovereign.R`.
- Tables (`output/tables/`):
  - `sov_daily_lp_all.csv`: every daily LP estimate (column `spec_stage` says when each specification was added;
    `se_type` is NW or HC1; `p_asy` is the normal p-value of that s.e.).
  - `sov_key_nonres.csv`: non-resident outcomes at h = 0, 1, 2, 5, 10, 20, for all shocks and specifications, with
    NW/HC1, permutation and weekday-permutation p-values.
  - `sov_headline.csv`: primary, events-only, fixed-sample, drop-2020-03-03 and T+2-aligned results.
  - `sov_daily_nonres_by_shock_spec_persd.csv`.
  - `sov_daily_pretrend.csv`: placebos in seven samples.
  - `sov_loeo_nonres.csv`, `sov_loeo_summary.csv`: leave-one-event-out.
  - `sov_composition_benchmark.csv` (with the gap's joint-NW s.e.), `sov_composition_gap_pretrend.csv`.
  - `sov_holders_primary.csv`: all holders, primary specification, with shares at day −1 and estimates relative to
    each holder's own position.
  - `sov_shock_sd.csv`.
  - `sov_events.csv`: event dates, ET time, day 0 under both timings, shock values, flags.
  - `sov_desc_summary.csv`, `sov_desc_composition.csv`, `sov_desc_nonres_share_daily.csv`.
  - `sov_monthly_bucket_shares.csv`, `sov_monthly_maturity_lp.csv`, `sov_monthly_diff_lp.csv` (both with
    `month_timing`).
- Figures (`output/figures/`): `sov_fig1_nonres_share.png`, `sov_fig2_holder_composition.png`,
  `sov_fig3_irf_nonresidents.png` (with drop-2020-03-03 and fixed-sample overlays), `sov_fig4_irf_holders.png`,
  `sov_fig5_robustness_diff.png`.
- No new raw or clean data were added; the module uses existing clean files only. One web search (documentation of
  the BI-SSSS settlement convention) was made; nothing was downloaded.
