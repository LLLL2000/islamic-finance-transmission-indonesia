# Data note: Bank Indonesia SEKI. Credit by sector and bank group, rates, SBN outstanding

Builder: `bi_credit`. Build script: `code/py/build_bi_credit.py`. It reruns end to end with
`python -I code/py/build_bi_credit.py`. It reads only `data/raw/bi/*.xls` and writes the five CSVs below.
All validation numbers in this note come from the console output of that script, plus two manual
cross-checks against OJK files that are marked as such.

| Output (data/clean/) | SEKI table | Rows | Coverage |
|---|---|---|---|
| `bi_credit_by_sector_group.csv` | I.4 | 38,052 | 2002-01 to 2026-08 |
| `bi_lending_rates.csv` | I.26 | 5,836 | 1990-01 to 2026-08 |
| `bi_deposit_rates.csv` | I.28 | 10,926 | 1990-01 to 2026-08 |
| `bi_money_market_rates.csv` | I.25 (file TABEL1_25_1) | 5,241 | 1990 to 2026-09, by series |
| `bi_sbn_outstanding.csv` | IV.4 (file TABEL4_4) | 6,036 | 2008-12, 2009-12, then monthly 2010-01 to 2026-09 |

## 1. Sources and provenance

All files come from Bank Indonesia's *Statistik Ekonomi dan Keuangan Indonesia* (SEKI), which is an
open download at `https://www.bi.go.id/SEKI/tabel/<NAME>.xls`.

| Raw file (data/raw/bi/) | Documented URL | Bytes | SHA-256 |
|---|---|---|---|
| BI_SEKI_TABEL1_4.xls | https://www.bi.go.id/SEKI/tabel/TABEL1_4.xls | 634,368 | 8d39f9c0…7062 |
| BI_SEKI_TABEL1_26.xls | https://www.bi.go.id/SEKI/tabel/TABEL1_26.xls | 150,016 | d437c35c…b83c |
| BI_SEKI_TABEL1_25_1.xls | https://www.bi.go.id/SEKI/tabel/TABEL1_25_1.xls | 247,296 | aae221bd…8058 |
| BI_SEKI_TABEL4_4.xls | https://www.bi.go.id/SEKI/tabel/TABEL4_4.xls | 111,104 | 313b1ad4…cdb |
| BI_SEKI_TABEL1_28.xls | https://www.bi.go.id/SEKI/tabel/TABEL1_28.xls | 208,384 | 4b19af0c8cbc3ed0ed3093a53062d5db66062491be3a8f30982e8f2f1909e69c |

- **Files 1 to 4** were already in `data/raw/bi/`, placed there by another builder, who retrieved them
  with the WebFetch tool from the documented links. I did not change them.
- **I.28** was obtained in this build. I made one WebFetch call to the documented link
  `https://www.bi.go.id/SEKI/tabel/TABEL1_28.xls` on 2026-10-29 at about 17:44 UTC, using a plain GET
  with no special headers. The tool saved the binary response (`application/vnd.ms-excel`), and I copied
  it unchanged to `data/raw/bi/BI_SEKI_TABEL1_28.xls`.
  - The workbook has four sheets: 'Th 1990-2008', 'Th 2009-2018', 'Th 2010-2024' and '1.28'.
  - Its title is "I.28 SUKU BUNGA SIMPANAN BERJANGKA RUPIAH MENURUT KELOMPOK BANK DAN JANGKA WAKTU"
    (Rupiah time-deposit rates by bank group and tenor).
- **Raw files are read-only data.** The script opens them with pandas and executes nothing from them.

### How the wide sheets are parsed

The column headers of the SEKI sheets have several defects, so the script assigns dates by these rules:

- **Month labels:** A column is treated as monthly only if it has a month label.
- **Year labels:**
  - SEKI puts a year label at the first column of a year. For a partial or final year it puts the label
    at the last column instead. Examples:
    - 'Th 2016-2024' carries "2024" above Dec-2024 and "2025" above Mar-2025.
    - I.4_1 carries "2026" above Aug-2026.
  - Every such label matches the year of its own column. The script therefore uses the label when one is
    present. Otherwise it carries the year forward and increments it when the month number falls.
- **Columns that are skipped:**
  - Unlabelled year-end duplicate columns, which repeat the December value.
  - Empty spacer columns. Examples: I.4 'Th 2016-2024' column F; I.26 and I.28 'Th 2010-2024' between
    Sep-2010 and Oct-2010; I.25 'Th 2010-2016' and '1.25A' between Sep and Oct of the first year.
- **Contiguity check:** The script requires the dates to be contiguous, and the build fails if they are not.
  - There are two documented exceptions. I.26 'Th 1990-2008' has a stray empty "2018 Dec" column, so
    the script reads only up to column 250. TABEL4_4 is annual for 2008 and 2009.
  - I.26 'Th 2009-2018' has two adjacent "Dec 2018" columns, one of them empty. They are merged, and
    the script reports any conflict between them. There were none.
- **Junk header rows:** The I.25 sheet 'Th 1990-2003' has a datetime header row (row 8) that runs from
  1999 to 2010 while the labels run from 1990 to 2003. That row is junk and is ignored; the year and month
  labels are used.
  - The values confirm the labels. In the column labelled Jul-1998, SBI 1-month is 65.16%, which fits the
    1998 crisis. The same sheet's header says "(Miliar Rp)", but the values are percentages.
- **Spot checks:** I compared output values with the raw cells by hand, and all of them matched:
  - I.4: Persero Dec-2024 = 3,376,523.8105; Persero Jan-2025 = 3,353,747.4712.
  - I.26: Persero working capital Aug-2026 = 7.9138; Oct-2010 = 13.23.
  - I.28: Persero 1-month Aug-2026 = 4.94452.
  - I.25, Jan-2009: BI Rate 8.75; PUAB morning overnight 8.89; PUAS 9.29; JIBOR 1m 10.14.
  - IV.4, Sep-2026: SUN 5,704,995.483; SBSN 1,406,052.85.

## 2. `bi_credit_by_sector_group.csv` (SEKI I.4)

The table is "I.4 Posisi pinjaman/kredit Rupiah & valas yang diberikan Bank Umum dan BPR menurut
kelompok bank & lapangan usaha": outstanding loans in Rupiah plus foreign currency, by bank group and
economic sector, in billions of Rupiah, end of month.

### Columns

| Column | Content |
|---|---|
| `date` | First day of the month. |
| `classification` | `old9` (old sector classification) or `kbli17` (KBLI-2015). |
| `bank_group_code` | Bank group code; see the list below. |
| `bank_group_id` / `bank_group_en` | Indonesian and English group label. |
| `sector_code` | Sector code; see the list below. |
| `sector_level` | `group_total`, `sector_aggregate`, `sector`, `consumption_item` or `memo`. |
| `sector_label_id` | Original Indonesian label. |
| `sector_label_en` | English label, taken from the sheet's own English column. |
| `credit_rp_bn` | Outstanding credit, Rp billion. |
| `flag` | Data-quality flags; see section 2.5. |
| `source_sheet`, `sheet_row` | The sheet and 1-based Excel row the value came from. |

The key `(date, classification, bank_group_code, sector_code)` is unique; there are 0 duplicates.

Bank group codes:

| Code | Group |
|---|---|
| `persero` | Bank Persero (state-owned) |
| `bpd` | Bank Pemerintah Daerah (regional government) |
| `bsn` | Bank Swasta Nasional (private national) |
| `foreign_joint` | Bank Asing dan Bank Campuran (foreign and joint-venture), up to 2024-12 |
| `foreign_branch` | Kantor Cabang dari Bank yang Berkedudukan di Luar Negeri (branches of foreign banks), from 2025-01 |
| `bpr` | Bank Perkreditan Rakyat (rural banks) |
| `total` | "Jumlah" / "Jumlah (1 s.d. 5)" |
| `memo` | Memo items: central government and non-residents, Rupiah and FX. Old sheet only, 2010-01 to 2017-06. |

Sector codes:

| Code | Meaning |
|---|---|
| `TOTAL` | Group total |
| `PROD_TOTAL` | "Pinjaman berdasarkan lapangan usaha": loans by industrial origin |
| `NONPROD_TOTAL` | "Pinjaman kepada bukan lapangan usaha (konsumsi rumah tangga)": household consumption |
| `old_*` | The 9 old sectors |
| `A_agri` … `RSU_other_services` | The 17 KBLI-2015 sectors |
| `HH_housing`, `HH_flat_apartment`, `HH_shophouse_office`, `HH_vehicles`, `HH_other` | Household consumption items |

### Sheets used

| Sheet | Classification | Months | Use |
|---|---|---|---|
| 'Th 2002-2017' | old9 | 2002-01 to 2017-06 (186) | All months |
| 'Th 2016-2024' | kbli17 | 2016-06 to 2025-03 (106) | 2016-06 to 2024-12 |
| 'I.4_1', 'I.4_2', 'I.4_3' (LBUT vintage) | kbli17 | 2025-01 to 2026-08 (20) | 2025-01 onwards |

- For Jan to Mar 2025, both 'Th 2016-2024' and the I.4_x sheets have data. The I.4_x values (newest
  vintage, new group definitions) are kept, and the older-vintage values are dropped. The comparison is
  in section 2.4.
- In the old9/kbli17 overlap (2016-06 to 2017-06), both classifications are kept. They are separate
  values of `classification`.

### 2.1 What "total" includes, and Islamic banks

**The total includes BPR.**
- The new sheets label the row "6. JUMLAH (1 s.d. 5)", meaning total of groups 1 through 5, and group 5
  is Bank Perkreditan Rakyat. The table title also says "Bank Umum dan BPR".
- Numerically, the sum of the five groups equals the published total in every cell:
  - old9: max abs gap 0.0000 Rp bn over all 17 sector rows × 186 months.
  - kbli17: max abs gap 0.0005 Rp bn over 25 sector rows × 123 months.
- **Exception: BPR not reported in 2002-03 and 2002-07.** In those months the BPR block is published as
  all zeros. The total equals the sum of the four commercial-bank groups, so that month's total excludes
  BPR. These cells are flagged `bpr_zero_not_reported` and `total_excludes_bpr`.
- To get commercial banks only, use `total` minus `bpr`. There is no published commercial-bank subtotal.

**Islamic banks are not shown as a separate group.** There is no BUS or UUS row in any sheet. BUS
(stand-alone Islamic banks) would sit in the ownership group of each bank, and UUS (Islamic windows) are
part of their conventional parent banks. The table itself cannot show either of these. The evidence:

- **Footnote (all I.4 sheets):** "Sejak Mei 2014 terdapat perubahan cakupan dan klarifikasi data Dana dan
  Kredit berkaitan dengan implementasi Laporan Bulanan Bank Umum Syariah (LBUS) berdasarkan Laporan
  Stabilitas Moneter dan Sistem Keuangan (LSMK)".
  - In English: since May 2014, the coverage and classification of deposit and credit data changed with
    the Islamic Commercial Bank Monthly Report (LBUS), based on the LSMK.
  - It refers readers to the SEKI Metadata, which I did not retrieve.
- **No level shift in May 2014.**
  - Change from the previous month in May 2014 (old9 sheet): total +1.27%; commercial banks (total less
    BPR) +1.26% (3,328,319 to 3,370,227); Persero +0.59%; BSN +1.34%. The median absolute monthly change
    of the total over 2002 to 2017 is 1.64%.
  - Stand-alone Islamic banks' financing to non-bank third parties was Rp 143.3 tn in Jun-2014. Source:
    OJK SPS file `data/raw/ojk/SPS_2024_12.xlsx`, sheet 'Tabel 1 Kinerja BUS dan UUS', row "Pembiayaan
    kepada Pihak Ketiga Bukan Bank", first column. That is 4.3% of I.4 commercial-bank credit.
  - Adding the BUS in May 2014 would therefore show up as a jump of about 4%, and none is visible.
  - Reading: either BUS were already in the series before May 2014, or BI revised the history back. The
    footnote describes a change of source report and classification, not a first inclusion that can be
    located in the data.
- **OJK cross-check at Dec-2024 (manual, not in the script):**
  - I.4 commercial banks (total less BPR) = 7,727,574.1 − 165,733.3 = **7,561,840.8**.
  - OJK SPI (`data/raw/ojk/SPI_2025_02.xlsx`, sheet 'Keg.usaha KBMI 1.1.-1.5.', row "- Kepada Pihak
    Ketiga", Des-2024) reports commercial-bank credit and financing to third parties of **7,827,147.6**.
    That covers 105 commercial banks (sheet 'Keg. Usaha Perbankan_1', "Jumlah Bank"), which includes the
    stand-alone Islamic banks.
  - BUS financing to non-bank third parties, Dec-2024, from SPS_2024_12.xlsx 'Tabel 6a KegiatanUsaha':
    profit-sharing 198,248.5 + receivables 209,419.1 + ijarah 5,587.7 = **413,255.4**.
  - UUS financing, same rows of 'Tabel 6b' = **213,890.7**.
  - If I.4 excluded the BUS, it could not exceed SPI minus BUS = 7,413,892. Yet I.4 is 147,949 higher than
    that, and I.4 is the narrower concept (resident borrowers, by sector).
  - **Conclusion:** I.4 almost certainly contains BUS financing. UUS financing is reported inside the parent
    conventional banks.
  - **Unreconciled:** The remaining gap of 265,307 between SPI and I.4 comes from definitions (the SPI
    figure includes credit to central government and non-residents, among other things). Treat
    "includes BUS and UUS" as strongly supported but not proven.
- **Implication for the paper:** I.4 groups mix conventional and Islamic credit. I.4 cannot serve as a
  "conventional only" control without subtracting OJK SPS Islamic financing by sector.

### 2.2 Internal consistency (both classifications)

| Check | old9 (1,116 group-months) | kbli17 (738 group-months) |
|---|---|---|
| Sum of sectors − PROD_TOTAL | max abs gap 0.0000 | 0.0003 |
| Sum of HH items − NONPROD_TOTAL | 0.0000 | 0.0002 |
| PROD_TOTAL + NONPROD_TOTAL − TOTAL | 0.0000 | 0.0001 |
| Sum of 5 groups − published total (every sector row) | 0.0000 | 0.0005 |

All gaps are in Rp bn. No cell exceeds 1 Rp bn.

Structural zeros and blanks:
- **BPR has no household breakdown.** All BPR consumption sits in `HH_other`, and the other HH items are 0.
  In 2024-01 to 2024-05 these BPR HH items are blank in the source, giving 20 empty `credit_rp_bn` cells.
- **No housing breakdown before 2010 (old9).** HH_housing, HH_flat_apartment, HH_shophouse_office and
  HH_vehicles are 0 for every group in 2002-01 to 2009-12. All consumption was then in "Lainnya". The
  breakdown starts in 2010-01 (see break B1).

### 2.3 Old (9-sector) vs KBLI-2015 classification, overlap 2016-06 to 2017-06 (13 months)

**Group totals are essentially identical.** Difference, new minus old, in Rp bn (mean, with min to max in
brackets):

| Group | Mean difference | Min to max | Mean % |
|---|---|---|---|
| persero | −30.1 | −117.4 to 0 | |
| bpd | +2.3 | | |
| bsn | −23.0 | −150.6 to +4.7 | |
| foreign_joint | 0.0 | | |
| bpr | −90.7 | | −0.10% |
| total | −141.6 | −249.0 to −80.5 | −0.003% |

Household consumption (NONPROD_TOTAL) and its items match to within 9 Rp bn.

**Sectors re-map substantially.** Total group, Jun-2016 (old → new):

| Comparison | Old | New | Difference |
|---|---|---|---|
| Agriculture | 279,601 | 279,698 | +0.03% |
| Mining | 113,922 | 112,958 | −0.85% |
| Manufacturing | 732,427 | 731,658 | −0.10% |
| Construction | 194,867 | 194,867 | 0.00% |
| Utilities vs D+E | 111,015 | 112,708 | +1.52% |
| Trade, hotels and restaurants vs G+I | 913,187 | 926,587 | +1.47% |
| Transport and communication vs H+J | 172,494 | 186,984 | +8.40% |
| Finance, real estate, business vs K+L+MN | 337,771 | 376,292 | +11.40% |
| Services vs O+P+Q+RSU | 156,982 | 90,433 | −42.39% |

The Jun-2017 figures are almost the same: +8.74%, +11.69% and −43.35% for the last three rows.

- **Usable one-to-one bridges:** agriculture, mining, manufacturing, construction.
- **Approximately usable:** utilities and trade, within about 1.5%.
- **Not comparable:** the services and finance aggregates.

There is no published crosswalk. Any splice before 2016 should be done only at these aggregate levels.

### 2.4 Breaks

Monthly changes below are compared with each group's median absolute monthly change:
- old9 (2002 to 2017): total 1.64%.
- kbli17 (2016 to 2026): total 0.89%; persero 0.87%; bsn 0.92%; bpd 0.70%; bpr 0.70%;
  foreign_joint 1.43%.

**B1. 2010-01, old9: reporting-form reclassification (not footnoted).**
- Household consumption is split into housing, flats, shophouses, vehicles and other for the first time.
  The total group's HH_other falls by 164,526 while the new items appear: housing 117,276, vehicles
  57,680, shophouse 3,995, flats 1,518.
- Sector shifts at the same time: services +62,308 (16,580 → 78,888); finance, real estate and business
  −47,386; trade, hotels and restaurants −30,823; construction −12,647.
- PROD_TOTAL −41,294; NONPROD_TOTAL +15,943; TOTAL −25,352 (−1.75%).
- **Treat 2010-01 as a sector-composition break in old9.**

**B2. 2014-05: LBUS/LSMK coverage change (footnoted).** There is no visible level shift; see section 2.1.

**B3. 2016-06/2017-06: switch to KBLI-2015.** See section 2.3. The old9 series ends in 2017-06 and the
kbli17 series starts in 2016-06.

**B4. 2017-08: footnoted coverage change.**
- Footnote in 'Th 2016-2024' (and in I.26 and I.28): "Sejak periode data Agustus 2017, terdapat
  perubahan cakupan Bank Swasta Nasional dan Pemerintah akibat adanya perubahan status pada salah satu
  bank". In English: since August 2017, the coverage of the private national and government bank groups
  changed because one bank changed status.
- Monthly changes in Aug-2017: persero +14,256 (+0.81%); bsn +2,405 (+0.13%); total +19,484 (+0.43%).
  In Jul-2017 they were −10,537, −12,038 and −23,529.
- No shift stands out from normal monthly noise, so the reclassified bank must be small. I could not
  size it from the table.

**B5. 2024-03: "Terdapat penyesuaian data untuk periode Maret 2024" (data adjustment for Mar-2024;
footnote in 'Th 2016-2024').**
- Monthly changes in Mar-2024: total +141,340 (+2.01%); foreign_joint +4.90%; bsn +2.26%; persero +1.57%;
  bpd +1.54%; bpr +1.32%.
- March changes of the total in other years: 2017 1.45%, 2018 1.67%, 2019 1.24%, 2020 2.89%, 2021 1.42%,
  2022 1.74%, 2023 1.20%, 2025 1.12%, 2026 1.14%.
- So Mar-2024 is high but within the range of past Marches. The size of the adjustment cannot be
  separated from genuine growth. The month is not flagged.

**B6. 2025-01: LBUT (integrated commercial bank report), footnoted in I.4_1..3.**
- **(a) Bank groups.** "Bank Asing dan Bank Campuran" becomes "Kantor Cabang dari Bank yang Berkedudukan
  di Luar Negeri". The joint-venture banks (domestic legal entities) move into **bsn**.
  - Comparing the two vintages for the same months:

    | Month | bsn, old vintage | bsn, LBUT | Difference | foreign_joint → foreign_branch |
    |---|---|---|---|---|
    | Jan-2025 | 3,156,065.8 | 3,348,373.2 | +192,307.4 | −192,292.9 |
    | Feb-2025 | | | +196,211.5 | −196,211.5 |
    | Mar-2025 | | | +200,208.6 | −200,208.6 |

  - persero, bpd and bpr TOTAL are identical across vintages (diff ≤ 0.0). The total differs by 14.5 in
    Jan-2025 and 0.0 in Feb and Mar.
  - The 2025+ `bsn` series includes the former joint banks (flag `lbut_2025_includes_former_joint_banks`).
    `foreign_branch` is not comparable with `foreign_joint`. A consistent series needs bsn plus
    foreign (2016-06 to 2024-12) against bsn plus foreign_branch (2025+), which is continuous at the
    total level.
- **(b) Sector assignment.** "Penyesuaian cakupan sumber data terkait klasifikasi sektor KBLI": the data
  source's coverage of the KBLI sector classification was adjusted.
  - At sector level the two vintages differ even where group totals agree. In 137 (group, sector) cells
    over Jan to Mar 2025 the difference is above 1 Rp bn: persero 21 cells (max 3,991.7), bpd 21 (max
    4,034.2), total 23 (max 11,003.8), bsn 72 (max 200,208.6, mostly from part a).
  - Monthly changes of the total group in Jan-2025 by sector, with the 2023 to 2024 median absolute
    monthly change in brackets:

    | Sector | Jan-2025 change | Median |
    |---|---|---|
    | Construction | −14,165 | 3,563 |
    | Trade | −22,462 | 12,105 |
    | Real estate | −4,927 | 1,406 |
    | Other services | −10,892 | 2,628 |
    | Accommodation | −2,372 | 636 |
    | HH_other | −20,991 | 8,886 |

    Most of these reverse in Feb-2025.
  - **Treat 2025-01 as a sector-level break for all groups.**

**B7. 2026-05: unexplained reallocation between bsn and persero (no footnote).**
- Monthly changes in May-2026:

  | Group | TOTAL | NONPROD | HH_other | HH_housing | Trade | Agriculture | Construction |
  |---|---|---|---|---|---|---|---|
  | persero | +413,420 (+10.68%) | +189,472 | +125,487 | +56,476 | | | |
  | bsn | −267,819 (−7.22%) | −180,313 | −119,400 | −53,483 | −32,189 | −20,323 | −18,166 |
  | total | +154,052 (+1.79%) | | | | | | |

- This looks like a bank of about Rp 270 tn of credit moving from the private national group to the
  state-bank group, with a large consumer book. Its size is similar to the financing of Bank Syariah
  Indonesia (about Rp 270 to 300 tn), but **this identification is not verified**. If it is right, it
  matters for the Islamic comparison.
- Flag `reclass_2026_05_bsn_to_persero_unexplained` is set on bsn and persero from 2026-05.

**B8. BPR anomalies (no footnote).**
- BPR TOTAL by month:

  | Month | BPR TOTAL |
  |---|---|
  | 2024-05 | 160,591 |
  | 2024-06 | 150,163 |
  | 2024-07 | 161,225 |
  | 2024-10 | 164,714 |
  | 2024-11 | 125,884 |
  | 2024-12 | 165,733 |
  | 2025-01 | 120,604 |
  | 2025-02 | 167,932 |

- The single-month dips in 2024-06, 2024-11 and 2025-01 (−6.5%, −23.6%, −27.2%, each fully reversed the
  next month) look like incomplete reporting. They also lower the published total in those months.
- These cells are flagged `bpr_dip_suspected_partial_reporting` and `total_includes_bpr_dip`. Do not use
  BPR, or the total including BPR, for those months without adjustment.
- Earlier BPR volatility (2006-03 to 2006-05: −6.8%, −13.8%, +18.3%) is not flagged.

**Memo items (old sheet only).** Central government and non-resident loans, Rupiah and FX, cover
2010-01 to 2017-06. They are small (5,811 in Jan-2010; 8,530 in Jun-2017) and are not part of the group
totals. They are kept with `bank_group_code = memo`.

### 2.5 Flags (column `flag`, semicolon-separated)

| Flag | Rows | Meaning |
|---|---|---|
| `bpr_zero_not_reported` | 26 | BPR published as 0 in 2002-03 and 2002-07 |
| `total_excludes_bpr` | 26 | Total for those two months excludes BPR |
| `bpr_dip_suspected_partial_reporting` | 63 | BPR in 2024-06, 2024-11 and 2025-01 |
| `total_includes_bpr_dip` | 63 | Total in those three months |
| `lbut_2025_includes_former_joint_banks` | 420 | bsn from 2025-01 |
| `reclass_2026_05_bsn_to_persero_unexplained` | 168 | bsn and persero from 2026-05 |

## 3. `bi_lending_rates.csv` (SEKI I.26)

The table is "Suku bunga pinjaman Rupiah yang diberikan menurut kelompok bank dan jenis pinjaman":
Rupiah lending rates by bank group and loan type, % per year.

Columns: `date`, `bank_group_code`, `bank_group_id`, `bank_group_en`, `loan_type_code`,
`loan_type_label_id`, `loan_type_label_en`, `rate_pct_pa`, `source_sheet`.
- Groups: persero, bpd, bsn, foreign_joint (to 2025-03), foreign_branch (2025-01+), commercial_banks
  ("Bank Umum", all commercial banks). There is no BPR.
- Loan types: working_capital, investment, consumption.

### Sheets and overlaps

The sheets are 'Th 1990-2008' (1990-01 to 2008-12), 'Th 2009-2018 ' (2009-01 to 2019-03),
'Th 2010-2024' (2010-01 to 2025-03) and '1.26' (2025-01 to 2026-08). Where sheets overlap, the newest
sheet wins.

| Overlap | Months | Cells | Max abs difference |
|---|---|---|---|
| 'Th 2009-2018 ' vs 'Th 2010-2024' | 2010-01 to 2019-03 | 1,665 | 0.0000 pp |
| 'Th 2010-2024' vs '1.26' | 2025-01 to 2025-03 | 36 | 0.313 pp |

In the second overlap, 12 cells differ by more than 0.005 pp: bsn 9 cells (max 0.313 pp) and
commercial_banks 3 cells (max 0.026 pp). This is the LBUT regrouping of joint banks into bsn (break B6).

Missing values: 773 cells published as 0 are treated as "not reported" and dropped. Most are consumer
loan rates before 2001-02 and BSN or commercial-bank rates in the early 1990s. No '-' cells were found.

Coverage:
- Persero, BPD and BSN working capital and investment: 1990 to 2026-08.
- Consumer loan rates for all groups: 2001-02 onwards.
- Commercial banks, working capital and investment: 1993-04 onwards.
- Range 5.47 to 52.53% (the maximum is foreign_joint working capital in 1998-09).
- Internal gaps (zeros dropped) exist only in BSN working capital and investment, 13 months in 1990-04
  to 1991-06, and foreign_joint working capital in 1992-05.

Same footnote as I.4: coverage change of BSN and government banks from 2017-08. There is no
group-specific BUS or UUS rate. I.26 is an interest-rate table for Rupiah loans; whether the Islamic
equivalent rates of BUS are included in the group averages is not stated.

## 4. `bi_deposit_rates.csv` (SEKI I.28, obtained in this build)

The table is "Suku bunga simpanan berjangka Rupiah menurut kelompok bank dan jangka waktu": Rupiah
time-deposit rates by bank group and tenor, % per year.

Columns: as in I.26, with `tenor_code` (1m, 3m, 6m, 12m, 24m), `tenor_label_id` and `tenor_label_en`.
- Groups: persero, bpd, bsn, foreign_joint / foreign_branch, commercial_banks.

### Sheets and overlaps

The sheets are 'Th 1990-2008', 'Th 2009-2018', 'Th 2010-2024' (to 2025-03) and '1.28' (2025-01 to
2026-08).

| Overlap | Months | Cells | Max abs difference |
|---|---|---|---|
| 'Th 2009-2018' vs 'Th 2010-2024' | 2010-01 to 2019-03 | 2,775 | 0.0000 pp |
| 'Th 2010-2024' vs '1.28' | 2025-01 to 2025-03 | 60 | 0.220 pp |

In the second overlap, 35 cells differ by more than 0.005 pp: bpd 8 (max 0.058), bsn 11 (max 0.155),
commercial_banks 10 (max 0.220), persero 6 (max 0.084). So the LBUT vintage revised the deposit rates of
all groups, not only bsn. '1.28' is used from 2025-01.

Missing values: 89 cells published as 0 are dropped, all in 1990 and 1991:
- BSN, all 5 tenors, 15 months: 1990-01 and 1990-02, plus 13 scattered months from 1990-04 to 1991-06.
- foreign_joint 24m, 14 months: 1990-01 to 1990-09 and 1991-01 to 1991-05.

Coverage: 1990-01 to 2026-08. Range 2.44 to 63.21%; the maximum is BSN 1-month in 1998-09.

## 5. `bi_money_market_rates.csv` (SEKI I.25, file TABEL1_25_1)

The table is "Suku bunga, diskonto, imbalan, margin": BI policy instruments and money-market rates,
% per year, **end-of-period** (footnote "Data akhir periode").

Columns: `date`, `series_code`, `label_id` (Indonesian, "instrument > tenor"), `label_en`, `rate_pct_pa`,
`source_sheet`, `sheet_row`.

### Sheets used (newest wins in overlaps)

| Sheet | Original table | Span | Main contents |
|---|---|---|---|
| 'Th 1990-2003' | II.29 | 1990 to 2003 | SBI, FASBI, PUAB, JIBOR, maximum guarantee-programme rates, SWBI, PUAS |
| 'Th 2002-2009' | 1.30 | values from 2003-12 to 2009-12 | BI Rate, SBI, SBIS, FASBI, repo by collateral (SBI/SUN/SBIS/SBSN), PUAB morning and afternoon, PUAB FX, JIBOR, LPS guarantee rates, PUAS, mudharabah deposit return |
| 'Th 2010-2016' | | 2010 to 2016 | Policy rate, SBI, SDBI, reverse repo SBN, repo, deposit facility (FASBI), lending facility, SBIS, reverse repo SBSN, FASBIS |
| '1.25A_1' and '1.25A_2' | | 2017-01 to 2026-09 | Adds SukBI (Sukuk Bank Indonesia, issued from 21 Dec 2018), SRBI, BI-FRN |

Overlap: the only overlap is 2003-12 between the first two sheets (5 cells). The one difference is JIBOR
overnight, 8.24 vs 8.23.

**How sheets are combined:** the newest sheet wins, but only among non-missing values.
- 'Th 2002-2009' shows '-' for most series in 1999 to 2003. A '-' or 0 in a newer sheet therefore never
  overwrites a value from an older sheet.
- An earlier version of the script let blanks override values, which wrongly deleted JIBOR, SBI and PUAS
  data for 1999 to 2003. This is fixed; for example, `jibor_on` now has 143 of 144 months.
- The same rule applies to I.26 and I.28. There it changed nothing, because their sheets have no blanks.

Missing values: 7,545 cells published as 0 (instrument not issued or not traded that month) and 3,952
cells shown as '-' were dropped. Both counts are over all sheets, before de-duplication. A missing month
for an auction instrument (e.g. SBIS 9m) means "no operation", not missing data.

Codes and labels:
- Each `series_code` has one English label, taken from its newest sheet.
- `label_id` keeps the original Indonesian row label, which can differ by sheet. For example, sbi_1m is
  "SBI - 1 Bulan" in 'Th 1990-2003' and "Sertifikat Bank Indonesia > 1 Bulan" later.
- The 1990-2003 interbank series (`puab_on`, `puab_all`, `fasbi_on`, `fasbi_7d`) are kept apart from the
  2003-12+ session-specific series (`puab_am_*`, `puab_pm_*`, `fasbi_on_am`, `fasbi_on_pm`). The
  definitions differ by trading session.

### Key series and coverage (first to last non-missing month)

| Series | Coverage | Notes |
|---|---|---|
| `bi_rate` | 2005-10 to 2009-12 | |
| `policy_rate` | 2010-01 to 2026-09 | BI Rate to 2016-07 (6.50), BI 7-Day Reverse Repo Rate from 2016-08 (5.25), as shown by the values. In 2026: 4.75 to 2026-04, 5.25 in 2026-05, 5.75 from 2026-06. |
| `puab_on`, `puab_all` | 1992-12 to 2003-12 | |
| `puab_am_on`, `puab_am_all` | 2003-12 to 2009-12 | |
| `puab_pm_*` | 2004-01 to 2009-12 | |
| `jibor_1m`, `jibor_3m` | 1996-12 to 2009-12 | 146 months each |
| `jibor_on` | 1998-01 to 2009-12 | 143 months |
| `puas` | 2000-03 to 2009-12 | 95 months; from 'Th 1990-2003' row "PUAS" to 2003-11, then 'Th 2002-2009' "Pasar Uang Antar Bank Syariah" |
| `swbi` | 2000-02 to 2003-12 | |
| `sbis_1m` | 2008-04 to 2010-06 | |
| `sbis_3m`, `sbis_6m`, `sbis_9m`, `sbis_12m` | 2010-07 to 2021-03 | Auction months only |
| `sukbi_7d` | 2018-12 to 2026-09 | |
| `sukbi_*` other tenors | 2018 to 2026 | |
| `fasbis` | 2010-01 to 2026-09 | |
| `fasbi_on_pm` (deposit facility) | 2003-12 to 2026-09 | |
| `lending_facility` | 2010-01 to 2026-09 | |
| `rr_sbn_7d` | 2013-07 to 2026-09 | |
| `rr_sbn_*` other tenors | various | |
| `rr_sbsn_28d` | 2011-12 to 2018-12 | |
| `repo_sbi`, `repo_sun`, `repo_sbis`, `repo_sbsn` | 2006 to 2009 | |
| `srbi_6m`, `srbi_9m`, `srbi_12m` | 2023-09 to 2026-09 | |
| `bi_frn_12m` | 2025-11 to 2026-09 | |
| `mudharabah_deposit` | 2003-12 to 2009-12 | |

**Not available in this file after 2009:** PUAB (overnight and term), JIBOR and PUAS. The 2010+ sheets
of TABEL1_25_1 contain only BI instruments and facilities. I did not look for or fetch the separate SEKI
table that publishes interbank rates after 2009, because only I.28 was in scope for fetching.

**Islamic vs conventional pairs available:**
- SBI vs SBIS
- FASBI vs FASBIS
- Reverse repo SBN vs reverse repo SBSN (SBSN only to 2018-12)
- SukBI vs policy rate / SRBI
- PUAB vs PUAS (to 2009 only)
- Repo with SUN vs SBSN collateral (2008 to 2009)

## 6. `bi_sbn_outstanding.csv` (SEKI IV.4, file TABEL4_4)

The table is "IV.4 Posisi Surat Berharga Negara (SBN)": outstanding government securities, Rp billion,
end of month.
- Dates: Dec-2008, Dec-2009, then monthly from 2010-01 to 2026-09.
- Columns: `date`, `instrument` (SUN or SBSN), `series_code`, `breakdown` (total / by_type / by_holder),
  `label_id`, `label_en`, `outstanding_rp_bn`, `source_sheet`, `sheet_row`.

Series:
- **SUN:** total = government bonds (Obligasi Negara) + treasury bills (SPN).
  - Bonds by type: fixed, variable, hedge, ORI retail, zero coupon.
  - Bonds by holder: government banks, private national banks, joint banks, foreign banks, regional
    development banks, Bank Indonesia ("including repo SBN, reverse repo SBN and FTE SBN"), customers,
    other institutions.
  - SPN by holder.
- **SBSN:** total, by type only: IFR & SDHI, Fixed Rate, retail SBSN, SPN Syariah, Savings Sukuk.
  - SBSN holder breakdown is **not** published in this table.
  - The IFR & SDHI row runs 2008-12 to 2015-12. A "Fixed Rate" row replaces it from 2016-01; both rows
    carry item number 29 in the sheet.

663 cells shown as '-' (nil) were dropped.

### Checks

| Check | Max abs gap (Rp bn) | Months over 1 bn |
|---|---|---|
| SUN − (bonds + SPN) | 1.24 | 2016-06, 2016-07 |
| Bonds − sum(types) | 1.0 | |
| Bonds − sum(holders) | 19.0 | 2012-01 (19.0); 2.0 in 2010-11 and 2011-01 |
| SPN − sum(holders) | 2.0 | 2013-04 |
| SBSN − sum(types) | 1.0 | |

The SBSN share of total SBN at December rose from 0.9% (2008) to 5.9% (2010), 11.5% (2012), 15.7% (2016),
18.8% (2019) and 19.9% (2024). It was 19.8% in 2026-09.

## 7. Known limitations / to do

1. **I.4 has no Islamic split.** A conventional-vs-Islamic comparison needs OJK SPS financing by sector,
   subtracted from or set against I.4. The SPS sector classification and I.4 KBLI-17 must be mapped, and
   SPS covers BUS and UUS separately.
2. **Islamic inclusion is inferred, not documented.** That BUS financing is in I.4 is inferred
   (section 2.1). The SEKI Metadata page referred to in the footnote was not retrieved.
3. **Three unexplained events in I.4:** the 2026-05 bsn → persero reallocation, the BPR dips, and the
   Mar-2024 adjustment. All have the sizes given above. None is corrected in the data; only flagged.
4. **Old/new sector bridge:** only agriculture, mining, manufacturing and construction match one-to-one.
5. **No interbank rates after 2009:** PUAB, JIBOR and PUAS for 2010+ are not in the files used here.
