# 21_tables.R ---------------------------------------------------------------
# Paper tables (Markdown) built only from output/tables/*.csv and data/clean. Writes
# output/tables/paper_tables.md. Every number quoted in the paper comes from this file
# or from the module notes.
source("C:/Users/consu/Documents/Universidad/Islamic_Finance_Project/wp_dual_banking/code/R/00_common.R")
TAB <- file.path(OUT, "tables")
md <- character(0)
add <- function(...) md <<- c(md, ...)
mdtab <- function(dt, align = NULL) {
  dt <- as.data.table(dt)
  h <- paste0("| ", paste(names(dt), collapse = " | "), " |")
  a <- paste0("|", paste(if (is.null(align)) rep("---", ncol(dt)) else align, collapse = "|"), "|")
  rows <- apply(dt, 1, function(r) paste0("| ", paste(r, collapse = " | "), " |"))
  c(h, a, rows, "")
}
est <- function(b, se, d = 2) ifelse(is.na(b), "n.e.", sprintf("%.*f (%.*f)", d, b, d, se))
star <- function(b, se) { t <- abs(b / se); ifelse(is.na(t), "", ifelse(t > 2.576, "***", ifelse(t > 1.96, "**", ifelse(t > 1.645, "*", "")))) }

pan <- fread(file.path(CLEAN, "panel_sector_banktype.csv")); pan[, date := as.IDate(date)]
shk <- load_shocks()

# Table 1: panel descriptives --------------------------------------------------------
d1 <- pan[bank_type %in% c("ISL", "BUS", "UUS", "CONV") & date >= SAMPLE_START & date <= SAMPLE_END]
t1 <- d1[, .(sectors = uniqueN(sector_h),
             months = uniqueN(date[!is.na(credit_rp_bn)]),
             first = format(min(date[!is.na(credit_rp_bn)]), "%Y-%m"),
             `mean monthly growth (%)` = sprintf("%.2f", 100 * mean(dlog_credit_mom[adj_growth_ok %in% TRUE], na.rm = TRUE)),
             `s.d. monthly growth (%)` = sprintf("%.2f", 100 * sd(dlog_credit_mom[adj_growth_ok %in% TRUE], na.rm = TRUE)),
             `clean changes (% of monthly changes)` = sprintf("%.1f", 100 * mean(adj_growth_ok[!is.na(dlog_credit_mom)] %in% TRUE)),
             `credit, last month (Rp tn)` = sprintf("%.0f", sum(credit_rp_bn[date == max(date[!is.na(credit_rp_bn)])], na.rm = TRUE) / 1000)),
         by = .(panel, bank_type)]
t1[, bank_type := factor(bank_type, levels = c("ISL", "BUS", "UUS", "CONV"))]
setorder(t1, -panel, bank_type)
add("## Table 1. The sector x bank-type credit panel", "",
    "ISL = BUS + UUS (all Islamic financing); CONV = commercial-bank credit minus ISL. Monthly growth is the log change of credit in a sector-month, over changes not flagged as contaminated. Clean changes: share of computable monthly changes that are not flagged (BUS and UUS are reported separately only from 2014-06).", "",
    mdtab(t1))

# Table 2: shocks -------------------------------------------------------------------------
S <- c("jk_mp_median", "jk_mp_pm", "usmpd_stmt", "usmpd_me", "bs_mps_orth", "jk_cbi_median", "bi_rule_resid")
x <- shk[date >= SAMPLE_START & date <= SAMPLE_END, c("date", S), with = FALSE]
t2 <- rbindlist(lapply(S, function(s) data.table(shock = s,
  months = sum(!is.na(x[[s]])), `nonzero months` = sum(x[[s]] != 0, na.rm = TRUE),
  `s.d. (bp)` = sprintf("%.1f", 100 * sd(x[[s]], na.rm = TRUE)),
  `max abs (bp)` = sprintf("%.1f", 100 * max(abs(x[[s]]), na.rm = TRUE)),
  `corr. with JK MP` = sprintf("%.2f", cor(x[[s]], x$jk_mp_median, use = "complete.obs")),
  `corr. with BI shock` = sprintf("%.2f", cor(x[[s]], x$bi_rule_resid, use = "complete.obs")))))
add("## Table 2. Monetary policy shocks, 2009-01 to 2025-06 (monthly sums)", "",
    "JK MP (median): Jarocinski-Karadi pure monetary policy shock, median rotation (primary). JK MP (poor man's): their sign-restriction version. FOMC statement and FOMC monetary event: surprises from the San Francisco Fed's US Monetary Policy Event-Study Database (USMPD). Bauer-Swanson (orth.): surprise orthogonalised to pre-FOMC news, to 2023-12. JK information (CBI): the central-bank-information component. BI policy rule: residual of a monthly Bank Indonesia policy rule (Section 3.2).", "",
    mdtab(t2))

# Table 3: headline differential ----------------------------------------------------------
lp9 <- fread(file.path(TAB, "lp_diff_H9_ISLCONV.csv")); lp15 <- fread(file.path(TAB, "lp_diff_H15_ISLCONV.csv"))
dl <- fread(file.path(TAB, "dl_diff.csv"))
pre9 <- fread(file.path(TAB, "lp_diff_pretrend_H9_ISLCONV.csv")); pre15 <- fread(file.path(TAB, "lp_diff_pretrend_H15_ISLCONV.csv"))
perm9 <- fread(file.path(TAB, "lp_diff_perm_H9_ISLCONV.csv")); perm15 <- fread(file.path(TAB, "lp_diff_perm_H15_ISLCONV.csv"))
jt <- fread(file.path(TAB, "credit_joint_power.csv"))
H <- c(0, 6, 12, 18, 24)
row3 <- function(P, s) {
  lp <- if (P == "H9") lp9 else lp15
  pre <- if (P == "H9") pre9 else pre15
  r1 <- c(list(panel = P, shock = s, estimator = "LP (plan)"),
          setNames(lapply(H, function(hh) { z <- lp[shock == s & h == hh]
            if (z$T < 36) "n.e." else paste0(est(25 * z$b, 25 * z$se), star(z$b, z$se)) }), paste0("h=", H)),
          list(placebo = { z <- pre[shock == s]; if (nrow(z)) paste0(est(25 * z$b_pre, 25 * z$se_pre), star(z$b_pre, z$se_pre)) else "" },
               `months (h=12)` = as.character(lp[shock == s & h == 12, T])))
  z2 <- dl[panel == P & shock == s]
  r2 <- c(list(panel = P, shock = s, estimator = "DL"),
          setNames(lapply(H, function(hh) { z <- z2[h == hh]; paste0(est(z$b25, z$se25), star(z$b, z$se)) }), paste0("h=", H)),
          list(placebo = paste0(est(z2$lead_b25[1], z2$lead_se25[1]), star(z2$lead_b[1], z2$lead_se[1])),
               `months (h=12)` = as.character(z2$T[1])))
  rbindlist(list(r1, r2))
}
t3 <- rbindlist(lapply(c("H9", "H15"), function(P) rbindlist(lapply(c("jk_mp_median", "bi_rule_resid"), function(s) row3(P, s)))))
add("## Table 3. Islamic minus conventional credit to the same sector-month", "",
    "Cumulative differential response, percent, per 25 bp shock; Driscoll-Kraay s.e. in parentheses (LP bandwidth h+2, DL bandwidth 12).",
    "LP (plan): the pre-registered local projection; windows touching a contaminated month are dropped.",
    "DL: distributed lag on clean monthly changes, without Islamic x macro controls (Section 4.3). Placebo: LP, regression of growth over t-4..t-1 (four clean changes) on the shock at t, without own-growth lags; DL, sum of six lead coefficients. * p<0.10, ** p<0.05, *** p<0.01. n.e.: fewer than 36 usable months.",
    "Months (h=12): number of months with at least one usable observation (LP: a clean window [t-1, t+12]; DL: a clean monthly change).", "",
    mdtab(t3))
pm <- rbind(perm9[, panel := "H9"], perm15[, panel := "H15"])
add(paste0("The plan's time-series LP on the cross-sector average differential (Newey-West s.e.) at h = 12, JK MP (median): ",
           paste(sprintf("%s %s", c("H9", "H15"), c(lp9[shock == "jk_mp_median" & h == 12, est(ts_b25, ts_se25)],
                                                    lp15[shock == "jk_mp_median" & h == 12, est(ts_b25, ts_se25)])), collapse = "; "),
           "; block permutation p-values (2,000 draws, blocks of 12 calendar months): ",
           paste(sprintf("%s p = %.3f", pm$panel, pm$p_two), collapse = "; "), "."), "")

# Table 4: all shocks at h = 12, DL and LP, plus permutation joint test and MDE ----------------
t4 <- jt[, .(panel, shock,
             `DL beta_12` = paste0(est(b12_25, se12_25), star(b12_25, se12_25)),
             `perm. p (beta_12, avg. differential)` = sprintf("%.3f", perm_p_b12),
             `perm. p (joint, all 25 lags)` = sprintf("%.3f", perm_p_joint),
             `MDE per 25 bp (5%, 80% power)` = sprintf("%.1f", mde12_25_a05),
             `MDE per 1 s.d.` = sprintf("%.2f", mde12_sd_a05),
             `shock s.d. (bp)` = sprintf("%.1f", shock_sd_bp))]
lpall <- rbind(lp9[h == 12, .(panel = "H9", shock, T, b, se, ts_b25, ts_se25)], lp15[h == 12, .(panel = "H15", shock, T, b, se, ts_b25, ts_se25)])
lpall[, `:=`(LP = ifelse(T < 36, "n.e.", paste0(est(25 * b, 25 * se), star(b, se))),
             TS = paste0(est(ts_b25, ts_se25), star(ts_b25, ts_se25)))]
t4 <- merge(lpall[, .(panel, shock, `LP (plan) beta_12` = LP, `time-series LP (plan, NW)` = TS)], t4, by = c("panel", "shock"), all.y = TRUE)
setnames(t4, "perm. p (beta_12, avg. differential)", "perm. p (DL beta_12, avg. differential)")
setorder(t4, -panel, shock)
add("## Table 4. All shocks at 12 months: estimates, permutation tests and minimum detectable effects", "",
    "Percent per 25 bp shock unless stated. Time-series LP: the plan's LP on the cross-sector average differential with Newey-West s.e. Permutation tests re-assign the shock series in blocks of 12 calendar months (2,000 draws) and re-estimate the DL on the cross-sector average differential; the permutation p-value of the plan's time-series LP is in the note to Table 4. Bauer-Swanson is available to 2023-12 and is estimated for H9 only.",
    "MDE: minimum detectable effect at 5% two-sided size and 80% power, 2.80 x s.e. of the panel DL beta_12. n.e.: fewer than 36 usable months.", "",
    mdtab(t4))

# Table 5: robustness grid -------------------------------------------------------------------
rob <- fread(file.path(TAB, "credit_robustness.csv"))
rob[, v := ifelse(is.na(b), "n.e.", paste0(est(b25, se25), star(b, se)))]
t5 <- dcast(rob[(est == "DL" & h == 12) | (est == "LP" & h == 12)],
            spec ~ panel + shock + est, value.var = "v")
ord <- c("baseline", "no_isl_x_controls", "dl_ctrl_pre", "weighted", "drop_break_years", "drop_pandemic",
         "dl_ctrl_post", "drop_post_conversion", "drop_2013_2015", "dl_ar3")
t5 <- t5[match(ord, spec)]
cn <- c("spec", "H9_jk_mp_median_LP", "H9_jk_mp_median_DL", "H15_jk_mp_median_LP", "H15_jk_mp_median_DL",
        "H9_bi_rule_resid_LP", "H9_bi_rule_resid_DL", "H15_bi_rule_resid_LP", "H15_bi_rule_resid_DL")
t5 <- t5[, cn, with = FALSE]
for (c in cn[-1]) t5[is.na(get(c)), (c) := "n.a."]
add("## Table 5. Robustness of the 12-month differential", "",
    "Percent per 25 bp shock (Driscoll-Kraay s.e.). Baseline: the plan's LP with Islamic x macro controls dated before the shock; the DL without them. The first six rows are pre-specified checks (plan sections 4, 6, 7); the last four were added after seeing the data. Islamic x macro controls in the DL are dated t-25 relative to the outcome month, so that they predate every shock lag, or t-1 (the first draft's specification, post-treatment for shock lags of one month or more). n.e.: fewer than 36 usable months. n.a.: not applicable.", "",
    mdtab(t5))

# Table 6: leave-one-sector-out and leave-one-year-out ranges, later start dates ------------------
lo <- fread(file.path(TAB, "credit_loso.csv"))
t6 <- lo[, .(`LOSO, LP range` = sprintf("%.2f to %.2f", min(lp_b25), max(lp_b25)),
             `LOSO, DL range` = sprintf("%.2f to %.2f", min(dl_b25), max(dl_b25)),
             `LOSO, DL sector moving it most` = sector_out[which.max(abs(dl_b25 - median(dl_b25)))]), by = .(panel, shock)]
sr <- fread(file.path(TAB, "credit_sample_robustness.csv"))
ly <- sr[grepl("^loyo_", sample)][, yr := sub("loyo_", "", sample)]
t6b <- ly[, .(`LOYO, DL range (year left out)` = sprintf("%.2f (%s) to %.2f (%s)", min(dl_b25), yr[which.min(dl_b25)],
                                                       max(dl_b25), yr[which.max(dl_b25)]),
              `LOYO, DL largest abs t (year)` = sprintf("%.2f (%s)", max(abs(dl_b25 / dl_se25)), yr[which.max(abs(dl_b25 / dl_se25))])),
          by = .(panel, shock)]
fs <- function(nm) sr[sample == nm, .(panel, shock, v = paste0(est(dl_b25, dl_se25), star(dl_b25, dl_se25)))]
t6 <- merge(t6, t6b, by = c("panel", "shock"))
t6 <- merge(t6, setnames(fs("from2010"), "v", "DL, outcomes from 2010"), by = c("panel", "shock"), all.x = TRUE)
t6 <- merge(t6, setnames(fs("from2011"), "v", "DL, outcomes from 2011"), by = c("panel", "shock"), all.x = TRUE)
for (c in c("DL, outcomes from 2010", "DL, outcomes from 2011")) t6[is.na(get(c)), (c) := "n.a."]
setorder(t6, -panel, shock)
add("## Table 6. Leave-one-sector-out (LOSO), leave-one-year-out (LOYO) and later start dates, 12-month differential", "",
    "Percent per 25 bp. LOYO drops one calendar year of outcome months at a time. With outcomes from 2011, every DL shock lag is from 2009 or later; the full-sample DL uses shock lags back to 2007. n.a.: H15 starts in 2016-06.", "",
    mdtab(t6))

# Table 7: BUS vs UUS -----------------------------------------------------------------------
bu <- fread(file.path(TAB, "credit_bus_uus.csv"))
bu[, v := ifelse(is.na(b), "n.e.", paste0(est(b25, se25), star(b, se)))]
t7 <- dcast(bu[h %in% c(12, 24) & est == "DL" & shock %in% c("jk_mp_median", "bi_rule_resid")],
            panel + shock + drop + h ~ treat, value.var = "v")
add("## Table 7. Funding channel: BUS and UUS each relative to conventional credit (DL, from 2014-06)", "",
    "Percent per 25 bp. drop = postconv removes the 12 months after each conversion and the 2021-02 merger.", "",
    mdtab(t7))

# Table 8: theta vs beta ------------------------------------------------------------------------
th <- fread(file.path(TAB, "credit_theta.csv"))
t8 <- th[est == "DL" & share_var == "share" & h %in% c(6, 12, 24) & shock %in% c("jk_mp_median", "jk_mp_pm", "bi_rule_resid"),
         .(panel, shock, h, theta = paste0(est(b25, se25, 1), star(b, se)))]
bb <- dl[shock %in% c("jk_mp_median", "jk_mp_pm", "bi_rule_resid") & h %in% c(6, 12, 24), .(panel, shock, h, `beta (composition benchmark)` = est(b25, se25, 1))]
t8 <- merge(t8, bb, by = c("panel", "shock", "h"))
add("## Table 8. Sector exposure: total sector credit on shock x pre-period Islamic share", "",
    "theta_h from dlog Y_{s,t} on eps x Share_s with sector and month FE (DL); share as a fraction, so under no substitution and a sector-invariant differential theta_h = beta_h. Percent per 25 bp.", "",
    mdtab(t8))

# Table 9: macro first stage --------------------------------------------------------------------
mf <- fread(file.path(TAB, "macro_first_stage.csv"))
t9 <- dcast(mf[h %in% c(0, 6, 12, 24) & shock %in% c("jk_mp_median", "usmpd_stmt", "bi_rule_resid") &
                 outcome %in% c("us2y", "bi", "jibor", "lidr", "l_tot")],
            shock + outcome ~ h, value.var = c("b25", "se25"))
t9 <- t9[, .(shock, outcome, `h=0` = paste0(est(b25_0, se25_0), star(b25_0, se25_0)),
             `h=6` = paste0(est(b25_6, se25_6), star(b25_6, se25_6)),
             `h=12` = paste0(est(b25_12, se25_12), star(b25_12, se25_12)),
             `h=24` = paste0(est(b25_24, se25_24), star(b25_24, se25_24)))]
add("## Table 9. Macro-financial responses (time-series LP, NW s.e.)", "",
    "pp (rates) or percent (IDR per USD, credit) per 25 bp shock. BI policy rate: monthly average, adjusted for the 2016 instrument switch. IDR per USD: 100 x log, so + = depreciation.", "",
    mdtab(t9))

# Table 10: NPF ----------------------------------------------------------------------------------
np <- fread(file.path(TAB, "credit_npf.csv"))
t10 <- dcast(np[h %in% c(6, 12, 24)], panel + shock ~ h, value.var = c("b25", "se25"))
t10 <- t10[, .(panel, shock, `h=6` = paste0(est(b25_6, se25_6), star(b25_6, se25_6)),
               `h=12` = paste0(est(b25_12, se25_12), star(b25_12, se25_12)),
               `h=24` = paste0(est(b25_24, se25_24), star(b25_24, se25_24)))]
add("## Table 10. Islamic non-performing financing ratio by sector (pp per 25 bp; LP, sector FE, DK)", "", mdtab(t10))

# Monte Carlo ---------------------------------------------------------------------------------------
f_mc <- file.path(TAB, "montecarlo_summary.csv")
if (file.exists(f_mc)) {
  mc <- fread(f_mc); ws <- fread(file.path(TAB, "montecarlo_wald_size.csv"))
  t11 <- mc[, .(shock, dgp, estimator = est, `bias` = sprintf("%.2f", bias25), `s.d. of estimate` = sprintf("%.2f", sd25),
                `mean s.e.` = sprintf("%.2f", mean_se25), `90% coverage` = sprintf("%.2f", cover90))]
  add("## Table 11. Monte Carlo on the actual H9 design (percent per 25 bp; true beta = -2.4 under 'ramp', 0 under 'null')", "",
      mdtab(t11),
      paste0("DK Wald test of all 25 DL lags under the null, rejection rate at 5%: ",
             paste(sprintf("%s %.3f", ws$shock, ws$dl_wald_reject_05), collapse = "; "), "."), "")
}
# Tables 12-14: mechanisms (module M) ----------------------------------------------------------------
mrob <- fread(file.path(TAB, "mech_robustness_h12.csv"))
mkey <- fread(file.path(TAB, "mech_key_results.csv"))
mpre <- fread(file.path(TAB, "mech_pretrend.csv"))
mpt  <- fread(file.path(TAB, "mech_passthrough.csv"))
msd  <- fread(file.path(TAB, "mech_shock_sd.csv"))
SHL <- c(jk_mp_median = "JK MP (median)", jk_mp_pm = "JK MP (poor man's)", usmpd_stmt = "FOMC statement",
         jk_cbi_median = "JK information (CBI)", bi_rule_resid = "BI policy rule")
cell_k <- function(o, s, e) { z <- mkey[outcome == o & shock == s & estimator == e & h == 12]
  if (!nrow(z) || is.na(z$b25)) "" else paste0(est(z$b25, z$se25), star(z$b25, z$se25)) }
cell_r <- function(o, s, e, v) { z <- mrob[outcome == o & shock == s & estimator == e]
  if (!nrow(z)) return(""); b <- z[[paste0("b25_", v)]]; se <- z[[paste0("se25_", v)]]
  if (is.na(b)) "" else paste0(est(b, se), star(b, se)) }
cell_l <- function(o, s) { z <- mpre[outcome == o & shock == s & test == "dl_sum_6_leads"]
  if (!nrow(z)) "" else sprintf("%s, p=%.2f", est(z$b25, z$se25), z$p) }
cell_sd <- function(o, s) { z <- mkey[outcome == o & shock == s & estimator == "dl" & h == 12]
  if (!nrow(z) || is.na(z$bsd)) "" else est(z$bsd, z$sesd) }
mech_rows <- function(outs, shocks) rbindlist(lapply(names(outs), function(o) rbindlist(lapply(shocks, function(s)
  data.table(outcome = outs[[o]], shock = SHL[[s]], `DL` = cell_k(o, s, "dl"), `LP` = cell_k(o, s, "lp"),
             `DL, from 2010` = cell_r(o, s, "dl", "from_2010"), `DL, from 2014-07` = cell_r(o, s, "dl", "post_2014_07"),
             `DL per s.d.` = cell_sd(o, s), `DL leads (sum of 6)` = cell_l(o, s))))))
t12 <- mech_rows(list(spread_1m = "Islamic (BUS+UUS) minus conventional, 2009+",
                      spread_bus_1m = "BUS minus conventional, 2014-06+",
                      gap_bus_uus_1m = "BUS minus UUS, 2014-06+"), names(SHL))
t12 <- t12[!(outcome != "Islamic (BUS+UUS) minus conventional, 2009+" & shock %in% c("JK information (CBI)"))]
add("## Table 12. Deposit pricing: 1-month deposit-rate spreads at 12 months", "",
    "pp per 25 bp shock (Newey-West s.e.); aggregate monthly series. DL per s.d.: pp per 1 s.d. of the shock (25 bp = 7.1 s.d. for JK MP, 11.2 for the statement surprise, 12.9 for CBI, 2.0 for the BI shock).",
    "From 2010 drops the 2009 outcome months; from 2014-07 uses only the new-format OJK data. For the 2014-06+ series the first three DL columns coincide. Blank: fewer than 40 months. * p<0.10, ** p<0.05, *** p<0.01.", "",
    mdtab(t12))

ptl <- c(dep_conv_1m = "Conventional 1m", dep_isl_1m = "Islamic 1m (BUS+UUS, 2009+)",
         dep_isl_1m_post14 = "Islamic 1m, rupiah, 2014-06+", dep_conv_1m_on_post14 = "Conventional 1m, same months",
         dep_bus_1m = "BUS 1m (2014-06+)", dep_conv_1m_on_bus = "Conventional 1m, same months as BUS",
         dep_uus_1m = "UUS 1m (2014-06+)", dep_conv_1m_on_uus = "Conventional 1m, same months as UUS",
         fin_isl_murabahah = "Islamic murabahah", lend_conv_cons = "Conventional consumption lending",
         lend_conv_wc = "Conventional working-capital lending",
         fin_isl_use_wc = "Islamic working-capital financing (2014-06+)", lend_conv_wc_on_use = "Conventional working capital, same months")
t13 <- dcast(mpt[estimator == "dl" & outcome %in% names(ptl) & shock %in% c("bi_rule_resid", "jk_mp_median", "jk_mp_pm") & h %in% c(6, 12)],
             outcome ~ shock + h, value.var = c("ratio", "se_ratio"))
t13 <- t13[match(names(ptl), outcome)][!is.na(outcome)]
t13 <- t13[, .(rate = ptl[outcome],
               `BI shock, h=6` = est(ratio_bi_rule_resid_6, se_ratio_bi_rule_resid_6),
               `BI shock, h=12` = est(ratio_bi_rule_resid_12, se_ratio_bi_rule_resid_12),
               `JK MP, h=6` = est(ratio_jk_mp_median_6, se_ratio_jk_mp_median_6),
               `JK MP, h=12` = est(ratio_jk_mp_median_12, se_ratio_jk_mp_median_12),
               `JK MP pm, h=12` = est(ratio_jk_mp_pm_12, se_ratio_jk_mp_pm_12))]
add("## Table 13. Pass-through to the BI policy rate (cumulative rate response / cumulative BI-rate response, DL)", "",
    "Both responses estimated on the same months; joint Newey-West covariance; delta-method s.e. 'Same months' rows restrict the conventional rate to the clean months of the Islamic series above them.", "",
    mdtab(t13))

t14 <- mech_rows(list(fspread_isl_murabahah_wc = "Murabahah minus conventional working-capital rate (pp)",
                      fspread_isl_murabahah_cons = "Murabahah minus conventional consumption rate (pp)",
                      fspread_use_wc = "Islamic minus conventional working-capital rate, 2014-06+ (pp)",
                      dpk_diff_total = "Islamic minus conventional deposit growth (%)",
                      fdr_isl = "Islamic financing-to-deposit ratio (pp)",
                      npf_isl = "Islamic NPF ratio (pp)"), c("jk_mp_median", "jk_mp_pm", "bi_rule_resid"))
mde <- mkey[outcome == "dpk_diff_total" & estimator == "dl" & h == 12, .(shock, mde25)]
add("## Table 14. Financing rates, deposit flows, financing-to-deposit ratio (FDR) and NPF at 12 months", "",
    "Units per row; per 25 bp shock (Newey-West s.e.). Columns as in Table 13. Blank: not estimated or fewer than 40 months.",
    paste0("MDE of the deposit-growth differential at 12 months (DL, 5% size, 80% power), percent per 25 bp: ",
           paste(sprintf("%s %.1f", SHL[mde$shock], mde$mde25), collapse = "; "), "."), "",
    mdtab(t14))

# Table 15: sovereign investor base (module S) --------------------------------------------------------
sh <- fread(file.path(TAB, "sov_headline.csv"))
skn <- fread(file.path(TAB, "sov_key_nonres.csv"))
spt <- fread(file.path(TAB, "sov_daily_pretrend.csv"))
outs15 <- list(c("SUN", "pct", "Non-resident SUN, pp of SUN outstanding"), c("SBSN", "pct", "Non-resident SBSN, pp of SBSN outstanding"),
               c("SBSN_minus_SUN", "pct", "SBSN minus SUN, pp of outstanding"), c("SBSN_minus_SUN", "log", "SBSN minus SUN, log change (%)"))
pc <- function(z) if (!nrow(z) || is.na(z$bsd)) "" else paste0(est(z$bsd, z$sesd, 3), star(z$bsd, z$sesd))
t15 <- rbindlist(lapply(outs15, function(o) {
  z <- sh[spec == "allday_settle" & instrument == o[1] & scaling == o[2]]
  data.table(outcome = o[3], `h=0` = pc(z[h == 0]), `h=2` = pc(z[h == 2]), `h=5` = pc(z[h == 5]),
             `h=10` = pc(z[h == 10]), `h=20` = pc(z[h == 20]),
             `MDE, h=5` = sprintf("%.3f", z[h == 5, mdesd]),
             `p perm., h=5` = sprintf("%.3f", z[h == 5, p_perm]))
}))
add("## Table 15. Non-resident holdings of government bonds after a US pure monetary policy surprise", "",
    "Per 1 s.d. JK MP surprise (3.7 bp; 25 bp = 6.8 s.d.). Daily all-trading-day LP, 2015-12-31 to 2022-06-27, 58 event days; 5 lags of the outcome's daily change and settlement-day counts; Newey-West s.e. (lag h+5). Day 0 = first Jakarta trading day after the announcement.", "",
    mdtab(t15))
SPL <- c(allday_settle = "Primary", events_hc1 = "Events only, HC1 (chosen before results; not in the plan)", allday_fixedsample_settle = "Fixed event sample",
         allday_drop0303_settle = "Drop 2020-03-03", allday_t2aligned_settle = "Measured from day +1 (T+2)",
         allday_exCOVID_settle = "Excluding Mar-Apr 2020")
t15b <- rbindlist(lapply(names(SPL), function(sp) {
  g <- function(i, sc, hh) pc(skn[shock == "jk_mp_median" & spec == sp & instrument == i & scaling == sc & h == hh])
  pre_spec <- c(allday_settle = "pre_window_m6_m1_settle", allday_exCOVID_settle = "pre_window_m6_m1_settle_exCOVID",
                allday_drop0303_settle = "pre_window_m6_m1_settle_drop0303",
                allday_fixedsample_settle = "pre_window_m6_m1_settle_fixedsample")[sp]
  pz <- if (is.na(pre_spec)) data.table() else spt[shock == "jk_mp_median" & spec == pre_spec & outcome == "nonresidents|SUN|pct"]
  data.table(specification = SPL[[sp]], `SUN, h=5` = g("SUN", "pct", 5), `SUN, h=20` = g("SUN", "pct", 20),
             `SBSN-SUN pp, h=5` = g("SBSN_minus_SUN", "pct", 5), `SBSN-SUN log, h=5` = g("SBSN_minus_SUN", "log", 5),
             `SUN placebo [-6,-1]` = if (nrow(pz)) paste0(est(pz$bsd, pz$sesd, 3), star(pz$bsd, pz$sesd)) else "")
}))
add("Robustness, per 1 s.d. (placebo: change over days -6 to -1 on the event shock):", "", mdtab(t15b))
# readable labels in the rendered tables (codes stay in the CSVs) -----------------------------------
relabel <- function(md) {
  SL <- c(jk_mp_median = "JK MP (median)", jk_mp_pm = "JK MP (poor man's)", usmpd_stmt = "FOMC statement",
          usmpd_me = "FOMC monetary event", bs_mps_orth = "Bauer-Swanson (orth.)",
          jk_cbi_median = "JK information (CBI)", bi_rule_resid = "BI policy rule")
  for (k in names(SL)) {
    for (P in c("H9", "H15")) for (e in c("LP", "DL"))
      md <- gsub(paste0(P, "_", k, "_", e), paste0(P, ", ", SL[[k]], ", ", e), md, fixed = TRUE)
    md <- gsub(paste0("| ", k, " |"), paste0("| ", SL[[k]], " |"), md, fixed = TRUE)
  }
  OL <- c(bi = "BI policy rate", jibor = "JIBOR 1M", l_tot = "Commercial-bank credit", lidr = "IDR per USD",
          us2y = "US 2-year yield")
  for (k in names(OL)) md <- gsub(paste0("| ", k, " |"), paste0("| ", OL[[k]], " |"), md, fixed = TRUE)
  SC <- c(H9_MIN = "mining", H9_TRN = "transport", H15_MIN = "mining", H15_TRN = "transport")
  for (k in names(SC)) md <- gsub(paste0("| ", k, " |"), paste0("| ", SC[[k]], " |"), md, fixed = TRUE)
  md <- gsub("| panel | bank_type |", "| panel | lender |", md, fixed = TRUE)
  md <- gsub("| h | bus | uus |", "| h | BUS | UUS |", md, fixed = TRUE)
  md <- gsub("| postconv |", "| post-conversion months dropped |", md, fixed = TRUE)
  md <- gsub("| spec |", "| specification |", md, fixed = TRUE)
  SP <- c(baseline = "Baseline", no_isl_x_controls = "No Islamic x macro controls", weighted = "Weighted by Islamic credit",
          drop_break_years = "Drop 2014, 2016-17, 2021", drop_pandemic = "Drop 2020-03 to 2021-12",
          drop_post_conversion = "Drop 12 months after conversions and merger", drop_2013_2015 = "Drop 2013-2015",
          dl_ar3 = "DL with 3 own lags", dl_ctrl_pre = "DL with Islamic x macro controls dated t-25",
          dl_ctrl_post = "DL with Islamic x macro controls dated t-1 (first draft)")
  for (k in names(SP)) md <- gsub(paste0("| ", k, " |"), paste0("| ", SP[[k]], " |"), md, fixed = TRUE)
  md
}
md <- relabel(md)
# number the tables in the order the paper first cites them (old number -> new number)
renumber <- function(md) {
  NEWNO <- c(`1` = 1, `2` = 2, `3` = 4, `4` = 5, `5` = 6, `6` = 10, `7` = 7, `8` = 8, `9` = 3, `10` = 9,
             `11` = 11, `12` = 13, `13` = 12, `14` = 14, `15` = 15)
  start <- grep("^## Table [0-9]+\\.", md)
  blocks <- lapply(seq_along(start), function(i) md[start[i]:(if (i < length(start)) start[i + 1] - 1 else length(md))])
  old <- as.integer(sub("^## Table ([0-9]+)\\..*", "\\1", md[start]))
  new <- NEWNO[as.character(old)]
  blocks <- Map(function(b, n) { b[1] <- sub("^## Table [0-9]+\\.", paste0("## Table ", n, "."), b[1]); b }, blocks, new)
  unlist(blocks[order(new)])
}
md <- renumber(md)
writeLines(md, file.path(TAB, "paper_tables.md"))
cat("wrote output/tables/paper_tables.md\n")
