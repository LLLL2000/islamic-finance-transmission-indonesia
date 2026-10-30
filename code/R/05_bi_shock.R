# 05_bi_shock.R -------------------------------------------------------------
# Domestic (Bank Indonesia) monetary policy shock, pre-analysis plan section 3:
# the residual of a monthly policy rule. Identification is selection on
# observables: the residual is a shock only if BI reacts to nothing that is
# missing from the rule. It is reported as less credible than the US
# high-frequency shock.
source("C:/Users/consu/Documents/Universidad/Islamic_Finance_Project/wp_dual_banking/code/R/00_common.R")

bp <- fread(file.path(CLEAN, "bi_policy_candidates.csv"))
bp[, date := as.IDate(date)][, m := mid(date)]
mac <- fread(file.path(CLEAN, "macro_monthly.csv"))
mac[, date := as.IDate(date)][, m := mid(date)]
s <- fread(file.path(CLEAN, "us_shocks_monthly.csv"))[shock == "jk_mp_median"]
s[, date := as.IDate(date)][, m := mid(date)]

d <- merge(bp[, .(m, date, dpol = d_policy_eom_adj_pp, decision_month)],
           mac[, .(m, infl = idn_cpi_yoy_pct, ipg = idn_mfg_prod_yoy_pct,
                   lidr = log(idr_per_usd_avg), vix = us_vix_avg_index,
                   us2y = us_2y_yield_avg_pct, lbrent = log(brent_spot_avg_usd_bbl))], by = "m")
d <- merge(d, s[, .(m, us_mp = fifelse(is.na(value), 0, value))], by = "m", all.x = TRUE)
setorder(d, m)
d[, `:=`(dlidr = 100 * (lidr - shift(lidr)), dvix = vix - shift(vix),
         dus2y = us2y - shift(us2y), dlbrent = 100 * (lbrent - shift(lbrent)))]
for (l in 1:3) d[, paste0("dpol_l", l) := shift(dpol, l)]
d[, `:=`(infl_l1 = shift(infl), ipg_l1 = shift(ipg), dlidr_l1 = shift(dlidr),
         dlidr_l2 = shift(dlidr, 2), dvix_l1 = shift(dvix), dus2y_l1 = shift(dus2y),
         dlbrent_l1 = shift(dlbrent))]

rule <- dpol ~ dpol_l1 + dpol_l2 + dpol_l3 + infl_l1 + ipg_l1 + dlidr_l1 + dlidr_l2 +
  dvix_l1 + dus2y_l1 + dlbrent_l1 + us_mp
est <- d[date >= as.IDate("2006-01-01") & date <= as.IDate("2026-08-01")]
fit <- lm(rule, data = est)
cat("=== BI policy rule (monthly, d policy rate, pp; 2016 instrument switch adjusted) ===\n")
print(round(summary(fit)$coefficients, 4))
cat(sprintf("R2 = %.3f, n = %d\n", summary(fit)$r.squared, nobs(fit)))

# attach residuals by month (lm drops incomplete rows, so match on m)
mf <- model.frame(fit)
rr <- data.table(m = est[as.integer(rownames(mf)), m], r = unname(resid(fit)))
d[, bi_rule_resid := NA_real_]
d[rr, on = "m", bi_rule_resid := i.r]
d[, bi_dpol_raw := dpol]

cat(sprintf("\nresidual s.d. = %.3f pp; corr with raw d policy = %.3f; corr with US MP shock = %.3f\n",
            sd(d$bi_rule_resid, na.rm = TRUE),
            cor(d$bi_rule_resid, d$dpol, use = "complete.obs"),
            cor(d$bi_rule_resid, d$us_mp, use = "complete.obs")))
cat(sprintf("share of residual variance in BI decision months: %.2f\n",
            d[decision_month == 1, sum(bi_rule_resid^2, na.rm = TRUE)] / sum(d$bi_rule_resid^2, na.rm = TRUE)))

out <- d[, .(date, bi_rule_resid, bi_dpol_raw)]
fwrite(out, file.path(CLEAN, "bi_shock_residual.csv"))
cat("wrote data/clean/bi_shock_residual.csv\n")
