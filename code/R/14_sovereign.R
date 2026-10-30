# 14_sovereign.R --------------------------------------------------------------
# Module S (supplementary): the sovereign investor base. Sukuk negara (SBSN) vs
# conventional government bonds (SUN): same issuer, currency, credit risk, trading days.
# Question: after a US monetary tightening, do non-residents cut SBSN holdings by less
# than SUN holdings (a less "flighty" Islamic investor base)?
#
# Data: DJPPR daily holdings of tradable Rupiah SBN by holder x instrument
#   (notes/data_djppr.md), 2015-12-31..2022-06-27 with the SUN/SBSN split;
#   DJPPR monthly non-resident holdings by maturity bucket, 2017-01..2022-05;
#   US event-level shocks (us_shocks_events.csv) and monthly shocks (load_shocks()).
#
# Timing convention (day 0). Shock dates are ET. Jakarta (WIB, UTC+7) is 11 h (EDT) or
# 12 h (EST) ahead, so the Jakarta close (about 16:00 WIB) is 04:00-05:00 ET. Every
# event in the 2016-2022 window is at 08:00 ET or later (USMPD gives no time; FOMC
# statements are 14:00 ET), i.e. after the Jakarta close of the ET date. Holdings are
# end-of-day positions. Day 0 = first Jakarta trading date STRICTLY AFTER the ET date;
# day -1 = the last Jakarta close before the announcement. Alternative ("same"):
# day 0 = first trading date ON OR AFTER the ET date (then day 0 is mostly pre-event).
# Settlement: the positions are BI-SSSS registry positions, i.e. settled holdings (new
# issues enter on the Thursday settlement date of Tuesday auctions). If secondary trades
# settle T+2, positions at days 0 and +1 still reflect pre-announcement trades; the
# variant allday_t2aligned_settle measures the response from day +1 instead of day -1.
#
# Daily event-study LP over all trading days t (common sample, 1,576 days):
#   y_{t+h} - y_{t-1} = b_h e_t + sum_{l=1..5} g_l dy_{t-l} [+ settlement counts] + u
#   e_t = event shock on day 0, 0 otherwise. Outcomes: holder H's holdings of instrument
#   I, change / I's total outstanding at t-1 x 100 (percent of outstanding); for
#   non-residents also 100 x log change and Rp tn; SBSN-minus-SUN difference series.
#   NW s.e., lag h+5. Robustness: no settlement control, same-date timing, excluding
#   windows touching 2020-03..04, events-only cross-section (HC1), and a permutation
#   test that re-draws event dates among non-event trading days.
# Added after the independent verification (2026-10-30), reported in full:
#   leave-one-event-out; dropping the 2020-03-03 emergency cut; dropping the March 2020
#   easings (03-15 and 03-23; 03-03, 03-15 and 03-23); a fixed event sample across
#   horizons (t <= T-21); the T+2-aligned outcome; a joint-NW s.e. for the composition
#   gap; permutation draws restricted to the event values retained in each sample;
#   monthly shocks assigned by the Jakarta day-0 month.
# Monthly: non-resident holdings by maturity bucket x instrument, LP on monthly shocks,
#   h = 0..12, NW lag h+1, 3 lags (house style of 11_macro_first_stage.R). Descriptive.
#
# Units: shocks in pp; b is per 1 pp. Reported per 25 bp (b x 0.25) and per 1 s.d. of
# the shock (event-sample s.d. for daily; monthly s.d. 2009-01..2025-06 for monthly).
source("C:/Users/consu/Documents/Universidad/Islamic_Finance_Project/wp_dual_banking/code/R/00_common.R")
suppressPackageStartupMessages(library(ggplot2))
set.seed(20261029L)
options(width = 220)

TAB <- file.path(OUT, "tables"); FIG <- file.path(OUT, "figures")
# bs_mps_orth (Bauer-Swanson, orthogonalised to pre-FOMC news; plan s.3 robustness) was
# added after the ex-COVID pre-window placebo failed; it is NA for the 2020 events
# (authors' choice), and those event days are dropped, never set to 0.
SHOCKS_D <- c("jk_mp_median", "jk_mp_pm", "usmpd_stmt", "jk_cbi_median", "bs_mps_orth")
SHOCKS_M <- c(SHOCKS_D, "bi_rule_resid")   # bs_mps_orth monthly: NA in 2020 months, dropped
PRIMARY  <- "jk_mp_median"
HOLDERS  <- c("nonresidents", "banks_conventional", "banks_islamic", "bi_net",
              "mutual_funds", "insurance_pension", "individuals", "others")
INSTR    <- c("SUN", "SBSN")
H_D      <- 20L     # trading days
NLAG_D   <- 5L      # lags of the outcome's daily change (one trading week)
JUMP_TH  <- 0.5     # Rp tn; |daily change of total outstanding of I| > JUMP_TH = settlement day
NPERM    <- 2000L
H_M      <- 12L
COVID    <- as.IDate(c("2020-03-01", "2020-04-30"))   # acute market stress (chosen before results)
PANDEMIC <- as.IDate(c("2020-03-01", "2021-12-31"))   # pre-analysis plan s.6 pandemic window (added after)
# event exclusions added after the verification (ET dates of the events dropped)
DROP_SETS <- list(drop0303    = "2020-03-03",                               # -12.4 bp JK emergency cut
                  dropMar20x2 = c("2020-03-15", "2020-03-23"),              # JK coded 0 (no S&P)
                  dropMar20x3 = c("2020-03-03", "2020-03-15", "2020-03-23"))
Z90      <- qnorm(0.95)
MDE_K    <- 2.80    # 80% power, 5% two-sided

# =============================================================================
# 1. Daily holdings
# =============================================================================
hd <- fread(file.path(CLEAN, "djppr_holdings_daily.csv"))
hd[, date := as.IDate(date)]
hd <- hd[instrument %in% INSTR & holder %in% c("total", HOLDERS) &
         row_type %in% c("reported", "derived")]
stopifnot(hd[, .N, by = .(date, holder, instrument)][, all(N == 1L)])
W <- dcast(hd, date ~ holder + instrument, value.var = "holdings_rp_tn")
setorder(W, date)
# common SUN/SBSN sample: SBSN is missing on 2022-06-28 (data_djppr.md, QA repair 4)
W <- W[!is.na(total_SBSN) & !is.na(total_SUN)]
stopifnot(!anyNA(W))
N <- nrow(W)
cat(sprintf("Daily sample: %s .. %s, %d trading days\n", min(W$date), max(W$date), N))
for (i in INSTR) {
  gap <- W[[paste0("total_", i)]] - Reduce(`+`, lapply(HOLDERS, function(h) W[[paste0(h, "_", i)]]))
  cat(sprintf("  adding-up %s: max |total - sum of 8 holders| = %.4f Rp tn\n", i, max(abs(gap))))
}
stopifnot(all(W$banks_islamic_SUN == 0))

# settlement / redemption days: jumps in total outstanding of each instrument
for (i in INSTR) {
  o <- W[[paste0("total_", i)]]
  W[, paste0("S_", i) := as.integer(abs(o - shift(o)) > JUMP_TH)]
}
W[, wday := weekdays(date)]

# =============================================================================
# 2. Descriptives
# =============================================================================
sh <- W[, .(date, SUN = 100 * nonresidents_SUN / total_SUN,
            SBSN = 100 * nonresidents_SBSN / total_SBSN)]
fwrite(sh, file.path(TAB, "sov_desc_nonres_share_daily.csv"))

long <- melt(W[, c("date", paste0(rep(c("total", HOLDERS), each = 2), "_", INSTR)), with = FALSE],
             id.vars = "date")
long[, instrument := sub(".*_", "", variable)]
long[, holder := sub("_(SUN|SBSN)$", "", variable)]
tot <- long[holder == "total", .(date, instrument, total = value)]
comp <- merge(long[holder != "total", .(date, instrument, holder, rp_tn = value)], tot,
              by = c("date", "instrument"))
comp[, share_pct := 100 * rp_tn / total]
# year-end snapshots (last trading day of each year) plus the last sample day
snap <- W[, .(date = max(date)), by = .(y = year(date))]$date
compsnap <- comp[date %in% snap]
compavg <- comp[, .(rp_tn = mean(rp_tn), total = mean(total), share_pct = mean(share_pct)),
                by = .(instrument, holder)][, date := as.IDate(NA)]
fwrite(rbind(compsnap[, .(period = as.character(date), instrument, holder, rp_tn, total, share_pct)],
             compavg[, .(period = "mean_2015-12-31_2022-06-27", instrument, holder, rp_tn, total, share_pct)]),
       file.path(TAB, "sov_desc_composition.csv"))

dsum <- rbindlist(lapply(INSTR, function(i) {
  nr <- W[[paste0("nonresidents_", i)]]; ot <- W[[paste0("total_", i)]]
  d_pct <- 100 * (nr - shift(nr)) / shift(ot)
  d_log <- 100 * (log(nr) - log(shift(nr)))
  d_rp  <- nr - shift(nr)
  iss   <- (ot - shift(ot)) > JUMP_TH      # increases of outstanding (issue settlements)
  data.table(instrument = i,
             outstanding_first = ot[1], outstanding_last = ot[length(ot)], outstanding_mean = mean(ot),
             nonres_first = nr[1], nonres_last = nr[length(nr)], nonres_mean = mean(nr),
             nonres_share_mean = mean(100 * nr / ot), nonres_share_min = min(100 * nr / ot),
             nonres_share_max = max(100 * nr / ot),
             sd_daily_dnonres_pct_outst = sd(d_pct, na.rm = TRUE),
             sd_daily_dnonres_log_pct = sd(d_log, na.rm = TRUE),
             sd_daily_dnonres_rp_tn = sd(d_rp, na.rm = TRUE),
             n_settlement_days = sum(W[[paste0("S_", i)]], na.rm = TRUE),
             n_settlement_days_thursday = sum(W[[paste0("S_", i)]] == 1 & W$wday == "Thursday", na.rm = TRUE),
             n_increase_days = sum(iss, na.rm = TRUE),
             n_increase_days_thursday = sum(iss & W$wday == "Thursday", na.rm = TRUE),
             n_increase_days_tuesday = sum(iss & W$wday == "Tuesday", na.rm = TRUE),
             n_days = nrow(W))
}))
fwrite(dsum, file.path(TAB, "sov_desc_summary.csv"))
cat("\n=== descriptive summary ===\n"); print(dsum)

# =============================================================================
# 3. Events and the daily shock series
# =============================================================================
ev_all <- fread(file.path(CLEAN, "us_shocks_events.csv"))
ev_all[, date := as.IDate(date)]
# JK events whose S&P 500 surprise is missing: the authors set MP = CBI = 0 there
jk_nosp <- ev_all[shock == "jk_sp500" & is.na(value), date]
td <- as.integer(W$date)
idx_after  <- function(d) findInterval(as.integer(d), td) + 1L        # first date >  d
idx_onafter <- function(d) findInterval(as.integer(d) - 1L, td) + 1L  # first date >= d
ev_all[, `:=`(t0_next = idx_after(date), t0_same = idx_onafter(date))]
ev_all[, in_sample := t0_next >= 2L & t0_next <= nrow(W) & t0_same >= 2L]

ev <- ev_all[shock %in% SHOCKS_D & in_sample == TRUE]   # NA values kept: day dropped, not 0
cat("In-sample events with NA shock value (dropped from the regressions):\n")
print(ev[is.na(value), .(shock, date)])
ev[, `:=`(day0_next = W$date[t0_next], day0_same = W$date[t0_same],
          jk_missing_sp500 = grepl("^jk_", shock) & date %in% jk_nosp)]
ev[, src := ifelse(grepl("^jk_", shock), "JK", "USMPD")]
cat(sprintf("\nMax calendar days from ET date to day 0 (next): %d\n",
            max(as.integer(ev$day0_next - ev$date))))
coll <- ev[, .N, by = .(shock, t0_next)][N > 1L]
cat(sprintf("Day-0 collisions within a shock (summed if any): %d\n", nrow(coll)))
evw <- dcast(ev, date + day0_next + day0_same ~ shock, value.var = "value",
             fun.aggregate = function(x) if (length(x)) sum(x) else NA_real_)
evw <- merge(ev[src == "JK", .(time_et_jk = time_et[1]), by = date], evw, by = "date", all.y = TRUE)
evw[, `:=`(jk_missing_sp500 = date %in% jk_nosp, weekday_et = weekdays(date), weekday_day0 = weekdays(day0_next))]
fwrite(evw, file.path(TAB, "sov_events.csv"))

shock_vec <- function(s, timing) {
  e <- ev[shock == s]
  a <- e[, .(v = sum(value)), by = .(t0 = get(paste0("t0_", timing)))]
  v <- numeric(nrow(W)); v[a$t0] <- a$v; v
}
event_flag <- function(s, timing) {
  v <- logical(nrow(W)); v[ev[shock == s][[paste0("t0_", timing)]]] <- TRUE; v
}
# rows used by the events-only cross-section (missing-S&P JK events excluded)
event_rows <- function(s) sort(unique(ev[shock == s & !jk_missing_sp500 & !is.na(value), t0_next]))

# event-sample s.d. of each shock (2016-01..2022-06 events, missing-S&P JK events excluded)
sdt <- ev[jk_missing_sp500 == FALSE & !is.na(value), .(n_events = .N, n_nonzero = sum(value != 0), mean = mean(value),
                               sd_event_pp = sd(value), min = min(value), max = max(value)), by = shock]
shk_m <- load_shocks()
sdm <- shk_m[date >= SAMPLE_START & date <= SAMPLE_END,
             lapply(.SD, sd, na.rm = TRUE), .SDcols = SHOCKS_M]
sdm <- data.table(shock = SHOCKS_M, sd_monthly_2009_2025_pp = unlist(sdm))
sdt <- merge(sdm, sdt, by = "shock", all.x = TRUE)
sdt[, `:=`(sd_event_bp = 100 * sd_event_pp, bp25_in_event_sd = 0.25 / sd_event_pp,
           sd_monthly_bp = 100 * sd_monthly_2009_2025_pp,
           bp25_in_monthly_sd = 0.25 / sd_monthly_2009_2025_pp)]
fwrite(sdt, file.path(TAB, "sov_shock_sd.csv"))
cat("\n=== shock s.d. ===\n"); print(sdt)
SD_EV <- setNames(sdt$sd_event_pp, sdt$shock)
SD_M  <- setNames(sdt$sd_monthly_2009_2025_pp, sdt$shock)

# permutation pool: trading days (with a day -1) that are not day 0 of ANY US event in
# the events file, under either timing
ev_days <- unique(c(ev_all[in_sample == TRUE, t0_next], ev_all[in_sample == TRUE, t0_same]))
POOL <- setdiff(2:nrow(W), ev_days)
cat(sprintf("Permutation pool: %d non-event trading days\n", length(POOL)))

# =============================================================================
# 4. Outcomes
# =============================================================================
shift_lead <- function(x, h) if (h == 0L) x else shift(x, h, type = "lead")
mk_outcome <- function(holder, instr, type) {
  if (instr == "diff") {
    a <- mk_outcome(holder, "SBSN", type); b <- mk_outcome(holder, "SUN", type)
    return(list(dh = Map(`-`, a$dh, b$dh), d1 = a$d1 - b$d1, pre = a$pre - b$pre))
  }
  y <- W[[paste0(holder, "_", instr)]]; sc <- W[[paste0("total_", instr)]]
  chg <- function(yh, k) {          # change from t-k to the date of yh
    yl <- shift(y, k)
    switch(type, pct = 100 * (yh - yl) / shift(sc, k),
                 log = 100 * (log(yh) - log(yl)),
                 rp  = yh - yl)
  }
  dh <- lapply(0:H_D, function(h) chg(shift_lead(y, h), 1L))
  list(dh = dh, d1 = dh[[1]], pre = chg(shift(y, 1L), 6L))   # pre: change over [t-6, t-1]
}
# T+2-aligned outcome: change from day +1 (last position settled from pre-announcement
# trades if secondary trades settle T+2) to day h, same scaling (h >= 2 only)
add_t2 <- function(o) {
  o$dh_t2 <- lapply(0:H_D, function(h) if (h < 2L) rep(NA_real_, N) else o$dh[[h + 1L]] - o$dh[[2L]])
  o
}
OUTS <- list()
for (hl in c("total", HOLDERS)) for (i in INSTR) {
  if (hl == "banks_islamic" && i == "SUN") next   # identically 0
  OUTS[[paste(hl, i, "pct", sep = "|")]] <- mk_outcome(hl, i, "pct")
}
OUTS[["nonresidents|diff|pct"]] <- mk_outcome("nonresidents", "diff", "pct")
for (i in c(INSTR, "diff")) OUTS[[paste("nonresidents", i, "log", sep = "|")]] <- mk_outcome("nonresidents", i, "log")
for (i in INSTR) OUTS[[paste("nonresidents", i, "rp", sep = "|")]] <- mk_outcome("nonresidents", i, "rp")
OUTS <- lapply(OUTS, add_t2)
NR_OUTS <- grep("^nonresidents\\|", names(OUTS), value = TRUE)

# settlement-count controls over the outcome window [t, t+h]
CTRL <- lapply(0:H_D, function(h)
  cbind(C_SUN  = frollsum(W$S_SUN,  h + 1L, align = "left"),
        C_SBSN = frollsum(W$S_SBSN, h + 1L, align = "left")))
CTRL_PRE <- cbind(C_SUN  = shift(frollsum(W$S_SUN,  5L, align = "right"), 1L),
                  C_SBSN = shift(frollsum(W$S_SBSN, 5L, align = "right"), 1L))
# issuance-amount controls (added after seeing that total SUN outstanding "responds" on
# day 0): change in total outstanding of each instrument over [t-1, t+h], % of t-1
CTRL_AMT <- lapply(0:H_D, function(h) {
  a <- sapply(INSTR, function(i) { o <- W[[paste0("total_", i)]]; 100 * (shift_lead(o, h) - shift(o)) / shift(o) })
  colnames(a) <- paste0("I_", INSTR)
  cbind(CTRL[[h + 1L]], a)
})
# windows [t-1, t+h] that overlap a date range
keep_window <- function(rng) lapply(0:H_D, function(h) {
  d_lo <- shift(W$date, 1L); d_hi <- shift_lead(W$date, h)
  !(d_lo <= rng[2] & d_hi >= rng[1]) %in% TRUE
})
KEEP_COVID <- keep_window(COVID)
KEEP_PAND  <- keep_window(PANDEMIC)
# event-row exclusions: drop the day-0 row of the listed events (all shocks share day 0)
ev_t0 <- function(d) unique(ev_all[date %in% as.IDate(d) & in_sample == TRUE, t0_next])
KEEP_DROP <- lapply(DROP_SETS, function(d) { k <- rep(TRUE, N); k[ev_t0(d)] <- FALSE; k })
for (nm in names(DROP_SETS))
  cat(sprintf("%s drops day-0 rows: %s\n", nm, paste(W$date[!KEEP_DROP[[nm]]], collapse = ", ")))
# fixed event sample across horizons: only days whose h = 20 window is inside the data
KEEP_FIXED <- seq_len(N) <= N - H_D

# =============================================================================
# 5. Estimators
# =============================================================================
lag_mat <- function(d1, from = 1L) sapply(seq(from, from + NLAG_D - 1L), function(l) shift(d1, l))
lp_allday <- function(dh, d1, e, h, ctrl, keep, evflag, lags_from = 1L) {
  X <- cbind(e = e, lag_mat(d1, lags_from))
  if (!is.null(ctrl)) X <- cbind(X, ctrl)
  ok <- complete.cases(dh, X) & keep
  nw <- nw_lp(dh[ok], X[ok, , drop = FALSE], lag = h + 5L)
  data.table(b = unname(nw$coef[2]), se = unname(nw$se[2]), n_days = nw$n,
             n_events = sum(evflag[ok]), n_events_nonzero = sum(e[ok] != 0))
}
lp_events <- function(dh, e, rows, ctrl) {
  y <- dh[rows]; X <- cbind(e = e[rows])
  if (!is.null(ctrl)) X <- cbind(X, ctrl[rows, , drop = FALSE])
  ok <- complete.cases(y, X)
  fit <- lm(y[ok] ~ X[ok, , drop = FALSE])
  V <- sandwich::vcovHC(fit, type = "HC1")
  data.table(b = unname(coef(fit)[2]), se = sqrt(V[2, 2]), n_days = sum(ok),
             n_events = sum(ok), n_events_nonzero = sum(X[ok, 1] != 0))
}
# Permutation test. The non-zero event values that enter THIS regression (event days in
# the estimation sample) are re-assigned to random non-event trading days that are also
# in the estimation sample; b by FWL. Restricting values and pool to the estimation
# sample (fix after the verification) keeps the permuted design comparable with the
# observed one in samples that drop windows or events.
# wday = TRUE: each value goes to a non-event day of the SAME weekday as its actual day 0
# (added after seeing the pre-window results: day 0 is almost always a Thursday, the main
# auction-settlement day, so event days are not exchangeable with arbitrary days).
perm_p <- function(dh, d1, ctrl, e, b_obs, lags_from = 1L, keep = TRUE, wday = FALSE) {
  Z <- cbind(1, lag_mat(d1, lags_from), ctrl)
  ok <- complete.cases(dh, Z) & !is.na(e) & keep
  okr <- which(ok)
  evr <- okr[e[okr] != 0]; vals <- e[evr]; k <- length(vals)
  pool <- intersect(POOL, okr)
  if (!wday) {
    P <- matrix(replicate(NPERM, pool[sample.int(length(pool), k)]), nrow = k)
  } else {
    wd <- W$wday[evr]; P <- matrix(0L, k, NPERM); pools <- split(pool, W$wday[pool])
    for (w in unique(wd)) {
      ix <- which(wd == w); p <- pools[[w]]
      P[ix, ] <- matrix(replicate(NPERM, p[sample.int(length(p), length(ix))]), nrow = length(ix))
    }
  }
  qz <- qr(Z[ok, , drop = FALSE]); yt <- qr.resid(qz, dh[ok])
  Q <- qr.Q(qz)[, seq_len(qz$rank), drop = FALSE]
  # self-check: FWL on the observed shock reproduces b_obs
  eo <- e[ok]; et <- eo - drop(Q %*% crossprod(Q, eo))
  stopifnot(abs(sum(yt * et) / sum(et^2) - b_obs) <= 1e-7 * max(1, abs(b_obs)))
  pos <- match(P, okr)          # column-major: draw j occupies positions (j-1)k+1..jk
  num <- colSums(matrix(yt[pos] * vals, nrow = k))
  QtE <- rowsum(Q[pos, , drop = FALSE] * vals, rep(seq_len(NPERM), each = k), reorder = FALSE)
  bp <- num / (sum(vals^2) - rowSums(QtE^2))
  (1 + sum(abs(bp) >= abs(b_obs) - 1e-12)) / (NPERM + 1)
}
# joint Newey-West for several single-equation LPs on the same days (stacked scores),
# reproducing sandwich::NeweyWest(prewhite = FALSE, adjust = TRUE) for each equation
joint_nw <- function(ys, Xs, lag) {
  n <- length(ys[[1]])
  P <- lapply(seq_along(ys), function(j) {
    X <- cbind(1, Xs[[j]]); XtXi <- solve(crossprod(X))
    b <- drop(XtXi %*% crossprod(X, ys[[j]])); u <- drop(ys[[j]] - X %*% b)
    list(b = b, XtXi = XtXi, S = X * u, k = ncol(X))
  })
  ks <- vapply(P, `[[`, 1L, "k"); stopifnot(length(unique(ks)) == 1L)
  S <- do.call(cbind, lapply(P, `[[`, "S"))
  M <- crossprod(S)
  for (l in seq_len(lag)) {
    G <- crossprod(S[(l + 1L):n, , drop = FALSE], S[seq_len(n - l), , drop = FALSE])
    M <- M + (1 - l / (lag + 1)) * (G + t(G))
  }
  K <- sum(ks); B <- matrix(0, K, K); off <- c(0L, cumsum(ks))
  for (j in seq_along(P)) B[off[j] + seq_len(ks[j]), off[j] + seq_len(ks[j])] <- P[[j]]$XtXi
  V <- B %*% M %*% B * n / (n - ks[1])
  ie <- off[-length(off)] + 2L    # coefficient on e (after the constant)
  list(be = vapply(P, function(p) p$b[2], 0), Vee = V[ie, ie, drop = FALSE], n = n)
}

SPECS <- data.table(
  spec   = c("allday_settle", "allday_nosettle", "allday_same_settle", "allday_exCOVID_settle",
             "allday_exPandemic_settle", "allday_issuance_settle", "events_hc1", "events_hc1_settle",
             "allday_fixedsample_settle", "allday_drop0303_settle", "allday_dropMar20x2_settle",
             "allday_dropMar20x3_settle", "allday_t2aligned_settle"),
  timing = c(rep("next", 2), "same", rep("next", 10)),
  ctrl   = c("count", "none", "count", "count", "count", "amount", "none", "count",
             "count", "count", "count", "count", "count_t2"),
  keep   = c("all", "all", "all", "covid", "pandemic", "all", "all", "all",
             "fixed", "drop0303", "dropMar20x2", "dropMar20x3", "all"),
  outc   = c(rep("dh", 12), "t2"),
  events = c(rep(FALSE, 6), TRUE, TRUE, rep(FALSE, 5)),
  stage  = c(rep("before_results", 4), rep("after_results", 2), rep("before_results", 2),
             rep("after_verification", 5)))
PRIMARY_SPEC <- "allday_settle"
PERM_SPECS   <- c("allday_settle", "allday_exCOVID_settle", "allday_exPandemic_settle",
                  "allday_fixedsample_settle", "allday_drop0303_settle", "allday_dropMar20x2_settle",
                  "allday_dropMar20x3_settle", "allday_t2aligned_settle")
ALLKEEP <- rep(TRUE, nrow(W))
get_keep <- function(k, h) {
  if (k %in% names(KEEP_DROP)) return(KEEP_DROP[[k]])
  switch(k, all = ALLKEEP, covid = KEEP_COVID[[h + 1L]], pandemic = KEEP_PAND[[h + 1L]], fixed = KEEP_FIXED)
}
get_ctrl <- function(c, h) switch(c, none = NULL, count = CTRL[[h + 1L]], amount = CTRL_AMT[[h + 1L]],
                                  count_t2 = CTRL[[h + 1L]] - CTRL[[2L]])   # settlements in [t+2, t+h]
get_dh <- function(o, outc, h) if (outc == "t2") o$dh_t2[[h + 1L]] else o$dh[[h + 1L]]
# pre-window [t-6, t-1] samples
pre_keep <- function(rng) !(shift(W$date, 6L) <= rng[2] & shift(W$date, 1L) >= rng[1]) %in% TRUE
PRE_KEEPS <- c(list(all = ALLKEEP, exCOVID = pre_keep(COVID), exPandemic = pre_keep(PANDEMIC),
                    fixedsample = KEEP_FIXED), KEEP_DROP)

res <- list(); pre <- list()
for (s in SHOCKS_D) {
  e_next <- shock_vec(s, "next"); e_same <- shock_vec(s, "same")
  f_next <- event_flag(s, "next"); f_same <- event_flag(s, "same")
  rows_ev <- event_rows(s)
  nz <- which(!is.na(e_next) & e_next != 0)
  cat(sprintf("%s: weekday of day 0 (nonzero events): %s\n", s,
              paste(names(table(W$wday[nz])), table(W$wday[nz]), sep = "=", collapse = ", ")))
  for (on in names(OUTS)) {
    o <- OUTS[[on]]
    do_perm <- on %in% NR_OUTS && !grepl("\\|rp$", on)
    specs <- if (on %in% NR_OUTS) SPECS else SPECS[spec %in% c("allday_settle", "allday_nosettle")]
    for (k in seq_len(nrow(specs))) {
      sp <- specs[k]
      e  <- if (sp$timing == "next") e_next else e_same
      fl <- if (sp$timing == "next") f_next else f_same
      for (h in 0:H_D) {
        if (sp$outc == "t2" && h < 2L) next
        dh <- get_dh(o, sp$outc, h); ctrl <- get_ctrl(sp$ctrl, h); keep <- get_keep(sp$keep, h)
        r <- if (sp$events) lp_events(dh, e_next, rows_ev, ctrl) else
          lp_allday(dh, o$d1, e, h, ctrl, keep, fl)
        r[, `:=`(shock = s, outcome = on, spec = sp$spec, h = h, se_type = if (sp$events) "HC1" else "NW")]
        if (sp$spec %in% PERM_SPECS && do_perm)
          r[, `:=`(p_perm = perm_p(dh, o$d1, ctrl, e, b, keep = keep),
                   p_perm_wday = perm_p(dh, o$d1, ctrl, e, b, keep = keep, wday = TRUE))]
        res[[length(res) + 1L]] <- r
      }
    }
    # pre-event placebo: change over [t-6, t-1] on e_t (lags dated t-6..t-10)
    if (do_perm) {
      for (kp in names(PRE_KEEPS)) {
        kv <- PRE_KEEPS[[kp]]
        r <- lp_allday(o$pre, o$d1, e_next, 0L, CTRL_PRE, kv, f_next, lags_from = 6L)
        r[, `:=`(p_perm = perm_p(o$pre, o$d1, CTRL_PRE, e_next, b, lags_from = 6L, keep = kv),
                 p_perm_wday = perm_p(o$pre, o$d1, CTRL_PRE, e_next, b, lags_from = 6L, keep = kv, wday = TRUE))]
        r[, `:=`(shock = s, outcome = on, h = -1L, se_type = "NW",
                 spec = if (kp == "all") "pre_window_m6_m1_settle" else paste0("pre_window_m6_m1_settle_", kp))]
        pre[[length(pre) + 1L]] <- r
      }
    }
  }
  cat(sprintf("done: %s\n", s))
}
res <- rbindlist(res, fill = TRUE)
pre <- rbindlist(pre, fill = TRUE)

decorate <- function(x, sdv) {
  x[, c("holder", "instrument", "scaling") := tstrsplit(outcome, "|", fixed = TRUE)]
  x[instrument == "diff", instrument := "SBSN_minus_SUN"]
  x[, unit := fcase(scaling == "pct", "percent of instrument's outstanding at t-1",
                    scaling == "log", "percent (100 x log change)",
                    scaling == "rp",  "Rp tn")]
  x[, sd_shock_pp := sdv[shock]]
  x[, `:=`(b25 = 0.25 * b, se25 = 0.25 * se, bsd = sd_shock_pp * b, sesd = sd_shock_pp * se)]
  x[, `:=`(lo90_25 = b25 - Z90 * se25, hi90_25 = b25 + Z90 * se25,
           lo90_sd = bsd - Z90 * sesd, hi90_sd = bsd + Z90 * sesd,
           mde25 = MDE_K * se25, mdesd = MDE_K * sesd, t = b / se, p_asy = 2 * pnorm(-abs(b / se)))]
  x[]
}
res <- decorate(res, SD_EV); pre <- decorate(pre, SD_EV)
res <- merge(res, SPECS[, .(spec, spec_stage = stage)], by = "spec", all.x = TRUE)
setcolorder(res, c("shock", "spec", "spec_stage", "holder", "instrument", "scaling", "unit", "h"))
setorder(res, shock, spec, outcome, h)
fwrite(res, file.path(TAB, "sov_daily_lp_all.csv"))
fwrite(pre, file.path(TAB, "sov_daily_pretrend.csv"))

# =============================================================================
# 5b. Leave-one-event-out (added after the verification): primary shock and spec,
#     non-resident outcomes, h in {0, 2, 5, 10, 20} and the full-sample pre-window placebo
# =============================================================================
LOEO_OUTS <- c("nonresidents|SUN|pct", "nonresidents|SBSN|pct", "nonresidents|diff|pct",
               "nonresidents|SUN|log", "nonresidents|SBSN|log", "nonresidents|diff|log")
LOEO_H <- c(0L, 2L, 5L, 10L, 20L)
e_p <- shock_vec(PRIMARY, "next"); f_p <- event_flag(PRIMARY, "next")
loeo <- list()
for (tr in which(f_p)) {
  kv <- rep(TRUE, N); kv[tr] <- FALSE
  for (on in LOEO_OUTS) {
    o <- OUTS[[on]]
    for (h in LOEO_H) {
      r <- lp_allday(o$dh[[h + 1L]], o$d1, e_p, h, CTRL[[h + 1L]], kv, f_p)
      loeo[[length(loeo) + 1L]] <- r[, `:=`(drop_row = tr, outcome = on, h = h)]
    }
    r <- lp_allday(o$pre, o$d1, e_p, 0L, CTRL_PRE, kv, f_p, lags_from = 6L)
    loeo[[length(loeo) + 1L]] <- r[, `:=`(drop_row = tr, outcome = on, h = -1L)]
  }
}
loeo <- rbindlist(loeo)
loeo[, shock := PRIMARY]
loeo <- decorate(loeo, SD_EV)
evp <- ev[shock == PRIMARY, .(drop_row = t0_next, dropped_et_date = date, jk_missing_sp500)]
loeo <- merge(loeo, evp, by = "drop_row", all.x = TRUE)
loeo[, `:=`(dropped_day0 = W$date[drop_row], dropped_value_bp = 100 * e_p[drop_row])]
setcolorder(loeo, c("shock", "dropped_et_date", "dropped_day0", "dropped_value_bp", "jk_missing_sp500",
                    "holder", "instrument", "scaling", "h"))
setorder(loeo, instrument, scaling, h, dropped_day0)
fwrite(loeo[, !"drop_row"], file.path(TAB, "sov_loeo_nonres.csv"))
full_ref <- rbind(res[shock == PRIMARY & spec == PRIMARY_SPEC & outcome %in% LOEO_OUTS & h %in% LOEO_H,
                      .(outcome, h, bsd_full = bsd, sesd_full = sesd, p_full = p_asy)],
                  pre[shock == PRIMARY & spec == "pre_window_m6_m1_settle" & outcome %in% LOEO_OUTS,
                      .(outcome, h, bsd_full = bsd, sesd_full = sesd, p_full = p_asy)])
loeo_sum <- loeo[, .(n_drops = .N, bsd_min = min(bsd), day0_at_min = dropped_day0[which.min(bsd)],
                     bsd_max = max(bsd), day0_at_max = dropped_day0[which.max(bsd)],
                     t_min = min(t), t_max = max(t), n_p_below_010 = sum(p_asy < 0.10),
                     n_p_below_005 = sum(p_asy < 0.05)),
                 by = .(outcome, instrument, scaling, h)]
loeo_sum <- merge(full_ref, loeo_sum, by = c("outcome", "h"))
d0303 <- loeo[dropped_et_date == as.IDate("2020-03-03"), .(outcome, h, bsd_drop0303 = bsd, sesd_drop0303 = sesd,
                                                          p_drop0303 = p_asy)]
loeo_sum <- merge(loeo_sum, d0303, by = c("outcome", "h"))
# range excluding the 2020-03-03 drop
ex0303 <- loeo[dropped_et_date != as.IDate("2020-03-03") | is.na(dropped_et_date),
               .(bsd_min_ex0303 = min(bsd), bsd_max_ex0303 = max(bsd)), by = .(outcome, h)]
loeo_sum <- merge(loeo_sum, ex0303, by = c("outcome", "h"))
setorder(loeo_sum, instrument, scaling, h)
fwrite(loeo_sum, file.path(TAB, "sov_loeo_summary.csv"))
cat("\n=== leave-one-event-out, jk_mp_median, per 1 s.d. (h = -1: pre-window placebo) ===\n")
print(loeo_sum[, .(instrument, scaling, h, full = fmt(bsd_full, 4), min = fmt(bsd_min, 4), at_min = day0_at_min,
                   max = fmt(bsd_max, 4), at_max = day0_at_max, t_min = fmt(t_min, 2), t_max = fmt(t_max, 2),
                   drop0303 = fmt(bsd_drop0303, 4), p0303 = fmt(p_drop0303, 3),
                   min_ex = fmt(bsd_min_ex0303, 4), max_ex = fmt(bsd_max_ex0303, 4))], nrows = 100)

# =============================================================================
# 5c. Composition-only benchmark for the % of outstanding differential
# =============================================================================
# Non-residents hold a much smaller share of SBSN than of SUN, so equal PROPORTIONAL
# selling (equal log responses) already makes SBSN fall less in % of outstanding.
# Benchmark differential ~ b_log(SUN) x NR share(SBSN)/100 - b_pct(SUN), shares = mean NR
# share at day -1 of the primary shock's in-sample events. Gap = observed - benchmark =
# b_diff_pct - b_log(SUN) x share(SBSN)/100 + b_pct(SUN). A positive gap would mean SBSN
# non-residents sell proportionally LESS than SUN non-residents. The gap's s.e. comes from
# a joint NW over the three equations (added after the verification).
rr <- event_rows(PRIMARY) - 1L
sh_ev <- sapply(INSTR, function(i) mean(100 * W[[paste0("nonresidents_", i)]][rr] / W[[paste0("total_", i)]][rr]))
bm <- dcast(res[holder == "nonresidents" & grepl("^allday", spec) &
                  ((instrument == "SUN" & scaling %in% c("pct", "log")) |
                   (instrument == "SBSN" & scaling == "pct") |
                   (instrument == "SBSN_minus_SUN" & scaling == "pct"))],
            shock + spec + h ~ paste(instrument, scaling, sep = "_"), value.var = c("bsd", "sesd", "lo90_sd", "hi90_sd"))
bm[, `:=`(nr_share_SUN_dm1 = sh_ev[["SUN"]], nr_share_SBSN_dm1 = sh_ev[["SBSN"]])]
bm[, `:=`(check_SUN_pct_from_log = bsd_SUN_log * nr_share_SUN_dm1 / 100,
          bench_diff_pct_sd = bsd_SUN_log * nr_share_SBSN_dm1 / 100 - bsd_SUN_pct,
          bench_SBSN_pct_sd = bsd_SUN_log * nr_share_SBSN_dm1 / 100)]
bm[, gap_obs_minus_bench_sd := bsd_SBSN_minus_SUN_pct - bench_diff_pct_sd]

o_d <- OUTS[["nonresidents|diff|pct"]]; o_sl <- OUTS[["nonresidents|SUN|log"]]; o_sp <- OUTS[["nonresidents|SUN|pct"]]
a_gap <- c(1, -sh_ev[["SBSN"]] / 100, 1)
gp <- list()
for (s in SHOCKS_D) {
  e_next <- shock_vec(s, "next"); e_same <- shock_vec(s, "same")
  for (k in which(!SPECS$events)) {
    sp <- SPECS[k]; e <- if (sp$timing == "next") e_next else e_same
    for (h in 0:H_D) {
      if (sp$outc == "t2" && h < 2L) next
      ctrl <- get_ctrl(sp$ctrl, h); keep <- get_keep(sp$keep, h)
      Xs <- lapply(list(o_d, o_sl, o_sp), function(o) { X <- cbind(e = e, lag_mat(o$d1)); if (!is.null(ctrl)) X <- cbind(X, ctrl); X })
      ys <- lapply(list(o_d, o_sl, o_sp), get_dh, outc = sp$outc, h = h)
      oks <- Map(function(y, X) complete.cases(y, X) & keep, ys, Xs)
      stopifnot(identical(oks[[1]], oks[[2]]), identical(oks[[1]], oks[[3]]))
      ok <- oks[[1]]
      jn <- joint_nw(lapply(ys, `[`, ok), lapply(Xs, function(X) X[ok, , drop = FALSE]), lag = h + 5L)
      gp[[length(gp) + 1L]] <- data.table(shock = s, spec = sp$spec, h = h,
        jb_diff = jn$be[1], jb_SUN_log = jn$be[2], jb_SUN_pct = jn$be[3],
        jse_diff = sqrt(jn$Vee[1, 1]), jse_SUN_log = sqrt(jn$Vee[2, 2]), jse_SUN_pct = sqrt(jn$Vee[3, 3]),
        gap_b = sum(a_gap * jn$be), gap_se = sqrt(drop(t(a_gap) %*% jn$Vee %*% a_gap)), n_days_joint = jn$n)
    }
  }
}
gp <- rbindlist(gp)
# the joint estimator must reproduce the single-equation estimates and NW s.e.
chk <- merge(gp, dcast(res[holder == "nonresidents" & grepl("^allday", spec) &
                             ((instrument == "SUN" & scaling %in% c("pct", "log")) |
                              (instrument == "SBSN_minus_SUN" & scaling == "pct"))],
                       shock + spec + h ~ paste(instrument, scaling, sep = "_"), value.var = c("b", "se")),
             by = c("shock", "spec", "h"))
dev_b  <- chk[, max(abs(c(jb_diff - b_SBSN_minus_SUN_pct, jb_SUN_log - b_SUN_log, jb_SUN_pct - b_SUN_pct)) /
                      pmax(1, abs(c(b_SBSN_minus_SUN_pct, b_SUN_log, b_SUN_pct))))]
dev_se <- chk[, max(abs(c(jse_diff / se_SBSN_minus_SUN_pct, jse_SUN_log / se_SUN_log, jse_SUN_pct / se_SUN_pct) - 1))]
cat(sprintf("\nJoint NW check vs single-equation NW: max rel. dev. b %.2e, se %.2e\n", dev_b, dev_se))
stopifnot(dev_b < 1e-6, dev_se < 1e-6)
gp[, sd_shock_pp := SD_EV[shock]]
gp[, `:=`(gap_sd_joint = sd_shock_pp * gap_b, gap_se_sd = sd_shock_pp * gap_se,
          gap_25 = 0.25 * gap_b, gap_se_25 = 0.25 * gap_se, gap_p_nw = 2 * pnorm(-abs(gap_b / gap_se)))]
bm <- merge(bm, gp[, .(shock, spec, h, gap_sd_joint, gap_se_sd, gap_25, gap_se_25, gap_p_nw)],
            by = c("shock", "spec", "h"), all.x = TRUE)
stopifnot(bm[, max(abs(gap_sd_joint - gap_obs_minus_bench_sd))] < 1e-8)
bm[, gap_sd_joint := NULL]
fwrite(bm, file.path(TAB, "sov_composition_benchmark.csv"))
# the same gap on the pre-window [t-6, t-1] placebo outcomes (added after the verification)
gpp <- list()
for (s in SHOCKS_D) {
  e_next <- shock_vec(s, "next")
  for (kp in names(PRE_KEEPS)) {
    kv <- PRE_KEEPS[[kp]]
    Xs <- lapply(list(o_d, o_sl, o_sp), function(o) cbind(e = e_next, lag_mat(o$d1, 6L), CTRL_PRE))
    ys <- lapply(list(o_d, o_sl, o_sp), `[[`, "pre")
    oks <- Map(function(y, X) complete.cases(y, X) & kv, ys, Xs)
    stopifnot(identical(oks[[1]], oks[[2]]), identical(oks[[1]], oks[[3]]))
    ok <- oks[[1]]
    jn <- joint_nw(lapply(ys, `[`, ok), lapply(Xs, function(X) X[ok, , drop = FALSE]), lag = 5L)
    gpp[[length(gpp) + 1L]] <- data.table(
      shock = s, spec = if (kp == "all") "pre_window_m6_m1_settle" else paste0("pre_window_m6_m1_settle_", kp), h = -1L,
      jb_diff = jn$be[1], jse_diff = sqrt(jn$Vee[1, 1]),
      gap_b = sum(a_gap * jn$be), gap_se = sqrt(drop(t(a_gap) %*% jn$Vee %*% a_gap)), n_days_joint = jn$n)
  }
}
gpp <- rbindlist(gpp)
chk2 <- merge(gpp, pre[instrument == "SBSN_minus_SUN" & scaling == "pct", .(shock, spec, b, se)], by = c("shock", "spec"))
stopifnot(nrow(chk2) == nrow(gpp), chk2[, max(abs(jb_diff - b) / pmax(1, abs(b)))] < 1e-6,
          chk2[, max(abs(jse_diff / se - 1))] < 1e-6)
gpp[, sd_shock_pp := SD_EV[shock]]
gpp[, `:=`(gap_sd = sd_shock_pp * gap_b, gap_se_sd = sd_shock_pp * gap_se, gap_25 = 0.25 * gap_b,
           gap_se_25 = 0.25 * gap_se, gap_p_nw = 2 * pnorm(-abs(gap_b / gap_se)))]
fwrite(gpp[, !c("jb_diff", "jse_diff")], file.path(TAB, "sov_composition_gap_pretrend.csv"))
cat("\n=== composition gap on the pre-window placebo outcomes, per 1 s.d. ===\n")
print(gpp[, .(shock, spec, gap = fmt(gap_sd, 4), se = fmt(gap_se_sd, 4), p = fmt(gap_p_nw, 3), n_days_joint)], nrows = 100)
cat(sprintf("\nMean non-resident share at day -1 of %s events: SUN %.2f%%, SBSN %.2f%%\n",
            PRIMARY, sh_ev[["SUN"]], sh_ev[["SBSN"]]))
cat("=== composition benchmark, per 1 s.d. (jk_mp_median) ===\n")
print(bm[shock == PRIMARY & h %in% c(0L, 2L, 5L, 10L, 20L),
         .(spec, h, SUN_pct = fmt(bsd_SUN_pct, 4), SUN_pct_from_log = fmt(check_SUN_pct_from_log, 4),
           SBSN_pct = fmt(bsd_SBSN_pct, 4), SBSN_lo = fmt(lo90_sd_SBSN_pct, 4), SBSN_hi = fmt(hi90_sd_SBSN_pct, 4),
           bench_SBSN = fmt(bench_SBSN_pct_sd, 4),
           diff_obs = fmt(bsd_SBSN_minus_SUN_pct, 4), diff_se = fmt(sesd_SBSN_minus_SUN_pct, 4),
           bench = fmt(bench_diff_pct_sd, 4), gap = fmt(gap_obs_minus_bench_sd, 4), gap_se = fmt(gap_se_sd, 4),
           gap_p = fmt(gap_p_nw, 3))], nrows = 200)

# =============================================================================
# 5d. Summary tables
# =============================================================================
# headline: primary shock, primary spec and the main robustness specs, non-residents
HSEL <- c(0L, 1L, 2L, 5L, 10L, 15L, 20L)
HEAD_SPECS <- c(PRIMARY_SPEC, "events_hc1", "events_hc1_settle", "allday_fixedsample_settle",
                "allday_drop0303_settle", "allday_t2aligned_settle")
head_tab <- res[shock == PRIMARY & spec %in% HEAD_SPECS & holder == "nonresidents" & h %in% HSEL,
                .(spec, spec_stage, se_type, instrument, scaling, unit, h, b25, se25, lo90_25, hi90_25, bsd, sesd,
                  mde25, mdesd, p_asy, p_perm, p_perm_wday, n_days, n_events)]
setorder(head_tab, spec, scaling, instrument, h)
fwrite(head_tab, file.path(TAB, "sov_headline.csv"))
cat("\n=== headline: non-residents, jk_mp_median, per 25 bp and per 1 s.d. ===\n")
print(head_tab[scaling != "rp", .(spec, se_type, instrument, scaling, h, b25 = fmt(b25), se25 = fmt(se25),
                   bsd = fmt(bsd, 4), sesd = fmt(sesd, 4), mdesd = fmt(mdesd, 4), p_asy = fmt(p_asy, 3),
                   p_perm = fmt(p_perm, 3), p_perm_wday = fmt(p_perm_wday, 3), n_days, n_events)], nrows = 400)

# non-resident results at selected horizons, all shocks and specs (source for the notes)
key <- res[holder == "nonresidents" & h %in% c(0L, 1L, 2L, 5L, 10L, 20L),
           .(shock, spec, spec_stage, se_type, instrument, scaling, unit, h, b25, se25, bsd, sesd, p_asy,
             p_perm, p_perm_wday, mde25, mdesd, n_days, n_events)]
setorder(key, shock, spec, scaling, instrument, h)
fwrite(key, file.path(TAB, "sov_key_nonres.csv"))

# compact cross-shock / cross-spec view of the differential and the levels
xs <- res[holder == "nonresidents" & scaling %in% c("pct", "log") & h %in% c(0L, 2L, 5L, 10L, 20L)]
xs[, est := sprintf("%.4f (%.4f)", bsd, sesd)]
xsw <- dcast(xs, shock + spec + scaling + instrument ~ h, value.var = "est")
fwrite(xsw, file.path(TAB, "sov_daily_nonres_by_shock_spec_persd.csv"))
cat("\n=== non-residents, per 1 s.d. (s.e.), primary shock, all specs ===\n")
print(xsw[shock == PRIMARY], nrows = 400)
cat("\n=== non-residents SUN pct, per 1 s.d. (s.e.), p, all shocks, event-exclusion specs ===\n")
print(res[holder == "nonresidents" & instrument == "SUN" & scaling == "pct" & h %in% c(5L, 20L) &
            spec %in% c(PRIMARY_SPEC, "allday_drop0303_settle", "allday_dropMar20x2_settle", "allday_dropMar20x3_settle",
                        "allday_exCOVID_settle", "allday_fixedsample_settle"),
          .(shock, spec, h, bsd = fmt(bsd, 4), sesd = fmt(sesd, 4), p = fmt(p_asy, 3), p_perm = fmt(p_perm, 3), n_events)],
      nrows = 400)
cat("\n=== pre-event placebo (change over [-6,-1]) per 1 s.d. ===\n")
print(pre[scaling != "rp", .(spec, shock, instrument, scaling, bsd = fmt(bsd, 4), sesd = fmt(sesd, 4),
              mdesd = fmt(mdesd, 4), p = fmt(p_asy, 3), p_perm = fmt(p_perm, 3), p_perm_wday = fmt(p_perm_wday, 3),
              n_days, n_events)], nrows = 400)

# all holders, primary shock and spec: estimates relative to each holder's own position.
# share_dm1 = mean holder share of instrument outstanding at day -1 of the primary events.
hs <- rbindlist(lapply(INSTR, function(i) rbindlist(lapply(HOLDERS, function(hl)
  data.table(instrument = i, holder = hl,
             share_dm1 = mean(100 * W[[paste0(hl, "_", i)]][rr] / W[[paste0("total_", i)]][rr]))))))
hold_tab <- res[shock == PRIMARY & spec == PRIMARY_SPEC & scaling == "pct" & instrument %in% INSTR &
                  holder %in% c("total", HOLDERS),
                .(holder, instrument, h, b25, se25, lo90_25, hi90_25, bsd, sesd, p_asy, mde25, n_days, n_events)]
hold_tab <- merge(hold_tab, hs, by = c("holder", "instrument"), all.x = TRUE)
hold_tab[, `:=`(b25_pct_own = 100 * b25 / share_dm1, se25_pct_own = 100 * se25 / share_dm1,
                mde25_pct_own = 100 * mde25 / share_dm1)]
setorder(hold_tab, holder, instrument, h)
fwrite(hold_tab, file.path(TAB, "sov_holders_primary.csv"))
cat("\n=== holders, jk_mp_median, primary spec, per 25 bp, pp of outstanding (p) ===\n")
hw <- hold_tab[h %in% c(0L, 5L, 10L, 15L, 20L)][, `:=`(est = sprintf("%.3f (%.3f) p%.2f", b25, se25, p_asy),
                                                      share = round(share_dm1, 2))]
print(dcast(hw, holder + instrument + share ~ h, value.var = "est"), nrows = 200)
cat("\n=== SBSN holders with p < 0.10 at some horizon (primary spec, per 25 bp) ===\n")
print(hold_tab[instrument == "SBSN" & p_asy < 0.10, .(holder, h, b25 = fmt(b25), se25 = fmt(se25),
                                                     p = fmt(p_asy, 3), pct_own = fmt(b25_pct_own, 1))], nrows = 200)

# =============================================================================
# 6. Monthly: non-resident holdings by maturity bucket (descriptive LPs)
# =============================================================================
mm <- fread(file.path(CLEAN, "djppr_nonresident_maturity_monthly.csv"))
mm[, date := as.IDate(date)]
mm <- mm[instrument %in% INSTR]
mm[, `:=`(m = mid(date), nr = holdings_rp_bn / 1000)]
stopifnot(mm[, .N, by = .(m, instrument, maturity_bucket)][, all(N == 1L)])
# outstanding of I on the last trading day of each month (daily file)
Wfull <- dcast(hd[holder == "total"], date ~ instrument, value.var = "holdings_rp_tn")
outm <- Wfull[, m := mid(date)][order(date), .SD[.N], by = m][, .(m, out_SUN = SUN, out_SBSN = SBSN)]
outm <- melt(outm, id.vars = "m", variable.name = "instrument", value.name = "outst")
outm[, instrument := sub("out_", "", instrument)]
mm <- merge(mm, outm, by = c("m", "instrument"), all.x = TRUE)

bshare <- mm[maturity_bucket != "total", .(nr = sum(nr)), by = .(instrument, maturity_bucket, m)]
bshare[, share_pct := 100 * nr / sum(nr), by = .(instrument, m)]
bsh <- bshare[, .(mean_rp_tn = mean(nr), mean_share_pct = mean(share_pct),
                  share_first = share_pct[m == min(m)], share_last = share_pct[m == max(m)]),
              by = .(instrument, maturity_bucket)]
fwrite(bsh, file.path(TAB, "sov_monthly_bucket_shares.csv"))
cat("\n=== non-resident holdings by maturity bucket ===\n"); print(bsh)

shk_m <- shk_m[, c("m", SHOCKS_M), with = FALSE]
# Monthly shocks by Jakarta day-0 month (fix after the verification): the monthly file
# assigns each event to its ET month. Events whose Jakarta day 0 falls in the next month
# are moved there (an NA event makes both months NA). ET-month sums of the event file
# reproduce load_shocks() exactly for these shocks over 2016-2022 (checked separately).
shk_mj <- copy(shk_m)
mv <- ev_all[shock %in% SHOCKS_D & in_sample == TRUE][, d0 := W$date[t0_next]][mid(d0) != mid(date)]
cat("\nEvents moved to the following month by the Jakarta day-0 assignment:\n")
print(mv[, .(shock, date, time_et, day0 = d0, value)])
for (r in seq_len(nrow(mv))) {
  s <- mv$shock[r]; v <- mv$value[r]; m0 <- mid(mv$date[r]); m1 <- mid(mv$d0[r])
  if (is.na(v)) shk_mj[m %in% c(m0, m1), (s) := NA_real_] else {
    shk_mj[m == m0, (s) := get(s) - v]; shk_mj[m == m1, (s) := get(s) + v]
  }
}
SHK_MONTHLY <- list(et_month = shk_m, jakarta_day0_month = shk_mj)

mres <- list()
for (tm in names(SHK_MONTHLY)) for (i in INSTR) for (bk in unique(mm$maturity_bucket)) {
  x <- mm[instrument == i & maturity_bucket == bk][order(m)]
  stopifnot(all(diff(x$m) == 1L))
  x <- merge(x, SHK_MONTHLY[[tm]], by = "m", all.x = TRUE)
  x[, dyv := 100 * (nr - shift(nr)) / shift(outst)]
  for (l in 1:3) x[, paste0("lag", l) := shift(dyv, l)]
  for (s in SHOCKS_M) for (h in 0:H_M) {
    z <- copy(x)
    z[, dh := 100 * (shift(nr, h, type = "lead") - shift(nr)) / shift(outst)]
    z <- z[complete.cases(z[, c("dh", s, "lag1", "lag2", "lag3"), with = FALSE])]
    X <- as.matrix(z[, c(s, "lag1", "lag2", "lag3"), with = FALSE])
    nw <- nw_lp(z$dh, X, lag = h + 1L)
    mres[[length(mres) + 1L]] <- data.table(month_timing = tm, instrument = i, bucket = bk, shock = s, h = h,
                                            b = unname(nw$coef[2]), se = unname(nw$se[2]), n_months = nw$n,
                                            first_m = as.character(mid2date(min(z$m))),
                                            last_m = as.character(mid2date(max(z$m))))
  }
}
mres <- rbindlist(mres)
mres[, sd_shock_pp := SD_M[shock]]
mres[, `:=`(b25 = 0.25 * b, se25 = 0.25 * se, bsd = sd_shock_pp * b, sesd = sd_shock_pp * se)]
mres[, `:=`(lo90_25 = b25 - Z90 * se25, hi90_25 = b25 + Z90 * se25, mde25 = MDE_K * se25, mdesd = MDE_K * sesd,
            p_nw = 2 * pnorm(-abs(b / se)), unit = "percent of instrument's total outstanding at t-1")]
fwrite(mres, file.path(TAB, "sov_monthly_maturity_lp.csv"))
mw <- mres[h %in% c(0L, 3L, 6L, 12L), .(est = sprintf("%7.3f (%5.3f)", bsd, sesd)),
           by = .(month_timing, shock, instrument, bucket, h)]
cat("\n=== monthly: non-resident holdings by maturity bucket, per 1 s.d. of the monthly shock ===\n")
print(dcast(mw[bucket == "total"], month_timing + shock + instrument + bucket ~ h, value.var = "est"), nrows = 200)
# monthly differential of totals (SBSN - SUN), percent of own outstanding
md0 <- merge(mm[maturity_bucket == "total", .(m, instrument, nr, outst)][instrument == "SBSN", .(m, nrB = nr, oB = outst)],
             mm[maturity_bucket == "total", .(m, instrument, nr, outst)][instrument == "SUN", .(m, nrS = nr, oS = outst)], by = "m")
mdres <- list()
for (tm in names(SHK_MONTHLY)) {
  md <- merge(md0[order(m)], SHK_MONTHLY[[tm]], by = "m", all.x = TRUE)
  md[, dyv := 100 * (nrB - shift(nrB)) / shift(oB) - 100 * (nrS - shift(nrS)) / shift(oS)]
  for (l in 1:3) md[, paste0("lag", l) := shift(dyv, l)]
  for (s in SHOCKS_M) for (h in 0:H_M) {
    z <- copy(md)
    z[, dh := 100 * (shift(nrB, h, type = "lead") - shift(nrB)) / shift(oB) -
              100 * (shift(nrS, h, type = "lead") - shift(nrS)) / shift(oS)]
    z <- z[complete.cases(z[, c("dh", s, "lag1", "lag2", "lag3"), with = FALSE])]
    nw <- nw_lp(z$dh, as.matrix(z[, c(s, "lag1", "lag2", "lag3"), with = FALSE]), lag = h + 1L)
    mdres[[length(mdres) + 1L]] <- data.table(month_timing = tm, shock = s, h = h, b = unname(nw$coef[2]),
                                              se = unname(nw$se[2]), n_months = nw$n)
  }
}
mdres <- rbindlist(mdres)
mdres[, sd_shock_pp := SD_M[shock]]
mdres[, `:=`(b25 = 0.25 * b, se25 = 0.25 * se, bsd = sd_shock_pp * b, sesd = sd_shock_pp * se,
             mde25 = MDE_K * 0.25 * se, mdesd = MDE_K * sd_shock_pp * se, p_nw = 2 * pnorm(-abs(b / se)))]
fwrite(mdres, file.path(TAB, "sov_monthly_diff_lp.csv"))
cat("\n=== monthly SBSN-minus-SUN non-resident change (pct of own outstanding) ===\n")
print(mdres[h %in% c(0L, 3L, 6L, 12L), .(month_timing, shock, h, b25 = fmt(b25), se25 = fmt(se25), bsd = fmt(bsd),
                                          sesd = fmt(sesd), p = fmt(p_nw, 3), n_months)], nrows = 200)

# =============================================================================
# 7. Figures (7 x 4.5 in, 200 dpi)
# =============================================================================
COL_I <- c("SUN" = "#2a78d6", "SBSN" = "#eb6834", "SBSN minus SUN" = "#52514e")
theme_sov <- function() theme_minimal(base_size = 9.5) +
  theme(panel.grid.minor = element_blank(), panel.grid.major.x = element_blank(),
        legend.position = "top", legend.title = element_blank(), plot.title.position = "plot",
        strip.text = element_text(face = "bold", hjust = 0),
        plot.caption = element_text(hjust = 0, colour = "#52514e", size = 7),
        plot.subtitle = element_text(colour = "#52514e", size = 8))
save_fig <- function(p, f) ggsave(file.path(FIG, f), p, width = 7, height = 4.5, dpi = 200, bg = "white")

# Fig 1: non-resident share of outstanding
s1 <- melt(sh, id.vars = "date", variable.name = "instrument", value.name = "share")
lab1 <- s1[, .SD[.N], by = instrument]
p1 <- ggplot(s1, aes(date, share, colour = instrument)) +
  geom_line(linewidth = 0.5) +
  geom_text(data = lab1, aes(label = instrument), hjust = -0.15, size = 3, show.legend = FALSE) +
  scale_colour_manual(values = COL_I) +
  scale_x_date(expand = expansion(mult = c(0.01, 0.07))) +
  scale_y_continuous(limits = c(0, NA), labels = function(x) paste0(x, "%")) +
  labs(x = NULL, y = "Non-resident holdings / outstanding",
       title = "Non-resident share of tradable Rupiah government bonds, SUN vs sukuk (SBSN)",
       caption = "Source: DJPPR daily ownership of tradable Rupiah SBN (face value), 2015-12-31 to 2022-06-27.") +
  theme_sov() + theme(legend.position = "none")
save_fig(p1, "sov_fig1_nonres_share.png")

# Fig 2: holder composition
HLAB <- c(nonresidents = "Non-residents", banks_conventional = "Conventional banks",
          banks_islamic = "Islamic banks", bi_net = "Bank Indonesia (net)",
          insurance_pension = "Insurance & pension", mutual_funds = "Mutual funds",
          individuals = "Individuals", others = "Others")
c2 <- copy(comp)
c2[, holder := factor(HLAB[holder], levels = HLAB[c("nonresidents", "banks_conventional", "banks_islamic",
                                                    "bi_net", "insurance_pension", "mutual_funds",
                                                    "individuals", "others")])]
c2[, instrument := factor(instrument, levels = INSTR, labels = c("SUN (conventional)", "SBSN (sukuk)"))]
COL8 <- c("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948")
p2 <- ggplot(c2, aes(date, share_pct, fill = holder)) +
  geom_area(position = "stack", linewidth = 0) +
  facet_wrap(~instrument) +
  scale_fill_manual(values = setNames(COL8, levels(c2$holder))) +
  scale_y_continuous(labels = function(x) paste0(x, "%"), expand = c(0, 0)) +
  scale_x_date(expand = c(0, 0)) +
  guides(fill = guide_legend(nrow = 2)) +
  labs(x = NULL, y = "Share of outstanding",
       title = "Who holds tradable Rupiah government bonds",
       caption = "Source: DJPPR daily ownership (face value). Islamic banks hold no SUN by construction of the DJPPR table.\nBank Indonesia net of SBN used in monetary operations with banks; insurance & pension merged across the 2020 break.") +
  theme_sov() + theme(panel.spacing = unit(1.2, "lines"))
save_fig(p2, "sov_fig2_holder_composition.png")

# Fig 3: non-resident IRFs, primary shock and spec (band), with the drop-2020-03-03 and
# fixed-event-sample point estimates overlaid
VLAB <- c(allday_settle = "Primary (90% NW band)", allday_drop0303_settle = "Dropping the 2020-03-03 event",
          allday_fixedsample_settle = "Fixed event sample (t <= T-21)")
f3 <- res[shock == PRIMARY & spec %in% names(VLAB) & holder == "nonresidents" & scaling %in% c("pct", "log")]
f3[, series := factor(fifelse(instrument == "SBSN_minus_SUN", "SBSN minus SUN", instrument), levels = names(COL_I))]
f3[, panel := factor(paste0(series, ": ", fifelse(scaling == "pct", "pp of outstanding", "log change, %")),
                     levels = c(paste0(names(COL_I), ": pp of outstanding"), paste0(names(COL_I), ": log change, %")))]
f3[, variant := factor(VLAB[spec], levels = VLAB)]
f3p <- f3[spec == PRIMARY_SPEC]
p3 <- ggplot(f3, aes(h, b25)) +
  geom_hline(yintercept = 0, colour = "grey60", linewidth = 0.3) +
  geom_ribbon(data = f3p, aes(ymin = lo90_25, ymax = hi90_25, fill = series), alpha = 0.18, colour = NA) +
  geom_line(aes(colour = series, linetype = variant), linewidth = 0.55) +
  facet_wrap(~panel, ncol = 3, scales = "free_y") +
  scale_colour_manual(values = COL_I, guide = "none") + scale_fill_manual(values = COL_I, guide = "none") +
  scale_linetype_manual(values = setNames(c("solid", "22", "62"), VLAB)) +
  labs(x = "Trading days after the FOMC announcement (day 0 = next Jakarta trading day)", y = NULL,
       title = "Non-resident holdings after a US pure monetary policy surprise (JK MP_median)",
       subtitle = sprintf("Per 25 bp tightening; 1 s.d. of the event shock = %.1f bp, so 25 bp = %.1f s.d. (linear extrapolation).",
                          100 * SD_EV[PRIMARY], 0.25 / SD_EV[PRIMARY]),
       caption = sprintf(paste0("All-trading-day LP, %d days, %d event days (2016-01 to 2022-06); controls: 5 lags of the outcome's daily change, settlement-day counts.\n",
                                "If secondary trades settle T+2 (not verified), positions on days 0-1 still reflect pre-announcement trades."),
                         max(f3p$n_days), max(f3p$n_events))) +
  theme_sov() + theme(legend.key.width = unit(1.6, "lines"))
save_fig(p3, "sov_fig3_irf_nonresidents.png")

# Fig 4: all holders, primary shock and spec
f4 <- res[shock == PRIMARY & spec == PRIMARY_SPEC & scaling == "pct" & holder %in% HOLDERS & instrument %in% INSTR]
f4[, holder := factor(HLAB[holder], levels = HLAB)]
f4[, instrument := factor(instrument, levels = INSTR)]
p4 <- ggplot(f4, aes(h, b25, colour = instrument, fill = instrument)) +
  geom_hline(yintercept = 0, colour = "grey60", linewidth = 0.3) +
  geom_ribbon(aes(ymin = lo90_25, ymax = hi90_25), alpha = 0.15, colour = NA) +
  geom_line(linewidth = 0.55) +
  facet_wrap(~holder, ncol = 4, scales = "free_y") +
  scale_colour_manual(values = COL_I[INSTR]) + scale_fill_manual(values = COL_I[INSTR]) +
  labs(x = "Trading days after the FOMC announcement", y = "% of instrument outstanding",
       title = "Holdings by investor type after a 25 bp US pure monetary policy surprise (JK MP_median)",
       subtitle = "Change from day -1 to day h, % of the instrument's outstanding at day -1; 90% NW bands. Islamic banks: SBSN only.",
       caption = "All-trading-day LP with settlement-day controls; free y-scales.") +
  theme_sov()
save_fig(p4, "sov_fig4_irf_holders.png")

# Fig 5: robustness of the non-resident differential, per 1 s.d., across shocks and specs
SLAB <- c(allday_settle = "All days, settlement counts (primary)", allday_nosettle = "All days, no settlement ctrl",
          allday_same_settle = "All days, same-date timing", allday_exCOVID_settle = "All days, excl. Mar-Apr 2020",
          allday_exPandemic_settle = "All days, excl. 2020-03..2021-12",
          allday_issuance_settle = "All days, + issuance amounts",
          events_hc1 = "Events only, HC1", events_hc1_settle = "Events only, HC1, settlement counts")
f5 <- res[holder == "nonresidents" & instrument == "SBSN_minus_SUN" & scaling == "pct" & h %in% c(0L, 2L, 5L, 10L, 20L) &
            spec %in% names(SLAB)]
f5[, spec := factor(SLAB[spec], levels = SLAB)]
f5[, shock := factor(shock, levels = SHOCKS_D)]
p5 <- ggplot(f5, aes(factor(h), bsd, colour = spec)) +
  geom_hline(yintercept = 0, colour = "grey60", linewidth = 0.3) +
  geom_pointrange(aes(ymin = lo90_sd, ymax = hi90_sd), position = position_dodge(width = 0.75),
                  size = 0.15, linewidth = 0.35) +
  facet_wrap(~shock, ncol = 3, scales = "free_y") +
  scale_colour_manual(values = setNames(COL8, SLAB)) +
  guides(colour = guide_legend(ncol = 1)) +
  labs(x = "Trading days after the announcement", y = "SBSN minus SUN, pp of outstanding",
       title = "Non-resident SBSN-minus-SUN differential: shocks and specifications",
       subtitle = "Per 1 s.d. of each shock's event distribution (2016-2022); 90% intervals.",
       caption = "Positive = non-resident SBSN holdings rise relative to SUN (% of each instrument's outstanding) after a positive surprise.\nbs_mps_orth: 2020 events are NA in the source and dropped.") +
  theme_sov() +
  theme(legend.position = "inside", legend.position.inside = c(0.84, 0.24),
        legend.text = element_text(size = 7), legend.key.height = unit(0.75, "lines"))
save_fig(p5, "sov_fig5_robustness_diff.png")

cat("\nFigures written: sov_fig1..5. Tables: sov_*.csv\n")
