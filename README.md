# Does Islamic Finance Change Monetary Transmission? Within-Sector Evidence from Indonesia

Working paper (draft, 30 October 2026) with all code and public data needed to reproduce it.

**Paper:** [paper/working_paper.pdf](paper/working_paper.pdf) (Markdown source: [paper/working_paper.md](paper/working_paper.md)).

## What the paper does

Islamic banks may not pay or charge interest, so a growing Islamic banking sector could weaken or distort monetary
transmission. The paper builds a public monthly panel of credit by economic sector and lender type for Indonesia,
2009-2025 (stand-alone Islamic banks, Islamic windows, conventional banks). It compares Islamic and conventional
credit to the same sector in the same month, so that sector x month fixed effects absorb demand. The shocks are US
high-frequency monetary policy surprises (Jarociński-Karadi pure policy shock, primary) and a Bank Indonesia
policy-rule residual. The specification was fixed in a pre-analysis plan ([notes/pre_analysis_plan.md](notes/pre_analysis_plan.md)).

Main findings (per 25 bp, 12 months):
- **US shocks:** no detectable differential. Pre-registered local projection -1.7 percent (s.e. 3.9); distributed lag
  -2.9 (s.e. 2.1, permutation p = 0.33). Insulation of Islamic credit is close to excluded; a moderately larger
  Islamic contraction is not.
- **Domestic shocks:** the distributed lag points to a 2-3 percent larger Islamic contraction (permutation p = 0.055
  and 0.010 in the two panels), but the pre-registered estimator does not detect it and the main panel shows a pre-trend.
- **Channels:** Islamic deposit returns lag conventional rates only modestly; murabahah rates reprice like comparable
  conventional credit after 2014; deposit flows are too noisy to test a funding squeeze.
- **Sukuk vs conventional government bonds:** the daily comparison of non-resident holdings is uninformative.
- **Penetration regressions** (shock x sectoral Islamic share) give large estimates of opposite sign in the two panels.

## Status

This is a working draft. It went through an independent multi-agent review; the corrections are listed in
Appendix B of the paper. Still open ([notes/revision_status.md](notes/revision_status.md)): a full foreign-currency
valuation adjustment of the credit series (Section 6.4 gives only a back-of-the-envelope size), and a final
number-by-number check of the revised text.

## Repository layout

| Folder | Contents |
|---|---|
| `data/raw/` | Downloaded source files, unchanged (BI SEKI tables, OJK statistics via Internet Archive copies, DJPPR bond holdings, shock series, FRED/IMF macro). Provenance in `notes/data_*.md`. |
| `data/clean/` | Analysis-ready CSVs built by `code/py/build_*.py`. |
| `code/py/` | Data builders, paper assembly (`assemble_paper.py`) and PDF rendering (`build_pdf.py`). |
| `code/R/` | Estimation, figures and tables (numbered in run order). |
| `output/` | Result tables (CSV and `paper_tables.md`), figures (PNG) and run logs. |
| `notes/` | Data notes, the pre-analysis plan and the module result notes. |
| `paper/` | Section sources (`sections/`), the assembled Markdown and the PDF. |

## Reproducing

Requirements: Python 3.11 (pandas, numpy, openpyxl, xlrd, requests), R 4.4 (data.table, fixest, sandwich, ggplot2),
and Microsoft Edge for the PDF. Run from the repository root.

```
python -I code/py/build_shocks_macro.py
python -I code/py/build_bi_credit.py
python -I code/py/build_ojk_sector.py
python -I code/py/build_panel.py
python -I code/py/build_ojk_mechanisms.py
python -I code/py/build_bi_deposits.py
python -I code/py/build_djppr.py
Rscript --vanilla code/R/05_bi_shock.R
Rscript --vanilla code/R/10_lp_differential.R H9 jk_mp_median,jk_mp_pm,usmpd_stmt,usmpd_me,bs_mps_orth,jk_cbi_median,bi_rule_resid
Rscript --vanilla code/R/10_lp_differential.R H15 jk_mp_median,jk_mp_pm,usmpd_stmt,usmpd_me,bs_mps_orth,jk_cbi_median,bi_rule_resid
Rscript --vanilla code/R/10_lp_differential.R H9 bi_rule_resid ISL,CONV _bi
Rscript --vanilla code/R/11_macro_first_stage.R
Rscript --vanilla code/R/12_dl_differential.R
Rscript --vanilla code/R/13_mechanisms.R
Rscript --vanilla code/R/14_sovereign.R
Rscript --vanilla code/R/15_credit_secondary.R
Rscript --vanilla code/R/16_dl_montecarlo.R
Rscript --vanilla code/R/20_figures.R
Rscript --vanilla code/R/21_tables.R
python -I code/py/assemble_paper.py
python -I code/py/build_pdf.py
```

The R scripts set their project root in `code/R/00_common.R` (and in the `source()` line at the top of each
script); change that path if you clone the repository elsewhere.

## Data

All inputs are public and were obtained with plain downloads, without registration. OJK statistics that are no
longer on OJK's website were taken from Internet Archive copies, whose digests match the archive's records. The
raw files are redistributed here unchanged for reproducibility; their copyright remains with the publishers
(Bank Indonesia, OJK, the Ministry of Finance, the Federal Reserve Bank of San Francisco, the shock series' authors,
FRED and the IMF). Please cite the original sources.
