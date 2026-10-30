# 15_credit_secondary.R -----------------------------------------------------
# Secondary estimands and pre-specified checks on the sector x bank-type credit panel
# (pre-analysis plan sections 5.1-5.3, 5.5, 6 and 7), for the plan's LP and for the
# distributed-lag (DL) deviation.
#   A. robustness grid for beta_12 (and DL beta_12, beta_24): plan checks + extra checks
#   B. leave-one-sector-out
#   C. funding channel: BUS vs UUS (from 2014-06)
#   D. sector exposure theta_h on TOTAL sector credit vs the composition benchmark beta_h
#   E. Islamic NPF ratio by sector
#   F. joint Wald test of all DL lag coefficients; power / minimum detectable effects
source("C:/Users/consu/Documents/Universidad/Islamic_Finance_Project/wp_dual_banking/code/R/00_common.R")

pan0 <- fread(file.path(CLEAN, "panel_sector_banktype.csv")); pan0[, date := as.IDate(date)]
shr0 <- fread(file.path(CLEAN, "sector_islamic_share.csv")); shr0[, date := as.IDate(date)]
shk  <- load_shocks()
mac  <- load_macro()
mac_l <- copy(mac)[, m := m + 1L]
setnames(mac_l, CONTROLS, paste0(CONTROLS, "_l1"))
CL <- paste0(CONTROLS, "_l1")
# DL controls dated t-25: predetermined for every shock lag k = 0..24 (robustness only; the DL baseline has
# no ISL x X controls, because X_{t-1} dated relative to the outcome month is post-treatment for k >= 1)
mac_p <- copy(mac)[, m := m + 25L]
setnames(mac_p, CONTROLS, paste0(CONTROLS, "_l25"))
CLp <- paste0(CONTROLS, "_l25")
SH_MAIN <- c("jk_mp_median", "bi_rule_resid")
MIN_T   <- 36L   # minimum effective months for a DK-based LP estimate

months_in <- function(a, b) seq(mid(a), mid(b))
DROPS <- list(
  none      = integer(0),
  breakyrs  = c(months_in("2014-01-01", "2014-12-01"), months_in("2016-01-01", "2017-12-01"),
                months_in("2021-01-01", "2021-12-01")),                       # plan section 6
  pandemic  = months_in("2020-03-01", "2021-12-01"),                          # plan section 6
  postconv  = c(months_in("2016-09-01", "2017-08-01"), months_in("2018-09-01", "2019-08-01"),
                months_in("2021-02-01", "2022-01-01"), months_in("2022-08-01", "2023-07-01")),  # extra
  y2013_15  = months_in("2013-01-01", "2015-12-01")                           # extra
)

# panel prep ------------------------------------------------------------------
prep <- function(P, types, start = SAMPLE_START) {
  p <- pan0[panel == P & bank_type %in% types & date >= start & date <= SAMPLE_END]
  p[, m := mid(date)]
  p[, unit := paste(sector_h, bank_type, sep = "|")][, uid := as.integer(factor(unit))]
  p[, y := fifelse(credit_rp_bn > 0, log(credit_rp_bn), NA_real_)]
  p[, ok := adj_growth_ok %in% TRUE]
  p[, isl := as.integer(bank_type %in% c("ISL", "BUS", "UUS"))]
  p[, bus := as.integer(bank_type == "BUS")][, uus := as.integer(bank_type == "UUS")]
  # weight: the sector's average Islamic credit over the sample (plan section 4)
  wts <- pan0[panel == P & bank_type == "ISL" & date >= start & date <= SAMPLE_END,
              .(w = mean(credit_rp_bn, na.rm = TRUE)), by = sector_h]
  p <- merge(p, wts, by = "sector_h")
  p[, .(unit, uid, sector_h, bank_type, isl, bus, uus, m, date, y, ok, w)]
}

# plan LP for one horizon, with options -----------------------------------------
lp_one <- function(p, shock, h, treat = "isl", controls = TRUE, drop = integer(0),
                   weights = FALSE, sector_out = NULL) {
  q <- copy(p)
  if (length(drop)) q[m %in% drop, ok := FALSE]
  if (!is.null(sector_out)) q <- q[sector_h != sector_out]
  f <- lp_frame(q, h)
  f <- merge(f, shk[, c("m", shock), with = FALSE], by = "m"); setnames(f, shock, "eps")
  f <- merge(f, mac_l[, c("m", CL), with = FALSE], by = "m")
  rhs <- character(0)
  for (tr in treat) {
    f[, paste0("sx_", tr) := eps * get(tr)]; rhs <- c(rhs, paste0("sx_", tr))
    if (controls) for (c in CL) { v <- paste0(tr, "_", c); f[, (v) := get(tr) * get(c)]; rhs <- c(rhs, v) }
  }
  rhs <- c(rhs, "lag1", "lag2", "lag3")
  fml <- as.formula(paste("dh ~", paste(rhs, collapse = " + "), "| sector_h^m + sector_h^bank_type"))
  est <- tryCatch(feols(fml, data = f, panel.id = ~uid + m, vcov = DK(h + 2L),
                        weights = if (weights) ~w else NULL, warn = FALSE, notes = FALSE),
                  error = function(e) NULL)
  if (is.null(est)) return(NULL)
  nm <- paste0("sx_", treat)
  Tm <- uniqueN(f$m[obs(est)])
  if (Tm < MIN_T)   # too few months for DK inference: report as not estimable
    return(data.table(treat = treat, b = NA_real_, se = NA_real_, n = nobs(est), T = Tm))
  data.table(treat = treat, b = unname(coef(est)[nm]), se = unname(se(est)[nm]),
             n = nobs(est), T = uniqueN(f$m[obs(est)]))
}

# DL with options ------------------------------------------------------------------
# The IRF always comes from the DL without leads; when leads > 0, the lead placebo (sum of
# the lead coefficients) comes from a second regression with the leads added.
# ctrl_mode: "none" (baseline), "post" (ISL x X_{t-1} dated relative to the outcome month, the first draft's
# specification; post-treatment for shock lags >= 1) or "pre" (ISL x X_{t-25}, predetermined for every lag)
dl_one <- function(p, shock, treat = "isl", ctrl_mode = "none", drop = integer(0), weights = FALSE,
                   sector_out = NULL, ar = 0L, leads = 6L, K = 24L) {
  r <- dl_fit(p, shock, treat, ctrl_mode, drop, weights, sector_out, ar, 0L, K)
  if (leads > 0) {
    rl <- dl_fit(p, shock, treat, ctrl_mode, drop, weights, sector_out, ar, leads, K)
    lk <- unique(rl[, .(treat, lead_b, lead_se)])
    r[, c("lead_b", "lead_se") := NULL]
    r <- merge(r, lk, by = "treat", sort = FALSE)
  }
  r
}
dl_fit <- function(p, shock, treat, ctrl_mode, drop, weights, sector_out, ar, leads, K) {
  q <- copy(p)
  if (length(drop)) q[m %in% drop, ok := FALSE]
  if (!is.null(sector_out)) q <- q[sector_h != sector_out]
  setkey(q, uid, m)
  q[, `:=`(dy = y - shift(y), gap = m - shift(m)), by = uid]
  q[!ok | is.na(gap) | gap != 1L, dy := NA_real_]
  if (ar > 0) for (l in seq_len(ar)) q[, paste0("ar", l) := shift(dy, l), by = uid]
  q <- merge(q, mac_l[, c("m", CL), with = FALSE], by = "m")   # always merged, so the sample is the same
  ctrl <- character(0)
  if (ctrl_mode == "pre") q <- merge(q, mac_p[, c("m", CLp), with = FALSE], by = "m")
  if (ctrl_mode != "none") for (tr in treat) for (c in (if (ctrl_mode == "pre") CLp else CL)) {
    v <- paste0(tr, "_", c); q[, (v) := get(tr) * get(c)]; ctrl <- c(ctrl, v) }
  if (ar > 0) ctrl <- c(ctrl, paste0("ar", seq_len(ar)))
  q <- q[!is.na(dy)]
  if (weights) {
    # dl_irf has no weights argument; replicate its estimator here with weights
    f <- add_shock_lags(q, shk, shock, K, leads)
    lagn <- c(if (leads > 0) paste0("e_f", leads:1), paste0("e_l", 0:K))
    terms <- character(0)
    for (tr in treat) for (nm in lagn) { v <- paste0(tr, "_x_", nm); f[, (v) := get(tr) * get(nm)]; terms <- c(terms, v) }
    fml <- as.formula(paste("dy ~", paste(c(terms, ctrl), collapse = " + "), "| sector_h^m + uid"))
    est <- feols(fml, data = f, panel.id = ~uid + m, vcov = DK(12L), weights = ~w, warn = FALSE, notes = FALSE)
    out <- rbindlist(lapply(treat, function(tr) {
      nms <- paste0(tr, "_x_e_l", 0:K); V <- vcov(est)[nms, nms]
      ln <- if (leads > 0) paste0(tr, "_x_e_f", leads:1) else character(0)
      data.table(treat = tr, h = 0:K, b = cumsum(coef(est)[nms]),
                 se = sapply(0:K, function(h) sqrt(sum(V[1:(h + 1), 1:(h + 1)]))),
                 lead_b = if (leads > 0) sum(coef(est)[ln]) else NA_real_,
                 lead_se = if (leads > 0) sqrt(sum(vcov(est)[ln, ln])) else NA_real_)
    }))
    out[, `:=`(n = nobs(est), T = uniqueN(f$m[obs(est)]))]
    attr(out, "est") <- est
    return(out)
  }
  r <- dl_irf(q, shk, shock, treat = treat, K = K, fe = "sector_h^m + uid", ctrl = ctrl, L = 12L, leads = leads)
  if (!"lead_b" %in% names(r)) r[, `:=`(lead_b = NA_real_, lead_se = NA_real_)]
  r
}

# A. robustness grid --------------------------------------------------------------
SPECS <- list(
  list(id = "baseline",            drop = "none"),                         # LP: ISL x X_{t-1}; DL: no controls
  list(id = "no_isl_x_controls",   drop = "none", lp_controls = FALSE, dl = FALSE),  # plan section 7 (LP)
  list(id = "dl_ctrl_pre",         drop = "none", ctrl_mode = "pre",  lp = FALSE),   # plan section 7 (DL)
  list(id = "dl_ctrl_post",        drop = "none", ctrl_mode = "post", lp = FALSE),   # first draft's DL
  list(id = "weighted",            drop = "none", weights = TRUE),         # plan section 4
  list(id = "drop_break_years",    drop = "breakyrs"),                     # plan section 6
  list(id = "drop_pandemic",       drop = "pandemic"),                     # plan section 6
  list(id = "drop_post_conversion",drop = "postconv"),                     # extra, not pre-registered
  list(id = "drop_2013_2015",      drop = "y2013_15"),                     # extra, not pre-registered
  list(id = "dl_ar3",              drop = "none", ar = 3L, lp = FALSE)    # extra: DL with own lags
)
grid <- list()
for (P in c("H9", "H15")) {
  p <- prep(P, c("ISL", "CONV"))
  for (s in SH_MAIN) for (sp in SPECS) {
    if (P == "H15" && sp$id == "drop_2013_2015") next   # H15 starts in 2016-06
    wt  <- isTRUE(sp$weights)
    dr  <- DROPS[[sp$drop]]
    if (!isFALSE(sp[["lp"]])) {
      r <- lp_one(p, s, 12L, controls = !isFALSE(sp[["lp_controls"]]), drop = dr, weights = wt)
      if (!is.null(r)) grid[[length(grid) + 1L]] <- r[, `:=`(panel = P, shock = s, spec = sp$id, est = "LP", h = 12L,
                                                              lead_b = NA_real_, lead_se = NA_real_)]
    }
    if (isFALSE(sp[["dl"]])) next
    d <- dl_one(p, s, ctrl_mode = if (is.null(sp$ctrl_mode)) "none" else sp$ctrl_mode, drop = dr, weights = wt,
                ar = if (is.null(sp$ar)) 0L else sp$ar)
    for (hh in c(12L, 24L))
      grid[[length(grid) + 1L]] <- d[h == hh, .(treat, b, se, n, T, panel = P, shock = s, spec = sp$id,
                                                est = "DL", h, lead_b, lead_se)]
  }
  cat("  grid", P, "done\n")
}
grid <- rbindlist(grid, use.names = TRUE)
grid[, `:=`(b25 = 25 * b, se25 = 25 * se, lead_b25 = 25 * lead_b, lead_se25 = 25 * lead_se)]
fwrite(grid, file.path(OUT, "tables", "credit_robustness.csv"))
cat("\n=== A. robustness: ISL-CONV differential, percent per 25 bp ===\n")
print(grid[, .(panel, shock, spec, est, h, b25 = fmt(b25, 2), se25 = fmt(se25, 2), t = fmt(b / se, 2), n, T,
               lead = fmt(lead_b25, 2), lead_se = fmt(lead_se25, 2))], nrows = 400)

# B. leave-one-sector-out (plan section 7) ------------------------------------------
loso <- list()
for (P in c("H9", "H15")) {
  p <- prep(P, c("ISL", "CONV"))
  for (s in SH_MAIN) for (sec in sort(unique(p$sector_h))) {
    r <- lp_one(p, s, 12L, sector_out = sec)
    d <- dl_one(p, s, sector_out = sec, leads = 0L)[h == 12L]
    loso[[length(loso) + 1L]] <- data.table(panel = P, shock = s, sector_out = sec,
                                            lp_b25 = 25 * r$b, lp_se25 = 25 * r$se,
                                            dl_b25 = 25 * d$b, dl_se25 = 25 * d$se)
  }
}
loso <- rbindlist(loso)
fwrite(loso, file.path(OUT, "tables", "credit_loso.csv"))
cat("\n=== B. leave-one-sector-out, h = 12, percent per 25 bp ===\n")
print(loso[, .(panel, shock, sector_out, lp = sprintf("%6.2f (%4.2f)", lp_b25, lp_se25),
               dl = sprintf("%6.2f (%4.2f)", dl_b25, dl_se25))], nrows = 200)

# C. funding channel: BUS vs UUS, from 2014-06 (plan 5.2) ---------------------------------
bu <- list()
for (P in c("H9", "H15")) {
  p <- prep(P, c("BUS", "UUS", "CONV"), start = as.IDate("2014-06-01"))
  for (s in c(SH_MAIN, "jk_mp_pm", "usmpd_stmt")) for (dn in c("none", "postconv")) {
    for (h in c(0L, 3L, 6L, 12L, 18L, 24L)) {
      r <- lp_one(p, s, h, treat = c("bus", "uus"), drop = DROPS[[dn]])
      if (!is.null(r)) bu[[length(bu) + 1L]] <- r[, `:=`(panel = P, shock = s, est = "LP", h = h, drop = dn)]
    }
    d <- dl_one(p, s, treat = c("bus", "uus"), leads = 6L, drop = DROPS[[dn]])
    bu[[length(bu) + 1L]] <- d[, .(treat, b, se, n, T, panel = P, shock = s, est = "DL", h, lead_b, lead_se, drop = dn)]
  }
}
bu <- rbindlist(bu, fill = TRUE)
bu[, `:=`(b25 = 25 * b, se25 = 25 * se)]
fwrite(bu, file.path(OUT, "tables", "credit_bus_uus.csv"))
cat("\n=== C. BUS vs UUS (each relative to CONV, same sector-month), percent per 25 bp ===\n")
print(dcast(bu[h %in% c(0, 6, 12, 24), .(panel, shock, drop, est, h, treat, v = sprintf("%6.2f (%4.2f)", b25, se25))],
            panel + shock + drop + est + h ~ treat, value.var = "v"), nrows = 300)

# D. sector exposure theta_h on TOTAL sector credit (plan 5.3) ------------------------------
# dlog Y_{s,t} = sh_s dlog ISL + (1 - sh_s) dlog CONV, so with the share as a FRACTION and a
# sector-invariant differential beta, the composition identity gives theta_h = beta_h.
th <- list()
for (P in c("H9", "H15")) {
  sh <- unique(shr0[panel == P, .(sector_h, share = isl_share_pre_avg_pct / 100,
                                  share_alt = isl_share_pre_alt_avg_pct / 100)])
  p <- pan0[panel == P & bank_type == "TOTAL" & date >= SAMPLE_START & date <= SAMPLE_END]
  p[, m := mid(date)][, uid := as.integer(factor(sector_h))]
  p[, y := log(credit_rp_bn)][, ok := adj_growth_ok %in% TRUE]
  p <- merge(p, sh, by = "sector_h")
  for (s in c(SH_MAIN, "jk_mp_pm", "usmpd_stmt")) for (sv in c("share", if (P == "H9") "share_alt")) {
    p[, expo := get(sv)]
    # LP (plan): theta_h with sector and month FE, expo x X_{t-1} controls, 3 own lags
    for (h in c(0L, 3L, 6L, 12L, 18L, 24L)) {
      f <- lp_frame(p[, .(unit = sector_h, uid, sector_h, m, y, ok, expo)], h)
      f <- merge(f, shk[, c("m", s), with = FALSE], by = "m"); setnames(f, s, "eps")
      f <- merge(f, mac_l[, c("m", CL), with = FALSE], by = "m")
      f[, sx := eps * expo]
      for (c in CL) f[, paste0("ex_", c) := expo * get(c)]
      fml <- as.formula(paste("dh ~ sx +", paste(paste0("ex_", CL), collapse = " + "),
                              "+ lag1 + lag2 + lag3 | uid + m"))
      est <- tryCatch(feols(fml, data = f, panel.id = ~uid + m, vcov = DK(h + 2L), warn = FALSE, notes = FALSE),
                      error = function(e) NULL)
      if (!is.null(est)) th[[length(th) + 1L]] <- data.table(panel = P, shock = s, share_var = sv, est = "LP", h = h,
        b = coef(est)["sx"], se = se(est)["sx"], n = nobs(est))
    }
    # DL
    q <- copy(p); setkey(q, uid, m)
    q[, dy := y - shift(y), by = uid]; q[ok %in% FALSE, dy := NA_real_]
    q <- merge(q, mac_l[, c("m", CL), with = FALSE], by = "m")
    for (c in CL) q[, paste0("ex_", c) := expo * get(c)]
    # DL without expo x X controls (dated relative to the outcome month they would be post-treatment)
    d <- dl_irf(q[!is.na(dy)], shk, s, treat = "expo", K = 24L, fe = "uid + m", L = 12L)
    th[[length(th) + 1L]] <- d[, .(panel = P, shock = s, share_var = sv, est = "DL", h, b, se, n)]
  }
}
th <- rbindlist(th)
th[, `:=`(b25 = 25 * b, se25 = 25 * se)]
fwrite(th, file.path(OUT, "tables", "credit_theta.csv"))
cat("\n=== D. theta_h: TOTAL sector credit on shock x pre-period Islamic share (fraction), percent per 25 bp ===\n")
print(dcast(th[h %in% c(0, 6, 12, 24), .(panel, shock, share_var, est, h, v = sprintf("%7.1f (%5.1f)", b25, se25))],
            panel + shock + share_var + est ~ h, value.var = "v"), nrows = 200)
cat("cross-sector spread of the exposure (pre-period share, pct):\n")
print(unique(shr0[, .(panel, sector_h, pre = isl_share_pre_avg_pct)])[, .(min = min(pre), max = max(pre), sd = sd(pre)), by = panel])

# D2. checks on theta (added after review): a household x shock control (H15) and leave-one-sector-out,
# DL, h = 12, pre-period share. Tests whether household composition explains theta.
HH <- c("H15_HRE", "H15_HSH", "H15_HVE", "H15_HOT")
tc <- list()
for (P in c("H9", "H15")) {
  sh <- unique(shr0[panel == P, .(sector_h, expo = isl_share_pre_avg_pct / 100)])
  p <- pan0[panel == P & bank_type == "TOTAL" & date >= SAMPLE_START & date <= SAMPLE_END]
  p[, m := mid(date)][, uid := as.integer(factor(sector_h))]
  p[, y := log(credit_rp_bn)][, ok := adj_growth_ok %in% TRUE]
  p <- merge(p, sh, by = "sector_h"); setkey(p, uid, m)
  p[, dy := y - shift(y), by = uid]; p[ok %in% FALSE, dy := NA_real_]
  p <- merge(p, mac_l[, c("m", CL), with = FALSE], by = "m")
  p[, hh := as.integer(sector_h %in% HH)]
  q <- p[!is.na(dy)]
  for (s in SH_MAIN) {
    r0 <- dl_irf(q, shk, s, treat = "expo", K = 24L, fe = "uid + m", L = 12L)[h == 12L]
    tc[[length(tc) + 1L]] <- data.table(panel = P, shock = s, check = "baseline", sector_out = NA_character_,
                                        b = r0$b, se = r0$se)
    if (P == "H15") {
      r1 <- dl_irf(q, shk, s, treat = c("expo", "hh"), K = 24L, fe = "uid + m", L = 12L)[h == 12L]
      tc[[length(tc) + 1L]] <- data.table(panel = P, shock = s, check = "household_x_shock", sector_out = NA_character_,
                                          b = r1[treat == "expo", b], se = r1[treat == "expo", se],
                                          b_hh = r1[treat == "hh", b], se_hh = r1[treat == "hh", se])
    }
    for (sec in sort(unique(q$sector_h))) {
      r2 <- dl_irf(q[sector_h != sec], shk, s, treat = "expo", K = 24L, fe = "uid + m", L = 12L)[h == 12L]
      tc[[length(tc) + 1L]] <- data.table(panel = P, shock = s, check = "loso", sector_out = sec, b = r2$b, se = r2$se)
    }
  }
}
tc <- rbindlist(tc, fill = TRUE)
tc[, `:=`(b25 = 25 * b, se25 = 25 * se)]
if ("b_hh" %in% names(tc)) tc[, `:=`(b_hh25 = 25 * b_hh, se_hh25 = 25 * se_hh)]
fwrite(tc, file.path(OUT, "tables", "credit_theta_checks.csv"))
cat("\n=== D2. theta_12 checks (DL), percent per 25 bp ===\n")
print(tc[check != "loso", .(panel, shock, check, b25 = fmt(b25, 1), se25 = fmt(se25, 1))])
print(tc[check == "loso", .(min = min(b25), max = max(b25), sector_min = sector_out[which.min(b25)],
                            sector_max = sector_out[which.max(b25)]), by = .(panel, shock)])

# E. Islamic NPF ratio by sector (plan 5.5): level responses, sector FE + X_{t-1} ----------------
np <- list()
for (P in c("H9", "H15")) {
  p <- pan0[panel == P & bank_type == "ISL" & date >= SAMPLE_START & date <= SAMPLE_END]
  p[, m := mid(date)][, uid := as.integer(factor(sector_h))]
  p[, y := 100 * npf_rp_bn / credit_rp_bn][, ok := adj_growth_ok %in% TRUE & !is.na(y)]
  for (s in c(SH_MAIN, "jk_mp_pm", "usmpd_stmt")) {
    for (h in c(0L, 3L, 6L, 12L, 18L, 24L)) {
      f <- lp_frame(p[, .(unit = sector_h, uid, sector_h, m, y, ok)], h)
      f <- merge(f, shk[, c("m", s), with = FALSE], by = "m"); setnames(f, s, "eps")
      f <- merge(f, mac_l[, c("m", CL), with = FALSE], by = "m")
      fml <- as.formula(paste("dh ~ eps +", paste(CL, collapse = " + "), "+ lag1 + lag2 + lag3 | uid"))
      est <- tryCatch(feols(fml, data = f, panel.id = ~uid + m, vcov = DK(h + 2L), warn = FALSE, notes = FALSE),
                      error = function(e) NULL)
      if (!is.null(est)) np[[length(np) + 1L]] <- data.table(panel = P, shock = s, h = h,
        b = coef(est)["eps"], se = se(est)["eps"], n = nobs(est))
    }
  }
}
np <- rbindlist(np)
np[, `:=`(b25 = 0.25 * b, se25 = 0.25 * se)]   # outcome already in pp of the NPF ratio
fwrite(np, file.path(OUT, "tables", "credit_npf.csv"))
cat("\n=== E. Islamic NPF ratio by sector, pp per 25 bp (LP, DK) ===\n")
print(dcast(np[, .(panel, shock, h, v = sprintf("%6.2f (%4.2f)", b25, se25))], panel + shock ~ h, value.var = "v"))

# F. joint test over all DL lags, by block permutation, and power ----------------------------------
# A DK-based Wald test of 25 restrictions with ~180 months is badly oversized (it rejected for
# every shock, including ones with tiny coefficients), so the joint test is calibrated by
# permutation instead: on the cross-sector average differential D_t, compute the OLS F-statistic
# for the 25 shock lags (and beta_12 = sum of the first 13), then recompute both after
# re-assigning the shock series across months in 12-month blocks (2,000 draws).
NPERM <- 2000L
perm_dl <- function(D, s, K = 24L) {
  ev <- shk[, c("m", s), with = FALSE]; setnames(ev, s, "e")
  D <- D[m >= ev[!is.na(e), min(m)] + K]          # full lag history (binds only for short shock series)
  mm <- seq(min(D$m) - K, max(D$m))
  sv <- data.table(m = mm, e = ev$e[match(mm, ev$m)])   # interior NAs (e.g. Bauer-Swanson 2020) stay NA
  stat <- function(e) {   # no macro controls, as in the panel DL baseline
    L <- sapply(0:K, function(k) e[match(D$m - k, mm)])
    ok <- complete.cases(L)
    f1 <- lm(D$y[ok] ~ L[ok, ]); f0 <- lm(D$y[ok] ~ 1)
    a <- anova(f0, f1)
    c(F = a$F[2], b12 = sum(coef(f1)[2:14]))
  }
  obs <- stat(sv$e)
  set.seed(20261029)
  dr <- t(replicate(NPERM, stat(sv$e[block_perm(sv$e, 12L)])))
  list(F = obs["F"], p_F = mean(dr[, "F"] >= obs["F"]), b12 = obs["b12"],
       p_b12 = mean(abs(dr[, "b12"]) >= abs(obs["b12"])), n = nrow(D))
}
jt <- list()
for (P in c("H9", "H15")) {
  p <- prep(P, c("ISL", "CONV"))
  q <- copy(p); setkey(q, uid, m)
  q[, `:=`(dy = y - shift(y), gap = m - shift(m)), by = uid]
  q[!ok | is.na(gap) | gap != 1L, dy := NA_real_]
  w <- dcast(q[!is.na(dy)], sector_h + m ~ bank_type, value.var = "dy")
  D <- w[!is.na(ISL) & !is.na(CONV), .(y = mean(ISL - CONV)), by = m]
  D <- merge(D, mac_l[, c("m", CL), with = FALSE], by = "m"); setorder(D, m)
  for (s in c("jk_mp_median", "jk_mp_pm", "usmpd_stmt", "usmpd_me", if (P == "H9") "bs_mps_orth",
              "jk_cbi_median", "bi_rule_resid")) {
    d <- dl_one(p, s, leads = 0L)
    pm <- perm_dl(D, s)
    sd_s <- sd(shk[date >= SAMPLE_START & date <= SAMPLE_END, get(s)], na.rm = TRUE)
    se12 <- d[h == 12, se]; b12 <- d[h == 12, b]
    jt[[length(jt) + 1L]] <- data.table(panel = P, shock = s,
      ts_F = pm$F, perm_p_joint = pm$p_F, ts_b12_25 = 25 * pm$b12, perm_p_b12 = pm$p_b12, ts_n = pm$n,
      b12_25 = 25 * b12, se12_25 = 25 * se12,
      mde12_25_a05 = 2.80 * 25 * se12, mde12_25_a10 = 2.49 * 25 * se12,
      mde12_sd_a05 = 2.80 * 100 * se12 * sd_s, shock_sd_bp = 100 * sd_s)
    cat("  perm", P, s, "\n")
  }
}
jt <- rbindlist(jt)
fwrite(jt, file.path(OUT, "tables", "credit_joint_power.csv"))
cat("\n=== F. permutation joint test (all 25 DL lags = 0, average differential) and MDE at h = 12 (panel DL) ===\n")
print(jt[, .(panel, shock, F = fmt(ts_F, 2), p_joint = fmt(perm_p_joint, 3), ts_b12 = fmt(ts_b12_25, 2),
             p_b12 = fmt(perm_p_b12, 3), b12_25 = fmt(b12_25, 2), se12_25 = fmt(se12_25, 2),
             MDE25_5pct = fmt(mde12_25_a05, 2), MDE25_10pct = fmt(mde12_25_a10, 2),
             MDEsd_5pct = fmt(mde12_sd_a05, 2), sd_bp = fmt(shock_sd_bp, 1))])

# G. sample robustness in calendar time (added after the mechanism module's verification) ------
# The DL regresses the first H9 outcome months (2009) on shock lags back to 2007-01, which the LP
# never uses; 2007-08 carries large Fed surprises. Re-estimate beta_12 with outcome months from
# 2010 (no 2009 outcomes) and from 2011 (every DL shock lag from 2009 or later), and leaving out
# one calendar year at a time.
yr_months <- function(y) months_in(sprintf("%d-01-01", y), sprintf("%d-12-01", y))
SAMP <- c(list(full = integer(0), from2010 = yr_months(2009), from2011 = c(yr_months(2009), yr_months(2010))),
          setNames(lapply(2009:2025, yr_months), paste0("loyo_", 2009:2025)))
sr <- list()
for (P in c("H9", "H15")) {
  p <- prep(P, c("ISL", "CONV"))
  yrs <- unique(year(p$date))
  for (s in SH_MAIN) for (nm in names(SAMP)) {
    if (grepl("^loyo_", nm) && !(as.integer(sub("loyo_", "", nm)) %in% yrs)) next
    if (P == "H15" && nm %in% c("from2010", "from2011")) next     # H15 starts in 2016-06
    dr <- SAMP[[nm]]
    r <- lp_one(p, s, 12L, drop = dr)
    d <- dl_one(p, s, drop = dr, leads = 0L)[h == 12L]
    sr[[length(sr) + 1L]] <- data.table(panel = P, shock = s, sample = nm,
      lp_b25 = 25 * r$b, lp_se25 = 25 * r$se, lp_T = r$T,
      dl_b25 = 25 * d$b, dl_se25 = 25 * d$se, dl_T = d$T)
  }
}
sr <- rbindlist(sr)
fwrite(sr, file.path(OUT, "tables", "credit_sample_robustness.csv"))
cat("\n=== G. sample robustness of beta_12, percent per 25 bp ===\n")
print(sr[, .(panel, shock, sample, lp = sprintf("%6.2f (%4.2f) T=%d", lp_b25, lp_se25, lp_T),
             dl = sprintf("%6.2f (%4.2f) T=%d", dl_b25, dl_se25, dl_T))], nrows = 200)
cat("\nLOYO ranges (DL):\n")
print(sr[grepl("^loyo_", sample), .(dl_min = min(dl_b25), dl_max = max(dl_b25),
                                     min_abs_t = min(abs(dl_b25 / dl_se25)), max_abs_t = max(abs(dl_b25 / dl_se25)),
                                     lp_min = min(lp_b25, na.rm = TRUE), lp_max = max(lp_b25, na.rm = TRUE)),
         by = .(panel, shock)])
