## 6. Robustness and inference

### 6.1 Pre-specified checks

Table 6 and Figure 6 report the 12-month differential under the plan's checks and four that were added after the data were seen. The plan listed three outcomes that would undermine a positive result:
- dependence on one sector;
- sensitivity to the Islamic x macro controls;
- a pre-trend.

The main US result is a null, so for it these checks ask whether the null hides an effect. They do not suggest one:
- The DL $\beta_{12}$ for the JK shock stays between -4.0 and +0.6 in H9 across all nine DL specifications. Only one, dropping 2013-2015 (-4.0, s.e. 2.0), is significant.
- Adding the Islamic x macro controls moves it towards zero: -1.2 (s.e. 3.4) with controls dated t-25, -1.0 (s.e. 2.0) with the first draft's controls dated t-1.
- H15 is less stable. With controls dated t-25 it is -6.2 (s.e. 2.8), and with three own lags -6.6 (s.e. 3.3), but dropping the post-conversion windows gives -1.3 (s.e. 7.4). The plan's LP cannot be estimated in H15 once break years, the pandemic or the post-conversion windows are dropped, because fewer than 36 usable months remain.

For the domestic DL estimate, the checks mostly confirm the sign:
- In H9 it ranges from -1.7 (weighted, s.e. 1.2) to -4.9 (dropping break years, s.e. 1.4). The plan's section-7 criterion, a significant estimate that disappears when the Islamic x macro controls are added, is not met: with controls dated t-25 it is -2.1 (s.e. 1.2).
- In H15 every check is negative and significant except the DL with three own lags (-0.5, s.e. 1.3).
- The H9 lead placebo is significant (Section 5.3), which is the main reason the estimate is not read as causal.

![Figure 6](../output/figures/fig5_robustness.png)

*Figure 6. The 12-month differential across specifications (distributed lag).*

### 6.2 Leave one sector out, leave one year out

**Sectors.** No single sector drives the estimates (Table 10). Dropping one sector at a time keeps the H9 DL $\beta_{12}$ for the US shock between -4.5 and -0.6, and the domestic one between -2.6 and -1.5.

**Years.** The DL regresses each month's change on 25 shock lags, so the first outcome months of H9 (2009) draw on shocks from 2007 and 2008, which the LP never uses. These include some of the largest Fed surprises in the sample. Section 7 shows that one mechanism result depends on this.
- **US shock, H9.** With outcomes from 2010 the DL $\beta_{12}$ is -1.3 (s.e. 2.7). With outcomes from 2011, so that every shock lag falls in 2009 or later, it is +0.2 (s.e. 2.7). Leaving out one calendar year at a time keeps it between -4.5 and -1.3, and no estimate has $|t| > 1.9$. The negative point estimate of the full-sample DL therefore leans partly on the early years.
- **Domestic shock, H9.** The DL estimate is -2.7 (s.e. 1.2) from 2010 and -2.6 (s.e. 1.2) from 2011. Leaving out one year keeps it between -3.4 and -1.1.
- **US shock, H15.** This panel covers only nine years, and its DL estimate depends on which ones are included. Leaving out 2016 to 2020, 2024 or 2025 keeps it between -2.9 and +1.0. Leaving out 2021 gives -5.5 (s.e. 2.9). Leaving out 2022 gives **-14.7 (s.e. 2.5)**. The 2021 merger and the 2022 conversion fall in those two years, and with so few years the panel cannot separate the US shocks from these events. The pre-registered headline is the H9 estimate. H15 agrees with it in the full sample but adds little information.

These swings are large relative to the reported standard errors, and the Monte Carlo below shows that the Driscoll-Kraay standard errors are too small. A single year's removal producing a large $t$ in a nine-year panel should be read as fragility, not as a hidden effect.

### 6.3 How good are the estimators? A Monte Carlo on the actual design

Inference in this setting is delicate. There are 8 or 15 sectors, fewer than 200 months, all-unit contamination events, and a shock that varies only over time. The paper therefore checks its estimators by simulation on the actual H9 design:
- the real units, months, contamination pattern and shock series;
- simulated growth rates with a sector-month common component;
- a bank-type-specific AR(1) error, with innovation standard deviations set to the observed monthly growth volatility;
- either no differential effect, or a differential that builds to -2.4 percent per 25 bp over 12 months.

The DL in the simulation is the paper's baseline DL, without Islamic x macro controls. Table 11 reports 300 draws per design. Three results matter for the paper.

1. **The DL estimator is unbiased. For the US shock it is far more precise than the plan's LP; for the domestic shock the LP is attenuated.**
    - JK shock, 12 months: DL bias -0.2 or less and standard deviation 4.5 to 4.8; LP standard deviation 14.0 to 14.4. The LP loses precision because the contamination rule discards most long windows.
    - Domestic shock: the DL is not more precise (standard deviation 2.1 to 2.2, against 2.0 for the LP at 12 months), but the LP is biased towards zero. When the true differential builds to -2.4, the LP's mean estimate is -1.1 at 12 months and -0.5 at 24 months, while the DL's is unbiased.
2. **Driscoll-Kraay standard errors are too small for both estimators.** Nominal 90 percent bands cover 74 to 83 percent of the time for the DL and 49 to 76 percent for the LP. For the DL, the true spread of the estimates is 17 to 35 percent larger than the average reported standard error. This widens the range of differences the US nulls leave open, and overstates the significance of the domestic DL estimate. The permutation tests in Table 5 do not rely on these standard errors.
3. **The Driscoll-Kraay Wald test of all 25 lag coefficients rejects a true null in 300 of 300 draws for the US shock and 299 of 300 for the domestic shock.** With 25 restrictions and fewer than 200 months, the estimated covariance matrix is far too noisy for a joint test. This is why the paper's joint tests are permutation-based.

The simulation's noise level is set by the raw volatility of monthly growth, which includes predictable components. Its absolute standard deviations are therefore larger than the standard errors in Table 4. The comparisons between estimators, and the coverage rates, are the informative quantities.

### 6.4 Foreign-currency valuation

Both credit series include foreign-currency loans valued in rupiah. Islamic banks hold about 3 percent of their financing in foreign currency (OJK SPS: 6.1 percent in 2015, 3.2 percent in 2025). For all commercial banks the figure is roughly 12 to 14 percent (Bank Indonesia financial soundness indicators), which implies about 13 to 15 percent for conventional banks. A rupiah depreciation after a US tightening therefore raises measured conventional credit relative to Islamic credit, pushing the measured differential negative; sector x month fixed effects do not absorb this.

A back-of-the-envelope calculation gives the size. The foreign-currency share gap of about 11 percentage points, times the 6.4 percent depreciation per 25 bp at 12 months in Table 3, is a mechanical bias of about -0.7 percent per 25 bp, and about -1.1 at 24 months. The depreciation estimate is itself imprecise (s.e. 5.0). A bias of this size would move the H9 DL estimate for the US shock from -2.9 to about -2.2, which strengthens the null; it is small for the domestic shock, which barely moves the rupiah. A full valuation adjustment needs foreign-currency credit by sector and lender type, which this draft does not yet construct.
