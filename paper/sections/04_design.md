## 4. Empirical strategy

### 4.1 The within-sector comparison

Let $y_{s,b,t}$ be log credit to sector $s$ from bank type $b \in \{\text{ISL}, \text{CONV}\}$ in month $t$, where ISL = BUS + UUS is all Islamic financing and CONV is conventional credit, and let $\varepsilon_t$ be a monetary policy shock. The estimand is the **differential** cumulative response of Islamic relative to conventional credit to the same sector:

$$
\begin{aligned}
y_{s,b,t+h} - y_{s,b,t-1} = {} & \beta_h\,(\varepsilon_t \times \text{ISL}_b) + \alpha_{s,t} + \alpha_{s,b} \\
 & + \sum_{l=1}^{3}\gamma_l\,\Delta y_{s,b,t-l} + \text{ISL}_b \times X_{t-1}'\delta + u_{s,b,t+h}.
\end{aligned} \tag{1}
$$

The terms in (1) are:
- **Sector x month fixed effects** $\alpha_{s,t}$. They absorb everything that moves credit to a sector in a month: sector-specific demand, sector-wide risk, and the aggregate effect of the shock itself. This applies the within-borrower logic of Khwaja and Mian (2008) at the sector level. Within a sector-month, Islamic and conventional lenders face the same demand conditions, so $\beta_h$ isolates the lender side up to residual composition within sectors.
- **Sector x bank-type fixed effects** $\alpha_{s,b}$. They absorb permanent growth differences, for example the faster trend growth of Islamic finance.
- **Lagged growth and lagged controls.** Three lags of own monthly growth (lag augmentation, as in Montiel Olea and Plagborg-Møller, 2021), and the macro controls $X$ (VIX, Brent oil growth, IDR/USD growth and the BI rate) dated $t-1$, before the shock, interacted with the Islamic dummy. The interactions absorb any differential cyclicality of Islamic credit with respect to these variables.

Identification needs $\varepsilon_t$ to be uncorrelated with whatever else moves the Islamic-minus-conventional gap in a sector. For the US high-frequency shocks this is plausible: FOMC surprises measured in 30-minute windows are not driven by Indonesian Islamic-credit conditions. Two concerns remain. The first is a US shock that coincides with an Indonesia-specific Islamic event; the paper tests this with leads, by dropping event windows, and by permutation. The second is mechanical: both credit series include foreign-currency loans valued in rupiah, and Islamic banks hold a much smaller foreign-currency share than conventional banks. A US tightening that weakens the rupiah therefore raises measured conventional credit relative to Islamic credit, and sector x month fixed effects do not absorb this. Section 6.4 estimates the size of this valuation effect.

### 4.2 Pre-analysis plan

The specification, panels, controls, shocks, inference, checks and the headline number were written down before any outcome regression was run (notes/pre_analysis_plan.md, dated 2026-10-29). The headline is $\beta_{12}$ in H9 for a 25 bp JK pure-policy tightening, with its 90 percent band. The plan also pre-specifies:
- the secondary estimands: levels by bank type, BUS vs UUS, sector exposure, mechanisms, NPF and domestic shocks;
- the checks: leads, the CBI contrast, dropping break years, dropping the pandemic, and power;
- three outcomes that would undermine a positive finding:
  - dependence on one sector;
  - sensitivity to the controls;
  - a pre-trend.

Appendix B lists every deviation from the plan.

### 4.3 Estimation: local projections and a distributed-lag deviation

The plan estimates (1) as a local projection (LP; Jordà, 2005) for $h = 0, \dots, 24$. It drops any window $[t-1, t+h]$ that contains a contaminated change.

This rule turned out to be costly. Seven contamination events hit every unit at once: the three conversions, three classification changes, and the 2023 gap. Together they cut the sample into short clean stretches. In H9 the LP sample falls from 2,244 observations at $h=0$ to 1,043 at $h=12$ (about 92 months) and 552 at $h=24$. Long-horizon LP estimates therefore rest on a small and selected set of months.

As a **deviation** from the plan, the paper also reports a distributed-lag (DL) estimator. It regresses each *clean* monthly change on current and lagged shocks:

$$
\Delta y_{s,b,t} = \sum_{k=0}^{24}\phi_k\,(\varepsilon_{t-k}\times\text{ISL}_b) + \alpha_{s,t} + \alpha_{s,b}
 + e_{s,b,t}, \qquad \beta^{DL}_h = \sum_{k=0}^{h}\phi_k. \tag{2}
$$

Under exogenous and serially uncorrelated shocks, (1) and (2) target the same impulse response, much as local projections and VARs do in population (Plagborg-Møller and Wolf, 2021). The DL loses only the contaminated months themselves, not every window that contains one. Equation (2) has no Islamic x macro controls. In a DL, controls are dated relative to the outcome month, so $X_{t-1}$ would come after the shock for every lag $k \ge 1$; since the BI rate, the rupiah and the VIX all respond to US shocks, such controls would net out part of the effect being measured. With exogenous shocks they are not needed for consistency. The first draft of this paper did include them; Table 6 reports that version and one with the controls dated $t-25$, before every shock lag. A Monte Carlo on the actual H9 design checks both estimators (Section 6.3). The design uses the real units, months, contamination pattern and shock series.

### 4.4 Inference

The shock varies only over time, so the effective sample is the number of months.
- **Main standard errors.** Driscoll and Kraay (1998), with bandwidth $h+2$ for the LP and 12 for the DL.
- **Time-series check.** The plan also asks for a time-series regression on the cross-sector average differential, with Newey-West (1987) errors.
- **Permutation tests.** These re-assign the shock series across months in blocks of 12 calendar months (2,000 draws), on that average differential. They give p-values for $\beta_{12}$, and for the joint null that all 25 DL lag coefficients are zero. The permutation version replaces a Driscoll-Kraay Wald test, which is badly oversized with 25 restrictions and fewer than 200 months (Section 6.3).
- **Power.** For a null result the paper reports the minimum detectable effect at 5 percent size and 80 percent power, $2.80 \times \text{s.e.}$, and calls an imprecise null "uninformative".
