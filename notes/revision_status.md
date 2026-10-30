# Revision status, 2026-10-30 (paused: usage limit)

## Done
- Independent review of the draft (5 lenses, each verified): 69 findings, none refuted. Full list:
  scratchpad review/findings_all.txt (session ae5f7916); key ones summarised below.
- Code fixes, all re-run and reflected in output/tables and output/figures:
  - DL baseline now has NO Islamic x macro controls (they were post-treatment for shock lags >= 1).
    Variants with controls dated t-25 and t-1 (first draft) are rows in the robustness table.
  - LP placebo fixed (four clean changes, no own lags): H9 JK 1.31 (1.82); H15 JK 2.48 (1.38).
  - LP permutation now in calendar-month blocks (H9 p 0.983, H15 0.522).
  - LP estimates on < 36 months shown as n.e. in tables and omitted in figures.
  - Bauer-Swanson added to the all-shocks table; plan's time-series LP column added.
  - Theta checks (household x shock control, leave-one-sector-out): credit_theta_checks.csv.
  - Tables renumbered by first citation; readable labels; Table 1 clean-change column fixed.
- Text fixes applied in paper/sections 02, 03, 04, 07, 08, 99 (backup of the earlier version in the
  session scratchpad sections_bak_v1).

## New headline numbers (per 25 bp, h = 12)
- US JK, H9: LP -1.69 (3.86); DL -2.88 (2.06), band -6.3 to +0.5, perm p 0.33; from 2010 -1.29 (2.69),
  from 2011 +0.24 (2.67). H15: DL -2.36 (3.10); leaving out 2022 gives -14.7 (2.5).
- Domestic, H9: LP -0.34 (0.63) (Monte Carlo: this LP recovers < half of a true effect); DL -2.13 (1.09),
  perm p 0.055, lead +1.88 (0.77). H15: DL -2.98 (0.83), perm p 0.010. Robust to most checks, incl. dropping
  post-conversion months (H9 -2.43 (1.56), H15 -5.00 (1.56)) - the old "post-conversion" argument no longer holds.
- Theta: H15 41.5 (18.1), with household control 55.7 (17.9); LOSO 26.6..76.4. H9 -90.8 (45.0).

## Left to do
1. Rewrite sections 00 (abstract), 01 (findings 1, 2, 5), 05 (5.2, 5.3, 5.5, 5.4 swing sentence), 06
   (6.1, 6.2; new 6.4 on FX valuation), 09, and Appendix B (new deviations: DL controls, placebo fix,
   MDE definition, BI-rule regressors, theta as DL, "both estimators" wording, Wald 299/300).
   Figure renumbering: levels figure becomes Figure 3; old 3, 4, 5 become 4, 5, 6 (update assemble_paper.py).
2. FX valuation module: workflow wf_7d2d8676-892 was stopped mid-build to save quota. Re-run or resume it
   (script code/R/17_fx_valuation.R may be partial; check before use).
3. Re-assemble paper/working_paper.md, regenerate doc sections (code/py/doc_sections.py), upload changed
   figures as new blobs, and update the Doc https://claude.ai/artifact/M1ASsWSum7D14qdjQLekCA
   (sections 1-9 and references are filled with the PRE-review text; tables and appendix are still pending).
4. A final numbers check of the revised text.
