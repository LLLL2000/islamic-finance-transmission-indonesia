# 11_macro_first_stage.R ----------------------------------------------------
# Do the shocks move Indonesian financial conditions at all? Time-series LPs, NW errors.
#   y_{t+h} - y_{t-1} = b_h eps_t + sum_{l=1..3} g_l dy_{t-l} + u
# Outcomes: US 2y yield (sanity check for the US shocks), BI policy rate, JIBOR 1M,
# log IDR/USD, VIX, log aggregate commercial-bank credit, conventional and Islamic credit,
# Indonesian CPI. Percent (log x 100) or percentage points; per 25 bp shock.
source("C:/Users/consu/Documents/Universidad/Islamic_Finance_Project/wp_dual_banking/code/R/00_common.R")

SHOCKS <- c("jk_mp_median", "jk_mp_pm", "usmpd_stmt", "jk_cbi_median", "bi_rule_resid")
mac <- fread(file.path(CLEAN, "macro_monthly.csv")); mac[, date := as.IDate(date)][, m := mid(date)]
pan <- fread(file.path(CLEAN, "panel_sector_banktype.csv")); pan[, date := as.IDate(date)]
# aggregate credit from H9 sectors (sum over sectors). Months with any sector missing are NA;
# the change into a month is clean only if no unit of that type is flagged in that month.
agg <- pan[panel == "H9" & bank_type %in% c("ISL", "CONV", "TOTAL"),
           .(lev = if (anyNA(credit_rp_bn)) NA_real_ else sum(credit_rp_bn),
             ok = all(adj_growth_ok %in% TRUE)), by = .(date, bank_type)]
agg <- dcast(agg, date ~ bank_type, value.var = c("lev", "ok"))
agg[, m := mid(date)]

d <- merge(mac[, .(m, date, us2y = us_2y_yield_avg_pct, bi = idn_policy_rate_avg_adj_pct,
                   jibor = idn_jibor_1m_eom_pct, lidr = 100 * log(idr_per_usd_avg),
                   vix = us_vix_avg_index, lcpi = 100 * log(idn_cpi_index_2022eq100))],
           agg[, .(m, l_tot = 100 * log(lev_TOTAL), l_conv = 100 * log(lev_CONV), l_isl = 100 * log(lev_ISL),
                   ok_tot = ok_TOTAL, ok_conv = ok_CONV, ok_isl = ok_ISL)], by = "m", all.x = TRUE)
setorder(d, m)
shk <- load_shocks()
d <- merge(d, shk[, c("m", SHOCKS), with = FALSE], by = "m", all.x = TRUE)

OUTC <- list(us2y = NULL, bi = NULL, jibor = NULL, lidr = NULL, vix = NULL, lcpi = NULL,
             l_tot = "ok_tot", l_conv = "ok_conv", l_isl = "ok_isl")
res <- list()
for (yv in names(OUTC)) {
  okc <- OUTC[[yv]]
  x <- copy(d)
  x[, y := get(yv)]
  x[, dyv := y - shift(y)]
  if (!is.null(okc)) x[!(get(okc) %in% TRUE), dyv := NA_real_]
  x[, bad := cumsum(is.na(dyv))]   # windows must contain no missing or contaminated change
  for (l in 1:3) x[, paste0("lag", l) := shift(dyv, l)]
  for (s in SHOCKS) for (h in 0:H_MAX) {
    z <- copy(x)
    z[, dh := shift(y, h, type = "lead") - shift(y, 1L)]
    z[(shift(bad, h, type = "lead") - shift(bad, 1L)) != 0, dh := NA_real_]
    z <- z[date >= SAMPLE_START & date <= SAMPLE_END]
    z <- z[complete.cases(z[, c("dh", s, "lag1", "lag2", "lag3"), with = FALSE])]
    if (nrow(z) < 40) next
    X <- as.matrix(z[, c(s, "lag1", "lag2", "lag3"), with = FALSE])
    nw <- nw_lp(z$dh, X, lag = h + 1L)
    res[[length(res) + 1L]] <- data.table(outcome = yv, shock = s, h = h,
                                          b = unname(nw$coef[2]), se = unname(nw$se[2]), n = nw$n)
  }
}
res <- rbindlist(res)
res[, `:=`(b25 = 0.25 * b, se25 = 0.25 * se)]   # outcomes already in pct / pp
fwrite(res, file.path(OUT, "tables", "macro_first_stage.csv"))
cat("=== macro first stage: response per 25 bp shock (pp or percent), NW s.e. ===\n")
w <- res[h %in% c(0, 3, 6, 12, 24), .(est = sprintf("%6.2f (%4.2f)", b25, se25)), by = .(shock, outcome, h)]
print(dcast(w, shock + outcome ~ h, value.var = "est"), nrows = 200)
