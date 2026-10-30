# 12_dl_differential.R ------------------------------------------------------
# Distributed-lag version of the primary estimand (deviation from the pre-analysis plan;
# see dl_irf in 00_common.R for why). Same identifying comparison as 10_lp_differential.R:
# Islamic vs conventional credit to the same sector in the same month, sector x month FE.
#
#   dy_{s,b,t} = sum_{k=0..24} phi_k (eps_{t-k} x ISL_b) + sum_{j=1..6} psi_j (eps_{t+j} x ISL_b)
#                + a_{s,t} + a_{s,b} + u
#   beta_h = sum_{k<=h} phi_k ;  sum_j psi_j is the lead placebo
#
# No ISL x X controls in the baseline: X dated t-1 relative to the OUTCOME month is post-treatment for
# every shock lag k >= 1 (the BI rate, the rupiah and the VIX respond to the shock), so it would net out
# part of the effect. With exogenous shocks the controls are not needed for consistency. Variants with
# the controls (dated t-1, and dated t-25 so that they predate every shock lag) are in 15_credit_secondary.R.
#
# Also: the same DL on the cross-sector average differential (NW), and level responses
# by bank type (no time FE; sector FE only), the "first stage" of section 5.1.
source("C:/Users/consu/Documents/Universidad/Islamic_Finance_Project/wp_dual_banking/code/R/00_common.R")

args <- commandArgs(trailingOnly = TRUE)
PANELS <- if (length(args) >= 1) strsplit(args[1], ",")[[1]] else c("H9", "H15")
SHOCKS <- if (length(args) >= 2) strsplit(args[2], ",")[[1]] else
  c("jk_mp_median", "jk_mp_pm", "usmpd_stmt", "usmpd_me", "bs_mps_orth", "jk_cbi_median", "bi_rule_resid")
K <- 24L; LEADS <- 6L

pan0 <- fread(file.path(CLEAN, "panel_sector_banktype.csv"))
pan0[, date := as.IDate(date)]
shk <- load_shocks()
mac <- load_macro()
mac_l <- copy(mac)[, m := m + 1L]
setnames(mac_l, CONTROLS, paste0(CONTROLS, "_l1"))
CL <- paste0(CONTROLS, "_l1")

clean_dy <- function(p) {
  p[, m := mid(date)]
  p[, dy := fifelse(adj_growth_ok %in% TRUE & !is.na(dlog_credit_mom), dlog_credit_mom, NA_real_)]
  p
}

diff_rows <- list(); lev_rows <- list(); ts_rows <- list()
for (P in PANELS) {
  p <- clean_dy(pan0[panel == P & bank_type %in% c("ISL", "CONV") &
                       date >= SAMPLE_START & date <= SAMPLE_END])
  p[, isl := as.integer(bank_type == "ISL")]
  p[, unit := paste(sector_h, bank_type, sep = "|")][, uid := as.integer(factor(unit))]
  p <- merge(p, mac_l[, c("m", CL), with = FALSE], by = "m")
  for (c in CL) p[, paste0("isl_", c) := isl * get(c)]
  p <- p[!is.na(dy)]
  # cross-sector average differential, months where both types are clean in a sector
  w <- dcast(p, sector_h + m ~ bank_type, value.var = "dy")
  D <- w[!is.na(ISL) & !is.na(CONV), .(y = mean(ISL - CONV), ns = .N), by = m]
  D <- merge(D, mac_l[, c("m", CL), with = FALSE], by = "m")
  for (s in SHOCKS) {
    if (!s %in% names(shk)) next
    # Bauer-Swanson ends 2023-12 and drops the 2020 meetings: with 31 lag/lead terms the H15
    # window (2016-06+) leaves too few months, so it is reported for H9 only
    if (P == "H15" && s == "bs_mps_orth") next
    sd_s <- sd(shk[date >= SAMPLE_START & date <= SAMPLE_END, get(s)], na.rm = TRUE)
    # IRF from the DL without leads; the lead placebo is a separate regression with 6 leads added
    r  <- dl_irf(p, shk, s, treat = "isl", K = K, fe = "sector_h^m + uid", L = 12L, leads = 0L)
    rl <- dl_irf(p, shk, s, treat = "isl", K = K, fe = "sector_h^m + uid", L = 12L, leads = LEADS)
    r[, `:=`(lead_b = rl$lead_b[1], lead_se = rl$lead_se[1])]
    diff_rows[[length(diff_rows) + 1L]] <- r[, `:=`(panel = P, shock = s, shock_sd = sd_s)]
    tsr <- dl_ts(D, shk, s, K = K, L = 12L)
    ts_rows[[length(ts_rows) + 1L]] <- tsr[, `:=`(panel = P, shock = s, shock_sd = sd_s)]
    for (bt in c("ISL", "CONV")) {
      q <- p[bank_type == bt]
      lr <- dl_irf(q, shk, s, treat = "one", K = K, fe = "uid", L = 12L, leads = 0L)
      lev_rows[[length(lev_rows) + 1L]] <- lr[, `:=`(panel = P, shock = s, bank_type = bt, shock_sd = sd_s)]
    }
    cat(sprintf("  %s %s done\n", P, s))
  }
}
sc <- function(x) { x[, `:=`(b25 = 25 * b, se25 = 25 * se, bsd = 100 * b * shock_sd, sesd = 100 * se * shock_sd)]
  if ("lead_b" %in% names(x)) x[, `:=`(lead_b25 = 25 * lead_b, lead_se25 = 25 * lead_se)]; x }
diff <- sc(rbindlist(diff_rows)); lev <- sc(rbindlist(lev_rows)); tsd <- sc(rbindlist(ts_rows))
fwrite(diff, file.path(OUT, "tables", "dl_diff.csv"))
fwrite(lev,  file.path(OUT, "tables", "dl_levels.csv"))
fwrite(tsd,  file.path(OUT, "tables", "dl_diff_ts.csv"))

H <- c(0, 3, 6, 12, 18, 24)
cat("\n=== DL differential ISL - CONV, percent per 25 bp (DK(12)); lead placebo = sum of 6 leads ===\n")
x <- merge(diff[h %in% H, .(panel, shock, h, b25, se25, n, T, lead_b25, lead_se25)],
           tsd[h %in% H, .(panel, shock, h, ts_b25 = b25, ts_se25 = se25)], by = c("panel", "shock", "h"))
print(x[, .(panel, shock, h, b25 = fmt(b25, 2), se25 = fmt(se25, 2), t = fmt(b25 / se25, 2),
            ts_b25 = fmt(ts_b25, 2), ts_se25 = fmt(ts_se25, 2), n, T,
            lead = fmt(lead_b25, 2), lead_se = fmt(lead_se25, 2))], nrows = 200)
cat("\n=== DL levels by bank type, percent per 25 bp (DK(12)) ===\n")
print(dcast(lev[h %in% H], panel + shock + h ~ bank_type, value.var = c("b25", "se25"))[
  , lapply(.SD, function(v) if (is.numeric(v)) round(v, 2) else v)], nrows = 200)
