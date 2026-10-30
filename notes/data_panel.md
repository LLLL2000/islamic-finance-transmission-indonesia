# Data note: harmonised sector x bank-type credit panel (H9, H15)

Builder: `harmonizer`. Script: `code/py/build_panel.py`. Rerun from the project root with
`python -I code/py/build_panel.py`. The script prints one JSON validation block, and every number below comes from
that block (final run of 2026-10-29). Two consecutive runs gave byte-identical outputs and an identical JSON block.

## 0. Summary

- **Inclusion decision.** SEKI I.4 commercial-bank credit (`total` minus `bpr`) **includes Islamic financing in every
  month 2009-01..2025-06**. Conventional credit is therefore `CONV = SEKI commercial - SPS (BUS+UUS)` in every month.
  - For BUS (stand-alone Islamic banks) the evidence is decisive.
  - For UUS (Islamic windows) it is strong but indirect (section 2).
- **H9** is the coarse panel, 2009-01..2025-06. It has **8 sectors**, not 9. The label "H9" is kept because the
  pre-analysis plan uses it.
  - The old SPS rows mix business services with household property (S08), and unclassified activities with other
    household financing (S10).
  - SEKI has no household breakdown before 2010-01.
  - So the only consistent treatment of households over 2009-2025 is one merged sector, `H9_SHH`: finance, real
    estate, business and social services, plus households.
- **H15** is the fine panel, 2016-06..2025-06, with **15 sectors**, including four household sectors.
  - It cannot start in 2014-06: SEKI's old classification, the only SEKI series before 2016-06, has 9 business
    sectors and cannot support the finer split.
- **`adj_growth_ok`** is FALSE for 5.96% (H9) and 5.12% (H15) of the rows that have a month-on-month change. The reason
  is always in `flag_reasons`.

## 1. Inputs and outputs

| Input (data/clean/) | Rows | md5 |
|---|---|---|
| `ojk_islamic_financing_by_sector.csv` (ojk_sector builder) | 9,997 | `08cc588938484b4aff758469d7c17b43` |
| `ojk_conversion_events.csv` (ojk_sector builder) | 975 | `521fcddd9e296401f129b5f6d95484eb` |
| `bi_credit_by_sector_group.csv` (bi_credit builder) | 38,052 | `1abbe663d18fb758935269249b80de23` |

There is one validation-only input. The script reads `data/raw/ojk/SPI_2025_02.xlsx` (OJK *Statistik Perbankan
Indonesia*, Feb-2025 edition, placed there by the bi_credit builder) read-only and values-only, for check T7. No
output depends on it, and the check is skipped if the file is absent. Nothing else in `data/raw/` is read.

| Output (data/clean/) | Rows | md5 |
|---|---|---|
| `sector_crosswalk.csv` | 108 | `dec19a8e6b35444943bcb1c4ec205792` |
| `panel_sector_banktype.csv` | 16,095 | `98ba7386997438ddd677d9ae31afd46c` |
| `sector_islamic_share.csv` | 3,526 | `806f4e241eeb7e861dfb50398e26fc8e` |

All amounts are in Rp billion, end of month, nominal and not seasonally adjusted. `date` is the first day of the month.

## 2. Does SEKI commercial-bank credit include Islamic financing?

The two hypotheses are:
- **A:** SEKI includes BUS and UUS financing throughout.
- **B:** SEKI excludes them before May 2014 (the LBUS/LSMK footnote month) and includes them after.

Under B, conventional credit equals SEKI before 2014-05 and SEKI minus Islamic from 2014-05. The tests are
T1..T9 in the JSON block.

**T1. Level of the commercial total at 2014-05.**
- Change: 3,328,319.2 to 3,370,227.3 Rp bn, Δlog +1.25%. The median absolute monthly Δlog over 2009-2025 is 1.10%.
- Islamic financing in 2014-05 was 189,689.7 = 5.63% of SEKI commercial credit. Under B that block would have entered
  SEKI in one month. It did not.
- **T6, BUS alone:** BUS was 143,315.6 in Jun-2014. If BUS had entered in May 2014, the underlying growth that month
  would have been **-3.09%**. That is below every month of 2009-2025 (minimum -2.21%; share of months at or below = 0.000).
- **T9:** no other month looks like a first inclusion. The five months with a rise above 3% (2009-12, 2010-05,
  2010-06, 2010-12, 2011-06) are broad-based across bank groups.
  - For example, 2010-06: persero +3.94%, BSN +3.55%, BPD +2.91%, foreign/joint +3.46%.
  - Most Islamic banks sit in the private national group (BSN). The largest BSN excess over the other groups is about
    1.5 pp at the year-ends. BSN held 41.3-44.7% of commercial credit in those months, so adding all Islamic financing
    (3.3-3.9% of commercial credit) to BSN would have raised it by roughly 8%.

**T2. Conventional growth at 2014-05 under A and B** (Δlog %, with z = Δlog / sd of the A-series over 2009-2025):

| series | A: Δlog | B: Δlog | sd (A) | z A | z B |
|---|---|---|---|---|---|
| commercial total | 1.27 | **-4.54** | 1.21 | | |
| H9_AGR | 1.90 | -0.05 | 1.92 | 0.99 | -0.03 |
| H9_MIN | -6.79 | -9.56 | 5.12 | -1.33 | -1.87 |
| H9_MAN | 0.34 | -0.71 | 1.96 | 0.17 | -0.36 |
| H9_UTL | 1.71 | -3.45 | 5.92 | 0.29 | -0.58 |
| H9_CON | 2.49 | -4.66 | 3.05 | 0.82 | -1.53 |
| H9_TRD | 1.76 | -0.46 | 2.08 | 0.84 | -0.22 |
| H9_TRN | -1.32 | -5.55 | 2.58 | -0.51 | -2.15 |
| H9_SHH | 2.26 | **-8.69** | 1.07 | 2.10 | **-8.10** |

- Under B, conventional credit would fall 4.54% in one month. That is twice the largest monthly fall of the A-series
  in 2009-2025 (-2.30%).
- Under B, the services-and-households sector would fall by 8.1 standard deviations.
- Under A, every sector is within 2.1 sd. That month is flagged anyway (section 5).

**T3. SEKI mirrors SPS reclassifications in the same month.** In 2014-07 OJK moved Islamic shop-house financing
(N03) into other household financing (N05). SEKI's household items moved the same way in the same month.

| SEKI old9 item (commercial) | SPS codes | ΔSEKI 2014-07 | ΔISL 2014-07 | ΔCONV 2014-07 | sd ΔSEKI | sd ΔCONV |
|---|---|---|---|---|---|---|
| HH_shophouse_office | N03 | **-11,034.7** | **-11,174.8** | **+140.1** | 1,892.4 | **234.2** |
| HH_housing | N01 | -804.6 | -3,014.6 | +2,210.0 | 1,864.3 | 1,510.2 |
| HH_other | N05+N06 | +13,057.8 | +9,250.5 | +3,807.3 | 4,064.1 | 3,894.0 |
| KLMN finance/real estate/business | L10+L11 | -2,885.8 | -2,436.6 | -449.2 | 6,442.8 | 5,862.3 |
| OPQRS services | L12..L18 | -259.2 | -476.1 | +216.9 | 5,809.9 | 5,613.2 |

- The sd columns are over 35 months, 2014-07..2017-06, excluding the 2016-09 conversion.
- Shop-house: the slope of ΔSEKI on ΔISL is 0.99, and subtracting Islamic financing makes the series 8 times smoother.
- Removing the Islamic part lowers the volatility of every one of the 14 SEKI items tested.
- In 2014-07 OJK moved 6.5 tn out of "not clearly defined" (L18) and 5.4 tn into community services (L15). SEKI
  services moved only -0.26 tn. So SEKI's services contain both L15 and L18 (relevant to the L18 mapping in
  section 3).

**T8. SEKI's own reshuffle at the footnoted 2014-05 change** (abnormal change = change minus the median monthly change
of the previous 12 months):
- Services: -30,160.6 (-20.0%).
- Finance/real estate/business: +15,601.5 (+5.7%).
- Shop-house: +12,756.0 (+51.3%).
- Housing: +12,400.5 (+4.6%).
- Vehicles: +7,889.6 (+7.5%).
- Other household: -17,474.8 (-3.5%).
- Commercial total: -9,740.3 (-0.29%).

About 50 tn was reallocated across SEKI categories while the total did not move. That is what a reclassification of
data already inside SEKI looks like; a first inclusion would have raised the total. It fits the footnote's "change of
coverage and classification with LBUS", although the reshuffle need not be confined to the Islamic component.

**T4. Whole conventional regional banks converting to BUS.** If SEKI excluded Islamic banks, the converting bank
would leave SEKI's BPD group that month.

| event | BUS abnormal jump | SEKI BPD Δlog | implied BPD Δlog if Islamic excluded |
|---|---|---|---|
| Bank Aceh, 2016-09 | 14,883.9 | +0.89% | **-3.46%** |
| Bank NTB, 2018-09 | 4,381.4 | +1.10% | +0.03% |
| Bank Riau Kepri, 2022-08 | 19,870.8 | +0.68% | **-3.05%** |

The median absolute monthly BPD Δlog is 0.76%. Aceh and Riau Kepri are decisive. NTB is too small to discriminate.

**T6/T7. UUS specifically.** UUS are units inside conventional banks, so the question is whether SEKI counts the
UUS book with its parent bank.
- *2014-05 is uninformative for UUS.* UUS was 49,820.5 in Jun-2014 (1.48% of commercial credit). A UUS entry would
  imply -0.24% underlying growth, and 16.8% of months are lower.
- *Riau Kepri, 2022-08.* The converting bank's UUS book (UUS abnormal change -9,429.8) moved into the new BUS. If SEKI
  excluded UUS, that book would have entered the BPD group, which implies underlying BPD growth of **-1.08%**. Only 6.5%
  of BPD months in 2016-07..2025-06 are that low.
- *OJK SPI cross-check (T7).*
  - SPI Tabel 3.1.a, "Kredit/Pembiayaan dan NPL/NPF Bank Umum Kepada Pihak Ketiga Bukan Bank", covers credit and
    financing of all commercial banks, conventional and sharia (105 banks in Dec-2024, SPI Tabel 1). It uses the same
    LBU sector codes as SPS.
  - SPI's household items equal SEKI's commercial household items within **0.004% (housing), 0.074% (flats), 0.023%
    (shop-houses), 0.003% (vehicles) and 0.146% (other)** in all 12 clean monthly columns (2024-02..2025-02, without the
    provisional 2024-03).
  - UUS household financing was **119,802.4** in Dec-2024. The SPI-minus-SEKI household gap was **1,669.8**. So SPI and
    SEKI treat UUS identically.
  - SPI is OJK's statistic for commercial banks' credit and financing. Its label ("Kredit/Pembiayaan, NPL/NPF") and its
    bank count include the sharia side.
  - The SPI total exceeds SEKI by 265,307.0 in Dec-2024. Of this, **95,987.0 is public administration** (SPI L12
    96,690.1 vs SEKI O 703.1; SEKI I.4 leaves central-government credit out of its sector table, as a memo item in the
    old sheet) and only 1,669.8 is households. The rest is in business sectors (non-resident borrowers and
    classification differences, section 3).
  - So the earlier Dec-2024 comparison (a 265 tn gap, of similar size to UUS financing of 211 tn) does not indicate
    that UUS is excluded.
  - No LBU code has SPI below BUS+UUS: the minimum of SPI minus (BUS+UUS) over codes and months is 0.0.

**Decision:** A holds. Subtract BUS+UUS in every month.

**Sensitivity:** if SEKI nevertheless excluded UUS, CONV would be understated by UUS/CONV.
- In 2025-06 that ratio is 0.7-3.0% in business sectors, 5.3% in H9_SHH, and 14.9%, 14.7% and 5.5% in the H15
  housing, shop-house and vehicle sectors.
- The maxima over the sample are given in the JSON (`uus_as_pct_of_conv_max`, at most 19.3%, H15_HSH).

**Before 2014-05 (T5).**
- SPS used an older sector basis up to 2014-04. SEKI's classification of the Islamic part it contains need not match
  that basis.
- The SPS reclassification at 2014-05 bounds the resulting level error in CONV, as a share of CONV in 2014-04:
  - TRN: 8,500.1, **5.46%**.
  - SHH: -16,063.5, 1.33%.
  - UTL: 0.98%. CON: 0.88%. MAN: 0.79%. TRD: 0.47%. AGR: 0.37%. MIN: 0.33%.
- These are level offsets, roughly constant over 2009-2014. They affect growth rates only through the growth of the
  misallocated Islamic piece.

## 3. Sector crosswalk (`sector_crosswalk.csv`)

One row per (panel, harmonised sector, source code). Columns:
- `panel`, `sector_h`, `sector_label`
- `source` (OJK SPS / BI SEKI I.4), `source_classification` (old9 / new19 / kbli17), `source_code`
- `source_label_id`, `source_label_en`
- `valid_from`, `valid_to`: the months in which this source code feeds the panel
- `mapping_quality`, `basis`

Every source code is used exactly once per panel and source (asserted). Sector sums equal the source totals (V3).

Source windows:

| panel | Islamic side | SEKI side |
|---|---|---|
| H9 | SPS old9 (S01-S10, BUS+UUS only) 2009-01..2014-05; SPS new19 (L01-L18, N01-N06) 2014-06..2025-06 | SEKI old9 2009-01..2017-06; SEKI kbli17 2017-07..2025-06 |
| H15 | SPS new19 2016-06..2025-06 | SEKI kbli17 2016-06..2025-06 |

### 3.1 H9 (8 sectors)

| sector_h | SPS old9 | SPS new19 | SEKI old9 | SEKI kbli17 | kbli17 vs old9, 13 overlap months |
|---|---|---|---|---|---|
| H9_AGR agriculture, forestry, fishery | S01 | L01, L02 | old_A_agri | A_agri | +0.02 to +0.04% |
| H9_MIN mining | S02 | L03 | old_B_mining | B_mining | -0.90 to -0.58% |
| H9_MAN manufacturing | S03 | L04 | old_C_manuf | C_manuf | -0.12 to +0.04% |
| H9_UTL electricity, gas, water | S04 | L05 | old_DE_utilities | D_elec_gas, E_water_waste | +1.08 to +1.53% |
| H9_CON construction | S05 | L06 | old_F_construction | F_construction | 0.00% |
| H9_TRD trade, hotels, restaurants | S06 | L07, L08 | old_GI_trade_hotel_rest | G_trade, I_accom_food | +1.36 to +1.51% |
| H9_TRN transport, storage, communication | S07 | L09 | old_HJ_transport_comm | H_transport, J_info_comm | +8.48 to +9.26% |
| H9_SHH services and households | S08, S09, S10 | L10-L18, N01-N06 | old_KLMN, old_OPQRS, NONPROD_TOTAL | K, L, MN, O, P, Q, RSU, NONPROD_TOTAL | -1.71 to -1.56% |

Justification:
- **SPS old9 to new19 is exact.** OJK's own concordance holds exactly in the 12 overlap months: S01 = L01+L02,
  S02 = L03, S03 = L04, S04 = L05, S05 = L06, S06 = L07+L08, S07 = L09, S08 = L10+L11+N01+N02+N03, S09 = L12..L17,
  S10 = L18+N04+N05+N06.
  - Recomputed here at H9 level: the maximum absolute gap is 0.000 Rp bn for financing in every sector, and 0.000 for
    NPF except H9_TRD at 2.41 (the source inconsistency of 2014-09).
  - So the switch from old9 to new19 at 2014-06 introduces no break. The old9 values from 2014-05 are already a mapping
    of the LSMK data.
- **SPS new19 to SEKI old9.** SEKI's old 9-sector table aggregates the LBU categories that SPS still uses:
  - L01+L02 to agriculture incl. fishery; L07+L08 to trade/hotels/restaurants; L09 to transport and communication;
    L10+L11 to finance/real estate/business; L12..L18 to services; N01..N06 to household consumption.
  - T3 is consistent with these correspondences: subtracting the mapped Islamic series lowers the month-to-month
    volatility of all 14 SEKI items. It also shows that "not clearly defined" (L18) sits in SEKI services.
- **SEKI old9 to kbli17.** At the H9 level the two classifications differ only by the stable gaps in the table, so the
  switch in 2017-07 is a level step of known size. It is flagged (`break_seki_splice_2017_07`).
  - H9 uses the old table until 2017-06 because that table shares the LBU lineage of SPS, so `SEKI - ISL` is better
    matched by classification for as long as it exists.
- **Why 8 sectors (households cannot be separated in H9):**
  - S08 contains household house, flat and shop-house ownership; S10 contains L18 plus vehicles and other household
    financing. The only union of old SPS rows that is also a union of SEKI rows is S08+S09+S10 = KLMN + OPQRS +
    household consumption.
  - SEKI's household items are all zero before 2010-01 (all consumption sat in "Lainnya"), so a household-property split
    fails in 2009 on the SEKI side too.
  - The old SPS basis before 2014-05 differs from the LSMK basis. Between 2014-04 and 2014-05 S08 rose from 49,532.3 to
    69,662.7, S09 fell from 12,148.7 to 8,006.4, and S10 fell from 77,871.1 to 47,448.9 Rp bn, while the total rose only
    1.0%. So even the S08 to finance+property correspondence, which is exact only from 2014-05, cannot be assumed for
    2009-2014-04.
  - Coarser is preferred to wrong precision. H9_SHH is 57-73% of Islamic financing (June shares) and about two-fifths of
    commercial credit.

### 3.2 H15 (15 sectors)

| sector_h | SPS new19 | SEKI kbli17 | all banks: SPI (LBU) vs SEKI (KBLI), % gap min / median / max | quality |
|---|---|---|---|---|
| H15_AGR | L01, L02 | A_agri | 0.35 / 0.44 / 0.51 | exact |
| H15_MIN | L03 | B_mining | 7.79 / 10.05 / 11.17 | exact (level gap) |
| H15_MAN | L04 | C_manuf | 3.82 / 4.01 / 4.17 | exact (level gap) |
| H15_UTL | L05 | D_elec_gas, E_water_waste | 3.48 / 5.05 / 5.33 | approximate |
| H15_CON | L06 | F_construction | 0.10 / 0.20 / 0.53 | exact |
| H15_TRD | L07 | G_trade | 0.96 / 1.86 / 2.21 | approximate |
| H15_ACC | L08 | I_accom_food | 0.10 / 0.35 / 0.40 | approximate |
| H15_TRN | L09 | H_transport, J_info_comm | -5.81 / -5.10 / -3.41 | approximate |
| H15_FIN | L10 | K_finance_insurance | 1.86 / 2.51 / 4.57 | approximate |
| H15_REB | L11 | L_real_estate, MN_business_services | 5.09 / 5.79 / 6.27 | approximate |
| H15_SOC | L12-L18 | O, P, Q, RSU | L13-L18 vs P+Q+RSU: 15.68 / 18.25 / 25.30; L12 vs O: central government | approximate |
| H15_HRE house and apartment | N01, N02 | HH_housing, HH_flat_apartment | 0.00 / 0.00 / 0.01 | exact |
| H15_HSH shop-house/office-house | N03 | HH_shophouse_office | 0.01 / 0.01 / 0.02 | exact |
| H15_HVE vehicles | N04 | HH_vehicles | 0.00 / 0.00 / 0.00 | exact |
| H15_HOT other household, other non-business | N05, N06 | HH_other | 0.12 / 0.13 / 0.15 | exact |

The SPI comparison (T7) puts the LBU classification of SPS and the KBLI-2015 classification of SEKI side by side for
**all commercial banks**, from the same bank reports. It is therefore a direct measure of how well each H15 mapping
lines up.
- Household items line up exactly.
- Agriculture, construction and accommodation are within 0.6%.
- The positive gaps in mining (+10%) and manufacturing (+4%) most likely come from non-resident borrowers, which SPI
  includes and SEKI I.4 (resident borrowers) excludes. They are level differences, stable over time.
- In transport, SEKI's KBLI H+J is about 5% larger than LBU L09. KBLI J (information and communication) is broader than
  the old "communication".
- Social services (H15_SOC) is the weakest mapping. LBU L13-L18 are 16-25% larger than KBLI P+Q+RSU, so part of what OJK
  counts as Islamic "social services" sits in other KBLI sectors in SEKI.
  - For the Islamic part, this overstates H15_SOC's Islamic share and understates CONV_SOC by at most about 25% of
    ISL_SOC (≈ 4-5% of CONV_SOC).
  - The high Islamic share in SOC is nonetheless real: in SPI, Islamic banks hold up to 58.0% of all-bank education
    credit (LBU L13), the highest Islamic share of any LBU business code.
- L18 ("not clearly defined", no KBLI counterpart) goes to H15_SOC. T3 shows SEKI kept it in services, and most L18
  movements are re-assignments to and from L15 (also in SOC). Islamic L18 was 1,537 Rp bn in 2016-06 and 0 from 2022.
- SPS L12 (public administration) is at most 263 Rp bn on the Islamic side (2016-06) and below 94 Rp bn from 2017. So
  the central-government gap in L12 vs O concerns the conventional side only.

Why H15 starts in 2016-06 and not 2014-06: before 2016-06 the only SEKI series is the old 9-sector table. It cannot
separate finance from real estate/business, trade from accommodation, transport from information/communication, or the
social-service sectors. An H15 for 2014-06..2016-05 would need imputed SEKI splits, which is wrong precision.

## 4. The panel (`panel_sector_banktype.csv`)

Columns:
- `date`, `panel` (H9/H15), `sector_h`, `sector_label`.
- `bank_type`:
  - ISL = BUS+UUS, the published combined series (old Tabel 20 / new Tabel 14).
  - BUS (Tabel 14a), UUS (Tabel 14b).
  - TOTAL = SEKI `total` minus `bpr` (commercial banks).
  - CONV = TOTAL minus ISL.
- `credit_rp_bn`: Rp billion, rounded to 4 decimals.
- `npf_rp_bn`: Islamic non-performing financing, ISL/BUS/UUS only.
- `dlog_credit_mom`: log(credit_t) - log(credit_{t-1}). Computed only when both calendar months exist, so 2023-12 has no
  change.
- `adj_growth_ok` (TRUE/FALSE): see section 5.
- `flag_reasons`: why `adj_growth_ok` is FALSE.
- `info_flags`: informational, does not affect `adj_growth_ok`.
- `src_islamic`, `src_seki`: which source classification produced the row.

Rows form a balanced grid (sector x bank type x month), with missing levels left empty:
- 2023-01..2023-11 for ISL/BUS/UUS/CONV (no SPS edition carries them).
- BUS/UUS before 2014-06 (OJK published BUS+UUS only).

Construction details:
- BPR's four household items other than "Lainnya" are blank in 2024-01..05 and zero in every other month (BPR reports
  all consumption under "Lainnya"). The 20 blanks are set to 0 so that commercial household items exist in those
  months (asserted: no other non-zero BPR value).
- ISL vs BUS+UUS: max gap 25.90 Rp bn (H15_HVE 2017-12) and 8.96 at H9 level. These come from the source
  (ojk_sector V2).

## 5. `adj_growth_ok`: when the change into month t is contaminated

`adj_growth_ok` is FALSE for (sector, bank type, t) if any of the rules below applies. Each rule writes a reason
code into `flag_reasons`.

**R1. Missing neighbours.**
- `panel_first_month`: 2009-01 for H9, 2016-06 for H15.
- `level_missing`.
- `prev_month_missing`: 2023-12 for ISL/BUS/UUS/CONV, and 2014-06 for BUS/UUS in H9.

**R2. Classification or coverage breaks**, all sectors of the listed bank types:

| reason code | month | panels | bank types | basis |
|---|---|---|---|---|
| break_seki_reclass_2010_01 | 2010-01 | H9 | CONV, TOTAL | SEKI reporting-form reclassification. H9 Δlog of SEKI: UTL -20.8%, CON -22.1%, TRD -11.2%, AGR -11.5%, TRN +9.6% |
| break_seki_reclass_2010_02 | 2010-02 | H9 | CONV, TOTAL | partial reversal of 2010-01: transport -6.5% after +9.6%; utilities -3.8%, trade +4.8% |
| break_lsmk_revision_2014_05 | 2014-05 | H9 | all five | OJK footnote (SPS revised on LSMK basis) and BI footnote (LBUS/LSMK); T2, T8 |
| break_sps_reclass_2014_07 | 2014-07 | H9 | ISL, BUS, UUS, CONV (+TOTAL by mirror rule) | first-month instability of new19 (ojk_sector section 4) and BTPN Syariah spin-off |
| break_sps_reclass_2015_03 | 2015-03 | H9 | ISL, BUS, UUS, CONV (+TOTAL by mirror rule) | identified here: "not clearly defined" (L18) lost 70% (-4.2 tn) into named sectors. ISL Δlog AGR +14.7%, TRN +15.1%. BUS reallocation index 3.7% (median 0.5%) |
| break_seki_splice_2017_07 | 2017-07 | H9 | CONV, TOTAL | H9 switches SEKI old9 to kbli17 (section 3.1) |
| break_seki_adjustment_2024_03 | 2024-03 | H9, H15 | CONV, TOTAL | BI footnote "penyesuaian data untuk periode Maret 2024". SEKI Δlog: shop-house +19.6%, finance +7.6%, social services -5.8% |
| break_seki_lbut_2025_01 | 2025-01 | H9, H15 | CONV, TOTAL | BI footnote: LBUT reporting, sector reassignment for all groups (bi_credit B6) |

**Mirror rule.** SEKI contains the Islamic data with the same classification (T3), so an SPS reclassification also
moves SEKI. For 2014-07, 2015-03 and the BSI merger, TOTAL is flagged where the abnormal ISL change is at least 0.5% of
TOTAL. This flags H9_CON and H9_SHH at 2014-07 and H9_TRN at 2015-03 (`..._mirrored_in_seki`).

**R3. Conversion, merger and scan events** (`ojk_conversion_events.csv`):

| event | month | rule |
|---|---|---|
| E1 BTPN Syariah spin-off (UUS to BUS) | 2014-07 | BUS and UUS, every sector |
| E2 Bank Aceh, E3 Bank NTB, E5 Bank Riau Kepri: a whole conventional bank converts to BUS | 2016-09, 2018-09, 2022-08 | ISL, BUS, UUS and CONV, every sector. TOTAL is not flagged: SEKI includes the bank before and after (T4) |
| E4 BSI merger (three BUS) | 2021-02 | affected sectors (below), plus the mirror rule |
| conversion follow-up months | 2016-10, 2018-10, 2022-09 | affected sectors |
| S1, S2, S3 scan months with no bank attributed | 2015-06, 2021-10, 2021-11, 2021-12, 2016-12 | affected sectors |

**Affected sector.** A sector is affected in month t if any of its Islamic series (ISL, BUS or UUS) has an abnormal
change of at least 1% of the previous level **and** at least 3 times that series' noise scale. In an affected sector,
ISL, BUS, UUS and CONV are all flagged.
- Abnormal change = the m/m change minus the median m/m change of the previous 12 months. For H15 the history starts in
  2014-06, so events in its first months can be assessed.
- Noise scale = 1.4826 x the median absolute relative abnormal change over 2014-06..2025-06, excluding break and event
  months.
- Median noise over sectors: ISL 2.53% (H9) / 2.41% (H15); BUS 2.41 / 2.31; UUS 3.28 / 3.18.

Calibration: a first version used a fixed 1% threshold. Because monthly noise is 2-3%, it flagged nearly every sector
in every event month (e.g. 7 of 8 H9 sectors in the 2018-10 follow-up month). The noise-aware rule keeps only clear
footprints:

| event | sectors flagged (series with z of at least 3) |
|---|---|
| E2 follow-up 2016-10 | TRN (UUS z=-3.3) |
| E3 follow-up 2018-10 | UTL (BUS z=3.4), TRN (UUS z=-3.1) |
| E4 merger 2021-02 | MAN (ISL z=-3.1) |
| E5 follow-up 2022-09 | H15_HSH only (ISL z=-4.4, BUS z=-12.7) |
| S1 2015-06 | TRN (ISL z=-3.6, UUS z=-14.6) |
| S2 2021-10 | MAN (UUS z=5.0), UTL (UUS z=5.7), TRD (UUS z=4.3) |
| S2 2021-11 (a BUS drops out for a month) | MIN (BUS z=-3.6), MAN (BUS z=-5.2), UTL (BUS z=-4.7), TRN (BUS z=-3.3); H15 also REB (BUS z=-3.3) |
| S2 2021-12 (it returns) | AGR, MIN, MAN, UTL, TRN; H15 also REB, SOC, HOT |
| S3 2016-12 | H9: UTL, CON, SHH; H15: UTL, CON, REB, HOT |

**R4. One-month spikes that fully reverse** (reporting errors).
- Definition: |Δlog| ≥ 0.10 into t and out of t, with opposite signs, and the second move reverses at least 75% of the
  first.
- The change into t and into t+1 is flagged for that series, and for CONV when the series is ISL or TOTAL
  (`spike_reversal_<series>_<month>`).
- 34 spikes: 16 in H9 and 18 in H15. By series: 19 UUS, 12 ISL, 2 TOTAL, 1 BUS.
- Examples:
  - UUS utilities 2016-12: -0.662 then +0.634.
  - UUS real estate/business 2016-12: +0.587 then -0.613 (the S3 scan month, reversed in 2017-01).
  - SEKI social services (H15_SOC TOTAL) 2020-05: +0.118 then -0.104 (122,060 to 137,343 to 123,721 Rp bn).
  - SEKI utilities 2012-12: -0.135 then +0.113.
- A credit stock does not jump 10% and revert in a month in response to a policy shock, so these flags remove noise,
  not signal.

**Not flagged, with evidence:**
- **2014-06, H9 switch from SPS old9 to new19:** exact (0.000 at H9 level).
- **2017-08 SEKI footnote** (one bank moved between the private national and government groups): it cancels in the
  commercial sum. Commercial total Δlog +0.43% (median 0.87%). The largest abnormal move across the 15 H15 sectors is
  1.26%.
- **SPS 2024-01..05 come from an earlier edition:** the ojk_sector builder found 0 revisions across editions.
- **BPR dips** (2024-06, 2024-11, 2025-01): BPR is excluded. Total minus BPR equals the sum of the commercial groups
  within 0.0005 Rp bn.
- **2026-05 SEKI regrouping:** outside the panel window.

**Informational flags** (`info_flags`, never change `adj_growth_ok`):
- `sps_old_sector_basis_pre_lsmk`: H9 ISL/CONV, 2009-01..2014-04.
- `isl_realloc_high`, `bus_realloc_high`, `uus_realloc_high`, `seki_realloc_high`: the H-level reallocation index is
  above 4 times its median.
  - The index is the sum of absolute abnormal sector moves minus the absolute abnormal total move, as % of the total.
  - H9 ISL: 2009-12, 2010-01, 2010-02, 2010-03, 2011-11, 2012-10, 2013-01, 2013-05, 2014-05, 2014-07, 2015-03, 2018-06.
  - H9 SEKI: 2010-01, 2011-12, 2012-06, 2013-06, 2013-08.
  - H15 ISL: 2018-06 only.
  - These are candidates for robustness checks. They are not documented breaks.
- `sps_source_note`: a constituent SPS cell carries a builder note (corrections, provisional cells, year-end column).
- `conv_large_jump` / `total_large_jump`: |Δlog| > 0.10 in an otherwise unflagged month. 28 CONV and 27 TOTAL rows,
  almost all in the lumpy small sectors: mining and utilities (H9 MIN 10, UTL 12; H15 MIN 4, UTL 1) and H15_SOC 2017-12.
- `conv_nonpositive`, `isl_exceeds_conv`: never triggered. CONV is positive in every row (minimum 16,736.6 in
  H15_HSH). The largest Islamic share in any sector-month is 20.1% (H15_HRE).

## 6. Islamic shares and pre-period averages (`sector_islamic_share.csv`)

One row per panel x sector x month, plus a `<panel>_ALL` row per month (the sum over the panel's sectors; never use it
together with the sectors).

Columns:
- Levels: `isl_credit_rp_bn`, `bus_credit_rp_bn`, `uus_credit_rp_bn`, `total_credit_rp_bn`.
- Shares of commercial credit (TOTAL): `isl_share_pct`, `bus_share_pct`, `uus_share_pct`.
- Composition: `sector_pct_of_all_isl`, `sector_pct_of_all_total`.
- Pre-period, constant within sector: `isl_share_pre_avg_pct`, `bus_share_pre_avg_pct`, `uus_share_pre_avg_pct`,
  `pre_period`, `pre_period_n_months`.
- Alternative pre-period, H9 only: `isl_share_pre_alt_avg_pct` and `pre_alt_period`, the mean over 2015-03..2016-08.
  - This is the first 18 months on the final SPS sector basis (after the 2014-05, 2014-07 and 2015-03 breaks) and
    before the first conversion (2016-09).
  - It is offered because the main H9 window (2009-01..2011-12) lies on the old SPS sector basis and straddles SEKI's
    2010-01 reclassification. The Spearman rank correlation between the two H9 measures is **0.905**.

| sector | H9 pre 2009-01..2011-12 (n=36) | H9 alt 2015-03..2016-08 | H15 pre 2016-06..2017-11 (n=18): ISL / BUS / UUS |
|---|---|---|---|
| AGR | 1.98 | 3.35 | 3.54 / 2.77 / 0.76 |
| MIN | 2.45 | 4.63 | 6.08 / 4.53 / 1.55 |
| MAN | 0.77 | 2.35 | 2.63 / 2.13 / 0.50 |
| UTL | 3.61 | 6.67 | 5.99 / 5.44 / 0.55 |
| CON | 6.63 | 6.70 | 7.08 / 3.96 / 3.12 |
| TRD (H9) / TRD, ACC (H15) | 2.16 | 3.34 | 3.60 / 3.04 / 0.56; ACC 3.41 / 2.00 / 1.41 |
| TRN | 4.53 | 7.12 | 5.84 / 5.05 / 0.80 |
| SHH (H9) | 5.44 | 7.95 | |
| FIN (H15) | | | 9.94 / 6.17 / 3.77 |
| REB (H15) | | | 5.50 / 4.50 / 1.00 |
| SOC (H15) | | | 15.79 / 13.53 / 2.26 |
| HRE (H15) | | | 14.58 / 7.70 / 6.88 |
| HSH (H15) | | | 11.28 / 4.92 / 6.36 |
| HVE (H15) | | | 7.49 / 3.44 / 4.05 |
| HOT (H15) | | | 5.13 / 4.07 / 1.06 |
| ALL | 3.73 | 5.41 | 5.80 / 4.09 / 1.71 |

## 7. Descriptives

**Counts.**

| | H9 | H15 |
|---|---|---|
| sectors | 8 | 15 |
| months | 198 (2009-01..2025-06) | 109 (2016-06..2025-06) |
| rows (sector x bank type x month) | 7,920 | 8,175 |
| rows with a level | 6,528 (ISL 1,496; BUS 976; UUS 976; CONV 1,496; TOTAL 1,584) | 7,515 (1,470 each for ISL/BUS/UUS/CONV; TOTAL 1,635) |
| rows with a m/m change | 6,456 | 7,380 |
| flagged (`adj_growth_ok` FALSE) among those | **5.96%** (ISL 5.41, BUS 6.25, UUS 7.50, CONV 8.11, TOTAL 3.36) | **5.12%** (ISL 5.42, BUS 5.00, UUS 6.04, CONV 7.57, TOTAL 1.98) |
| usable m/m changes (`adj_growth_ok` TRUE) | ISL 1,400; BUS 900; UUS 888; CONV 1,360; TOTAL 1,523 | ISL 1,362; BUS 1,368; UUS 1,353; CONV 1,331; TOTAL 1,588 |
| months with any CONV flag | 33 | 24 |

Flag reasons, H9 (row counts among rows with a level):
- SPS breaks: 2014-07 32 (+2 mirrored); 2015-03 32 (+1); 2014-05 24.
- SEKI breaks: 2010-01, 2010-02, 2017-07 splice, 2024-03 and 2025-01, 16 each.
- Conversions: E2, E3 and E5, 32 each. E1 16.
- Affected-sector events: S2 48, S3 12, E3 follow-up 8, E2 follow-up 4, E4 4, S1 4.
- Spikes: ISL 28, UUS 16, TOTAL 4.
- Missing neighbours: panel first month 24, previous month missing 48.

Flag reasons, H15:
- Conversions: E2, E3 and E5, 60 each.
- Affected-sector events: S2 64, S3 16, E3 follow-up 8, E2 and E5 follow-ups 4 each, E4 4.
- SEKI breaks: 2024-03 and 2025-01, 30 each.
- Spikes: UUS 22, ISL 20, TOTAL 4, BUS 2.
- Missing neighbours: panel first month 75, previous month missing 60.

**Islamic share of commercial-bank credit, annual average of monthly shares (%).** 2023 is December only. 2025 is
January-June.

| sector | 2009 | 2011 | 2013 | 2015 | 2017 | 2019 | 2021 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|---|
| H9_AGR | 1.84 | 2.08 | 1.99 | 3.20 | 3.61 | 3.70 | 4.21 | 5.78 | 6.10 | 6.52 |
| H9_MIN | 3.33 | 1.80 | 2.58 | 3.81 | 6.31 | 4.56 | 4.49 | 3.06 | 3.15 | 2.88 |
| H9_MAN | 0.57 | 0.95 | 1.15 | 2.22 | 2.67 | 2.97 | 3.17 | 3.31 | 3.34 | 3.25 |
| H9_UTL | 2.14 | 4.58 | 5.67 | 6.65 | 6.12 | 7.79 | 6.81 | 7.85 | 7.07 | 7.37 |
| H9_CON | 5.68 | 7.50 | 7.22 | 7.27 | 7.88 | 8.21 | 9.60 | 10.56 | 10.18 | 8.55 |
| H9_TRD | 1.93 | 2.36 | 2.19 | 3.23 | 3.67 | 3.63 | 4.44 | 4.87 | 4.77 | 4.77 |
| H9_TRN | 4.61 | 4.39 | 3.94 | 7.64 | 5.94 | 3.92 | 3.82 | 6.48 | 6.54 | 6.33 |
| H9_SHH | 4.77 | 6.41 | 10.18 | 8.09 | 8.69 | 9.37 | 11.09 | 12.52 | 12.59 | 12.81 |
| **all sectors** | **3.21** | **4.35** | **5.74** | **5.42** | **5.96** | **6.28** | **7.25** | **8.25** | **8.26** | **8.27** |

| H15 sector | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|---|
| AGR | 3.43 | 3.61 | 3.64 | 3.70 | 4.19 | 4.21 | 4.64 | 5.78 | 6.10 | 6.52 |
| MIN | 5.72 | 6.33 | 5.82 | 4.56 | 4.45 | 4.49 | 4.74 | 3.06 | 3.15 | 2.88 |
| MAN | 2.56 | 2.67 | 2.78 | 2.97 | 3.10 | 3.17 | 3.02 | 3.31 | 3.34 | 3.25 |
| UTL | 6.03 | 6.09 | 8.37 | 7.79 | 6.89 | 6.81 | 7.26 | 7.85 | 7.07 | 7.37 |
| CON | 5.91 | 7.88 | 8.07 | 8.21 | 9.35 | 9.60 | 9.26 | 10.56 | 10.18 | 8.55 |
| TRD | 3.55 | 3.65 | 3.58 | 3.53 | 4.06 | 4.51 | 4.87 | 4.89 | 4.76 | 4.72 |
| ACC | 3.12 | 3.61 | 4.20 | 4.64 | 4.28 | 3.93 | 3.94 | 4.68 | 4.86 | 5.22 |
| TRN | 6.03 | 5.69 | 4.61 | 3.92 | 4.25 | 3.82 | 3.57 | 6.48 | 6.54 | 6.33 |
| FIN | 10.66 | 9.45 | 8.35 | 7.73 | 7.29 | 6.61 | 5.63 | 5.92 | 5.19 | 4.86 |
| REB | 5.38 | 5.58 | 5.42 | 5.15 | 4.94 | 4.77 | 5.56 | 4.66 | 5.01 | 5.26 |
| SOC | 15.52 | 15.85 | 15.47 | 16.07 | 15.25 | 14.23 | 13.92 | 13.26 | 13.76 | 14.06 |
| HRE | 14.03 | 14.96 | 15.72 | 16.35 | 17.48 | 18.33 | 19.06 | 19.98 | 20.04 | 19.94 |
| HSH | 11.03 | 11.45 | 12.19 | 13.74 | 16.13 | 18.26 | 18.49 | 18.66 | 15.91 | 14.66 |
| HVE | 7.30 | 7.65 | 7.40 | 6.79 | 6.64 | 8.43 | 9.46 | 10.62 | 10.54 | 10.80 |
| HOT | 4.66 | 5.45 | 5.77 | 6.46 | 7.66 | 9.18 | 10.74 | 12.38 | 12.73 | 13.35 |
| all sectors | 5.57 | 5.96 | 6.12 | 6.28 | 6.78 | 7.25 | 7.57 | 8.25 | 8.26 | 8.27 |

Reading notes:
- The jumps in H9 MAN, TRN and AGR shares in 2014 come from the SPS 2014-05 basis change.
- The HSH share falls in 2024 because SEKI's shop-house credit rose 19.6 Δlog % at the flagged 2024-03 adjustment.
  The rise was on the conventional side; SPI shows the same level shift.

**BUS as % of Islamic financing** (all sectors, annual average): 2014 74.9, 2015 72.9, 2016 71.9, 2017 69.4,
2018 64.9, 2019 63.3, 2020 63.7, 2021 63.8, 2022 63.7, 2023 64.8, 2024 65.6, 2025 66.5.

**Composition of Islamic financing, June (% of all Islamic):**
- H9_SHH: 62.2 (2009), 73.2 (2012), 65.4 (2014), 57.5 (2016), 59.1 (2019), 61.1 (2022), 64.2 (2025).
- H9_TRD 9.2-14.1; H9_MAN 3.3-8.2; H9_CON 4.2-8.6.
- In H15, the household sectors grow from 38.2% (2016) to 53.4% (2025) of Islamic financing:
  - HRE 21.6 to 24.3.
  - HOT 11.4 to 26.0.
  - HVE 3.9 to 2.4.
  - HSH 1.3 to 0.7.
- FIN falls from 8.8 to 3.3.

## 8. Validation checks (numeric)

- **V1. Inputs:** keys unique in both inputs (asserted). Input md5s are in section 1.
- **V2. SEKI commercial credit:**
  - total minus BPR vs the sum of commercial groups: max gap 0.0000 (old9) and 0.0005 Rp bn (kbli17).
  - sectors vs PROD_TOTAL: 0.0000 / 0.0002.
  - household items vs NONPROD_TOTAL: 0.0000 / 0.00005.
  - PROD+NONPROD vs TOTAL: 0.0000 / 0.0001.
  - 20 BPR household blanks set to 0.
- **V3. Adding-up:**
  - Sum of H-sectors vs the SPS total: max gap 2.285 Rp bn in both panels (the source's own sector-sum gap, 2020-08).
  - Sum of H-sectors vs the SEKI commercial total: 0.0002.
  - CONV + ISL = TOTAL exactly.
  - ISL vs BUS+UUS: max 25.903 (H15, 2017-12) and 8.961 (H9).
- **V4. Crosswalk:** each panel x source uses every code exactly once. Codes per source: H9 SPS old9 10, H9 SPS new19
  24, H9 SEKI old9 10, H9 SEKI kbli17 18, H15 SPS new19 24, H15 SEKI kbli17 22 (asserted).
- **V5. SPS old9 vs aggregated new19, H9 level, 2014-06..2015-05:** financing 0.000 in all 8 sectors. NPF 0.000 except
  TRD 2.41.
- **V6. SEKI old9 vs kbli17, H9 level, 2016-06..2017-06:** see the table in section 3.1. Each sector's gap is stable
  within ±0.8 pp over the 13 months.
- **V7. Inclusion tests T1-T9:** section 2.
- **V8. SPI cross-check (T7):** section 3.2 table and section 2.
  - 2024-03 is provisional in SPI and excluded from the statistics. In that month SPI's shop-house is 151% above SEKI
    and its housing 6.2% below.
- **V9. 2017-08 check:** section 5.
- **V10. Spot checks:** 9 cells recomputed directly from the input CSVs with plain filters. Absolute gap 0.000000 in
  all, asserted below 1e-6:
  - H9_AGR ISL 2009-01 = 1,180.703.
  - H9_SHH TOTAL 2012-06 = 1,082,532.27.
  - H9_SHH ISL 2012-06 = 86,083.156.
  - H9_TRN CONV 2020-06 = 248,735.2871.
  - H9_TRD TOTAL 2016-12 = 913,789.79.
  - H15_HSH TOTAL 2024-03 = 27,932.511.
  - H15_SOC UUS 2019-04 = 2,495.6895.
  - H15_HOT ISL 2023-12 = 134,854.2854.
  - H15_FIN CONV 2025-06 = 417,350.9715.
- **V11. Plausibility:** 0 non-positive CONV rows, and 0 rows with ISL > CONV. The maximum Islamic share by sector is in
  `conv_checks.max_isl_share_pct` (highest: H15_HRE 20.1%, H15_HSH 19.1%, H15_SOC 17.2%).
- **V12. Determinism:** two consecutive runs gave identical md5 for all three outputs and an identical JSON block.

## 9. Caveats

1. **UUS inclusion in SEKI is inferred, not documented.** The SEKI metadata page was not retrieved. If it were wrong,
   CONV would be understated by the UUS/CONV ratios in section 2. These are largest in housing and shop-houses
   (about 15% in 2025).
2. **H9 before 2014-05 rests on SPS's older sector basis.** Islamic sector levels jump at 2014-05; TRN +82 Δlog %,
   MAN +56%. Sector shares and the main H9 pre-period averages carry this basis; `isl_share_pre_alt_avg_pct` is the
   robustness alternative.
3. **H15 social services and transport are approximate mappings** (LBU vs KBLI; section 3.2). Mining and manufacturing
   have stable all-bank level gaps, most likely from non-resident borrowers. These affect shares and levels more than
   growth rates.
4. **The noise-aware event rule can miss small footprints** below 3 noise units. Users who want maximum caution can drop
   the whole event months listed in section 5, R3. The pre-analysis plan's break-robustness check (drop 2014, 2016-17
   and 2021) covers 7 of those 12 months.
5. **The spike rule and the 2015-03 break were identified from the data in this build.** They are not documented by
   OJK or BI. They have their own reason codes, so they can be switched off.
6. **2023-01..2023-11 are missing** for every Islamic series, and 2023-12 comes from a year-end column. Windows that
   cross 2023 lose 12 months of Islamic and conventional growth.
7. **The 2014-07 BTPN spin-off and the 2017-01 BUS/UUS allocation issue** affect BUS vs UUS comparisons only. The
   spin-off is flagged. The 2017-01 issue (±917 Rp bn placed in BUS in Tabel 14 and in UUS in Tabel 13, left
   unresolved by the ojk_sector builder) is not flagged.
