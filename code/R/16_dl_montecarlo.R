# 16_dl_montecarlo.R --------------------------------------------------------
# Monte Carlo check of the two estimators on the ACTUAL H9 design: the real units, months,
# contamination pattern and shock series (jk_mp_median, bi_rule_resid). Simulated outcomes:
#   dy_{s,b,t} = a_{s,t} + ISL_b sum_k phi_k eps_{t-k} + u_{s,b,t},  u AR(1), rho = 0.3,
# with innovation s.d. by bank type matched to the data's within-sector-month residual s.d.
# Reports bias, s.e. calibration and 90% coverage of beta_12 and beta_24 for the plan's LP
# (DK, h+2) and the DL (DK, 12), and the size of the DK Wald test of all 25 DL lags under
# the null (phi = 0).
source("C:/Users/consu/Documents/Universidad/Islamic_Finance_Project/wp_dual_banking/code/R/00_common.R")
set.seed(20261030)
R <- 300L
pan <- fread(file.path(CLEAN, "panel_sector_banktype.csv")); pan[, date := as.IDate(date)]
p0 <- pan[panel == "H9" & bank_type %in% c("ISL", "CONV") & date >= SAMPLE_START & date <= SAMPLE_END]
p0[, m := mid(date)][, unit := paste(sector_h, bank_type, sep = "|")][, uid := as.integer(factor(unit))]
p0[, isl := as.integer(bank_type == "ISL")][, ok := adj_growth_ok %in% TRUE & !is.na(credit_rp_bn)]
setkey(p0, uid, m)
# residual s.d. by type: dy net of sector-month means is ISL-CONV split; use within-unit s.d. of clean dy
sdu <- p0[ok == TRUE & !is.na(dlog_credit_mom), .(s = sd(dlog_credit_mom)), by = bank_type]
cat("innovation s.d. by type (monthly log change):\n"); print(sdu)
shk <- load_shocks()
mm <- sort(unique(p0$m)); nM <- length(mm)

simulate <- function(shock, phi) {
  e <- shk[J(seq(min(mm) - 24L, max(mm))), on = "m", get(shock)]
  e[is.na(e)] <- 0
  em <- seq(min(mm) - 24L, max(mm))
  q <- copy(p0)
  # differential path: sum_k phi_k eps_{t-k}
  drive <- sapply(mm, function(t) sum(phi * e[match(t - 0:24, em)]))
  q[, drv := drive[match(m, mm)]]
  q[, a := rnorm(1, 0, 0.01), by = .(sector_h, m)]
  q[, s_u := sdu$s[match(bank_type, sdu$bank_type)]]
  q[, u := { x <- numeric(.N); z <- rnorm(.N, 0, s_u[1]); x[1] <- z[1]; for (i in 2:.N) x[i] <- 0.3 * x[i - 1] + z[i]; x }, by = uid]
  q[, dy_sim := a + isl * drv + u]
  q[, y := cumsum(dy_sim), by = uid]          # simulated log level
  q[ok %in% FALSE, dy_sim := NA_real_]                   # same contamination pattern as the data
  q
}
mac <- load_macro(); mac_l <- copy(mac)[, m := m + 1L]
setnames(mac_l, CONTROLS, paste0(CONTROLS, "_l1")); CL <- paste0(CONTROLS, "_l1")

fit_lp <- function(q, shock, h) {
  f <- lp_frame(q[, .(unit, uid, sector_h, bank_type, isl, m, y, ok)], h)
  f <- merge(f, shk[, c("m", shock), with = FALSE], by = "m"); setnames(f, shock, "eps")
  f[, sx := eps * isl]
  est <- feols(dh ~ sx + lag1 + lag2 + lag3 | sector_h^m + sector_h^bank_type, data = f,
               panel.id = ~uid + m, vcov = DK(h + 2L), warn = FALSE, notes = FALSE)
  c(b = unname(coef(est)["sx"]), se = unname(se(est)["sx"]))
}
fit_dl <- function(q, shock) {
  d <- q[!is.na(dy_sim), .(m, uid, sector_h, bank_type, isl, dy = dy_sim)]
  r <- dl_irf(d, shk, shock, treat = "isl", K = 24L, fe = "sector_h^m + uid", L = 12L)
  est <- attr(r, "est")
  W <- wald(est, keep = "^isl_x_e_l", print = FALSE)
  list(b12 = r[h == 12, b], se12 = r[h == 12, se], b24 = r[h == 24, b], se24 = r[h == 24, se], wald_p = W$p)
}

PHI <- list(null = rep(0, 25), ramp = c(rep(-0.008, 12), rep(0, 13)))   # true beta_12 = beta_24 = -0.096 per pp
f_draws <- file.path(OUT, "tables", "montecarlo_draws.csv")
FORCE <- "--force" %in% commandArgs(trailingOnly = TRUE)
out <- list()
if (file.exists(f_draws) && !FORCE) {   # reuse saved draws; rerun with --force
  out <- list(fread(f_draws))
} else for (s in c("jk_mp_median", "bi_rule_resid")) for (nm in names(PHI)) {
  phi <- PHI[[nm]]; tb12 <- sum(phi[1:13]); tb24 <- sum(phi)
  for (r in seq_len(R)) {
    q <- simulate(s, phi)
    l12 <- fit_lp(q, s, 12L); l24 <- fit_lp(q, s, 24L); d <- fit_dl(q, s)
    out[[length(out) + 1L]] <- data.table(shock = s, dgp = nm, rep = r, true12 = tb12, true24 = tb24,
      lp12 = l12["b"], lp12_se = l12["se"], lp24 = l24["b"], lp24_se = l24["se"],
      dl12 = d$b12, dl12_se = d$se12, dl24 = d$b24, dl24_se = d$se24, dl_wald_p = d$wald_p)
  }
  cat("  done", s, nm, "\n")
}
out <- rbindlist(out)
fwrite(out, f_draws)
summ <- out[, {
  f <- function(b, se, tr) list(bias = mean(b) - tr, sd = sd(b), mean_se = mean(se),
                                cover90 = mean(abs(b - tr) <= 1.645 * se))
  rbind(data.table(est = "LP h=12", as.data.table(f(lp12, lp12_se, true12[1]))),
        data.table(est = "LP h=24", as.data.table(f(lp24, lp24_se, true24[1]))),
        data.table(est = "DL h=12", as.data.table(f(dl12, dl12_se, true12[1]))),
        data.table(est = "DL h=24", as.data.table(f(dl24, dl24_se, true24[1]))))
}, by = .(shock, dgp)]
# report per 25 bp in percent
summ[, `:=`(bias25 = 25 * bias, sd25 = 25 * sd, mean_se25 = 25 * mean_se)]
wald_size <- out[dgp == "null", .(dl_wald_reject_05 = mean(dl_wald_p < 0.05), dl_wald_reject_10 = mean(dl_wald_p < 0.10)), by = shock]
fwrite(summ, file.path(OUT, "tables", "montecarlo_summary.csv"))
fwrite(wald_size, file.path(OUT, "tables", "montecarlo_wald_size.csv"))
cat("\n=== Monte Carlo (", R, "draws ): percent per 25 bp; true beta = -2.4 under 'ramp' ===\n")
print(summ[, .(shock, dgp, est, bias25 = fmt(bias25, 2), sd25 = fmt(sd25, 2), mean_se25 = fmt(mean_se25, 2),
               cover90 = fmt(cover90, 2))])
cat("\nDK Wald test of all 25 DL lags under the null: rejection rates\n"); print(wald_size)
