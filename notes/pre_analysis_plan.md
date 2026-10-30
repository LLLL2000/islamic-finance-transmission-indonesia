# Pre-analysis plan

Written 2026-10-29, **before any outcome regression was run**. The data were still being
built when this was written. Deviations from this plan will be reported in the paper as
deviations.

## 1. Question

Does the presence and sectoral penetration of Islamic finance change how monetary policy
shocks are transmitted to bank credit? It asks this for international shocks (US) and
domestic ones (Bank Indonesia).

## 2. Setting and why it identifies

Indonesia runs a dual banking system. Islamic financing is about 7% of commercial-bank
credit. It comes from stand-alone Islamic banks (BUS) and from Islamic windows of
conventional banks (UUS). Both kinds lend to the same economic sectors as conventional
banks. OJK publishes Islamic financing by sector monthly, and Bank Indonesia publishes
total credit by sector monthly.

The core comparison is **Islamic vs conventional credit to the same sector in the same
month**:

- Sector × month fixed effects absorb anything that moves credit demand in a sector in a
  month, including the aggregate effect of the shock itself.
- The coefficient of interest is identified by the difference in how the two lenders'
  credit to that sector responds. This is Khwaja–Mian logic applied at the
  sector × bank-type level.

Bank-level data would be finer. It is not openly available, and this is the finest
open-data cut.

## 3. Shocks

- **International (primary, most credible).** The Jarocinski–Karadi (2020, updated to
  Sep 2026) *pure monetary policy* component (`MP_median`), summed within month. It is
  scaled so one unit equals a 25 bp surprise in the pc1 metric.
  - Robustness: `MP_pm`, USMPD statement (`STMT`) and monetary-event (`ME`) surprises,
    and Bauer–Swanson `MPS_ORTH` (to 2023-12).
  - The *information* component `CBI_median` is reported separately as a placebo-like
    contrast. Its sign is not predicted.
- **Domestic (secondary, explicitly less credible).** A policy-rule residual. Take the
  monthly change in the BI policy rate, adjusted for the Aug-2016 instrument switch, and
  regress it on lagged CPI inflation, activity growth, the IDR/USD change, the VIX
  change, lagged policy-rate changes and the contemporaneous US shock. The residual is
  the domestic shock. Identification is selection-on-observables. The paper will grade
  it accordingly and not present it as on par with the high-frequency shock.

## 4. Primary estimand and specification

For bank type b ∈ {ISL, CONV}, sector s and month t, with
Δʰy = log credit_{s,b,t+h} − log credit_{s,b,t−1}:

```
Δʰy_{s,b,t} = β_h · (ε_t × ISL_b) + α_{s,t} + α_{s,b}
              + Σ_{l=1..3} γ_l Δy_{s,b,t−l}
              + ISL_b × (X_{t−1})'δ  + u
```

- β_h is the **differential** response of Islamic vs conventional credit, in log points
  per 25 bp shock, for h = 0..24 months.
- X_{t−1} are lagged macro controls interacted with ISL: VIX, Brent, IDR/USD change, BI
  rate. They absorb differential cyclicality of Islamic credit.
- **Panels:** H9 (harmonised coarse sectors, 2009–2025) is the primary panel. H15
  (finer sectors, 2016–2025) is secondary.
- **Contaminated observations:** windows contaminated by conversions, mergers or
  reporting breaks (`adj_growth_ok == FALSE` anywhere in [t−1, t+h]) are dropped.
- **Inference:** the shock varies only over time, so the effective sample is the number
  of months.
  - Primary: Driscoll–Kraay standard errors with bandwidth h+2.
  - Also reported: (i) a time-series LP on the cross-sector average differential with
    Newey–West errors; (ii) a permutation test that re-assigns the shock series across
    months (block permutation, 12-month blocks, 2,000 draws).
- **Weights:** unweighted is primary. Weighting by the sector's average Islamic credit is
  reported.

**Headline number (pre-specified):** the cumulative differential β_12 at 12 months for a
25 bp pure-policy tightening, with its 90% band.

## 5. Secondary estimands

1. **Levels by bank type.** The same LP without α_{s,t}: sector FE plus macro controls
   and the shock main effect, estimated separately for ISL and CONV. This shows whether
   either credit type responds at all; it is the "first stage" for the interpretation.
2. **Funding channel, BUS vs UUS.** Replace ISL with separate BUS and UUS dummies. UUS can
   draw on conventional parent funding and internal capital markets. Pre-specified
   reading:
   - If a differential exists and is driven by segmented Islamic funding, it should
     appear for BUS and be smaller or absent for UUS.
   - If it is driven by contracts or clientele, both should show it.
3. **Sectoral penetration and aggregate consequences.** For total credit Y_{s,t} to
   sector s:
   ```
   Δʰ log Y_{s,t} = θ_h (ε_t × Share_{s,pre}) + α_s + α_t + controls + u
   ```
   Share_{s,pre} is the sector's pre-period Islamic share. Under no substitution between
   bank types, the composition identity implies θ_h ≈ β_h.
   - θ_h ≠ β_h is evidence of within-sector substitution or spillovers.
   - This answers "does heterogeneous sectoral penetration change sector-level
     transmission".
4. **Price and funding mechanisms** (aggregate time series, so reported as descriptive
   LPs with NW errors):
   - Islamic deposit equivalent returns vs conventional time-deposit rates by tenor.
   - Islamic financing margins vs conventional lending rates by use.
   - Islamic deposit (DPK) growth vs conventional deposit growth.
   - Contract mix (murabahah share vs profit-sharing share).
5. **Credit risk.** Islamic NPF ratio by sector after shocks, as a "consequences" outcome.
6. **Domestic shocks.** Items 4.0 and 5.1–5.3 repeated with the BI policy-rule residual.

## 6. Pre-specified checks

- **Leads.** The shock at t should not predict the differential growth over [t−4, t−1].
- **Information shock.** Report the CBI component; no sign prediction.
- **Break robustness.** Drop 2014, 2016–17 and 2021 entirely: the classification-break and
  merger years.
- **Pandemic.** Drop 2020-03..2021-12: COVID, BI burden-sharing and the BSI merger.
- **Power.** Report the minimum detectable effect at 80% power for β_12, given the
  residual variance of the cross-sector average differential. A null that is not precise
  will be called *uninformative*, not "no effect".

## 7. What would change the conclusion

- A significant β_12 that is driven by a single sector (leave-one-sector-out).
- A significant β_12 that disappears when the macro × ISL controls are added.
- A pre-trend in the leads.

Any of these will be reported as undermining the result.
