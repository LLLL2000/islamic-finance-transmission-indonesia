## 1. Introduction

Islamic banks may not charge or pay interest. Their deposits are nominally profit-sharing investment accounts, and their loans are mostly cost-plus sales with margins fixed at origination. Monetary policy works through interest rates. Does a banking system in which a growing share of credit is formally interest-free transmit monetary policy differently? The question matters for every central bank in a dual banking system: Indonesia, Malaysia, Pakistan, the Gulf, Turkey, Bangladesh and others. It also matters for how these economies absorb US monetary policy, which reaches emerging markets through their own interest rates and capital flows (Rey, 2013; Miranda-Agrippino and Rey, 2020; Kalemli-Özcan, 2019).

The existing evidence does not answer the question convincingly. Most studies estimate VARs on aggregate Islamic and conventional series, or interact the domestic policy rate with an Islamic-bank dummy in bank-level regressions. Both approaches face two problems:
- **Endogenous policy.** The policy rate responds to the credit conditions it is meant to explain.
- **Different borrowers.** Islamic and conventional banks lend to different borrowers. Islamic finance concentrates in household housing and consumer finance, which respond differently to rates whatever the lender's contract.

The literature reaches every possible conclusion. Islamic banks are found to be more sensitive (Kassim, Majid and Yusof, 2009), less sensitive (Caporale et al., 2020), or to behave like large conventional banks (Zaheer, Ongena and van Wijnbergen, 2013).

This paper studies Indonesia's dual banking system with a design built to address both problems.

**First, it compares Islamic and conventional credit to the same economic sector in the same month.**
- It constructs a monthly panel, 2009-2025, of credit by economic sector from three lender types: stand-alone Islamic banks, Islamic windows of conventional banks, and conventional banks.
- Sector x month fixed effects absorb sector demand, sector risk and the aggregate effect of the shock. This is the logic of Khwaja and Mian (2008), applied at the sector level, which is the finest level the public data allow.

**Second, it uses externally identified monetary policy shocks.**
- The primary shock is the Jarociński-Karadi (2020) pure monetary policy component of FOMC announcement surprises.
- Its identification does not depend on any Indonesian variable, and the paper shows it moves Indonesian interest rates: a 25 bp US surprise raises the Bank Indonesia policy rate by about 1 pp within a year.
- A domestic Bank Indonesia policy-rule shock is reported as a less credible complement.

**Third, the specification was written in a pre-analysis plan before any outcome was estimated.** Every deviation is reported. All data are public and downloadable, including archived copies of Indonesian statistics that are no longer online.

### Findings

**1. US monetary policy shocks do not detectably move Islamic and conventional credit to the same sector differently.**
- The pre-registered headline is a differential of -1.7 percent after 12 months per 25 bp tightening (s.e. 3.9). The plan's time-series version on the cross-sector average differential gives -0.1 (s.e. 2.4; block-permutation p = 0.98).
- A more precise distributed-lag estimator gives -2.9 percent (s.e. 2.1; permutation p = 0.33). Its negative sign leans on the early sample: with outcomes from 2011 it is +0.2.
- At the 12-month horizon none of the DL estimates for US policy shocks is significant under permutation, and no joint permutation test rejects. The plan's LP swings significantly at intermediate horizons (negative at 6-11 months, positive at 16-23), but the DL does not reproduce these swings, and the Monte Carlo shows the LP's bands are far too narrow. There is no pre-trend in the main panel, and its estimate is stable when any single sector or year is dropped. The shorter 2016-2025 panel is not.
- The nominal 90 percent band rules out Islamic credit falling more than about 6 percent more, or more than about 0.5 percent less, than conventional credit to the same sector per 25 bp (-0.9 to +0.1 percent per standard deviation of the shock). Insulation is the hypothesis the data come closest to excluding.

**2. After domestic shocks, Islamic credit may contract somewhat more.**
- The pre-registered LP estimate is small and insignificant, but the Monte Carlo shows that this estimator recovers less than half of a true differential for this shock.
- The distributed lag gives -2.1 percent per 25 bp in the main panel and -3.0 in the shorter one (permutation p = 0.055 and 0.010), robust to most checks. The main panel shows a pre-trend, and the shock is identified only by selection on observables, so this is suggestive rather than established.

**3. The channels behind a funding squeeze are weak or untestable.** Aggregate deposit and financing rates show:
- Conventional deposit rates pass Bank Indonesia's rate through one for one.
- Islamic deposit returns lag them modestly after US tightening, by about 0.1 pp per standard deviation of the shock. In the full sample only the distributed lag is significant, and for the primary shock it falls from -0.20 to -0.08 pp per standard deviation and loses significance without the 2009 outcome months.
- Deposits do not detectably flow out of Islamic banks, although the test has little power.
- After 2014, murabahah financing rates reprice no differently from comparable conventional consumer credit.

Nothing in these data points to a funding squeeze that would make Islamic credit contract more: the modest lag in Islamic returns is not followed by detectable deposit outflows.

**4. The sovereign market offers no evidence of a less flighty Islamic investor base.** In daily data, non-residents sell conventional government bonds in the week after US hawkish surprises. That finding is suggestive: it fails the events-only test and has a pre-announcement drift. Foreigners hold 5 percent of sukuk against 39 percent of conventional bonds, so by arithmetic sukuk lose less foreign funding relative to their size. Whether a foreign sukuk holder behaves differently from a foreign conventional-bond holder cannot be answered with these data.

**5. Penetration regressions are uninformative.** The obvious design for asking whether *heterogeneous sectoral penetration* matters interacts the shock with each sector's Islamic share. That design produces large estimates of opposite sign in two panels covering the same economy, far outside the within-sector bands. Controlling for household sectors does not remove them. With 8 or 15 sectors, these regressions cannot separate penetration from other sector characteristics or from within-sector spillovers. If there are no spillovers, the within-sector estimate bounds how much penetration can change a sector's response: up to about 1.5 percent per 25 bp at the highest penetration in the data.

### Contribution

The paper's first contribution is to the literature on Islamic banking and monetary policy. It is, to our knowledge, the first study in that literature to use externally identified shocks and to compare Islamic and conventional lenders within the same borrower segment. The answer, no detectable difference after US shocks and at most a modestly larger Islamic contraction after domestic ones, is consistent with the mimicry view that Islamic banks in practice price and fund like conventional banks (Chong and Liu, 2009; Khan, 2010) and is inconsistent with the insulation view.

The second contribution is methodological, and applies beyond Islamic finance. Public sector-level data are riddled with breaks from reclassifications, conversions and missing months. With such data, local projections that drop contaminated windows lose most of their long-horizon sample. A distributed-lag estimator on clean monthly changes recovers the same impulse response with about a third of the sampling variability for the US shock, and without the local projection's attenuation for the domestic shock. A Monte Carlo on the actual design shows this, and also shows that standard Driscoll-Kraay inference is anti-conservative, so permutation tests are needed. Distributed lags need one more care: macro controls dated relative to the outcome month are post-treatment and should be left out.

### Limitations

The design identifies the *differential* response of Islamic and conventional credit within sector-months, and only at the sector level. It cannot rule out differences between borrowers within a sector. Its bands are wide enough that moderate differences, a few percent per 25 bp, remain possible. Bank-level or loan-level data from the credit registry of the Financial Services Authority (OJK) would sharpen the answer considerably.
