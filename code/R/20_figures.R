# 20_figures.R --------------------------------------------------------------
# Figures for the credit module. Light print surface; categorical slots in fixed order
# (blue, orange, aqua), validated all-pairs with the dataviz validator; 90% bands as a
# light fill of the series hue; recessive zero line and grid; one y-axis per panel.
source("C:/Users/consu/Documents/Universidad/Islamic_Finance_Project/wp_dual_banking/code/R/00_common.R")
suppressPackageStartupMessages(library(ggplot2))

S1 <- "#2a78d6"; S2 <- "#eb6834"; S3 <- "#1baf7a"
INK <- "#0b0b0b"; INK2 <- "#52514e"; GRID <- "#e6e5e1"; SURF <- "#fcfcfb"
FIG <- file.path(OUT, "figures")
theme_wp <- function() theme_minimal(base_size = 10) + theme(
  plot.background = element_rect(fill = SURF, colour = NA),
  panel.grid.minor = element_blank(), panel.grid.major.x = element_blank(),
  panel.grid.major.y = element_line(colour = GRID, linewidth = 0.3),
  axis.text = element_text(colour = INK2), axis.title = element_text(colour = INK2, size = 9),
  strip.text = element_text(colour = INK, face = "bold", hjust = 0),
  plot.title = element_text(colour = INK, face = "bold", size = 11),
  plot.subtitle = element_text(colour = INK2, size = 9),
  plot.caption = element_text(colour = INK2, size = 7.5, hjust = 0),
  legend.position = "top", legend.justification = "left", legend.title = element_blank(),
  legend.text = element_text(colour = INK2),
  plot.title.position = "plot", plot.caption.position = "plot")
save <- function(p, name, w = 7, h = 4.5) ggsave(file.path(FIG, name), p, width = w, height = h, dpi = 200, bg = SURF)
Z <- 1.645
irf_layers <- function() list(
  geom_hline(yintercept = 0, colour = "#9a9893", linewidth = 0.35),
  geom_ribbon(aes(ymin = lo, ymax = hi, fill = series), alpha = 0.16, colour = NA),
  geom_line(aes(colour = series), linewidth = 0.55),
  scale_x_continuous(breaks = seq(0, 24, 6)),
  labs(x = "Months after the shock"), theme_wp())

pan <- fread(file.path(CLEAN, "panel_sector_banktype.csv")); pan[, date := as.IDate(date)]
shr <- fread(file.path(CLEAN, "sector_islamic_share.csv")); shr[, date := as.IDate(date)]
lp9  <- fread(file.path(OUT, "tables", "lp_diff_H9_ISLCONV.csv"))
lp15 <- fread(file.path(OUT, "tables", "lp_diff_H15_ISLCONV.csv"))
dl   <- fread(file.path(OUT, "tables", "dl_diff.csv"))
lev  <- fread(file.path(OUT, "tables", "dl_levels.csv"))
mfs  <- fread(file.path(OUT, "tables", "macro_first_stage.csv"))
rob  <- fread(file.path(OUT, "tables", "credit_robustness.csv"))

# Figure 1: Islamic share of commercial-bank credit -----------------------------------
a <- shr[panel == "H9" & sector_h == "H9_ALL"]   # NA rows kept so the 2023 gap shows as a break
if (!nrow(a)) a <- pan[panel == "H9" & bank_type %in% c("ISL", "TOTAL"),
                       .(isl_share_pct = 100 * sum(credit_rp_bn[bank_type == "ISL"]) / sum(credit_rp_bn[bank_type == "TOTAL"])), by = date]
p1a <- ggplot(a, aes(date, isl_share_pct)) + geom_line(colour = S1, linewidth = 0.55) +
  scale_y_continuous(limits = c(0, NA), labels = function(x) paste0(x, "%")) +
  labs(title = "A. Islamic share of commercial-bank credit",
       caption = "Gap: Jan-Nov 2023 Islamic statistics are not available from archived open sources.\nSteps in 2016-09, 2018-09 and 2022-08 are conversions of regional banks to Islamic banks.",
       x = NULL, y = NULL) + theme_wp()
dmax <- shr[panel == "H15" & !is.na(isl_share_pct), max(date)]
b <- shr[panel == "H15" & sector_h != "H15_ALL" & date == dmax, .(sector_label, isl_share_pct)]
all15 <- shr[panel == "H15" & sector_h == "H15_ALL" & date == dmax, isl_share_pct]
b[, sector_label := factor(sector_label, levels = sector_label[order(isl_share_pct)])]
p1b <- ggplot(b, aes(isl_share_pct, sector_label)) +
  geom_col(fill = S1, width = 0.68) +
  geom_vline(xintercept = all15, colour = INK2, linewidth = 0.35, linetype = "22") +
  annotate("text", x = all15, y = 0.4, label = sprintf(" all sectors %.1f%%", all15), hjust = 0, vjust = 0,
           size = 2.7, colour = INK2) +
  geom_text(aes(label = sprintf("%.1f%%", isl_share_pct)), hjust = -0.15, size = 2.7, colour = INK2) +
  scale_x_continuous(expand = expansion(mult = c(0, 0.15)), labels = function(x) paste0(x, "%")) +
  labs(title = sprintf("B. Islamic share by sector, %s", format(dmax, "%b %Y")),
       x = NULL, y = NULL) + theme_wp() + theme(panel.grid.major.y = element_blank())
save(p1a, "fig1a_islamic_share.png", 7, 3)
save(p1b, "fig1b_sector_shares.png", 7, 4.6)

# Figure 2: macro first stage to the US pure-policy shock ---------------------------------
lab <- c(us2y = "US 2-year yield (pp)", bi = "BI policy rate (pp)", jibor = "JIBOR 1M (pp)",
         lidr = "IDR per USD (%; + = depreciation)", l_tot = "Commercial-bank credit (%)", lcpi = "CPI (%)")
m2 <- mfs[shock == "jk_mp_median" & outcome %in% names(lab)]
m2[, `:=`(est = 0.25 * b, lo = 0.25 * (b - Z * se), hi = 0.25 * (b + Z * se), series = "US")]
m2[, outcome := factor(lab[outcome], levels = lab)]
p2 <- ggplot(m2, aes(h, est)) +
  geom_hline(yintercept = 0, colour = "#9a9893", linewidth = 0.35) +
  geom_ribbon(aes(ymin = lo, ymax = hi), fill = S1, alpha = 0.16) +
  geom_line(colour = S1, linewidth = 0.55) +
  facet_wrap(~outcome, scales = "free_y", ncol = 3) +
  scale_x_continuous(breaks = seq(0, 24, 6)) +
  labs(title = "US pure monetary policy shock: Indonesian macro-financial responses",
       subtitle = "Response per 25 bp Jarocinski-Karadi MP shock (about 7 s.d.), local projections, 90% Newey-West bands",
       x = "Months after the shock", y = NULL) + theme_wp()
save(p2, "fig2_macro_first_stage.png", 7.5, 4.6)

# Figure 3 and 4: the differential ISL - CONV, plan LP vs DL --------------------------------
diff_dt <- function(s) {
  # LP horizons resting on fewer than 36 usable months are not shown (H15 beyond about 14 months)
  x1 <- rbind(lp9[shock == s & T >= 36, .(panel = "H9 (8 sectors, 2009-2025)", h, est = 25 * b, se = 25 * se, series = "Local projection (pre-registered)")],
              lp15[shock == s & T >= 36, .(panel = "H15 (15 sectors, 2016-2025)", h, est = 25 * b, se = 25 * se, series = "Local projection (pre-registered)")])
  x2 <- dl[shock == s, .(panel = fifelse(panel == "H9", "H9 (8 sectors, 2009-2025)", "H15 (15 sectors, 2016-2025)"),
                         h, est = b25, se = se25, series = "Distributed lag")]
  x <- rbind(x1, x2)
  x[, `:=`(lo = est - Z * se, hi = est + Z * se)]
  x[, panel := factor(panel, levels = c("H9 (8 sectors, 2009-2025)", "H15 (15 sectors, 2016-2025)"))]
  x[, series := factor(series, levels = c("Local projection (pre-registered)", "Distributed lag"))]
  x
}
cols <- scale_colour_manual(values = c(S1, S2)); fills <- scale_fill_manual(values = c(S1, S2))
p3 <- ggplot(diff_dt("jk_mp_median"), aes(h, est)) + irf_layers() + cols + fills +
  facet_wrap(~panel, ncol = 2) +
  labs(title = "Islamic minus conventional credit to the same sector: US pure monetary policy shock",
       subtitle = "Cumulative differential, percent, per 25 bp Jarocinski-Karadi MP shock; sector x month FE; 90% Driscoll-Kraay bands",
       caption = "The distributed lag has no Islamic x macro controls (Section 4.3). LP horizons with fewer than 36 usable months are omitted.",
       y = "Percent")
save(p3, "fig3_diff_us.png", 7.5, 4.2)
p4 <- ggplot(diff_dt("bi_rule_resid"), aes(h, est)) + irf_layers() + cols + fills +
  facet_wrap(~panel, ncol = 2) +
  labs(title = "Islamic minus conventional credit to the same sector: Bank Indonesia policy-rule shock",
       subtitle = "Cumulative differential, percent, per 25 bp policy-rule residual (about 2 s.d.); 90% Driscoll-Kraay bands",
       caption = "The distributed lag has no Islamic x macro controls (Section 4.3). LP horizons with fewer than 36 usable months are omitted.",
       y = "Percent")
save(p4, "fig4_diff_bi.png", 7.5, 4.2)

# Figure 5: robustness at h = 12 (DL) and the LP baseline -----------------------------------
spec_lab <- c(baseline = "Baseline (no Islamic x macro controls)", dl_ctrl_pre = "Islamic x macro controls dated t-25",
              weighted = "Weighted by Islamic credit", drop_break_years = "Drop 2014, 2016-17, 2021",
              drop_pandemic = "Drop 2020-03..2021-12", dl_ctrl_post = "Controls dated t-1 (first draft)",
              drop_post_conversion = "Drop 12 months after conversions/merger", drop_2013_2015 = "Drop 2013-2015",
              dl_ar3 = "DL with 3 own lags")
r5 <- rob[h == 12 & est == "DL" & !is.na(b)]
r5[, `:=`(lo = b25 - Z * se25, hi = b25 + Z * se25, spec = factor(spec_lab[spec], levels = rev(spec_lab)),
          shock = fifelse(shock == "jk_mp_median", "US pure MP shock (JK)", "BI policy-rule shock"),
          series = factor(panel, levels = c("H9", "H15")))]
r5[, shock := factor(shock, levels = c("US pure MP shock (JK)", "BI policy-rule shock"))]
p5 <- ggplot(r5, aes(b25, spec, colour = series)) +
  geom_vline(xintercept = 0, colour = "#9a9893", linewidth = 0.35) +
  geom_errorbarh(aes(xmin = lo, xmax = hi), height = 0, linewidth = 0.5, position = position_dodge(width = 0.6)) +
  geom_point(size = 2, position = position_dodge(width = 0.6)) +
  scale_colour_manual(values = c(H9 = S1, H15 = S2)) +
  facet_wrap(~shock, scales = "free_x") +
  labs(title = "Differential at 12 months across specifications (distributed lag)",
       subtitle = "Percent per 25 bp shock; 90% Driscoll-Kraay bands. Rows 1-5 are pre-specified checks; rows 6-9 were added",
       x = "Percent", y = NULL) + theme_wp() + theme(panel.grid.major.y = element_blank())
save(p5, "fig5_robustness.png", 7.5, 4.4)

# Figure 6: level responses by bank type (DL), US shock ----------------------------------------
l6 <- lev[shock %in% c("jk_mp_median", "bi_rule_resid")]
l6[, `:=`(lo = b25 - Z * se25, hi = b25 + Z * se25,
          series = fifelse(bank_type == "ISL", "Islamic (BUS + UUS)", "Conventional"),
          panel = fifelse(panel == "H9", "H9", "H15"),
          shock = fifelse(shock == "jk_mp_median", "US pure MP shock (JK)", "BI policy-rule shock"))]
l6[, facet := factor(paste(shock, panel, sep = " | "),
                     levels = c("US pure MP shock (JK) | H9", "US pure MP shock (JK) | H15",
                                "BI policy-rule shock | H9", "BI policy-rule shock | H15"))]
l6[, series := factor(series, levels = c("Conventional", "Islamic (BUS + UUS)"))]
l6[, est := b25]
p6 <- ggplot(l6, aes(h, est)) + irf_layers() + cols + fills + facet_wrap(~facet, ncol = 2, scales = "free_y") +
  labs(title = "Credit levels by bank type (no sector x month FE)",
       subtitle = "Cumulative response, percent, per 25 bp shock; sector FE; distributed lag; 90% Driscoll-Kraay bands",
       y = "Percent")
save(p6, "fig6_levels.png", 7.5, 5.6)

# Figure 7: deposit-rate pass-through (module M), LP vs DL --------------------------------------
dep <- fread(file.path(OUT, "tables", "mech_deposit_rates.csv"))
lab7 <- c(bi_policy = "BI policy rate", dep_conv_1m = "Conventional 1m deposit rate",
          dep_isl_1m = "Islamic 1m deposit return", spread_1m = "Spread, Islamic minus conventional")
d7 <- dep[outcome %in% names(lab7) & shock %in% c("jk_mp_median", "bi_rule_resid") & estimator %in% c("lp", "dl") & !is.na(b25) & h <= 24]
d7[, `:=`(est = b25, lo = b25 - Z * se25, hi = b25 + Z * se25,
          series = factor(fifelse(estimator == "lp", "Local projection", "Distributed lag"),
                          levels = c("Local projection", "Distributed lag")),
          outcome = factor(lab7[outcome], levels = lab7),
          shock = factor(fifelse(shock == "jk_mp_median", "US pure MP shock (JK)", "BI policy-rule shock"),
                         levels = c("US pure MP shock (JK)", "BI policy-rule shock")))]
p7 <- ggplot(d7, aes(h, est)) + irf_layers() + cols + fills +
  facet_grid(shock ~ outcome, scales = "free_y", labeller = label_wrap_gen(18)) +
  labs(title = "Deposit pricing: Islamic returns and conventional deposit rates",
       subtitle = "Cumulative response, percentage points, per 25 bp shock; aggregate monthly series, 2009-2025; 90% Newey-West bands",
       caption = "The distributed lag also uses US shock lags back to 2007-02; the local projection's first shock month is 2009-05. LP horizons with fewer than 40 months are omitted.",
       y = "Percentage points") + theme(strip.text.y = element_text(angle = 0))
save(p7, "fig7_deposit_passthrough.png", 8, 4.8)

# Figure 8: the 12-month spread across samples, per s.d. (module M) ---------------------------------
mr  <- fread(file.path(OUT, "tables", "mech_robustness_h12.csv"))
msd <- fread(file.path(OUT, "tables", "mech_shock_sd.csv"))
var8 <- c(full = "Full sample", from_2010 = "Outcomes from 2010 (no 2009)", from_2011 = "Outcomes from 2011",
          post_2014_07 = "From 2014-07", pap_drop_years = "Drop 2014, 2016-17, 2021", pap_drop_pandemic = "Drop 2020-03..2021-12")
sh8 <- c(jk_mp_median = "JK MP (median), primary", jk_mp_pm = "JK MP (poor man's)", usmpd_stmt = "FOMC statement surprise")
out8 <- c(spread_1m = "All Islamic banks minus conventional (2009+)", spread_bus_1m = "Stand-alone Islamic banks minus conventional (2014+)")
m8 <- melt(mr[outcome %in% names(out8) & shock %in% names(sh8)],
           id.vars = c("outcome", "shock", "estimator"),
           measure.vars = patterns(b = "^b25_", se = "^se25_"), variable.name = "vi")
vnames <- sub("^b25_", "", grep("^b25_", names(mr), value = TRUE))
m8[, variant := vnames[as.integer(vi)]]
m8 <- merge(m8, msd[, .(shock, sd = sd_2009_2025)], by = "shock")
m8 <- m8[variant %in% names(var8) & !is.na(b)]
m8 <- m8[!(outcome == "spread_bus_1m" & variant %in% c("from_2010", "from_2011", "post_2014_07"))]  # coincide with full
m8[, `:=`(est = b / 0.25 * sd, lo = (b - Z * se) / 0.25 * sd, hi = (b + Z * se) / 0.25 * sd,
          variant = factor(var8[variant], levels = rev(var8)), series = factor(sh8[shock], levels = sh8),
          outcome = factor(out8[outcome], levels = out8),
          estimator = factor(fifelse(estimator == "dl", "Distributed lag", "Local projection"),
                             levels = c("Distributed lag", "Local projection")))]
p8 <- ggplot(m8, aes(est, variant, colour = series)) +
  geom_vline(xintercept = 0, colour = "#9a9893", linewidth = 0.35) +
  geom_errorbarh(aes(xmin = lo, xmax = hi), height = 0, linewidth = 0.5, position = position_dodge(width = 0.7)) +
  geom_point(size = 1.8, position = position_dodge(width = 0.7)) +
  scale_colour_manual(values = c(S1, S2, S3)) +
  facet_grid(estimator ~ outcome, labeller = label_wrap_gen(30)) +
  labs(title = "The 12-month deposit spread across samples",
       subtitle = "Islamic minus conventional 1-month deposit rate, percentage points per 1 s.d. US surprise; 90% Newey-West bands",
       caption = "Blank rows: fewer than 40 months for the local projection, or the variant coincides with the full sample (stand-alone banks start in 2014-06).",
       x = "Percentage points per s.d.", y = NULL) +
  theme_wp() + theme(panel.grid.major.y = element_blank(), strip.text.y = element_text(angle = 0))
save(p8, "fig8_spread_samples.png", 8, 5.6)

# Figure 9: non-resident holdings of SUN and SBSN around FOMC announcements (module S) ---------------
sv <- fread(file.path(OUT, "tables", "sov_daily_lp_all.csv"))
lab9 <- c("SUN|pct" = "Conventional bonds (SUN), pp of outstanding", "SBSN|pct" = "Sukuk (SBSN), pp of outstanding",
          "SBSN_minus_SUN|pct" = "SBSN minus SUN, pp of outstanding", "SBSN_minus_SUN|log" = "SBSN minus SUN, log change (%)")
s9 <- sv[shock == "jk_mp_median" & holder == "nonresidents" & spec %in% c("allday_settle", "allday_drop0303_settle")]
s9[, key := paste(instrument, scaling, sep = "|")]
s9 <- s9[key %in% names(lab9)]
s9[, `:=`(est = bsd, lo = fifelse(spec == "allday_settle", lo90_sd, NA_real_), hi = fifelse(spec == "allday_settle", hi90_sd, NA_real_),
          series = factor(fifelse(spec == "allday_settle", "Primary specification", "Dropping the 2020-03-03 emergency cut"),
                          levels = c("Primary specification", "Dropping the 2020-03-03 emergency cut")),
          panel = factor(lab9[key], levels = lab9))]
p9 <- ggplot(s9, aes(h, est)) +
  geom_hline(yintercept = 0, colour = "#9a9893", linewidth = 0.35) +
  geom_ribbon(data = s9[!is.na(lo)], aes(ymin = lo, ymax = hi), fill = S1, alpha = 0.16) +
  geom_line(aes(colour = series, linetype = series), linewidth = 0.55) +
  scale_colour_manual(values = c(S1, S2)) + scale_linetype_manual(values = c("solid", "22")) +
  facet_wrap(~panel, scales = "free_y", ncol = 2) +
  scale_x_continuous(breaks = seq(0, 20, 5)) +
  labs(title = "Non-resident holdings of government bonds after a US pure monetary policy surprise",
       subtitle = "Per 1 s.d. JK MP surprise (3.7 bp); daily local projection, 2016-2022, 58 FOMC events; 90% Newey-West band (primary)",
       caption = "Day 0 is the first Jakarta trading day after the announcement. If secondary trades settle T+2 (not verified), days 0-1 still reflect pre-announcement trades.",
       x = "Trading days after the announcement", y = NULL) + theme_wp()
save(p9, "fig9_sovereign.png", 7.5, 5.2)
cat("figures written to output/figures\n")
