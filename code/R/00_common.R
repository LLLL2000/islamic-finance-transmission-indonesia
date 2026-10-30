# 00_common.R ---------------------------------------------------------------
# Shared loaders and local-projection machinery. Implements notes/pre_analysis_plan.md.
suppressPackageStartupMessages({
  library(data.table)
  library(fixest)
  library(sandwich)
})

ROOT  <- "C:/Users/consu/Documents/Universidad/Islamic_Finance_Project/wp_dual_banking"
CLEAN <- file.path(ROOT, "data", "clean")
OUT   <- file.path(ROOT, "output")
dir.create(file.path(OUT, "tables"),  recursive = TRUE, showWarnings = FALSE)
dir.create(file.path(OUT, "figures"), recursive = TRUE, showWarnings = FALSE)

SAMPLE_START <- as.IDate("2009-01-01")
SAMPLE_END   <- as.IDate("2025-06-01")
H_MAX        <- 24L
SCALE_BP     <- 25    # pre-registered reporting unit: a 25 bp surprise

# month index helpers ---------------------------------------------------------
mid  <- function(d) { d <- as.IDate(d); year(d) * 12L + month(d) - 1L }
mid2date <- function(m) as.IDate(sprintf("%04d-%02d-01", m %/% 12L, m %% 12L + 1L))

# shocks ----------------------------------------------------------------------
load_shocks <- function() {
  s <- fread(file.path(CLEAN, "us_shocks_monthly.csv"))
  s[, date := as.IDate(date)]
  # months without an FOMC event are already 0 inside each series' coverage; NA means
  # out of coverage (e.g. Bauer-Swanson after 2023-12) or deliberately excluded (BS 2020
  # meetings), so NA is kept as NA and never filled with 0
  w <- dcast(s, date ~ shock, value.var = "value")
  # domestic Bank Indonesia policy-rule residual, if built (05_bi_shock.R)
  f_bi <- file.path(CLEAN, "bi_shock_residual.csv")
  if (file.exists(f_bi)) {
    bi <- fread(f_bi); bi[, date := as.IDate(date)]
    w <- merge(w, bi, by = "date", all.x = TRUE)
  }
  w[, m := mid(date)]
  w
}

# macro controls, dated t (lagged inside the LP) ------------------------------
load_macro <- function() {
  m <- fread(file.path(CLEAN, "macro_monthly.csv"))
  m[, date := as.IDate(date)]
  m[, m := mid(date)]
  setorder(m, m)
  m[, `:=`(
    c_vix      = us_vix_avg_index,
    c_dlbrent  = 100 * (log(brent_spot_avg_usd_bbl) - shift(log(brent_spot_avg_usd_bbl))),
    c_dlidr    = 100 * (log(idr_per_usd_avg) - shift(log(idr_per_usd_avg))),
    c_birate   = idn_policy_rate_avg_adj_pct,
    c_infl     = idn_cpi_yoy_pct,
    c_ipgrowth = idn_mfg_prod_yoy_pct
  )]
  m[, .(m, date, c_vix, c_dlbrent, c_dlidr, c_birate, c_infl, c_ipgrowth)]
}
CONTROLS <- c("c_vix", "c_dlbrent", "c_dlidr", "c_birate")

# build horizon-h outcomes for a long panel keyed by unit and month -----------
# dt must have: unit, m, y (log level), ok (TRUE if the change INTO month m is clean)
lp_frame <- function(dt, h, nlags = 3L) {
  dt <- copy(dt)
  setkey(dt, unit, m)
  dt[, dy := y - shift(y), by = unit]
  dt[!ok | is.na(ok), dy := NA_real_]
  # cumulative clean indicator over months t..t+h
  dt[, okn := as.integer(ok & !is.na(y))]
  dt[, bad_cum := cumsum(1L - okn), by = unit]
  dt[, `:=`(
    y_lead   = shift(y, h, type = "lead"),
    y_lag1   = shift(y, 1L),
    m_lead   = shift(m, h, type = "lead"),
    m_lag1   = shift(m, 1L),
    bad_lead = shift(bad_cum, h, type = "lead"),
    bad_lag1 = shift(bad_cum, 1L)
  ), by = unit]
  dt[, dh := y_lead - y_lag1]
  # require consecutive months and no contaminated change in [t, t+h]
  dt[(m_lead - m) != h | (m - m_lag1) != 1L | (bad_lead - bad_lag1) != 0, dh := NA_real_]
  for (l in seq_len(nlags)) dt[, paste0("lag", l) := shift(dy, l), by = unit]
  # pre-trend outcome: growth over [t-4, t-1], i.e. y_{t-1} - y_{t-5}, kept only when the four monthly
  # changes into t-4..t-1 are all clean and the months are consecutive. The placebo regression must not
  # include the own-growth lags (lag1..lag3 are three of these four changes; with them the coefficient
  # would be that of the change into t-4 alone).
  dt[, `:=`(y_lag5 = shift(y, 5L), m_lag5 = shift(m, 5L), bad_lag5 = shift(bad_cum, 5L)), by = unit]
  dt[, dpre := y_lag1 - y_lag5]
  dt[(m_lag1 - m_lag5) != 4L | (bad_lag1 - bad_lag5) != 0, dpre := NA_real_]
  dt[]
}

# Newey-West time-series LP ---------------------------------------------------
nw_lp <- function(yv, X, lag) {
  fit <- lm(yv ~ X)
  V <- sandwich::NeweyWest(fit, lag = lag, prewhite = FALSE, adjust = TRUE)
  list(coef = coef(fit), se = sqrt(diag(V)), n = nobs(fit), fit = fit)
}

# block permutation of a time series -----------------------------------------
block_perm <- function(x, block = 12L) {
  n <- length(x); nb <- ceiling(n / block)
  idx <- split(seq_len(n), ceiling(seq_len(n) / block))
  unlist(idx[sample.int(length(idx))])[seq_len(n)]
}

fmt <- function(x, d = 3) formatC(x, format = "f", digits = d)

# distributed-lag (DL) impulse responses ---------------------------------------
# Deviation from the pre-analysis plan, reported as such: the plan's LP drops a whole
# window if any month in [t, t+h] is contaminated, and the panel's all-unit breaks
# (2014-05, 2014-07, 2015-03, three conversions, the 2023 gap) leave few long clean
# windows. The DL regresses each CLEAN monthly growth rate on eps_{t-k}, k = 0..K, and
# cumulates: beta_h = sum_{k<=h} phi_k. With exogenous, serially uncorrelated shocks it
# targets the same IRF and loses only the contaminated months themselves.
#   d     : data.table with m, uid (integer unit id), dy, the treat columns, FE columns, ctrl
#   treat : columns multiplying the shock lags ("one" = main effect, a column of 1s)
#   leads : number of shock leads eps_{t+j} included as a placebo (should be ~0)
add_shock_lags <- function(d, shk, shock, K, leads = 0L) {
  sv <- shk[, c("m", shock), with = FALSE]; setnames(sv, shock, "e"); setkey(sv, m)
  mm <- sort(unique(d$m))
  E <- data.table(m = mm)
  for (k in -leads:K) {
    nm <- if (k >= 0) paste0("e_l", k) else paste0("e_f", -k)
    E[, (nm) := sv[J(mm - k), e]]
  }
  merge(d, E, by = "m")
}
dl_irf <- function(d, shk, shock, treat = "one", K = 24L, fe = "uid", ctrl = character(0),
                   L = 12L, leads = 0L) {
  f <- add_shock_lags(copy(d), shk, shock, K, leads)
  f[, one := 1]
  lagn <- c(if (leads > 0) paste0("e_f", leads:1), paste0("e_l", 0:K))
  terms <- character(0)
  for (tr in treat) for (nm in lagn) {
    v <- paste0(tr, "_x_", nm); f[, (v) := get(tr) * get(nm)]; terms <- c(terms, v)
  }
  fml <- as.formula(paste("dy ~", paste(c(terms, ctrl), collapse = " + "), "|", fe))
  est <- feols(fml, data = f, panel.id = ~uid + m, vcov = DK(L), warn = FALSE, notes = FALSE)
  out <- list()
  for (tr in treat) {
    nms <- paste0(tr, "_x_e_l", 0:K)
    b <- coef(est)[nms]; V <- vcov(est)[nms, nms]
    se <- sapply(0:K, function(h) sqrt(sum(V[1:(h + 1), 1:(h + 1)])))
    r <- data.table(treat = tr, h = 0:K, b = cumsum(b), se = se)
    if (leads > 0) {
      ln <- paste0(tr, "_x_e_f", leads:1)
      r[, `:=`(lead_b = sum(coef(est)[ln]), lead_se = sqrt(sum(vcov(est)[ln, ln])))]
    }
    out[[tr]] <- r
  }
  res <- rbindlist(out)
  res[, `:=`(n = nobs(est), T = uniqueN(f$m[obs(est)]))]
  attr(res, "est") <- est
  res
}
# time-series DL on one series D_t (e.g. cross-sector average differential), NW errors
dl_ts <- function(D, shk, shock, K = 24L, ctrl = character(0), L = 12L) {
  f <- add_shock_lags(copy(D), shk, shock, K)
  X <- as.matrix(f[, c(paste0("e_l", 0:K), ctrl), with = FALSE])
  ok <- complete.cases(X) & !is.na(f$y)
  fit <- lm(f$y[ok] ~ X[ok, , drop = FALSE])
  V <- sandwich::NeweyWest(fit, lag = L, prewhite = FALSE, adjust = TRUE)
  idx <- 1 + seq_len(K + 1)
  data.table(h = 0:K, b = cumsum(coef(fit)[idx]),
             se = sapply(0:K, function(h) sqrt(sum(V[idx[1:(h + 1)], idx[1:(h + 1)]]))),
             n = nobs(fit))
}
