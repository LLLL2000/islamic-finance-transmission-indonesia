# 10_lp_differential.R ------------------------------------------------------
# Primary estimand (pre-analysis plan, section 4): the differential response of
# Islamic vs conventional credit to the SAME sector in the SAME month.
#
#   dh_{s,b,t} = beta_h (eps_t x ISL_b) + a_{s,t} + a_{s,b}
#                + sum_l gamma_l dy_{s,b,t-l} + ISL_b x X_{t-1}' delta + u
#
# Inference: Driscoll-Kraay (bandwidth h+2); a time-series LP on the
# cross-sector average differential with Newey-West errors; block permutation.
source("C:/Users/consu/Documents/Universidad/Islamic_Finance_Project/wp_dual_banking/code/R/00_common.R")

args <- commandArgs(trailingOnly = TRUE)
PANEL  <- if (length(args) >= 1) args[1] else "H9"
SHOCKS <- if (length(args) >= 2) strsplit(args[2], ",")[[1]] else
  c("jk_mp_median", "jk_mp_pm", "usmpd_stmt", "usmpd_me", "bs_mps_orth", "jk_cbi_median")
TYPES  <- if (length(args) >= 3) strsplit(args[3], ",")[[1]] else c("ISL", "CONV")
TAG    <- if (length(args) >= 4) args[4] else ""
NPERM  <- 2000L

pan <- fread(file.path(CLEAN, "panel_sector_banktype.csv"))
pan[, date := as.IDate(date)]
pan <- pan[panel == PANEL & bank_type %in% TYPES & date >= SAMPLE_START & date <= SAMPLE_END]
pan[, m := mid(date)]
pan[, unit := paste(sector_h, bank_type, sep = "|")]
pan[, y := log(credit_rp_bn)]
pan[credit_rp_bn <= 0, y := NA_real_]
pan[, ok := as.logical(adj_growth_ok)]
pan[, isl := as.integer(bank_type != "CONV")]
pan <- pan[, .(unit, sector_h, bank_type, isl, m, date, y, ok)]

shk <- load_shocks()
mac <- load_macro()
mac_l <- copy(mac)[, m := m + 1L]               # X_{t-1} aligned to t
setnames(mac_l, CONTROLS, paste0(CONTROLS, "_l1"))
CL <- paste0(CONTROLS, "_l1")

cat(sprintf("panel %s | types %s | units %d | sectors %d | months %d (%s .. %s)\n",
            PANEL, paste(TYPES, collapse = "/"), uniqueN(pan$unit), uniqueN(pan$sector_h),
            uniqueN(pan$m), min(pan$date), max(pan$date)))

run_one <- function(shock, h) {
  f <- lp_frame(pan, h)
  f <- merge(f, shk[, c("m", shock), with = FALSE], by = "m")
  setnames(f, shock, "eps")
  f <- merge(f, mac_l[, c("m", CL), with = FALSE], by = "m")
  f[, sx := eps * isl]
  for (c in CL) f[, paste0("isl_", c) := isl * get(c)]
  f[, uid := as.integer(factor(unit))]
  rhs <- paste(c("sx", paste0("isl_", CL), "lag1", "lag2", "lag3"), collapse = " + ")
  fml <- as.formula(paste("dh ~", rhs, "| sector_h^m + sector_h^bank_type"))
  est <- tryCatch(feols(fml, data = f, panel.id = ~uid + m, vcov = DK(h + 2L), warn = FALSE, notes = FALSE),
                  error = function(e) NULL)
  pre <- NULL
  if (h == 0L) {
    # placebo (plan section 6): growth over [t-4, t-1] on eps_t, without the own-growth lags (see lp_frame)
    rhs_pre <- paste(c("sx", paste0("isl_", CL)), collapse = " + ")
    fpre <- as.formula(paste("dpre ~", rhs_pre, "| sector_h^m + sector_h^bank_type"))
    pre <- tryCatch(feols(fpre, data = f, panel.id = ~uid + m, vcov = DK(6L), warn = FALSE, notes = FALSE),
                    error = function(e) NULL)
  }

  # time-series version: average ISL-CONV differential across sectors
  w <- dcast(f[!is.na(dh)], sector_h + m ~ bank_type, value.var = "dh")
  isl_col <- setdiff(TYPES, "CONV")
  ts <- NULL
  if (length(isl_col) == 1L && all(c(isl_col, "CONV") %in% names(w))) {
    w[, d := get(isl_col) - CONV]
    D <- w[!is.na(d), .(D = mean(d), ns = .N), by = m]
    D <- merge(D, shk[, c("m", shock), with = FALSE], by = "m")
    D <- merge(D, mac_l[, c("m", CL), with = FALSE], by = "m")
    D <- D[complete.cases(D)]
    setorder(D, m)
    X <- as.matrix(D[, c(shock, CL), with = FALSE])
    nw <- nw_lp(D$D, X, lag = h + 1L)
    ts <- list(b = unname(nw$coef[2]), se = unname(nw$se[2]), n = nw$n, D = D)
  }
  list(est = est, pre = pre, ts = ts, n = if (!is.null(est)) nobs(est) else NA_integer_,
       T = if (!is.null(est)) uniqueN(f$m[obs(est)]) else NA_integer_)
}

res <- list(); perm <- list(); pretab <- list()
for (s in SHOCKS) {
  if (!s %in% names(shk)) { cat("  skip (no shock):", s, "\n"); next }
  sd_s <- sd(shk[date >= SAMPLE_START & date <= SAMPLE_END, get(s)], na.rm = TRUE)
  for (h in 0:H_MAX) {
    r <- run_one(s, h)
    b  <- if (!is.null(r$est)) coef(r$est)["sx"] else NA
    se <- if (!is.null(r$est)) se(r$est)["sx"] else NA
    res[[length(res) + 1L]] <- data.table(
      panel = PANEL, types = paste(TYPES, collapse = "/"), shock = s, h = h,
      b = b, se = se, n = r$n, T = r$T,
      ts_b = if (!is.null(r$ts)) r$ts$b else NA, ts_se = if (!is.null(r$ts)) r$ts$se else NA,
      ts_n = if (!is.null(r$ts)) r$ts$n else NA, shock_sd = sd_s)
    if (h == 0L && !is.null(r$pre))
      pretab[[s]] <- data.table(shock = s, b_pre = coef(r$pre)["sx"], se_pre = se(r$pre)["sx"],
                                n_pre = nobs(r$pre))
    # block permutation for the pre-registered horizon, primary shock only
    if (h == 12L && s == SHOCKS[1] && !is.null(r$ts)) {
      set.seed(20261029)
      D <- r$ts$D; Xc <- as.matrix(D[, CL, with = FALSE])
      bobs <- r$ts$b
      # permute the shock in blocks of 12 calendar months over the full month grid, then keep the
      # months in D (D holds only months with a clean window, so it has gaps)
      mm <- seq(min(D$m), max(D$m)); ev <- shk[match(mm, shk$m), get(s)]
      bp <- replicate(NPERM, {
        ep <- ev[block_perm(ev, 12L)][match(D$m, mm)]
        coef(lm(D$D ~ ep + Xc))[2]
      })
      perm[[s]] <- data.table(shock = s, h = 12L, b_obs = bobs,
                              p_two = mean(abs(bp) >= abs(bobs)), n_perm = NPERM)
    }
  }
  cat(sprintf("  done %s\n", s))
}
res <- rbindlist(res)
# report units: per 25 bp surprise (pre-registered) and per 1 s.d.; outcomes in percent (x100)
res[, `:=`(b25 = 100 * b * SCALE_BP / 100, se25 = 100 * se * SCALE_BP / 100,
           bsd = 100 * b * shock_sd,       sesd = 100 * se * shock_sd,
           ts_b25 = 100 * ts_b * SCALE_BP / 100, ts_se25 = 100 * ts_se * SCALE_BP / 100)]

tag <- paste0(PANEL, "_", paste(TYPES, collapse = ""), TAG)
fwrite(res, file.path(OUT, "tables", sprintf("lp_diff_%s.csv", tag)))
if (length(perm))   fwrite(rbindlist(perm),   file.path(OUT, "tables", sprintf("lp_diff_perm_%s.csv", tag)))
if (length(pretab)) fwrite(rbindlist(pretab), file.path(OUT, "tables", sprintf("lp_diff_pretrend_%s.csv", tag)))

cat("\n=== differential response, per 25 bp surprise, percent (DK s.e.) ===\n")
print(res[h %in% c(0, 3, 6, 12, 18, 24),
          .(shock, h, b25 = fmt(b25), se25 = fmt(se25), t = fmt(b / se, 2), n,
            ts_b25 = fmt(ts_b25), ts_se25 = fmt(ts_se25))])
if (length(perm))   { cat("\n=== block permutation, h = 12 ===\n"); print(rbindlist(perm)) }
if (length(pretab)) { cat("\n=== pre-trend (growth over t-4..t-1 on eps_t) ===\n"); print(rbindlist(pretab)) }
