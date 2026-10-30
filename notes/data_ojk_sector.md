# Data note: Islamic bank financing and NPF by economic sector (OJK SPS)

Builder: `ojk_sector`. Script: `code/py/build_ojk_sector.py` (helpers in `code/py/ojk_sector_lib.py`).
Rerun end to end with `python -I code/py/build_ojk_sector.py`. The script prints a JSON validation block,
and every number quoted below comes from that block (run of 2026-10-29). Two runs gave byte-identical outputs
(md5 of the main CSV `08cc5889…`).

Outputs
- `data/clean/ojk_islamic_financing_by_sector.csv`: 9,997 rows, tidy long format.
- `data/clean/ojk_conversion_events.csv`: 975 rows, BUS/UUS jumps by sector at conversion, merger and scan months.

## 1. Sources

All files are OJK *Statistik Perbankan Syariah* (SPS) monthly workbooks that OJK published as open downloads.
For each file in `data/raw/ojk/`, the SHA-1 (base32) equals the digest of the Internet Archive capture listed
below. Each file is therefore byte-identical to what ojk.go.id served.

| edition id | file | original URL (ojk.go.id) | archive capture | used for |
|---|---|---|---|---|
| SPS_2025_06 | SPS_2025_06.xlsx | https://ojk.go.id/id/kanal/syariah/data-dan-statistik/statistik-perbankan-syariah/Documents/Pages/Statistik-Perbankan-Syariah---Juni-2025/STATISTIK%20PERBANKAN%20SYARIAH%20-%20JUNI%202025.xlsx | 20251127230705 | new19, primary |
| SPS_2024_12 | SPS_2024_12.xlsx | …/Statistik-Perbankan-Syariah---Desember-2024/STATISTIK%20PERBANKAN%20SYARIAH%20-%20DESEMBER%202024.xlsx | 20251225135040 | new19: 2024-01..2024-05, plus revision check |
| SPS_2018_12 | SPS_2018_12.xlsx | https://www.ojk.go.id/…/Statistik-Perbankan-Syariah---Desember-2018/SPS%20Desember%202018.xlsx | 20240609205549 | new19 revision check |
| SPS_2015_06 | SPS_2015_06.xlsx (**fetched by this builder**) | https://www.ojk.go.id/id/kanal/syariah/data-dan-statistik/statistik-perbankan-syariah/Documents/Pages/Statistik-Perbankan-Syariah-Jun-2015/SPS%20Juni%202015.xlsx | https://web.archive.org/web/20240523070318id_/https://www.ojk.go.id/id/kanal/syariah/data-dan-statistik/statistik-perbankan-syariah/Documents/Pages/Statistik-Perbankan-Syariah-Jun-2015/SPS%20Juni%202015.xlsx | old9: 2014-01..2015-05, plus revision check |
| SPS_2014_12 | SPS_2014_12.xls | https://www.ojk.go.id/id/kanal/syariah/data-dan-statistik/statistik-perbankan-syariah/Documents/Pages/statistik-perbankan-syariah-desember-2014/SPS%20Desember%202014.xls | 20240613211100 | old9: 2009-01..2013-12 |

SHA-256 of the five files: 2025_06 `fc5edb35…ca44`, 2024_12 `72b5a4ee…2ac9`, 2018_12 `e60af764…9f30`,
2015_06 `7b2c481e…8b88`, 2014_12 `cf5604b1…889a`. The script recomputes them.

Tables used:
- New classification: sheet `Tabel 14-14a-14b LapUsaha` contains Tabel 14 (BUS+UUS), Tabel 14a (BUS) and Tabel 14b (UUS):
  "Pembiayaan dan NPF … berdasarkan Lapangan Usaha dan Bukan Lapangan Usaha Penerima Pembiayaan", in Rp bn.
  Each sector row is followed by its NPF row.
- Old classification: sheet `tabel 20 Pembiayaan BUS UUS SE` (Tabel 20, financing by *sektor ekonomi*) and sheet
  `tabel 28 NPF BUS UUS SE` (Tabel 28, *Pembiayaan Non Lancar* by sector), both BUS+UUS only, in Rp bn.
- Cross-check tables, used for validation only: new Tabel 13/13a/13b (financing and NPF by type of use, totals);
  old Tabel 18 (by akad), 22 (by use), 26 (by quality: Total Pembiayaan, Non Lancar) and 30 (NPF by use).

Search for a pre-2014 BUS/UUS split by sector. The CDX listing of
`ojk.go.id/id/kanal/syariah/data-dan-statistik/statistik-perbankan-syariah/*` was run with the
`application/vnd.ms-excel` filter (1 hit: the Dec-2014 .xls already in raw), with the xlsx filter (77 hits, all
June-2015 or later editions), and with a broader `ojk.go.id/id/kanal/syariah/*` query on `xls` URLs. No SPS
edition published before Dec-2014 is archived under OJK. Every old-format edition seen (Dec-2014 and Jun-2015)
publishes the sector tables for BUS+UUS combined only.
**A BUS/UUS split by sector before 2014-06 is therefore not available from open OJK sources.** The old9 series
is BUS+UUS only. No 2023 SPS edition is archived either (see the coverage gap in section 3).

## 2. Output 1: `ojk_islamic_financing_by_sector.csv`

Columns: `date` (YYYY-MM-01, end-of-month stock), `classification` (`old9` / `new19`), `sector_code`,
`sector_group` (business / non_business / other / total), `sector_id_label` (Indonesian label as printed),
`sector_en`, `bank_type` (`BUS` = Bank Umum Syariah, Islamic commercial banks; `UUS` = Unit Usaha Syariah,
Islamic windows of conventional banks; `BUSUUS` = both), `financing_rp_bn` (*pembiayaan yang diberikan*,
Rp billion), `npf_rp_bn` (non-performing financing, Rp billion, i.e. collectibility 3-5), `npf_ratio_pct`
(= 100·npf/financing, computed), `edition`, `table`, and `note` (any correction or flag on the row).

Units: Rp billion (*Miliar Rp*) as published. Values are not deflated and not seasonally adjusted.
Financing is gross, in rupiah plus foreign currency.

### new19 (2014-06 .. 2025-06; BUS, UUS, BUSUUS)
There are 18 *lapangan usaha* (business) sectors, L01-L18, and 6 non-business categories, N01-N06, plus TOTAL.

| code | Indonesian (short) | English |
|---|---|---|
| L01 | Pertanian, Perburuan dan Kehutanan | Agriculture, hunting, forestry |
| L02 | Perikanan | Fishery |
| L03 | Pertambangan dan Penggalian | Mining and quarrying |
| L04 | Industri Pengolahan | Manufacturing |
| L05 | Listrik, gas dan air | Electricity, gas, water |
| L06 | Konstruksi | Construction |
| L07 | Perdagangan Besar dan Eceran | Wholesale and retail trade |
| L08 | Penyediaan akomodasi dan makan minum | Accommodation and food services |
| L09 | Transportasi, pergudangan dan komunikasi | Transport, warehousing, communication |
| L10 | Perantara Keuangan | Financial intermediaries |
| L11 | Real Estate, Usaha Persewaan, Jasa Perusahaan | Real estate, renting, business services |
| L12 | Administrasi Pemerintahan… | Public administration, defence |
| L13 | Jasa Pendidikan | Education |
| L14 | Jasa Kesehatan dan Kegiatan Sosial | Health and social work |
| L15 | Jasa Kemasyarakatan, Sosial Budaya, Hiburan… | Community, social, personal services |
| L16 | Jasa Perorangan yang Melayani Rumah Tangga | Services to households |
| L17 | Badan Internasional… | Extra-territorial organisations |
| L18 | Kegiatan yang belum jelas batasannya | Not clearly defined |
| N01 | Rumah Tangga: Pemilikan Rumah Tinggal | Households: home ownership |
| N02 | … Pemilikan Flat/Apartemen | Households: flats/apartments |
| N03 | … Pemilikan Ruko/Rukan | Households: shop-houses |
| N04 | … Pemilikan Kendaraan Bermotor | Households: motor vehicles |
| N05 | … Peralatan RT lainnya (termasuk multiguna) | Households: other equipment, incl. multipurpose loans |
| N06 | Bukan Lapangan Usaha Lainnya | Other non-business recipients |

Edition rule: for each (classification, month, bank type), the latest edition that carries the month is used, so
all sectors of a month come from one edition. new19 rows come from SPS_2025_06 (8,775 rows) and, for
2024-01..2024-05, from SPS_2024_12 (375 rows). The Jun-2025 edition drops those five months.

### old9 (2009-01 .. 2015-05; BUSUUS only)
There are ten rows, S01-S10, plus TOTAL. The tables call them "sektor ekonomi". The project calls the set "old9"
(nine economic sectors plus *Lain-lain*).

| code | Indonesian | English |
|---|---|---|
| S01 | Pertanian, kehutanan dan sarana pertanian | Agriculture, forestry, agricultural facilities |
| S02 | Pertambangan | Mining |
| S03 | Perindustrian | Manufacturing |
| S04 | Listrik, gas dan air | Electricity, gas, water |
| S05 | Konstruksi | Construction |
| S06 | Perdagangan, restoran dan hotel | Trade, restaurants, hotels |
| S07 | Pengangkutan, pergudangan dan komunikasi | Transport, warehousing, communication |
| S08 | Jasa dunia usaha | Business services (**includes household home/flat/shop-house ownership, see section 4**) |
| S09 | Jasa sosial/masyarakat | Social/community services |
| S10 | Lain-lain | Others (incl. consumer and vehicle financing) |

Sources by period: 2009-01..2013-12 from SPS_2014_12 (660 rows); 2014-01..2015-05 from SPS_2015_06 (187 rows).
The 2015-06 column of SPS_2015_06 (headed "Juni*)", provisional) repeats 2015-05 exactly in every sector for both
financing and NPF. It is a carry-forward, and it is **dropped** because new19 covers that month. Annual-only columns
for 2005-2008 exist in the source but are out of scope.

## 3. Coverage and gaps

| series | first | last | months |
|---|---|---|---|
| new19 BUS / UUS / BUSUUS | 2014-06 | 2025-06 | 122 each |
| old9 BUSUUS | 2009-01 | 2015-05 | 77 |

- **Gap: 2023-01..2023-11 (11 months) is missing in every series.** SPS_2025_06 carries 2014-06..2022-12 monthly,
  a single 2023 year-end column, 2024-06..2024-12 and 2025-01..2025-06. SPS_2024_12 carries 2014-06..2022-12,
  2023 "Des" and 2024-01..12. No 2023 edition is archived (CDX search above). The 2023-12 value comes from the
  stand-alone 2023 column, which has no month label in SPS_2025_06. Its row note says so. That column equals the
  "Des 2023" column of SPS_2024_12 exactly (zero revisions, see section 5).
- Header quirks handled by the parser (`date_columns`):
  - Year blocks for 2020-2022 have merged headers and no month labels. They are read as 12 columns, Jan..Dec.
  - In SPS_2025_06, the columns headed Jan-Mar sit under the merged "2024" header. They are 2025-01..03.
  - Stand-alone year columns (e.g. "2014", "2015") are year-end duplicates. Each was checked against its Dec column.
- Overlap of old9 and new19: 2014-06..2015-05 (12 months).

## 4. Classification breaks and the old-to-new bridge

- **old9 break at 2014-05.** Source footnote 1 reads "Revisi data BUS-UUS mulai bulan Mei 2014 berdasarkan LSMK".
  From May-2014 the old table is a mapping of the new LSMK sector data, and sector levels jump. For example,
  Perindustrian goes from 6,015 (2014-04) to 10,540 (2014-05) Rp bn, while total financing moves smoothly
  (187,885 to 189,690). Rows dated 2014-05 carry a note.
- **new19 first month (2014-06) is unstable.** Between 2014-06 and 2014-07, BUS+UUS financing is reallocated:
  - N03 shop-houses: 13,035 to 1,860
  - L18 not clearly defined: 10,126 to 3,634
  - L15 community services: 3,454 to 8,899
  - N05 other household: 12,080 to 21,923
  - L10 financial intermediaries: 19,613 to 16,849

  Total financing moves only from 193,136 to 194,079. Treat 2014-06 sector shares with caution. These rows carry a note.
- **Bridge new19 → old9.** The concordance was found empirically and is exact on all 12 overlap months:
  - S01 = L01+L02; S02 = L03; S03 = L04; S04 = L05; S05 = L06; S06 = L07+L08; S07 = L09
  - **S08 = L10+L11+N01+N02+N03** (old "Jasa dunia usaha" includes households' home, flat and shop-house ownership)
  - S09 = L12+…+L17
  - **S10 = L18+N04+N05+N06**

  This mapping is coded as `NEW2OLD` in the script. The first concordance tried put N01-N03 in S10. That version
  showed gaps of 39-53 trn in S08 and S10, and the gaps equalled N01+N02+N03 exactly.

## 5. Validation (numbers from the final run)

**V1. Sum of sectors vs reported total, primary output.**

| series | months | financing: max abs gap | NPF: max abs gap |
|---|---|---|---|
| new19 BUSUUS (SPS_2025_06) | 117 | 2.29 Rp bn (2020-08; max rel 7.3e-6) | 0.26 (2016-09) |
| new19 BUS (SPS_2025_06) | 117 | 1.50 (2020-08) | 0.26 |
| new19 UUS (SPS_2025_06) | 117 | 1.59 (2016-05) | 0.04 |
| new19, all bank types (SPS_2024_12) | 5 | ≤ 3e-6 | ≤ 0.006 |
| old9 (SPS_2015_06) | 17 | 2e-6 | 1e-6 |
| old9 (SPS_2014_12) | 60 | **0.000** | 12.66 (2010-11; max rel 0.59%) |

  - new19 months with a financing gap above 1 Rp bn: 2016-04, 2016-05, 2016-09, 2016-10, 2020-06, 2020-08, 2021-04
    and 2021-05. All are below 2.3 bn and come from the source.
  - old9 NPF: the sector NPF sum falls **short** of the published total by 0.15-0.55 bn in 2009-02..2009-11,
    1.01-1.16 bn in 2009-12..2010-10, and 12.2-12.7 bn in 2010-11/12. This is in the source and was not reconciled.
    From 2011 the gap is under 0.01.

**V2. BUS + UUS = BUSUUS** (new19, 3,050 sector-month cells, 122 months, after the corrections in section 6).
- Financing: max abs gap 25.90 Rp bn (2017-12, N04 vehicles). Other months with gaps above 0.01: 2019-03, 2019-11,
  2019-12, 2020-06, 2020-07, 2020-08, 2020-10, 2021-02, 2021-04, 2021-05, 2021-12, 2022-01, 2022-02. All of these
  are ≤ 2.25 bn.
- NPF: max 1.27 (2021-06, L18). All other months are ≤ 0.32.
- Before the corrections, the gap was 94,123.58 bn (2018-01 TOTAL), which is the UUS doubling described in section 6.

**V3. Tabel 14 totals vs Tabel 13 totals** (same edition, raw values before corrections; 348 bank-type-months in
2025_06 and 2024_12, 165 in 2018_12). Gaps above 1 bn:
- Rounding-size gaps (1.1-2.3 bn): 2016-04/05, 2016-09/10, 2020-06, 2020-10, 2020-12, 2021-02/04/05.
- **2017-01: BUS 916.7 bn higher and UUS 916.7 bn lower in Tabel 14 than in Tabel 13** (NPF: 116.6), with identical
  BUS+UUS totals. Some bank's portfolio is classed BUS in one table and UUS in the other. Kept as in Tabel 14: the
  Tabel 14 BUS path (177,482 → 174,383 → 174,625 for Dec/Jan/Feb) has no extra dip. **Not reconciled.**
- 2017-12: BUS 8.96 bn.
- 2018-01 UUS: Tabel 14b is double Tabel 13b. Fixed, see C1.
- 2018-01 BUS: Tabel 13a = 116,378 vs 186,508 in Tabel 14a. The Tabel 13a value is wrong in the 2024/2025 editions
  (the 2018 edition agrees with Tabel 14a).
- NPF gap of 2.41 in 2014-09.
- NPF gap of 1.27 in 2021-06.

**V4. Old-table cross-checks, SPS_2014_12 (72 months, after the corrections in section 6):**
- Tabel 20 vs Tabel 22 and Tabel 26 financing totals: gap 0 except 2013-11/12 (2.5 bn) and 2010-02, where Tabel 26
  alone differs by 1,248 bn.
- Tabel 20 vs Tabel 18: gap 0 except 2012-03, where Tabel 18 alone is 4,877 bn lower. Tabel 20, 22 and 26 agree,
  so Tabel 20 is kept. The kept value (109,116) is above April (108,767). **Flag.**
- 2012-12: all four tables carry a monthly "Des 2012" that repeats Nov (140,318). The 2012 year-end columns of all
  of them show 147,505 (see C7).
- Tabel 28 total NPF vs Tabel 30: max gap 0.194 over 72 months.
- Tabel 28 vs Tabel 26 *Non Lancar*: gaps only at 2010-02 (the Tabel 26 anomaly) and 2012-12 (Tabel 26 repeats Nov).
- SPS_2015_06: max gaps 0.001 (financing) and 0.194 (NPF) over 18 months.

**V5. Year-end columns vs Dec columns:** 42 checks. Every gap is 0.000, except old Tabel 20 Dec-2012 (C7).

**V6. old9 vs aggregated new19 on 2014-06..2015-05**, using the concordance in section 4:
- Every sector S01-S10: max abs gap **0.000** bn for financing.
- NPF: 0.000 except S06 = 2.41 bn in 2014-09. That is the same 2.41 bn inconsistency as in V3.
- TOTAL: max 0.51 bn (2015-03..05, a small vintage difference between SPS_2015_06 and SPS_2025_06).

**V7. Revisions across editions, same cells:**

| comparison | overlap | financing | NPF |
|---|---|---|---|
| SPS_2025_06 vs SPS_2024_12 | 111 months, 8,325 cells | 0 cells revised | 0 cells revised |
| SPS_2025_06 vs SPS_2018_12 | 55 months, 4,125 cells | 0 cells revised | 1 cell: 2018-01 BUSUUS TOTAL (see C6) |
| SPS_2015_06 vs SPS_2014_12 (old9) | 2014-01..12, 132 cells | 0 | 0 |

Spot check: the SPS_2015_06 annual columns for 2009-2013 equal SPS_2014_12 (e.g. S01 2009 = 1,331.062;
2012 = 2,809.446). OJK does not revise this table across vintages. The only differences are errors introduced in
later editions (C6).

**V8. Sanity checks:**
- 0 cells with NPF > financing.
- 0 negative cells.
- 0 missing financing or NPF values after the fills in C2/C3.
- 6 cells were published as text with "*)", all in Aug-2020, 2020-08.

## 6. Corrections applied

Every corrected row says so in `note`. The script asserts or self-checks each rule.

- **C1, 2018-01 UUS (Tabel 14b) doubled.** Every UUS cell in Jan-2018 is exactly twice the true value: total
  188,247.16 vs BUS+UUS − BUS = 94,123.58. Every cell was halved. The halved financing cells equal
  (BUSUUS − BUS) to 0.000 bn in every sector, and the halved total equals the Tabel 13b UUS total (94,123.58; NPF 2,267.84).
- **C2/C3, blank cells filled from the identity BUS + UUS = BUSUUS:**
  - BUSUUS L15 NPF 2018-01 = 239.957 (BUS 201.485 + halved UUS 38.472)
  - UUS L05 and L12 NPF in 2019-04, 05 and 06 = 0.000 (BUSUUS − BUS)
- **C4, dash cell.** A "-" (nil) cell, BUSUUS L18 NPF 2022-01, was set to 0. Financing in that cell is 0.
- **C5, 2020-08 BUSUUS L01 published as text "16.009 *)".** The text is inconsistent with BUS (11,533.0) + UUS
  (4,566.4) = 16,099.4 and with the BUSUUS total: the sector-sum gap was −92.67 bn and is 2.29 bn after the fix.
  It is most likely a typo for 16.099. It was replaced by BUS + UUS. Five other text cells in Aug-2020 ("11.573 *)",
  "3.681 *)", "6.627 *)", "8.581 *)", "3.245 *)") are consistent and are kept, read as thousands-separated, so
  they are rounded to 1 bn.
- **C6, 2018-01 BUSUUS total NPF.** The 2024 and 2025 editions publish 11,747.54, which omits the blank L15 cell.
  It was corrected to the sum of sectors, 11,987.50. That equals the SPS_2018_12 value and the Tabel 13 total.
- **C7, old Tabel 20 Dec-2012.** The column headed "Des 2012" repeats Nov-2012 in every sector. It was replaced by
  the 2012 year-end column (total 147,505.141, consistent with Tabel 18, 22 and 26 year-end columns).
- **C8, old Tabel 28 (NPF), year 2012, column misalignment.**
  - The sheet has an extra column headed "2012 / Jan" placed before the 2011 year-end column, followed by a block
    headed Jan..Des 2012.
  - Tabel 26 *Non Lancar* and Tabel 30 show that the extra column is January. The columns headed Jan..Okt hold
    Feb..Nov. The column headed Nov repeats the one headed Okt, and Des is December.
  - The columns were re-mapped accordingly (`realign_t28_2012`). Before the fix, Tabel 28 differed from Tabel 30 by
    up to 207.9 bn in Jan-Oct 2012. After it, the max gap is 0.194 bn.

## 7. Output 2: `ojk_conversion_events.csv`

Columns:
- `event_id`, `event`, `bank`, `event_type`, `effective_date`, `date` (month inspected), `bank_type`,
  `sector_code`, `sector_en`
- `financing_prev_rp_bn`, `financing_rp_bn`, `change_rp_bn` (m/m), `median_change_prev12_rp_bn` (median m/m change
  over the 12 previous months), `abnormal_change_rp_bn` (= change − median), `npf_change_rp_bn`

The data are the new19 primary series, including corrections C1-C6.

Legal effective dates come from public announcements. They were **not verified against an official register** in
this build and are marked "approx.". The month columns are what the data show.

TOTAL financing, Rp bn (m/m change, and abnormal change where available):

| id | event | month | BUS | UUS | BUS+UUS | main sectors (abnormal change) |
|---|---|---|---|---|---|---|
| E1 | BTPN Syariah spin-off from BTPN's UUS (2014) | 2014-07 | +3,097 | −2,154 | +943 | No pre-period, and confounded by the 2014-06/07 reclassification (BUS N03 −11,177, N05 +9,793, L18 −6,510). Not separable by sector. |
| E2 | Bank Aceh conversion to BUS (2016) | **2016-09** | +15,356 (abn +14,884) | −804 (abn −1,351) | +14,552 | BUS N05 +10,035, N01 +1,413, L04 +645, L06 +615; UUS N01 −843, N05 −503 |
| E3 | Bank NTB Syariah conversion (2018) | **2018-09** | +5,607 (abn +4,381) | +1,400 (abn −777) | +7,007 (abn +4,060) | BUS N06 +3,199, N05 +1,073, L11 +320, N01 +320. 2018-10 shows no further jump. |
| E4 | BSI merger of BRIS, BSM and BNIS (all BUS), 2021-02-01 | 2021-02 | −161 | −487 | −650 | No BUS/UUS shift, as expected. BUS L04 −1,050 and L06 −844 abnormal (possible re-classification at the merger). |
| E5 | Bank Riau Kepri conversion to BUS (2022) | **2022-08** | +22,862 (abn +19,871) | −6,634 (abn −9,430) | +16,228 (abn +11,211) | BUS N05 +14,453, L01 +1,772, N01 +1,109, L06 +1,020; UUS N05 −6,708, L07 −1,720 |

Months flagged by an automatic scan, with no bank attributed: rows S1-S3 of the file.
- 2015-06: BUS +2,689, UUS −526.
- 2016-12: UUS +4,697.
- 2021-10: UUS +4,560.
- 2021-11: BUS −7,354.
- 2021-12: BUS +6,393.
- 2015-12 (BUS +3,101) also passed the scan threshold but is not in the file.

The scan rule flags a month when ΔUUS < −0.5·m and ΔBUS > 3·m, or when |ΔBUS| or |ΔUUS| > 4·m, where m is the
median absolute m/m change of the previous 12 months. The 2018-01 and 2018-02 artefacts disappeared after C1.

Not observable in this data:
- BUS/UUS events before 2014-06: BRI Syariah 2009, BNI Syariah and BJB Syariah 2010, among others. old9 has no BUS/UUS split.
- Any 2023 event, because of the coverage gap.
- No other BUS/UUS jump appears in 2024-01..2025-06.

## 8. Caveats for users
- For BUS vs UUS comparisons, add break dummies or bank-type re-weighting at 2016-09, 2018-09 and 2022-08.
  BUS+UUS also jumps at those dates, because whole conventional banks converted.
- 2014-06 (first new19 month) and 2014-05 (old9 LSMK revision) are classification breaks.
- 2023-01..2023-11 are missing. 2023-12 comes from a year-end column.
- 2020-08: six cells are provisional values rounded to 1 bn.
- The 2017-01 BUS/UUS allocation (±917 bn) and the old 2012-03 total (Tabel 18 disagrees) are unresolved.
- The raw file `data/raw/ojk/SPI_2025_02.xlsx` in the same folder belongs to another builder and was not used.
