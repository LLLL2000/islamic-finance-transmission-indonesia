## 8. The international investor base: sukuk versus conventional government bonds

US monetary policy reaches emerging markets partly through foreign portfolio investors, who sell local-currency bonds when US rates rise. If Islamic finance attracts a different, less flighty investor base, Islamic instruments would transmit US shocks less. Indonesia allows a clean test of this. The government issues both conventional bonds (SUN) and sovereign sukuk (SBSN). They share the issuer, credit risk, currency and trading calendar. Comparing foreign holdings of the two on the same day holds macroeconomic news and the exchange rate fixed.

This module is supplementary: the pre-analysis plan does not mention it (Appendix B, item 9). Its results should be read as exploratory.

### 8.1 Design

The data are the Ministry of Finance's (DJPPR) daily holdings of tradable rupiah government bonds by holder type, at face value, from 31 December 2015 to 27 June 2022. Over this period non-residents held on average 38.9 percent of SUN but only 4.7 percent of SBSN. SBSN is held mainly by domestic banks and insurers, and Islamic banks hold about 9 percent of it.

For each instrument, the outcome is the change in non-resident holdings from the day before an FOMC announcement to $h$ trading days after it, in percentage points of the instrument's outstanding stock. This scaling is robust to new issuance. A proportional (log) version is also reported. The estimator is an all-trading-day local projection. It has the following elements:
- the JK pure-policy surprise on the event day and zero on other days;
- five lags of the outcome's daily change;
- counts of settlement days in the window, because new issues settle on Thursdays and most announcements reach Jakarta on a Thursday;
- Newey-West errors and a permutation test that re-draws event dates.

Day 0 is the first Jakarta trading day after the announcement. The sample has 58 events. Identification rests on those events, not on the roughly 1,550 trading days.

### 8.2 Results

**Foreign investors may sell conventional bonds in the week after a US tightening (Table 15, Figure 9).** Per one-s.d. surprise (3.7 bp), non-resident SUN holdings fall by 0.08 pp of SUN outstanding by day 2 (s.e. 0.03) and 0.14 pp by day 5 (s.e. 0.06), about Rp 3 trillion. Newey-West p-values are 0.015 and 0.017, and permutation p-values 0.007 and 0.008. The day-5 estimate survives dropping any single event. The evidence is suggestive rather than established, for three reasons.
- The events-only cross-section, a check chosen before the results, does not reject: -0.11 (s.e. 0.08) at day 5.
- The pre-announcement placebo in the full sample is uninformative, not clean. Its minimum detectable effect, 0.18 pp, exceeds the effect it is meant to rule out. Excluding March-April 2020, the US shock predicts SUN selling in the five days *before* the announcement (-0.07, s.e. 0.03; Newey-West p 0.03, permutation p 0.14; excluding 2020-03 to 2021-12, -0.09, s.e. 0.03, permutation p 0.10). Dropping only the 3 March 2020 emergency cut gives -0.06 (s.e. 0.04).
- What happens after day 5 depends on one event, the emergency cut of 3 March 2020. With it, the outflow fades by day 20. Without it, the outflow keeps building to -0.37 pp (s.e. 0.14).

**The sukuk comparison is uninformative.** In pp of outstanding, the SBSN-minus-SUN differential is +0.04 per s.d. at day 5 (s.e. 0.04). Its minimum detectable effect is 0.12, and it is insignificant at every horizon after day 0. Its positive sign is what pure composition produces: with foreigners holding 5 percent of SBSN against 39 percent of SUN, equal *proportional* selling would move SBSN outstanding much less. The SBSN response itself cannot distinguish "no selling" from "selling like SUN holders": its 90 percent interval at day 5, -0.20 to +0.03, contains both.

In proportional terms the differential is -2.0 percent per s.d. at day 5 (s.e. 1.2, p = 0.09). That point estimate says foreign sukuk holdings fall proportionally *more*. It is not credible evidence of that either. Its minimum detectable effect is 3.3 percent, about 8.5 times the SUN response itself. In the samples where it is significant, the pre-announcement log differential has the opposite sign (+2.3, s.e. 1.0). A rise before the event followed by a fall is what mean reversion looks like in a tiny, noisy series: daily log changes of foreign SBSN holdings have a standard deviation of 3.1 percent.

**Domestic Islamic holders.** Islamic banks' SBSN holdings show no response in the first week (-0.02 pp of SBSN outstanding per s.d. at day 5, s.e. 0.03). At days 15-17 they rise by about 0.15 pp per s.d., and the 90 percent band just excludes zero; with 15 holder series and 21 horizons, this is not interpreted. The estimate is uninformative rather than zero: its minimum detectable effect at day 20 is about 19 percent of their own position per 25 bp, or about 2.8 percent per standard deviation of the shock. DJPPR does not separate Shariah mutual funds from other funds.

### 8.3 Interpretation

The sovereign market offers no evidence that the Islamic investor base is less flighty, and no evidence that it is more flighty. Foreigners hold so little sukuk that, by arithmetic, any proportional foreign selling moves the sukuk market less than the conventional market. That follows from ownership shares, not from different investor behaviour. Whether a foreign sukuk holder behaves differently from a foreign SUN holder cannot be answered with 58 events and a foreign sukuk base of about Rp 19 trillion.

The module also illustrates a design point. FOMC surprises in this period correlate with pre-meeting conditions that already move emerging-market portfolio flows. Daily data reveal this through the pre-announcement placebo; monthly data cannot. Any event study of EM bond flows on Fed surprises should report such a placebo.
