# 13_mechanisms.R ------------------------------------------------------------
# Module M: price and funding mechanisms (pre-analysis plan 5.4, plus 5.5 aggregate credit risk).
# Aggregate monthly time series, so these are descriptive LPs with Newey-West errors:
#   y_{t+h} - y_{t-1} = b_h eps_t + sum_{l=1..3} g_l dy_{t-l} [+ X_{t-1}'d] + u ,  NW lag h+1
# windows dropped if any monthly change in [t, t+h] (or a lag) is missing or contaminated,
# plus the distributed-lag version (dl_ts in 00_common.R; cumulated DL of the clean monthly change).
#
# Blocks
#   1. deposit-rate pass-through: conventional Rupiah time-deposit rate (SEKI I.28), Islamic mudharabah
#      time-deposit return (OJK SPS), their spread, BUS vs UUS, BI policy rate; pass-through ratios
#   2. financing-rate pass-through: murabahah / mudharabah / musyarakah equivalent rates vs conventional
#      lending rates by use (SEKI I.26); use-matched Islamic rates (SPS Tabel 18, 2014-06+)
#   3. funding volumes: Islamic DPK (OJK) vs conventional DPK (SEKI I.17 commercial banks minus Islamic), FDR
#   4. contract mix: murabahah share and profit-sharing share of Islamic financing
#   5. aggregate Islamic NPF ratio
# Estimators (column `estimator`): lp (3 own lags), lp_ctrl (+ CONTROLS at t-1), lp_seas (+ calendar-month
# dummies; data are not seasonally adjusted), dl (dl_ts, K = 24, NW 12), dl_seas (+ month dummies).
# Also: pass-through ratios (LP and DL, joint NW, delta method) and pre-trend / lead placebo tests.
# Revision after the independent verification (2026-10-30): event-month flags (noise-aware rule R3 of
# notes/data_panel.md) for conversion follow-up / scan / merger months; same-sample conventional comparators for
# the pass-through ratios; sample robustness incl. drop-2009 and leave-one-year-out and the plan's section-6
# checks (4c); block permutation (4d); FOMC month-end timing count (4e); rule D restricted to the audited cells.
# Section 0 neutralises the audited OJK copy errors A-F (and G, I); see notes/results_mechanisms.md.
# All outcome data are restricted to 2009-01..2025-06 (both ends), so Islamic and conventional series
# use the same window. Units: rates and ratios in pp, volumes in percent (100 x log).
# Run order: python -I code/py/build_bi_deposits.py, then this script (about 3-4 minutes).
source("C:/Users/consu/Documents/Universidad/Islamic_Finance_Project/wp_dual_banking/code/R/00_common.R")
suppressPackageStartupMessages(library(ggplot2))
set.seed(20261029)

SHOCKS <- c("bi_rule_resid", "jk_mp_median", "jk_mp_pm", "usmpd_stmt", "jk_cbi_median")
FIG_SHOCKS <- c("bi_rule_resid", "jk_mp_median")
MIN_N <- 40L                      # house style (11_macro_first_stage.R): horizons with < 40 months not reported
TAB <- file.path(OUT, "tables"); FIG <- file.path(OUT, "figures")
GRID <- data.table(m = mid(SAMPLE_START):mid(SAMPLE_END))
GRID[, date := mid2date(m)]
dm <- function(x) mid(as.IDate(x))

# =============================================================================================
# 0. Cleaning of the OJK rate files (known source copy errors A-F; I = complete monthly grid)
# =============================================================================================
ret <- fread(file.path(CLEAN, "ojk_deposit_returns.csv")); ret[, date := as.IDate(date)]
mar <- fread(file.path(CLEAN, "ojk_margins.csv"));         mar[, date := as.IDate(date)]
ret[, `:=`(rate = rate_pct, mflag = "")]
mar[, `:=`(rate = rate_pct, mflag = "")]
LOG <- list()
logit <- function(step, file, rule, n, detail = "") {
  LOG[[length(LOG) + 1L]] <<- data.table(step = step, file = file, rule = rule, cells_set_na = n, detail = detail)
}
setna <- function(dt, idx, flag) {
  n <- sum(idx & !is.na(dt$rate))
  dt[idx & !is.na(rate), mflag := flag]
  dt[idx, rate := NA_real_]
  n
}
# zero_published: "not applicable", not a zero price (data note section 2)
logit("0", "ojk_deposit_returns", "rate published as exactly 0 (zero_published) -> NA",
      setna(ret, ret$rate_pct %in% 0, "zero_published"))
logit("0", "ojk_margins", "rate published as exactly 0 (zero_published) -> NA",
      setna(mar, mar$rate_pct %in% 0, "zero_published"))

# verification of each audit claim before neutralising it (counts written to the log)
cmp_blocks <- function(dt, keys, d, dims = NULL) {
  x <- dt[date == as.IDate(d)]
  if (!is.null(dims)) x <- x[dimension %in% dims]
  w <- dcast(x, as.formula(paste(paste(keys, collapse = " + "), "~ bank_type")), value.var = "rate")
  w <- w[!is.na(BUS) & !is.na(UUS)]
  list(n = nrow(w), bus_eq_uus = sum(abs(w$BUS - w$UUS) < 1e-9),
       bu_eq_bus = sum(!is.na(w$BUS_UUS) & abs(w$BUS_UUS - w$BUS) < 1e-9),
       bu_const = if (nrow(w)) max(table(round(w$BUS_UUS, 6))) else 0L)
}
RK <- c("fund_type", "instrument", "currency", "tenor")
MK <- c("dimension", "category_code", "sub_category", "currency")
v <- cmp_blocks(ret, RK, "2015-11-01")
logit("A", "ojk_deposit_returns", "2015-11 UUS copy of BUS -> UUS and BUS_UUS 2015-11 NA",
      setna(ret, ret$date == as.IDate("2015-11-01") & ret$bank_type %in% c("UUS", "BUS_UUS"), "A_2015_11_uus_copy_of_bus"),
      sprintf("verified: UUS == BUS in %d of %d non-missing cell pairs", v$bus_eq_uus, v$n))
v <- cmp_blocks(mar, MK, "2024-09-01", "contract")
logit("B", "ojk_margins", "2024-09 contract margins BUS == UUS -> BUS, UUS, BUS_UUS 2024-09 contract NA",
      setna(mar, mar$date == as.IDate("2024-09-01") & mar$dimension == "contract", "B_2024_09_bus_eq_uus"),
      sprintf("verified: BUS == UUS in %d of %d non-missing contract cell pairs", v$bus_eq_uus, v$n))
for (cc in list(list("2015-08-01", "contract"), list("2018-09-01", "sector"), list("2018-10-01", "sector"),
                list("2020-04-01", "sector"))) {
  v <- cmp_blocks(mar, MK, cc[[1]], cc[[2]])
  logit("C", "ojk_margins", sprintf("%s %s: BUS_UUS == BUS while UUS non-missing -> BUS_UUS NA", substr(cc[[1]], 1, 7), cc[[2]]),
        setna(mar, mar$date == as.IDate(cc[[1]]) & mar$dimension == cc[[2]] & mar$bank_type == "BUS_UUS",
              paste0("C_", gsub("-", "_", substr(cc[[1]], 1, 7)), "_busuus_eq_bus")),
        sprintf("verified: BUS_UUS == BUS in %d of %d non-missing cell triples", v$bu_eq_bus, v$n))
}
v <- mar[date == as.IDate("2020-05-01") & dimension == "sector" & bank_type == "BUS_UUS" & !is.na(rate),
         .(n = .N, k = sum(abs(rate - 3.888789) < 1e-6))]
# only the audited cells (those equal to the constant); the other non-missing cells of the block have
# plausible, cell-specific values and are kept (revision: the first version set the whole 64-cell block to NA)
logit("D", "ojk_margins", "2020-05 sector BUS_UUS cells equal to the constant 3.888789 -> NA (other cells of the block kept)",
      setna(mar, mar$date == as.IDate("2020-05-01") & mar$dimension == "sector" & mar$bank_type == "BUS_UUS" &
              !is.na(mar$rate) & abs(mar$rate - 3.888789) < 1e-6, "D_2020_05_busuus_const"),
      sprintf("verified: %d of %d non-missing cells equal 3.888789", v$k, v$n))
v <- cmp_blocks(ret, RK, "2024-09-01")
logit("E", "ojk_deposit_returns", "2024-09 BUS_UUS == BUS while UUS non-missing -> BUS_UUS 2024-09 NA",
      setna(ret, ret$date == as.IDate("2024-09-01") & ret$bank_type == "BUS_UUS", "E_2024_09_busuus_eq_bus"),
      sprintf("verified: BUS_UUS == BUS in %d of %d non-missing cell triples", v$bu_eq_bus, v$n))

# F. one-month spikes: |x_t - x_{t-1}| > 5 and |x_{t+1} - x_t| > 5 with opposite signs (x_t above or
# below BOTH neighbours by more than 5 pp). Neighbours must be the adjacent calendar months and non-missing.
# Applied once, after 0 and A-E, to every OJK rate series and to the BI rate series used below.
spike_rule <- function(dt, keys) {
  dt[, mm := mid(date)]
  setorderv(dt, c(keys, "mm"))
  dt[, `:=`(xp = shift(rate), mp = shift(mm), xn = shift(rate, type = "lead"), mn = shift(mm, type = "lead")), by = keys]
  idx <- with(dt, !is.na(rate) & !is.na(xp) & !is.na(xn) & (mm - mp) == 1L & (mn - mm) == 1L &
                abs(rate - xp) > 5 & abs(xn - rate) > 5 & sign(rate - xp) != sign(xn - rate))
  hits <- dt[idx, c("date", keys, "rate"), with = FALSE]
  dt[, c("xp", "mp", "xn", "mn", "mm") := NULL]
  list(idx = idx, hits = hits)
}
SPIKES <- list()
add_spikes <- function(file, h) if (nrow(h)) SPIKES[[length(SPIKES) + 1L]] <<- cbind(file = file, h)   # skip empty hit tables
sr <- spike_rule(ret, c("bank_type", RK))
add_spikes("ojk_deposit_returns", sr$hits[, .(date, bank_type, series = paste(fund_type, instrument, currency, tenor, sep = "|"), rate)])
logit("F", "ojk_deposit_returns", "one-month spike > 5 pp from both neighbours, opposite signs -> NA",
      setna(ret, sr$idx, "F_spike"), paste(unique(format(sr$hits$date, "%Y-%m")), collapse = ";"))
sr <- spike_rule(mar, c("bank_type", MK))
add_spikes("ojk_margins", sr$hits[, .(date, bank_type, series = paste(dimension, category_code, sub_category, currency, sep = "|"), rate)])
logit("F", "ojk_margins", "one-month spike > 5 pp from both neighbours, opposite signs -> NA",
      setna(mar, sr$idx, "F_spike"), paste(unique(format(sr$hits$date, "%Y-%m")), collapse = ";"))

# BI rates (conventional), commercial banks; the same spike rule
bdr <- fread(file.path(CLEAN, "bi_deposit_rates.csv"))[bank_group_code == "commercial_banks"]
blr <- fread(file.path(CLEAN, "bi_lending_rates.csv"))[bank_group_code == "commercial_banks"]
bdr[, `:=`(date = as.IDate(date), rate = rate_pct_pa, mflag = "")]
blr[, `:=`(date = as.IDate(date), rate = rate_pct_pa, mflag = "")]
sr <- spike_rule(bdr, "tenor_code")
add_spikes("bi_deposit_rates", sr$hits[, .(date, bank_type = "commercial_banks", series = tenor_code, rate)])
logit("F", "bi_deposit_rates (commercial_banks)", "same spike rule", setna(bdr, sr$idx, "F_spike"),
      paste(unique(format(sr$hits$date, "%Y-%m")), collapse = ";"))
sr <- spike_rule(blr, "loan_type_code")
add_spikes("bi_lending_rates", sr$hits[, .(date, bank_type = "commercial_banks", series = loan_type_code, rate)])
logit("F", "bi_lending_rates (commercial_banks)", "same spike rule (full 1990+ series; any hit outside 2009-2025 is irrelevant)",
      setna(blr, sr$idx, "F_spike"), paste(unique(format(sr$hits$date, "%Y-%m")), collapse = ";"))
mac <- fread(file.path(CLEAN, "macro_monthly.csv")); mac[, date := as.IDate(date)]
pol <- mac[, .(date, rate = idn_policy_rate_avg_adj_pct, mflag = "")]
pol[, k := "bi"]
sr <- spike_rule(pol, "k"); logit("F", "macro_monthly policy rate", "same spike rule", setna(pol, sr$idx, "F_spike"))
logit("G", "ojk_aggregates", "FDR: computed FDR (100 x financing / DPK) used throughout; reported FDR (2014-04 BUS_UUS, 2014-10 BUS disagree) not used", 0L)
SPIKES <- rbindlist(SPIKES)

# =============================================================================================
# 1. Monthly series on the complete 2009-01..2025-06 grid (I: 2023-01..11 absent rows become NA,
#    so no change is computed across the gap), with the "change into month m is clean" flag ok
# =============================================================================================
# break months (change INTO the month is contaminated)
B_LSMK   <- dm("2014-05-01")                                   # OJK LSMK revision / BI LBUS footnote
B_FMT    <- dm("2014-06-01")                                   # SPS format switch: break for RATES
B_BTPN   <- dm("2014-07-01")                                   # BTPN Syariah spin-off UUS -> BUS (BUS, UUS only)
B_CONV   <- dm(c("2016-09-01", "2018-09-01", "2022-08-01"))    # whole conventional banks convert to BUS
B_LBUT   <- dm("2025-01-01")                                   # SEKI LBUT vintage switch (I.17, I.26, I.28)
BRK <- list(
  isl_rate_spliced = c(B_LSMK, B_FMT, B_CONV),
  isl_rate_split   = c(B_BTPN, B_CONV),          # BUS / UUS (start 2014-06)
  isl_rate_minbrk  = c(B_FMT),                   # robustness: only the format switch (and the 2023 gap)
  isl_vol_busuus   = c(B_LSMK, B_CONV),
  isl_vol_split    = c(B_BTPN, B_CONV),
  conv_rate        = c(B_LBUT),
  seki_vol         = c(B_LSMK, B_LBUT),
  none             = integer(0))

# Event months that are NOT automatic breaks (revision, after the verification): the conversion follow-up months
# and the unattributed scan months of data/clean/ojk_conversion_events.csv, plus the BSI merger month. The
# noise-aware rule R3 of notes/data_panel.md is applied to every OJK-based Islamic series at these months: the
# change into the month is flagged (treated as a break) if its abnormal change (change minus the median of the
# previous 12 clean changes, at least 6 of them) is at least 3 x the series' robust noise scale (1.4826 x median
# |abnormal change| over 2014-06..2025-06, excluding break and candidate months) and, for log-volume series, also at
# least 1% (as in R3). Every candidate month and its z-score is written to mech_event_flags.csv.
EVT_M <- dm(c("2015-06-01", "2016-10-01", "2016-12-01", "2018-10-01", "2021-02-01", "2021-10-01", "2021-11-01",
              "2021-12-01", "2022-09-01"))
EVT_LAB <- c("S1 scan", "E2 follow-up", "S3 scan", "E3 follow-up", "E4 BSI merger", "S2 scan", "S2 scan", "S2 scan",
             "E5 follow-up")
EVT <- list()
event_flags <- function(name, x, logv) {
  x <- copy(x)
  x[, d := y - shift(y)]
  x[ok == FALSE, d := NA_real_]
  x[, med12 := frollapply(shift(d), 12L, function(v) if (sum(!is.na(v)) >= 6L) median(v, na.rm = TRUE) else NA_real_)]
  x[, abn := d - med12]
  noise <- 1.4826 * median(abs(x[m >= dm("2014-06-01") & !(m %in% EVT_M), abn]), na.rm = TRUE)
  e <- x[m %in% EVT_M, .(m, change = d, abnormal = abn)]
  e[, `:=`(outcome = name, event = EVT_LAB[match(m, EVT_M)], noise = noise, z = abnormal / noise,
           flagged = !is.na(abnormal) & abs(abnormal) >= 3 * noise & (!logv | abs(abnormal) >= 1))]
  EVT[[name]] <<- e[, .(outcome, month = format(mid2date(m), "%Y-%m"), event, change, abnormal, noise, z, flagged)]
  e[flagged == TRUE, m]
}
SER <- list(); META <- list()
add_series <- function(name, d, brk, block, unit, label, bank_type = "", note = "", evt = FALSE, logv = FALSE) {
  # d: data.table(date, y); duplicates not allowed
  d <- d[!is.na(date)]
  stopifnot(!anyDuplicated(d$date))
  x <- merge(GRID, d[, .(m = mid(date), y)], by = "m", all.x = TRUE)
  setorder(x, m)
  x[, ok := !(m %in% brk)]
  if (evt) {
    fl <- event_flags(name, x, logv)
    brk <- sort(unique(c(brk, fl)))
    x[, ok := !(m %in% brk)]
  }
  x[, date := NULL]
  SER[[name]] <<- x
  META[[name]] <<- data.table(outcome = name, block = block, unit = unit, label = label, bank_type = bank_type,
                              first = mid2date(min(x[!is.na(y), m])), last = mid2date(max(x[!is.na(y), m])),
                              months_level = sum(!is.na(x$y)),
                              clean_changes = sum(!is.na(x$y - shift(x$y)) & x$ok),
                              breaks = paste(format(mid2date(sort(brk)), "%Y-%m"), collapse = ";"), note = note)
}
combine <- function(a, b, name, f, block, unit, label, bank_type = "", note = "") {
  x <- merge(SER[[a]], SER[[b]], by = "m", suffixes = c("_a", "_b"))
  d <- data.table(date = mid2date(x$m), y = f(x$y_a, x$y_b))
  brk <- x[!(ok_a & ok_b), m]
  add_series(name, d, brk, block, unit, label, bank_type, note)
}
win <- function(d) d[date >= SAMPLE_START & date <= SAMPLE_END]

# ---- 1a. deposit rates -------------------------------------------------------------------------
TEN <- c("1m", "3m", "6m", "12m")
add_series("bi_policy", win(pol[, .(date, y = rate)]), BRK$none, "deposit_rates", "pp", "BI policy rate (avg, 2016-adj.)")
for (tn in TEN) {
  add_series(paste0("dep_conv_", tn), win(bdr[tenor_code == tn, .(date, y = rate)]), BRK$conv_rate, "deposit_rates", "pp",
             paste("Conventional time-deposit rate", tn), "CONV", "SEKI I.28 commercial banks, Rupiah")
  old <- ret[bank_type == "BUS_UUS" & fund_type == "mudharabah" & instrument == "time" & currency == "unspecified" &
               tenor == tn & date <= as.IDate("2014-05-01"), .(date, y = rate)]
  new <- ret[bank_type == "BUS_UUS" & fund_type == "mudharabah" & instrument == "time" & currency == "IDR" &
               tenor == tn & date >= as.IDate("2014-06-01"), .(date, y = rate)]
  add_series(paste0("dep_isl_", tn), win(rbind(old, new)), BRK$isl_rate_spliced, "deposit_rates", "pp",
             paste("Islamic mudharabah time-deposit return", tn), "BUS_UUS",
             "old Tabel 36 (currency unstated) to 2014-05, Rupiah Tabel 17 from 2014-06; change into 2014-06 dropped", evt = TRUE)
  combine(paste0("dep_isl_", tn), paste0("dep_conv_", tn), paste0("spread_", tn), function(a, b) a - b,
          "deposit_rates", "pp", paste("Spread Islamic - conventional", tn), "BUS_UUS-CONV")
  for (bt in c("BUS", "UUS")) {
    nm <- tolower(bt)
    add_series(paste0("dep_", nm, "_", tn),
               win(ret[bank_type == bt & fund_type == "mudharabah" & instrument == "time" & currency == "IDR" & tenor == tn, .(date, y = rate)]),
               BRK$isl_rate_split, "deposit_rates", "pp", paste(bt, "mudharabah time-deposit return", tn), bt, "Rupiah, 2014-06+", evt = TRUE)
    combine(paste0("dep_", nm, "_", tn), paste0("dep_conv_", tn), paste0("spread_", nm, "_", tn), function(a, b) a - b,
            "deposit_rates", "pp", paste("Spread", bt, "- conventional", tn), paste0(bt, "-CONV"))
  }
}
combine("dep_bus_1m", "dep_uus_1m", "gap_bus_uus_1m", function(a, b) a - b, "deposit_rates", "pp",
        "BUS - UUS 1m return", "BUS-UUS")
# splice robustness: Rupiah-only, 2014-06+ (no old-format segment)
add_series("dep_isl_1m_post14", win(ret[bank_type == "BUS_UUS" & fund_type == "mudharabah" & instrument == "time" &
                                          currency == "IDR" & tenor == "1m", .(date, y = rate)]),
           BRK$isl_rate_split, "deposit_rates", "pp", "Islamic 1m return, Rupiah 2014-06+ only", "BUS_UUS", "splice robustness", evt = TRUE)
combine("dep_isl_1m_post14", "dep_conv_1m", "spread_1m_post14", function(a, b) a - b, "deposit_rates", "pp",
        "Spread 1m, 2014-06+ only", "BUS_UUS-CONV", "splice robustness")
# break-rule robustness: only the format switch as a break (no LSMK / conversion breaks)
add_series("dep_isl_1m_minbrk", SER$dep_isl_1m[, .(date = mid2date(m), y)], BRK$isl_rate_minbrk, "deposit_rates", "pp",
           "Islamic 1m return, minimal breaks", "BUS_UUS", "break-rule robustness")
combine("dep_isl_1m_minbrk", "dep_conv_1m", "spread_1m_minbrk", function(a, b) a - b, "deposit_rates", "pp",
        "Spread 1m, minimal breaks", "BUS_UUS-CONV", "break-rule robustness")
# conventional comparators restricted to exactly the clean months of a 2014-06+ Islamic series, so that pass-through
# ratios are compared on the same sample (revision, after the verification)
for (p in list(c("dep_isl_1m_post14", "post14"), c("dep_bus_1m", "bus"), c("dep_uus_1m", "uus")))
  combine("dep_conv_1m", p[1], paste0("dep_conv_1m_on_", p[2]), function(a, b) a + 0 * b, "deposit_rates", "pp",
          paste("Conventional 1m rate on the months of", p[1]), "CONV", "same-sample comparator")

# ---- 1b. financing rates -----------------------------------------------------------------------
LT <- c(consumption = "cons", working_capital = "wc", investment = "inv")
for (lt in names(LT)) add_series(paste0("lend_conv_", LT[[lt]]), win(blr[loan_type_code == lt, .(date, y = rate)]),
                                 BRK$conv_rate, "financing_rates", "pp", paste("Conventional lending rate,", lt), "CONV",
                                 "SEKI I.26 commercial banks, Rupiah")
for (ct in c("murabahah", "mudharabah", "musyarakah")) {
  old <- mar[dimension == "contract" & bank_type == "BUS_UUS" & category_code == ct & currency == "unspecified" &
               date <= as.IDate("2014-05-01"), .(date, y = rate)]
  new <- mar[dimension == "contract" & bank_type == "BUS_UUS" & category_code == ct & currency == "IDR" &
               date >= as.IDate("2014-06-01"), .(date, y = rate)]
  add_series(paste0("fin_isl_", ct), win(rbind(old, new)), BRK$isl_rate_spliced, "financing_rates", "pp",
             paste("Islamic", ct, "equivalent rate"), "BUS_UUS",
             "old Tabel 36 to 2014-05, Rupiah Tabel 17 from 2014-06; change into 2014-06 dropped", evt = TRUE)
}
for (bt in c("BUS", "UUS")) add_series(paste0("fin_", tolower(bt), "_murabahah"),
                                      win(mar[dimension == "contract" & bank_type == bt & category_code == "murabahah" & currency == "IDR", .(date, y = rate)]),
                                      BRK$isl_rate_split, "financing_rates", "pp", paste(bt, "murabahah equivalent rate"), bt, "Rupiah, 2014-06+", evt = TRUE)
SPR <- list(c("fin_isl_murabahah", "lend_conv_cons"), c("fin_isl_murabahah", "lend_conv_wc"),
            c("fin_isl_mudharabah", "lend_conv_wc"), c("fin_isl_mudharabah", "lend_conv_inv"),
            c("fin_isl_musyarakah", "lend_conv_wc"), c("fin_isl_musyarakah", "lend_conv_inv"),
            c("fin_bus_murabahah", "lend_conv_cons"), c("fin_uus_murabahah", "lend_conv_cons"))
for (p in SPR) combine(p[1], p[2], paste0("fspread_", sub("fin_", "", p[1]), "_", sub("lend_conv_", "", p[2])),
                       function(a, b) a - b, "financing_rates", "pp",
                       paste("Spread", sub("fin_", "", p[1]), "-", sub("lend_conv_", "conv ", p[2])),
                       ifelse(grepl("bus_", p[1]), "BUS-CONV", ifelse(grepl("uus_", p[1]), "UUS-CONV", "BUS_UUS-CONV")))
# use-matched Islamic rates (Tabel 18, all sizes, all currencies, 2014-06+)
for (lt in names(LT)) {
  add_series(paste0("fin_isl_use_", LT[[lt]]),
             win(mar[dimension == "use_size" & bank_type == "BUS_UUS" & category_code == lt & sub_category == "all" &
                       currency == "all", .(date, y = rate)]),
             BRK$isl_rate_split, "financing_rates", "pp", paste("Islamic equivalent rate by use,", lt), "BUS_UUS",
             "SPS Tabel 18, all debtor sizes, all currencies, 2014-06+", evt = TRUE)
  combine(paste0("fin_isl_use_", LT[[lt]]), paste0("lend_conv_", LT[[lt]]), paste0("fspread_use_", LT[[lt]]),
          function(a, b) a - b, "financing_rates", "pp", paste("Spread Islamic - conventional, same use:", lt), "BUS_UUS-CONV")
  combine(paste0("lend_conv_", LT[[lt]]), paste0("fin_isl_use_", LT[[lt]]), paste0("lend_conv_", LT[[lt]], "_on_use"),
          function(a, b) a + 0 * b, "financing_rates", "pp", paste("Conventional lending rate on the months of the use-matched Islamic rate,", lt),
          "CONV", "same-sample comparator")
}

# ---- 1c. funding volumes -----------------------------------------------------------------------
dep <- fread(file.path(CLEAN, "ojk_deposits.csv"))[series == "harmonised"]; dep[, date := as.IDate(date)]
seki <- fread(file.path(CLEAN, "bi_deposits_by_group.csv")); seki[, date := as.IDate(date)]
TY <- c(total = "h_total", demand = "h_demand", savings = "h_sav", time = "h_time")
for (ty in names(TY)) {
  for (bt in c("BUS_UUS", "BUS", "UUS")) {
    nm <- c(BUS_UUS = "isl", BUS = "bus", UUS = "uus")[[bt]]
    add_series(paste0("dpk_", nm, "_", ty), win(dep[bank_type == bt & series_code == TY[[ty]], .(date, y = 100 * log(deposits_rp_bn))]),
               if (bt == "BUS_UUS") BRK$isl_vol_busuus else BRK$isl_vol_split, "funding", "percent (100 log)",
               paste(bt, "DPK,", ty), bt, "OJK SPS harmonised series", evt = TRUE, logv = TRUE)
  }
  sk <- win(seki[bank_group_code == "commercial_banks" & currency == "all" & deposit_type == ty, .(date, s = deposits_rp_bn)])
  il <- win(dep[bank_type == "BUS_UUS" & series_code == TY[[ty]], .(date, i = deposits_rp_bn)])
  cv <- merge(sk, il, by = "date")
  add_series(paste0("dpk_comm_", ty), sk[, .(date, y = 100 * log(s))], BRK$seki_vol, "funding", "percent (100 log)",
             paste("All commercial banks private deposits (incl. Islamic),", ty), "ALL", "SEKI I.17, 4 commercial groups, Rp+FX")
  # conventional = SEKI - BUS_UUS inherits every break of the BUS_UUS series of the same type (incl. event flags)
  add_series(paste0("dpk_conv_", ty), cv[, .(date, y = 100 * log(s - i))],
             unique(c(BRK$seki_vol, SER[[paste0("dpk_isl_", ty)]][ok == FALSE, m])),
             "funding", "percent (100 log)", paste("Conventional DPK,", ty), "CONV", "SEKI I.17 commercial banks minus OJK BUS+UUS")
  combine(paste0("dpk_isl_", ty), paste0("dpk_conv_", ty), paste0("dpk_diff_", ty), function(a, b) a - b, "funding",
          "percent (100 log)", paste("Islamic - conventional DPK growth,", ty), "BUS_UUS-CONV")
}
# robustness: conventional total including the SEKI memo items (central government + non-residents), closer to
# the OJK DPK concept (which includes government and non-resident funds)
memo <- win(seki[bank_group_code %in% c("memo_central_gov", "memo_non_resident") & deposit_type == "total",
                 .(mm = sum(deposits_rp_bn), k = .N), by = date][k == 2])
cvm <- merge(merge(win(seki[bank_group_code == "commercial_banks" & currency == "all" & deposit_type == "total", .(date, s = deposits_rp_bn)]),
                   memo, by = "date"), win(dep[bank_type == "BUS_UUS" & series_code == "h_total", .(date, i = deposits_rp_bn)]), by = "date")
add_series("dpk_convmemo_total", cvm[, .(date, y = 100 * log(s + mm - i))], unique(c(BRK$seki_vol, SER$dpk_isl_total[ok == FALSE, m])),
           "funding", "percent (100 log)", "Conventional DPK incl. memo items, total", "CONV", "robustness: + central government + non-residents")
combine("dpk_isl_total", "dpk_convmemo_total", "dpk_diffmemo_total", function(a, b) a - b, "funding", "percent (100 log)",
        "Islamic - conventional DPK growth (conv. incl. memo), total", "BUS_UUS-CONV")
combine("dpk_bus_total", "dpk_uus_total", "dpk_diff_bus_uus_total", function(a, b) a - b, "funding", "percent (100 log)",
        "BUS - UUS DPK growth, total", "BUS-UUS")
agg <- fread(file.path(CLEAN, "ojk_aggregates.csv")); agg[, date := as.IDate(date)]
for (bt in c("BUS_UUS", "BUS", "UUS")) {
  nm <- c(BUS_UUS = "isl", BUS = "bus", UUS = "uus")[[bt]]
  add_series(paste0("fdr_", nm), win(agg[bank_type == bt & indicator == "fdr_pct_computed", .(date, y = value)]),
             if (bt == "BUS_UUS") BRK$isl_vol_busuus else BRK$isl_vol_split, "funding", "pp",
             paste(bt, "FDR (computed)"), bt, "100 x financing / DPK (rule G)", evt = TRUE)
}

# ---- 1d. contract mix --------------------------------------------------------------------------
con <- fread(file.path(CLEAN, "ojk_contracts.csv"))[currency == "all"]; con[, date := as.IDate(date)]
cw <- dcast(con[contract_code %in% c("murabahah", "mudharabah", "musyarakah", "other_profit_sharing", "total")],
            date + bank_type ~ contract_code, value.var = "financing_rp_bn")
cw[is.na(other_profit_sharing) & date <= as.IDate("2014-05-01"), other_profit_sharing := 0]  # old musyarakah includes it
cw[, `:=`(sh_mur = 100 * murabahah / total, sh_ps = 100 * (mudharabah + musyarakah + other_profit_sharing) / total)]
for (bt in c("BUS_UUS", "BUS", "UUS")) {
  nm <- c(BUS_UUS = "isl", BUS = "bus", UUS = "uus")[[bt]]
  brk <- if (bt == "BUS_UUS") BRK$isl_vol_busuus else BRK$isl_vol_split
  add_series(paste0("share_murabahah_", nm), win(cw[bank_type == bt, .(date, y = sh_mur)]), brk, "contract_mix", "pp",
             paste(bt, "murabahah share of financing"), bt, evt = TRUE)
  add_series(paste0("share_ps_", nm), win(cw[bank_type == bt, .(date, y = sh_ps)]), brk, "contract_mix", "pp",
             paste(bt, "profit-sharing (mudharabah+musyarakah) share"), bt, evt = TRUE)
  # ---- 1e. NPF ----
  add_series(paste0("npf_", nm), win(agg[bank_type == bt & indicator == "npf_gross_pct_computed", .(date, y = value)]), brk,
             "npf", "pp", paste(bt, "gross NPF ratio (computed)"), bt, "100 x NPF / financing", evt = TRUE)
}
# robustness: the same three differentials with the event-month rule switched off (the first version's breaks)
add_series("fin_isl_murabahah_noevt", SER$fin_isl_murabahah[, .(date = mid2date(m), y)], BRK$isl_rate_spliced, "financing_rates", "pp",
           "Islamic murabahah rate, event rule off", "BUS_UUS", "event-rule robustness")
combine("fin_isl_murabahah_noevt", "lend_conv_wc", "fspread_isl_murabahah_wc_noevt", function(a, b) a - b, "financing_rates", "pp",
        "Spread murabahah - conv wc, event rule off", "BUS_UUS-CONV", "event-rule robustness")
add_series("dpk_isl_total_noevt", SER$dpk_isl_total[, .(date = mid2date(m), y)], BRK$isl_vol_busuus, "funding", "percent (100 log)",
           "BUS_UUS DPK total, event rule off", "BUS_UUS", "event-rule robustness")
add_series("dpk_conv_total_noevt", SER$dpk_conv_total[, .(date = mid2date(m), y)], unique(c(BRK$seki_vol, BRK$isl_vol_busuus)), "funding",
           "percent (100 log)", "Conventional DPK total, event rule off", "CONV", "event-rule robustness")
combine("dpk_isl_total_noevt", "dpk_conv_total_noevt", "dpk_diff_total_noevt", function(a, b) a - b, "funding", "percent (100 log)",
        "Islamic - conventional DPK growth, total, event rule off", "BUS_UUS-CONV", "event-rule robustness")
for (bt in c("bus", "uus")) add_series(paste0("dep_", bt, "_1m_noevt"), SER[[paste0("dep_", bt, "_1m")]][, .(date = mid2date(m), y)],
                                      BRK$isl_rate_split, "deposit_rates", "pp", paste(toupper(bt), "1m return, event rule off"),
                                      toupper(bt), "event-rule robustness")
combine("dep_bus_1m_noevt", "dep_uus_1m_noevt", "gap_bus_uus_1m_noevt", function(a, b) a - b, "deposit_rates", "pp",
        "BUS - UUS 1m return, event rule off", "BUS-UUS", "event-rule robustness")
META <- rbindlist(META)
# BUS / UUS / BUS_UUS total DPK around every break and candidate event month (Rp bn): change and abnormal change
# (change minus the median change of the previous 12 months); a UUS -> BUS reclassification shows as a UUS fall
# mirrored by a BUS rise
lv <- dcast(dep[series_code == "h_total"], date ~ bank_type, value.var = "deposits_rp_bn")
lv[, m := mid(date)]; setorder(lv, m)
for (bt in c("BUS", "UUS", "BUS_UUS")) {
  lv[, (paste0("d_", bt)) := get(bt) - shift(get(bt))]
  lv[, (paste0("abn_", bt)) := get(paste0("d_", bt)) - frollapply(shift(get(paste0("d_", bt))), 12L, function(v) median(v, na.rm = TRUE))]
}
EVM <- data.table(m = c(B_BTPN, B_CONV, EVT_M),
                  event = c("E1 BTPN spin-off (break)", paste(c("E2", "E3", "E5"), "conversion (break)"), EVT_LAB))
EVL <- merge(EVM, lv[, .(m, BUS, UUS, d_BUS, abn_BUS, d_UUS, abn_UUS, d_BUS_UUS, abn_BUS_UUS)], by = "m")
EVL[, month := format(mid2date(m), "%Y-%m")]; setorder(EVL, m); EVL[, m := NULL]
setcolorder(EVL, c("month", "event"))
fwrite(EVL, file.path(TAB, "mech_event_levels.csv"))
EVT <- rbindlist(EVT)
fwrite(EVT, file.path(TAB, "mech_event_flags.csv"))
cat("=== event months flagged by the noise-aware rule (R3) ===\n"); print(EVT[flagged == TRUE, .(outcome, month, event, abnormal = round(abnormal, 2), z = round(z, 1))])
# level jump at the 2014-05 -> 2014-06 format switch of the spliced BUS_UUS rate series (this change is dropped)
SPL <- rbindlist(lapply(c(paste0("dep_isl_", TEN), "fin_isl_murabahah", "fin_isl_mudharabah", "fin_isl_musyarakah"), function(n) {
  x <- SER[[n]]
  data.table(outcome = n, old_2014_05 = x[m == dm("2014-05-01"), y], new_2014_06 = x[m == dm("2014-06-01"), y],
             jump = x[m == dm("2014-06-01"), y] - x[m == dm("2014-05-01"), y],
             median_abs_monthly_change_clean = median(abs((x$y - shift(x$y))[x$ok]), na.rm = TRUE))
}))
fwrite(SPL, file.path(TAB, "mech_splice_jumps.csv"))

# derived monthly data with flags (new clean file; never modifies other builders' files)
der <- rbindlist(lapply(names(SER), function(n) SER[[n]][, .(date = mid2date(m), outcome = n, value = y,
                                                                 change_clean = ok & !is.na(y - shift(y)))]))
fwrite(der, file.path(CLEAN, "mech_monthly_series.csv"))
fwrite(META, file.path(TAB, "mech_series_coverage.csv"))
# cells of the cleaned rate files that feed the series and were neutralised (for the record)
fwrite(rbind(ret[mflag != "", .(file = "ojk_deposit_returns", date, bank_type, series = paste(fund_type, instrument, currency, tenor, sep = "|"), published = rate_pct, mflag)],
             mar[mflag != "", .(file = "ojk_margins", date, bank_type, series = paste(dimension, category_code, sub_category, currency, sep = "|"), published = rate_pct, mflag)])[mflag != "zero_published"],
       file.path(TAB, "mech_cleaning_cells.csv"))
# neutralised cells inside the rate series actually used above (2009-01..2025-06)
u_ret <- ret[date >= SAMPLE_START & date <= SAMPLE_END & fund_type == "mudharabah" & instrument == "time" & tenor %in% TEN &
               ((currency == "IDR" & date >= as.IDate("2014-06-01")) | (currency == "unspecified" & bank_type == "BUS_UUS"))]
u_mar <- mar[date >= SAMPLE_START & date <= SAMPLE_END &
               ((dimension == "contract" & category_code %in% c("murabahah", "mudharabah", "musyarakah") &
                   ((currency == "IDR" & date >= as.IDate("2014-06-01")) | currency == "unspecified") &
                   (bank_type == "BUS_UUS" | category_code == "murabahah")) |
                (dimension == "use_size" & bank_type == "BUS_UUS" & sub_category == "all" & currency == "all"))]
USED <- rbind(u_ret[mflag != "", .(file = "ojk_deposit_returns", date, bank_type, series = paste(fund_type, instrument, currency, tenor, sep = "|"), published = rate_pct, mflag)],
              u_mar[mflag != "", .(file = "ojk_margins", date, bank_type, series = paste(dimension, category_code, sub_category, currency, sep = "|"), published = rate_pct, mflag)])
fwrite(USED, file.path(TAB, "mech_cleaning_used_series.csv"))
cat("=== neutralised cells inside the rate series used ===
"); print(USED[, .N, by = .(file, mflag, month = format(date, "%Y-%m"))])
LOG <- rbindlist(LOG)
fwrite(LOG, file.path(TAB, "mech_cleaning_log.csv"))
fwrite(SPIKES, file.path(TAB, "mech_spike_cells.csv"))
cat("=== cleaning log ===\n"); print(LOG[, .(step, file, cells_set_na, detail = substr(detail, 1, 70))])

# =============================================================================================
# 2. Does SEKI I.17 include Islamic deposits? (same logic as notes/data_panel.md section 2)
# =============================================================================================
sk <- dcast(win(seki[currency == "all" & deposit_type == "total" & bank_group_code %in% c("commercial_banks", "bpd")]),
            date ~ bank_group_code, value.var = "deposits_rp_bn")
il <- dcast(win(dep[series_code == "h_total"]), date ~ bank_type, value.var = "deposits_rp_bn")
z <- merge(sk, il, by = "date", all.x = TRUE); setorder(z, date)
z[, `:=`(g_comm = 100 * (log(commercial_banks) - log(shift(commercial_banks))),
         g_conv = 100 * (log(commercial_banks - BUS_UUS) - log(shift(commercial_banks - BUS_UUS))),
         d_bpd = bpd - shift(bpd), d_bus = BUS - shift(BUS))]
z[, `:=`(med_d_bpd = frollapply(shift(d_bpd), 12, median), med_d_bus = frollapply(shift(d_bus), 12, function(v) median(v, na.rm = TRUE)))]
TESTS <- list()
tst <- function(test, quantity, value, note = "") TESTS[[length(TESTS) + 1L]] <<- data.table(test, quantity, value, note)
ok_g <- z[!(mid(date) %in% c(B_LSMK, B_CONV, B_LBUT)) & !is.na(g_conv)]
i4 <- z[date == as.IDate("2014-04-01")]; i5 <- z[date == as.IDate("2014-05-01")]
tst("T1 2014-05 (LBUS footnote)", "SEKI commercial dlog 2014-05 (%)", i5$g_comm)
tst("T1 2014-05 (LBUS footnote)", "Islamic DPK share of SEKI commercial, 2014-04 (%)", 100 * i4$BUS_UUS / i4$commercial_banks)
tst("T1 2014-05 (LBUS footnote)", "conventional dlog 2014-05 under A: included throughout (%)", i5$g_conv)
tst("T1 2014-05 (LBUS footnote)", "conventional dlog 2014-05 under B: Islamic first included 2014-05 (%)",
    100 * (log(i5$commercial_banks - i5$BUS_UUS) - log(i4$commercial_banks)))
tst("T1 2014-05 (LBUS footnote)", "min / sd of conventional dlog under A, 2009-2025 excl. break months (%)",
    NA_real_, sprintf("min %.2f, sd %.2f, n %d", min(ok_g$g_conv), sd(ok_g$g_conv), nrow(ok_g)))
tst("T1 2014-05 (LBUS footnote)", "median |SEKI commercial dlog| 2009-2025 (%)", median(abs(z$g_comm), na.rm = TRUE))
for (e in c("2016-09-01", "2018-09-01", "2022-08-01")) {
  r <- z[date == as.IDate(e)]
  tst(paste("T4 conversion", substr(e, 1, 7)), "BUS DPK change, abnormal (Rp bn)", r$d_bus - r$med_d_bus,
      sprintf("raw %.0f; prev-12m median %.0f", r$d_bus, r$med_d_bus))
  tst(paste("T4 conversion", substr(e, 1, 7)), "SEKI BPD deposits change, abnormal (Rp bn)", r$d_bpd - r$med_d_bpd,
      sprintf("raw %.0f; prev-12m median %.0f; BPD level %.0f; under B expect roughly -(converted bank's deposits)", r$d_bpd, r$med_d_bpd, shift(z$bpd)[z$date == as.IDate(e)]))
}
vb <- fread(file.path(TAB, "mech_bi_deposits_validation.csv"))
gv <- function(k) as.numeric(vb[check == k, value])
for (yy in c("2023-12", "2024-12")) {
  bus <- agg[bank_type == "BUS" & indicator == "dpk_rp_bn" & date == as.IDate(paste0(yy, "-01")), value]
  spi <- gv(sprintf("spi_dpk_commercial[%s]", yy)); sc <- gv(sprintf("seki_private_commercial[%s]", yy))
  mm <- gv(sprintf("seki_memo_cg_plus_nonres[%s]", yy))
  tst(paste("T-level", yy), "OJK SPI commercial-bank DPK, incl. BUS (Rp bn)", spi)
  tst(paste("T-level", yy), "SEKI I.17 commercial private deposits + memo items (Rp bn)", sc + mm)
  tst(paste("T-level", yy), "OJK BUS DPK (Rp bn)", bus)
  tst(paste("T-level", yy), "gap SPI - SEKI under A (Rp bn)", spi - (sc + mm), "A: SEKI includes BUS")
  tst(paste("T-level", yy), "gap (SPI - BUS) - SEKI under B (Rp bn)", spi - bus - (sc + mm), "B: SEKI excludes BUS")
}
TESTS <- rbindlist(TESTS)
fwrite(TESTS, file.path(TAB, "mech_dpk_inclusion_tests.csv"))
cat("\n=== SEKI I.17 inclusion tests ===\n"); print(TESTS[, .(test, quantity = substr(quantity, 1, 60), value = round(value, 2), note = substr(note, 1, 60))])
shr <- z[, .(date, isl_share = 100 * BUS_UUS / commercial_banks)]
rep_dep <- fread(file.path(CLEAN, "ojk_deposits.csv"))[series == "reported" & bank_type == "BUS_UUS" & instrument == "time" &
                                                          fund_type == "investment_non_profit_sharing"]
rep_dep[, date := as.IDate(date)]
rsh <- dcast(rep_dep[currency %in% c("IDR", "FX") & tenor == "all"], date ~ currency, value.var = "deposits_rp_bn", fun.aggregate = sum)
rsh[, idr_share := 100 * IDR / (IDR + FX)]
r1m <- fread(file.path(CLEAN, "ojk_deposits.csv"))[series == "reported" & bank_type == "BUS_UUS" & instrument == "time" &
                                                     fund_type == "investment_non_profit_sharing" & currency == "IDR" & tenor %in% c("1m", "all")]
r1m[, date := as.IDate(date)]
r1m <- dcast(r1m, date ~ tenor, value.var = "deposits_rp_bn")
r1m[, sh1m := 100 * `1m` / all]
DESC <- data.table(
  item = c("Islamic share of commercial private deposits, 2009-01 (%)", "Islamic share, 2025-06 (%)",
           "Rupiah share of BUS_UUS mudharabah time deposits, 2014-06 (%)", "Rupiah share, 2025-06 (%)",
           "Rupiah share, mean 2014-06..2025-06 (%)", "1-month share of BUS_UUS Rupiah time deposits, mean 2014-06..2025-06 (%)",
           "1-month share, min over 2014-06..2025-06 (%)"),
  value = c(shr[date == SAMPLE_START, isl_share], shr[date == SAMPLE_END, isl_share],
            rsh[date == as.IDate("2014-06-01"), idr_share], rsh[date == SAMPLE_END, idr_share], mean(rsh[date <= SAMPLE_END, idr_share]),
            mean(r1m[date <= SAMPLE_END, sh1m]), min(r1m[date <= SAMPLE_END, sh1m])))
fwrite(DESC, file.path(TAB, "mech_descriptives.csv"))
print(DESC)

# =============================================================================================
# 3. Estimation: LP (NW, h+1), LP + X_{t-1} controls, DL (dl_ts, NW 12)
# =============================================================================================
shk <- load_shocks()
SD <- sapply(SHOCKS, function(s) sd(shk[date >= SAMPLE_START & date <= SAMPLE_END, get(s)], na.rm = TRUE))
macl <- load_macro()[, c("m", CONTROLS), with = FALSE][, m := m + 1L]
CL <- paste0(CONTROLS, "_l1"); setnames(macl, CONTROLS, CL)
fwrite(data.table(shock = SHOCKS, sd_2009_2025 = SD, sd_per_25bp = 0.25 / SD), file.path(TAB, "mech_shock_sd.csv"))

prep <- function(name) {
  x <- copy(SER[[name]]); setorder(x, m)
  x[, dyv := y - shift(y)]
  x[ok == FALSE, dyv := NA_real_]
  x[, bad := cumsum(is.na(dyv))]
  for (l in 1:3) x[, paste0("lag", l) := shift(dyv, l)]
  x <- merge(x, shk[, c("m", SHOCKS), with = FALSE], by = "m", all.x = TRUE)
  x <- merge(x, macl, by = "m", all.x = TRUE)
  setorder(x, m)
  for (k in 2:12) x[, paste0("mo", k) := as.numeric(m %% 12L + 1L == k)]   # calendar month of t (data are not SA)
  x
}
MO <- paste0("mo", 2:12)
lp_one <- function(x, h) {
  x[, dh := shift(y, h, type = "lead") - shift(y, 1L)]
  x[(shift(bad, h, type = "lead") - shift(bad, 1L)) != 0, dh := NA_real_]
  x
}
RES <- list()
t0 <- Sys.time()
for (nm in names(SER)) {
  x <- prep(nm)
  for (h in 0:H_MAX) {
    x <- lp_one(x, h)
    for (s in SHOCKS) for (est in c("lp", "lp_ctrl", "lp_seas")) {
      vars <- c(s, "lag1", "lag2", "lag3", if (est == "lp_ctrl") CL, if (est == "lp_seas") MO)
      z <- x[complete.cases(x[, c("dh", vars), with = FALSE])]
      if (nrow(z) < MIN_N) next
      nw <- nw_lp(z$dh, as.matrix(z[, vars, with = FALSE]), lag = h + 1L)
      RES[[length(RES) + 1L]] <- data.table(outcome = nm, shock = s, estimator = est, h = h,
                                            b = unname(nw$coef[2]), se = unname(nw$se[2]), n = nw$n,
                                            t_first = mid2date(min(z$m)), t_last = mid2date(max(z$m)))
    }
  }
  # distributed lag: clean monthly change on eps_{t-k}, k = 0..24, cumulated
  D <- x[!is.na(dyv), c("m", "dyv", MO), with = FALSE]; setnames(D, "dyv", "y")
  for (s in SHOCKS) for (est in c("dl", "dl_seas")) {
    r <- tryCatch(dl_ts(D, shk, s, K = H_MAX, L = 12L, ctrl = if (est == "dl_seas") MO else character(0)),
                  error = function(e) NULL)
    if (is.null(r) || r$n[1] < MIN_N) next
    RES[[length(RES) + 1L]] <- r[, .(outcome = nm, shock = s, estimator = est, h, b, se, n,
                                     t_first = mid2date(min(D$m)), t_last = mid2date(max(D$m)))]
  }
}
cat(sprintf("\nestimation done in %.1f s\n", as.numeric(difftime(Sys.time(), t0, units = "secs"))))
RES <- rbindlist(RES)
RES[, shock_sd := SD[shock]]
RES[, `:=`(b25 = 0.25 * b, se25 = 0.25 * se, bsd = b * shock_sd, sesd = se * shock_sd)]   # outcomes in pp / percent
RES <- merge(RES, META[, .(outcome, block, unit, bank_type)], by = "outcome")
setcolorder(RES, c("outcome", "shock", "estimator", "h", "b", "se", "b25", "se25", "bsd", "sesd", "n"))
setorder(RES, block, outcome, shock, estimator, h)
for (bl in unique(RES$block)) fwrite(RES[block == bl], file.path(TAB, paste0("mech_", bl, ".csv")))

# =============================================================================================
# 4. Pass-through ratios: cumulative response of a rate / cumulative response of the BI policy rate,
#    both LPs on the SAME months, joint Newey-West covariance (lag h+1), delta-method s.e.
# =============================================================================================
joint_nw <- function(f1, f2, lag) {
  n <- nobs(f1)
  if1 <- sandwich::estfun(f1) %*% t(sandwich::bread(f1)) / n
  if2 <- sandwich::estfun(f2) %*% t(sandwich::bread(f2)) / n
  P <- cbind(if1, if2) * n                       # n x (k1+k2) influence functions
  S <- crossprod(P) / n
  for (j in seq_len(lag)) {
    G <- crossprod(P[(j + 1):n, , drop = FALSE], P[1:(n - j), , drop = FALSE]) / n
    S <- S + (1 - j / (lag + 1)) * (G + t(G))
  }
  k <- max(length(coef(f1)), length(coef(f2)))
  S / n * n / (n - k)                             # same finite-sample adjustment as NeweyWest(adjust = TRUE)
}
PT_OUT <- c(paste0("dep_conv_", TEN), paste0("dep_isl_", TEN), paste0("dep_bus_", TEN), paste0("dep_uus_", TEN),
            "dep_isl_1m_post14", "dep_isl_1m_minbrk",
            "dep_conv_1m_on_post14", "dep_conv_1m_on_bus", "dep_conv_1m_on_uus",
            "lend_conv_cons", "lend_conv_wc", "lend_conv_inv", "fin_isl_murabahah", "fin_isl_mudharabah", "fin_isl_musyarakah",
            "fin_bus_murabahah", "fin_uus_murabahah", "fin_isl_use_cons", "fin_isl_use_wc", "fin_isl_use_inv",
            "lend_conv_cons_on_use", "lend_conv_wc_on_use", "lend_conv_inv_on_use",
            # spreads: ratio = (Islamic - conventional) / BI = difference in pass-through, with its own s.e.
            paste0("spread_", TEN), "spread_bus_1m", "spread_uus_1m", "gap_bus_uus_1m", "spread_1m_post14", "spread_1m_minbrk",
            "fspread_isl_murabahah_cons", "fspread_isl_murabahah_wc", "fspread_isl_mudharabah_wc", "fspread_isl_musyarakah_inv",
            "fspread_use_cons", "fspread_use_wc", "fspread_use_inv")
xb <- prep("bi_policy")
PT <- list()
for (nm in PT_OUT) {
  x <- prep(nm)
  for (h in c(6L, 12L)) {
    x <- lp_one(x, h); xb <- lp_one(xb, h)
    j <- merge(x[, c("m", "dh", "lag1", "lag2", "lag3", SHOCKS), with = FALSE],
               xb[, .(m, dhb = dh, blag1 = lag1, blag2 = lag2, blag3 = lag3)], by = "m")
    for (s in SHOCKS) {
      z <- j[complete.cases(j[, c("dh", "dhb", s, "lag1", "lag2", "lag3", "blag1", "blag2", "blag3"), with = FALSE])]
      if (nrow(z) < MIN_N) next
      f1 <- lm(z$dh ~ as.matrix(z[, c(s, "lag1", "lag2", "lag3"), with = FALSE]))
      f2 <- lm(z$dhb ~ as.matrix(z[, c(s, "blag1", "blag2", "blag3"), with = FALSE]))
      V <- joint_nw(f1, f2, h + 1L)
      k1 <- length(coef(f1))
      b1 <- coef(f1)[2]; b2 <- coef(f2)[2]
      v11 <- V[2, 2]; v22 <- V[k1 + 2, k1 + 2]; v12 <- V[2, k1 + 2]
      g <- c(1 / b2, -b1 / b2^2)
      se_r <- sqrt(drop(t(g) %*% matrix(c(v11, v12, v12, v22), 2) %*% g))
      PT[[length(PT) + 1L]] <- data.table(outcome = nm, shock = s, estimator = "lp", h = h, n = nrow(z),
                                          b_rate25 = 0.25 * b1, se_rate25 = 0.25 * sqrt(v11),
                                          b_bi25 = 0.25 * b2, se_bi25 = 0.25 * sqrt(v22),
                                          ratio = unname(b1 / b2), se_ratio = se_r, t_bi = unname(b2 / sqrt(v22)),
                                          weak_denominator = abs(b2 / sqrt(v22)) < 2)
    }
  }
}
# DL version: both clean monthly changes on eps_{t-k}, k = 0..24, on the same months; joint NW(12);
# cumulative responses = sums of the first h+1 lag coefficients
for (nm in PT_OUT) {
  x <- prep(nm)
  D <- merge(x[!is.na(dyv), .(m, y1 = dyv)], xb[!is.na(dyv), .(m, y2 = dyv)], by = "m")
  for (s in SHOCKS) {
    f <- add_shock_lags(copy(D), shk, s, H_MAX)
    E <- as.matrix(f[, paste0("e_l", 0:H_MAX), with = FALSE])
    okr <- complete.cases(E)
    if (sum(okr) < MIN_N) next
    f1 <- lm(f$y1[okr] ~ E[okr, ]); f2 <- lm(f$y2[okr] ~ E[okr, ])
    V <- joint_nw(f1, f2, 12L); k1 <- length(coef(f1))
    for (h in c(6L, 12L)) {
      a <- c(0, rep(1, h + 1), rep(0, H_MAX - h))
      b1 <- sum(a * coef(f1)); b2 <- sum(a * coef(f2))
      v11 <- drop(t(a) %*% V[1:k1, 1:k1] %*% a); v22 <- drop(t(a) %*% V[k1 + 1:k1, k1 + 1:k1] %*% a)
      v12 <- drop(t(a) %*% V[1:k1, k1 + 1:k1] %*% a)
      g <- c(1 / b2, -b1 / b2^2)
      se_r <- sqrt(drop(t(g) %*% matrix(c(v11, v12, v12, v22), 2) %*% g))
      PT[[length(PT) + 1L]] <- data.table(outcome = nm, shock = s, estimator = "dl", h = h, n = sum(okr),
                                          b_rate25 = 0.25 * b1, se_rate25 = 0.25 * sqrt(v11),
                                          b_bi25 = 0.25 * b2, se_bi25 = 0.25 * sqrt(v22),
                                          ratio = b1 / b2, se_ratio = se_r, t_bi = b2 / sqrt(v22),
                                          weak_denominator = abs(b2 / sqrt(v22)) < 2)
    }
  }
}
PT <- rbindlist(PT)
setorder(PT, outcome, shock, estimator, h)
fwrite(PT, file.path(TAB, "mech_passthrough.csv"))

# =============================================================================================
# 4b. Pre-trend / lead placebo (pre-analysis plan section 6): the shock at t should not predict
#     (i) LP: the change over [t-4, t-1], y_{t-1} - y_{t-5}, regressed on eps_t, NW lag 5, clean windows only;
#     (ii) DL: the sum of the coefficients on eps_{t+1..t+6} in the DL of the clean monthly change (NW 12).
# =============================================================================================
PRE_OUT <- c("bi_policy", "dep_conv_1m", "dep_isl_1m", "spread_1m", "dep_bus_1m", "dep_uus_1m", "spread_bus_1m", "spread_uus_1m", "gap_bus_uus_1m",
             "lend_conv_wc", "fin_isl_murabahah", "fspread_isl_murabahah_wc", "fspread_isl_murabahah_cons",
             "dpk_isl_total", "dpk_conv_total", "dpk_diff_total", "dpk_diff_time", "fdr_isl", "share_murabahah_isl", "share_ps_isl", "npf_isl")
PRE <- list()
for (nm in PRE_OUT) {
  x <- prep(nm)
  x[, dpre := shift(y, 1L) - shift(y, 5L)]
  x[(shift(bad, 1L) - shift(bad, 5L)) != 0, dpre := NA_real_]
  D <- x[!is.na(dyv), .(m, y = dyv)]
  for (s in SHOCKS) {
    z <- x[!is.na(dpre) & !is.na(get(s))]
    if (nrow(z) >= MIN_N) {
      nw <- nw_lp(z$dpre, as.matrix(z[, s, with = FALSE]), lag = 5L)
      PRE[[length(PRE) + 1L]] <- data.table(outcome = nm, shock = s, test = "lp_pretrend_[t-4,t-1]",
                                            b25 = 0.25 * unname(nw$coef[2]), se25 = 0.25 * unname(nw$se[2]), n = nw$n)
    }
    f <- add_shock_lags(copy(D), shk, s, H_MAX, leads = 6L)
    vn <- c(paste0("e_f", 6:1), paste0("e_l", 0:H_MAX))
    X <- as.matrix(f[, vn, with = FALSE]); okr <- complete.cases(X)
    if (sum(okr) >= MIN_N) {
      fit <- lm(f$y[okr] ~ X[okr, ])
      V <- sandwich::NeweyWest(fit, lag = 12L, prewhite = FALSE, adjust = TRUE)
      li <- 1 + 1:6
      PRE[[length(PRE) + 1L]] <- data.table(outcome = nm, shock = s, test = "dl_sum_6_leads",
                                            b25 = 0.25 * sum(coef(fit)[li]), se25 = 0.25 * sqrt(sum(V[li, li])), n = nobs(fit))
    }
  }
}
PRE <- rbindlist(PRE)
PRE[, `:=`(t = b25 / se25, p = 2 * pnorm(-abs(b25 / se25)))]
fwrite(PRE, file.path(TAB, "mech_pretrend.csv"))

# =============================================================================================
# 4c. Sample robustness (revision, after the verification) and the pre-analysis plan's section-6 checks.
#     The DL regresses the change of month t on eps_{t-k}, k = 0..24, so the 2009 outcome months (first clean
#     change 2009-02) load on 2007-02..2008-12 shocks; the LP never uses a shock before 2009-05 (3 own lags need 2009-01..04).
#     Every variant restricts the OUTCOME months: DL keeps month t's clean change if t is kept; LP keeps
#     the window t if every month of [t-1, t+h] is kept. All variants run are reported (mech_robustness.csv).
#       full; from_2010 (no 2009 outcome month); from_2011 (DL: every shock lag in 2009+);
#       post_2014_07; to_2014_04; pap_drop_years (drop 2014, 2016, 2017, 2021); pap_drop_pandemic
#       (drop 2020-03..2021-12); loyo_<y> (leave calendar year y out, y = 2009..2025)
# =============================================================================================
HS_ROB <- c(0L, 3L, 6L, 12L, 24L)
ROB_OUT <- c("bi_policy", "dep_conv_1m", "dep_isl_1m", "spread_1m", "spread_1m_post14", "dep_bus_1m", "dep_uus_1m",
             "spread_bus_1m", "spread_uus_1m", "gap_bus_uus_1m", "lend_conv_wc", "lend_conv_cons", "fin_isl_murabahah",
             "fspread_isl_murabahah_wc", "fspread_isl_murabahah_cons", "fin_isl_use_wc", "fspread_use_wc", "fspread_use_cons",
             "dpk_diff_total", "dpk_diff_time", "fdr_isl", "fspread_isl_murabahah_wc_noevt", "dpk_diff_total_noevt", "gap_bus_uus_1m_noevt")
yr_of <- function(m) m %/% 12L
VARS <- c(list(full              = function(m) rep(TRUE, length(m)),
               from_2010         = function(m) m >= dm("2010-01-01"),
               from_2011         = function(m) m >= dm("2011-01-01"),
               post_2014_07      = function(m) m >= dm("2014-07-01"),
               to_2014_04        = function(m) m <= dm("2014-04-01"),
               pap_drop_years    = function(m) !(yr_of(m) %in% c(2014L, 2016L, 2017L, 2021L)),
               pap_drop_pandemic = function(m) !(m >= dm("2020-03-01") & m <= dm("2021-12-01"))),
          setNames(lapply(2009:2025, function(yy) { force(yy); function(m) yr_of(m) != yy }), paste0("loyo_", 2009:2025)))
ROB <- list()
t0 <- Sys.time()
for (nm in ROB_OUT) {
  x <- prep(nm)
  D0 <- x[!is.na(dyv), .(m, y = dyv)]
  for (v in names(VARS)) {
    kp <- VARS[[v]](x$m)
    x[, exc := cumsum(!kp)]
    for (s in SHOCKS) {
      r <- tryCatch(dl_ts(D0[VARS[[v]](m)], shk, s, K = H_MAX, L = 12L), error = function(e) NULL)
      if (!is.null(r) && r$n[1] >= MIN_N)
        ROB[[length(ROB) + 1L]] <- r[h %in% HS_ROB, .(outcome = nm, shock = s, estimator = "dl", variant = v, h, b, se, n)]
    }
    for (h in HS_ROB) {
      x <- lp_one(x, h)
      x[, wok := (shift(exc, h, type = "lead") - shift(exc, 2L)) == 0]
      for (s in SHOCKS) {
        vars <- c(s, "lag1", "lag2", "lag3")
        z <- x[wok %in% TRUE & complete.cases(x[, c("dh", vars), with = FALSE])]
        if (nrow(z) < MIN_N) next
        nw <- nw_lp(z$dh, as.matrix(z[, vars, with = FALSE]), lag = h + 1L)
        ROB[[length(ROB) + 1L]] <- data.table(outcome = nm, shock = s, estimator = "lp", variant = v, h = h,
                                              b = unname(nw$coef[2]), se = unname(nw$se[2]), n = nw$n)
      }
    }
  }
}
ROB <- rbindlist(ROB)
ROB[, `:=`(b25 = 0.25 * b, se25 = 0.25 * se, bsd = b * SD[shock], sesd = se * SD[shock], t = b / se)]
setcolorder(ROB, c("outcome", "shock", "estimator", "variant", "h", "b", "se", "b25", "se25", "bsd", "sesd", "n", "t"))
fwrite(ROB, file.path(TAB, "mech_robustness.csv"))
# check: the "full" variant reproduces the main estimates exactly
chk <- merge(ROB[variant == "full", .(outcome, shock, estimator, h, b_rob = b, n_rob = n)],
             RES[estimator %in% c("lp", "dl"), .(outcome, shock, estimator, h, b, n)], by = c("outcome", "shock", "estimator", "h"))
cat(sprintf("\nrobustness 'full' vs main: max |diff b| = %.2e, n mismatches = %d (rows %d)\n",
            max(abs(chk$b_rob - chk$b)), sum(chk$n_rob != chk$n), nrow(chk)))
# h = 12 summary: named variants plus the leave-one-year-out range
RS <- ROB[h == 12L]
LOYO <- RS[grepl("^loyo_", variant), .(loyo_min_b25 = min(b25), loyo_min_year = sub("loyo_", "", variant[which.min(b25)]),
                                        loyo_max_b25 = max(b25), loyo_max_year = sub("loyo_", "", variant[which.max(b25)]),
                                        loyo_min_abs_t = min(abs(t)), loyo_min_t_year = sub("loyo_", "", variant[which.min(abs(t))]),
                                        loyo_n_sig90 = sum(abs(t) > 1.645), loyo_k = .N),
           by = .(outcome, shock, estimator)]
RSW <- dcast(RS[!grepl("^loyo_", variant)], outcome + shock + estimator ~ variant,
             value.var = c("b25", "se25", "n"))
RSW <- merge(RSW, LOYO, by = c("outcome", "shock", "estimator"), all = TRUE)
fwrite(RSW, file.path(TAB, "mech_robustness_h12.csv"))
cat(sprintf("robustness done in %.1f s\n", as.numeric(difftime(Sys.time(), t0, units = "secs"))))

# =============================================================================================
# 4d. Block permutation (pre-analysis plan section 4/6: 12-month blocks, 2,000 draws), h = 12, DL and LP.
#     The monthly shock series over 2007-01..2025-06 (covering every month the DL uses) is permuted in 12-month
#     blocks; the DL and the LP are re-estimated with the permuted series (same rows, same own lags).
#     p = share of draws with |b*| >= |b|.
# =============================================================================================
NPERM <- 2000L
PERM_OUT <- c("spread_1m", "spread_1m_post14", "spread_bus_1m", "gap_bus_uus_1m", "fspread_isl_murabahah_wc", "dpk_diff_total")
SPAN <- (mid(SAMPLE_START) - H_MAX):mid(SAMPLE_END)
PERM <- list()
for (nm in PERM_OUT) {
  x <- lp_one(prep(nm), 12L)
  D0 <- x[!is.na(dyv), .(m, y = dyv)]
  for (s in SHOCKS) {
    sv <- shk[match(SPAN, m)][[s]]
    sp <- SPAN[!is.na(sv)]; sv <- sv[!is.na(sv)]
    P <- matrix(match(outer(D0$m, 0:H_MAX, "-"), sp), nrow(D0))
    rr <- complete.cases(P); P <- P[rr, , drop = FALSE]; yd <- D0$y[rr]
    stat_dl <- function(e) 0.25 * sum(qr.coef(qr(cbind(1, matrix(e[P], nrow(P)))), yd)[2:14])
    z <- x[complete.cases(x[, c("dh", "lag1", "lag2", "lag3"), with = FALSE])]
    pz <- match(z$m, sp); z <- z[!is.na(pz)]; pz <- pz[!is.na(pz)]
    Lz <- as.matrix(z[, .(lag1, lag2, lag3)])
    stat_lp <- function(e) 0.25 * qr.coef(qr(cbind(1, e[pz], Lz)), z$dh)[2]
    set.seed(20261029)
    IDX <- replicate(NPERM, block_perm(sv, 12L))
    for (est in c("dl", "lp")) {
      nob <- if (est == "dl") nrow(P) else nrow(z)
      if (nob < MIN_N) next
      f <- if (est == "dl") stat_dl else stat_lp
      b0 <- f(sv); bp <- apply(IDX, 2, function(ii) f(sv[ii]))
      PERM[[length(PERM) + 1L]] <- data.table(outcome = nm, shock = s, estimator = est, h = 12L, b25 = b0, n = nob,
                                              n_perm = NPERM, p_perm = mean(abs(bp) >= abs(b0)),
                                              q05 = unname(quantile(bp, 0.05)), q95 = unname(quantile(bp, 0.95)))
    }
  }
}
PERM <- rbindlist(PERM)
chk <- merge(PERM, RES[h == 12L, .(outcome, shock, estimator, b25_main = b25, n_main = n)], by = c("outcome", "shock", "estimator"))
cat(sprintf("permutation: observed b25 vs main max |diff| = %.2e; n mismatches = %d\n", max(abs(chk$b25 - chk$b25_main)), sum(chk$n != chk$n_main)))
fwrite(PERM, file.path(TAB, "mech_permutation.csv"))

# =============================================================================================
# 4e. Timing: FOMC announcements on the last calendar day of a month (ET) reach Jakarta on day 1 of the next
#     month (14:00 ET is after midnight in Jakarta), but the monthly shock series dates them in the earlier month.
# =============================================================================================
ev <- fread(file.path(CLEAN, "us_shocks_events.csv"))[shock %in% SHOCKS]
ev[, date := as.IDate(date)]
ev <- ev[mid(date) >= mid(SAMPLE_START) & mid(date) <= mid(SAMPLE_END) & value != 0]
ev[, last_day := month(date + 1L) != month(date)]
TIM <- ev[, .(events_nonzero = .N, on_last_day = sum(last_day), share_sumsq_last_day = sum(value[last_day]^2) / sum(value^2),
              last_day_dates = paste(format(date[last_day]), collapse = ";")), by = shock]
fwrite(TIM, file.path(TAB, "mech_timing.csv"))
# shocks of 2007-02..2008-12 enter the DL only (as lags of the 2009-2010 outcome months; the first clean change is
# 2009-02, whose longest lag is 2007-02); list them in s.d. units
PRES <- melt(shk[m > mid(SAMPLE_START) - H_MAX & m < mid(SAMPLE_START), c("m", SHOCKS), with = FALSE], id.vars = "m",
             variable.name = "shock", value.name = "value", variable.factor = FALSE)
PRES[, `:=`(month = format(mid2date(m), "%Y-%m"), z_sd_2009_2025 = value / SD[shock])]
PRES_SUM <- PRES[, .(months = .N, sum_sq_2007_02_2008_12 = sum(value^2, na.rm = TRUE),
                     largest = paste(head(sprintf("%s %.3f (%.1f sd)", month, value, z_sd_2009_2025)[order(-abs(value))], 4), collapse = "; ")), by = shock]
PRES_SUM <- merge(PRES_SUM, shk[m >= mid(SAMPLE_START) & m <= mid(SAMPLE_END), lapply(.SD, function(v) sum(v^2, na.rm = TRUE)), .SDcols = SHOCKS][
  , .(shock = SHOCKS, sum_sq_2009_2025 = unlist(.SD))], by = "shock")
PRES_SUM[, ratio_presample_to_2009_25 := sum_sq_2007_02_2008_12 / sum_sq_2009_2025]
fwrite(PRES[, .(shock, month, value, z_sd_2009_2025)], file.path(TAB, "mech_presample_shocks.csv"))
fwrite(PRES_SUM, file.path(TAB, "mech_presample_shocks_summary.csv"))
print(PRES_SUM)
print(TIM[, .(shock, events_nonzero, on_last_day, share_sumsq_last_day = round(share_sumsq_last_day, 3))])

# =============================================================================================
# 5. Summary tables (markdown, for the notes) and figures
# =============================================================================================
KEY <- c("bi_policy", "dep_conv_1m", "dep_isl_1m", "spread_1m", "dep_bus_1m", "dep_uus_1m", "spread_bus_1m", "spread_uus_1m",
         "gap_bus_uus_1m", "spread_1m_post14", "spread_1m_minbrk", "dep_conv_3m", "dep_isl_3m", "spread_3m", "spread_6m", "spread_12m",
         "lend_conv_cons", "lend_conv_wc", "lend_conv_inv", "fin_isl_murabahah", "fspread_isl_murabahah_cons", "fspread_isl_murabahah_wc",
         "fin_isl_mudharabah", "fspread_isl_mudharabah_wc", "fin_isl_musyarakah", "fspread_isl_musyarakah_inv",
         "fspread_use_cons", "fspread_use_wc", "fspread_use_inv", "fin_bus_murabahah", "fin_uus_murabahah", "fin_isl_use_wc", "fin_isl_use_cons",
         "dpk_isl_total", "dpk_conv_total", "dpk_diff_total", "dpk_diff_time", "dpk_diff_savings", "dpk_diff_demand",
         "dpk_diffmemo_total", "dpk_bus_total", "dpk_uus_total", "dpk_diff_bus_uus_total", "fdr_isl", "fdr_bus", "fdr_uus",
         "share_murabahah_isl", "share_ps_isl", "npf_isl", "npf_bus", "npf_uus",
         "fin_isl_murabahah_noevt", "fspread_isl_murabahah_wc_noevt", "dpk_diff_total_noevt", "gap_bus_uus_1m_noevt")
HS <- c(0, 3, 6, 12, 24)
cell <- function(b, se) ifelse(is.na(b), "", sprintf("%.2f (%.2f)%s", b, se, ifelse(abs(b / se) > 1.645, "*", "")))
md <- c("# Module M: auto-generated result tables (13_mechanisms.R)", "",
        "Per 25 bp shock: b25 (se25); * = |t| > 1.645 (90% band excludes 0). Rates/ratios in pp; volumes in percent.",
        "Columns h = months after the shock; n = months in the LP at h = 12. Blank = fewer than 40 usable months.", "")
for (s in SHOCKS) for (est in c("lp", "lp_ctrl", "lp_seas", "dl", "dl_seas")) {
  w <- RES[shock == s & estimator == est & outcome %in% KEY & h %in% HS]
  if (!nrow(w)) next
  w[, c := cell(b25, se25)]
  tb <- dcast(w, outcome ~ h, value.var = "c")
  nn <- w[h == 12, .(outcome, n12 = n)]
  tb <- merge(tb, nn, by = "outcome", all.x = TRUE)
  tb <- tb[match(intersect(KEY, tb$outcome), tb$outcome)]
  hcols <- setdiff(names(tb), c("outcome", "n12"))
  md <- c(md, sprintf("## shock = %s, estimator = %s (1 s.d. = %.4f pp; 25 bp = %.1f s.d.)", s, est, SD[[s]], 0.25 / SD[[s]]), "",
          paste0("| outcome | ", paste(paste0("h=", hcols), collapse = " | "), " | n (h=12) |"),
          paste0("|", paste(rep("---", ncol(tb)), collapse = "|"), "|"))
  for (i in seq_len(nrow(tb))) md <- c(md, paste0("| ", paste(unlist(tb[i]), collapse = " | "), " |"))
  md <- c(md, "")
}
md <- c(md, "## Per 1 s.d. of the shock, LP, h = 12 (bsd (sesd))", "")
w <- RES[estimator == "lp" & outcome %in% KEY & h == 12]
w[, c := cell(bsd, sesd)]
tb <- dcast(w, outcome ~ shock, value.var = "c"); tb <- tb[match(intersect(KEY, tb$outcome), tb$outcome)]
md <- c(md, paste0("| outcome | ", paste(names(tb)[-1], collapse = " | "), " |"), paste0("|", paste(rep("---", ncol(tb)), collapse = "|"), "|"))
for (i in seq_len(nrow(tb))) md <- c(md, paste0("| ", paste(unlist(tb[i]), collapse = " | "), " |"))
md <- c(md, "", "## Minimum detectable effect (80% power, 5% two-sided) = 2.80 x se25, LP and DL, h = 12 and 24", "",
        "| outcome | shock | MDE lp h12 | MDE lp h24 | MDE dl h12 | MDE dl h24 |", "|---|---|---|---|---|---|")
MDEO <- c("spread_1m", "spread_bus_1m", "spread_uus_1m", "fspread_isl_murabahah_cons", "fspread_use_cons", "dpk_diff_total", "dpk_diff_time",
          "share_murabahah_isl", "npf_isl")
for (o in MDEO) for (s in SHOCKS) {
  g <- function(e, hh) { v <- RES[outcome == o & shock == s & estimator == e & h == hh, se25]; if (length(v)) sprintf("%.2f", 2.8 * v) else "" }
  md <- c(md, sprintf("| %s | %s | %s | %s | %s | %s |", o, s, g("lp", 12), g("lp", 24), g("dl", 12), g("dl", 24)))
}
md <- c(md, "", "## Pass-through ratios (rate / BI policy rate, cumulative, same months; delta-method s.e.)", "",
        "| outcome | shock | estimator | h | n | rate b25 (se) | BI b25 (se) | ratio (se) | t(BI) |", "|---|---|---|---|---|---|---|---|---|")
for (i in seq_len(nrow(PT))) {
  p <- PT[i]
  md <- c(md, sprintf("| %s | %s | %s | %d | %d | %.2f (%.2f) | %.2f (%.2f) | %s | %.1f |", p$outcome, p$shock, p$estimator, p$h, p$n,
                      p$b_rate25, p$se_rate25, p$b_bi25, p$se_bi25,
                      if (p$weak_denominator) sprintf("%.2f (%.2f) weak", p$ratio, p$se_ratio) else sprintf("%.2f (%.2f)", p$ratio, p$se_ratio),
                      p$t_bi))
}
md <- c(md, "", "## Pre-trend / lead placebo (b25 (se25); should be ~0)", "",
        "| outcome | test | bi_rule_resid | jk_mp_median | jk_mp_pm | usmpd_stmt | jk_cbi_median |", "|---|---|---|---|---|---|---|")
for (o in PRE_OUT) for (tt in unique(PRE$test)) {
  g <- function(sh) { v <- PRE[outcome == o & test == tt & shock == sh]; if (nrow(v)) cell(v$b25, v$se25) else "" }
  md <- c(md, sprintf("| %s | %s | %s | %s | %s | %s | %s |", o, tt, g("bi_rule_resid"), g("jk_mp_median"), g("jk_mp_pm"), g("usmpd_stmt"), g("jk_cbi_median")))
}
md <- c(md, "", "## Sample robustness at h = 12 (b25 (se25); * = |t| > 1.645). Outcome months restricted; see section 4c of the script", "",
        "| outcome | shock | est | full | from_2010 | from_2011 | post_2014_07 | to_2014_04 | pap_drop_years | pap_drop_pandemic | leave-one-year-out range of b25 | min abs t (year) | LOYO sig90 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|")
vc <- function(r, v) { b <- r[[paste0("b25_", v)]]; s <- r[[paste0("se25_", v)]]; if (is.null(b) || is.na(b)) "" else cell(b, s) }
for (o in ROB_OUT) for (s in SHOCKS) for (est in c("dl", "lp")) {
  r <- RSW[outcome == o & shock == s & estimator == est]
  if (!nrow(r)) next
  md <- c(md, sprintf("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |", o, s, est,
                      vc(r, "full"), vc(r, "from_2010"), vc(r, "from_2011"), vc(r, "post_2014_07"), vc(r, "to_2014_04"),
                      vc(r, "pap_drop_years"), vc(r, "pap_drop_pandemic"),
                      if (is.na(r$loyo_min_b25)) "" else sprintf("%.2f (%s) .. %.2f (%s)", r$loyo_min_b25, r$loyo_min_year, r$loyo_max_b25, r$loyo_max_year),
                      if (is.na(r$loyo_min_abs_t)) "" else sprintf("%.2f (%s)", r$loyo_min_abs_t, r$loyo_min_t_year),
                      if (is.na(r$loyo_n_sig90)) "" else sprintf("%d of %d", r$loyo_n_sig90, r$loyo_k)))
}
md <- c(md, "", sprintf("## Block permutation of the shock (12-month blocks, %d draws), h = 12: p = share of |b*| >= |b|", NPERM), "",
        "| outcome | shock | est | b25 | n | p_perm | 5% / 95% of permuted b25 |", "|---|---|---|---|---|---|---|")
for (i in seq_len(nrow(PERM))) md <- c(md, with(PERM[i], sprintf("| %s | %s | %s | %.2f | %d | %.3f | %.2f / %.2f |", outcome, shock, estimator, b25, n, p_perm, q05, q95)))
md <- c(md, "", "## Event months flagged by the noise-aware rule (R3 of notes/data_panel.md)", "",
        "| outcome | month | event | abnormal change | z |", "|---|---|---|---|---|")
for (i in which(EVT$flagged)) md <- c(md, with(EVT[i], sprintf("| %s | %s | %s | %.2f | %.1f |", outcome, month, event, abnormal, z)))
md <- c(md, "", "## Timing: US shock events on the last calendar day of a month (ET), 2009-01..2025-06", "",
        "| shock | non-zero events | on last day | share of sum of squares |", "|---|---|---|---|")
for (i in seq_len(nrow(TIM))) md <- c(md, with(TIM[i], sprintf("| %s | %d | %d | %.3f |", shock, events_nonzero, on_last_day, share_sumsq_last_day)))
writeLines(md, file.path(TAB, "mech_results_tables.md"))
KR <- RES[outcome %in% KEY & h %in% HS, .(outcome, shock, estimator, h, b25, se25, bsd, sesd, n, mde25 = 2.8 * se25,
                                          sig90 = abs(b25 / se25) > 1.645)]
fwrite(KR, file.path(TAB, "mech_key_results.csv"))

# ---- figures --------------------------------------------------------------------------------
SHOCK_LAB <- c(bi_rule_resid = "BI policy-rule residual (25 bp)", jk_mp_median = "US pure MP shock, JK MP_median (25 bp)")
fig <- function(outs, labs, file, title) {
  d <- RES[outcome %in% outs & shock %in% FIG_SHOCKS & estimator %in% c("lp", "dl")]
  d[, panel := factor(labs[outcome], levels = labs)]
  d[, sh := factor(SHOCK_LAB[shock], levels = SHOCK_LAB)]
  d[, est := factor(toupper(estimator), levels = c("LP", "DL"))]
  p <- ggplot(d, aes(h, b25)) +
    geom_hline(yintercept = 0, linewidth = 0.3, colour = "grey50") +
    geom_ribbon(data = d[estimator == "dl"], aes(ymin = b25 - 1.645 * se25, ymax = b25 + 1.645 * se25), fill = "#E08A4F", alpha = 0.13) +
    geom_ribbon(data = d[estimator == "lp"], aes(ymin = b25 - 1.645 * se25, ymax = b25 + 1.645 * se25), fill = "#3B6EA8", alpha = 0.22) +
    geom_line(aes(linetype = est, colour = est), linewidth = 0.6) +
    scale_colour_manual(values = c(LP = "#1F3F66", DL = "#C2571A"), name = NULL) +
    scale_linetype_manual(values = c(LP = "solid", DL = "22"), name = NULL) +
    facet_grid(sh ~ panel, scales = "free_y", labeller = label_wrap_gen(24)) +
    scale_x_continuous(breaks = c(0, 6, 12, 18, 24)) +
    labs(x = "months after shock", y = "response per 25 bp shock", title = title,
         caption = paste("LP (solid, blue band) and DL (dashed, orange band), Newey-West 90% bands; LP horizons with < 40 months omitted.",
                         "Outcomes 2009-01..2025-06 (BUS/UUS 2014-06+). The DL also uses shock lags back to 2007-02; the LP's first shock month is 2009-05.",
                         sep = "\n")) +
    theme_minimal(base_size = 9) +
    theme(panel.grid.minor = element_blank(), strip.text = element_text(size = 7.5), plot.title = element_text(size = 10),
          plot.caption = element_text(size = 6.5, colour = "grey40"), legend.position = "top",
          legend.key.width = unit(1.2, "lines"), legend.margin = margin(0, 0, -6, 0))
  ggsave(file.path(FIG, file), p, width = 7, height = 4.5, dpi = 200, bg = "white")
}
fig(c("bi_policy", "dep_conv_1m", "dep_isl_1m", "spread_1m"),
    c(bi_policy = "BI policy rate (pp)", dep_conv_1m = "Conventional 1m deposit rate (pp)",
      dep_isl_1m = "Islamic 1m mudharabah return (pp)", spread_1m = "Spread Islamic - conventional, 1m (pp)"),
    "mech_fig1_deposit_passthrough.png", "Deposit-rate pass-through, 1-month tenor")
fig(c("dep_bus_1m", "dep_uus_1m", "spread_bus_1m", "gap_bus_uus_1m"),
    c(dep_bus_1m = "BUS 1m return (pp)", dep_uus_1m = "UUS 1m return (pp)", spread_bus_1m = "Spread BUS - conventional (pp)",
      gap_bus_uus_1m = "Gap BUS - UUS, 1m (pp)"),
    "mech_fig2_bus_uus_returns.png", "Islamic deposit returns, stand-alone banks (BUS) vs windows (UUS), 2014-06+")
fig(c("fin_isl_murabahah", "lend_conv_wc", "fspread_isl_murabahah_cons", "fspread_isl_murabahah_wc"),
    c(fin_isl_murabahah = "Islamic murabahah rate (pp)", lend_conv_wc = "Conventional working-capital rate (pp)",
      fspread_isl_murabahah_cons = "Spread murabahah - conv. consumption (pp)", fspread_isl_murabahah_wc = "Spread murabahah - conv. working capital (pp)"),
    "mech_fig3_financing_rates.png", "Financing-rate pass-through")
fig(c("dpk_isl_total", "dpk_conv_total", "dpk_diff_total", "dpk_diff_time"),
    c(dpk_isl_total = "Islamic DPK (%)", dpk_conv_total = "Conventional DPK (%)", dpk_diff_total = "Islamic - conventional DPK (%)",
      dpk_diff_time = "Islamic - conventional time deposits (%)"),
    "mech_fig4_funding.png", "Funding volumes: deposit (DPK) growth")
fig(c("share_murabahah_isl", "share_ps_isl", "fdr_isl", "npf_isl"),
    c(share_murabahah_isl = "Murabahah share (pp)", share_ps_isl = "Profit-sharing share (pp)", fdr_isl = "FDR (pp)", npf_isl = "NPF ratio (pp)"),
    "mech_fig5_mix_fdr_npf.png", "Islamic contract mix, FDR and NPF (BUS+UUS)")

cat("\n=== key results, LP, per 25 bp (se) ===\n")
w <- RES[estimator == "lp" & h %in% c(0, 6, 12, 24) & outcome %in% c("bi_policy", "dep_conv_1m", "dep_isl_1m", "spread_1m",
                                                                      "fspread_isl_murabahah_cons", "dpk_diff_total", "share_murabahah_isl", "npf_isl")]
print(dcast(w[, .(outcome, shock, h, e = sprintf("%6.2f (%4.2f)", b25, se25))], outcome + shock ~ h, value.var = "e"), nrows = 100)
cat("\nwrote: output/tables/mech_*.csv, mech_results_tables.md; output/figures/mech_fig1..5; data/clean/mech_monthly_series.csv\n")
