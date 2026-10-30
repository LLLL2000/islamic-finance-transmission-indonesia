# Data note: Islamic bank mechanism series from OJK SPS (contracts, deposits, returns, margins, aggregates)

Builder: `ojk_mechanisms` (resumed run of 2026-10-29). Build script: `code/py/build_ojk_mechanisms.py`.
Independent spot check: `code/py/check_ojk_mechanisms.py`. Rerun with

```
python -I code/py/build_ojk_mechanisms.py      # writes the 5 CSVs and prints every validation number below
python -I code/py/check_ojk_mechanisms.py      # re-reads 1,000 sampled cells straight from the workbooks
```

The build takes about 2.5 minutes. Two consecutive runs gave byte-identical CSVs and an identical validation log.
MD5 of the outputs: contracts `bdb9ae5c…`, deposits `52bf5fea…`, deposit_returns `70bf54a2…`, margins `ac2edd01…`,
aggregates `91afc239…`. All numbers in this note come from the build's printed output (or the check script).

## 0. Status of the earlier, unverified files

An interrupted earlier run had written the five CSVs with no note and no validation. I kept its script and its
file names and column conventions, re-ran it (it reproduced the old CSVs byte for byte), and audited the outputs
against the raw workbooks. I found and fixed the following:

- **The June 2015 edition (`SPS_2015_06.xlsx`) was not used.** It is the later of the two old-format editions and
  revises 2014. The Dec 2014 edition has a garbled time-deposit tenor split from May 2014 onwards: for example,
  Mar 2014 1-month deposits are 428.0 instead of 75,406, and in May-Dec 2014 the 12-month row holds 0.04-3.2 while
  the >12-month row holds 13,090-31,080. As a result, the old tenor rows failed to add up by up to 74,978 Rp bn.
  The 2015_06 edition (flagged `r)`, revised) is now preferred for 2014-01..2014-05. The old-format tenor rows
  now add up to within 0.41 Rp bn.
- **Source errors in the new format were passed through uncorrected.** There are 61 corrected cells, listed in
  section 6. Examples:
  - The Jul 2019 UUS deposit column is a copy of June.
  - Decimal-separator typos in Jun 2020.
  - The Nov 2017 BUS FDR (80.069%) appears in four other tables.
  - The Dec 2024 UUS 6-month row repeats the 3-month row.
  - The Oct 2021 UUS Rupiah murabahah is short by 1,370.9.
- **Several cells were lost to the parser.** Cells written as `13,00*` and `-r` were dropped, and old ratio cells
  written as `14.06% *)` failed to parse. The parser now handles all three.
- **No NPF in Rp bn before 2014-06.** Added from old Tabel 26 (*Non Lancar*), with one correction (Feb 2010).
- **BUS DPK was missing in Feb 2022**, because Tabel 6a has no column for that month. It is now filled from the
  Tabel 22 sum and flagged.
- **Implausible rates were kept as values.** Rates of 33-50% for old >12-month deposits (2011-12) and 73-121% for
  old murabahah/mudharabah/ijarah margins (Apr-Jun 2010) are now set to missing, with the published value kept in
  `note`.
- **Added a `source_cell` column to all five files.** It gives the row/column of the workbook cell, e.g. `r19c47`;
  for contracts `fin:`/`npf:` cells. Old row counts are unchanged except aggregates, which gains 132 rows: old NPF,
  the BUS DPK fallback and its FDR.

Changes in values relative to the unverified files:
- contracts: 3 cells.
- deposits: 62 cells.
- deposit_returns: 18 cells.
- margins: 9 cells.
- aggregates: 2 cells, plus the 132 new rows.

## 1. Sources

All five raw files are OJK *Statistik Perbankan Syariah* (SPS) monthly workbooks that OJK published as open
downloads. They are the same files documented in `notes/data_ojk_sector.md`, where each one's SHA-1 is shown to
equal the Internet Archive digest of the original ojk.go.id URL. SHA-256 prefixes, recomputed now:
- 2025_06 `fc5edb35dc28f8d8`
- 2024_12 `72b5a4ee22c32044`
- 2018_12 `e60af764e3bc8abb`
- 2015_06 `7b2c481e2a0d4c88`
- 2014_12 `cf5604b19913e170`

No new download was made by this builder.

| file | original URL | archive copy used |
|---|---|---|
| SPS_2025_06.xlsx | https://ojk.go.id/id/kanal/syariah/data-dan-statistik/statistik-perbankan-syariah/Documents/Pages/Statistik-Perbankan-Syariah---Juni-2025/STATISTIK%20PERBANKAN%20SYARIAH%20-%20JUNI%202025.xlsx | capture 20251127230705 |
| SPS_2024_12.xlsx | …/Statistik-Perbankan-Syariah---Desember-2024/STATISTIK%20PERBANKAN%20SYARIAH%20-%20DESEMBER%202024.xlsx | capture 20251225135040 |
| SPS_2018_12.xlsx | https://www.ojk.go.id/…/Statistik-Perbankan-Syariah---Desember-2018/SPS%20Desember%202018.xlsx | capture 20240609205549 |
| SPS_2015_06.xlsx | https://www.ojk.go.id/id/kanal/syariah/data-dan-statistik/statistik-perbankan-syariah/Documents/Pages/Statistik-Perbankan-Syariah-Jun-2015/SPS%20Juni%202015.xlsx | https://web.archive.org/web/20240523070318id_/ (same URL) |
| SPS_2014_12.xls | https://www.ojk.go.id/id/kanal/syariah/data-dan-statistik/statistik-perbankan-syariah/Documents/Pages/statistik-perbankan-syariah-desember-2014/SPS%20Desember%202014.xls | capture 20240613211100 |

**Edition priority.** For every cell, the latest edition that carries the month is kept. In practice:
- New format (2014-06..2025-06): almost everything comes from SPS_2025_06. SPS_2024_12 supplies the few cells that
  only it carries; SPS_2018_12 is superseded everywhere and used only for the revision check.
- Old format: 2014-01..2014-05 comes from SPS_2015_06, and 2009-01..2013-12 from SPS_2014_12. SPS_2015_06 has
  only year-end columns for 2009-2013.
- Old-format values for months from 2014-06 onwards are superseded by the new format. They are used only for the
  overlap checks in section 7.

**No SPS edition with 2023 monthly columns is archived** (see `data_ojk_sector.md` for the CDX search). Months
2023-01..2023-11 are therefore missing in every new-format series. 2023-12 comes from the year-end column of the
2024/2025 editions. Wherever a year-end column and a December column both exist, they are equal: max |gap| = 0 over
about 13,000 cell pairs across all tables and editions (section 7).

Tables used (sheet names as in the workbooks):

| content | new format (2014-06+; blocks: BUS+UUS, *a* = BUS, *b* = UUS) | old format (2009-01..2014-05; BUS+UUS only) |
|---|---|---|
| financing and NPF by contract, all currencies | Tabel 11 (`Tabel 11-11a-11b Akad-NPF`) | Tabel 18 (`tabel 18 Komps Pembyan BUS UUS`), financing only |
| same, Rupiah only | Tabel 12 (`Tabel 12-12a-12b Akad-NPF-RP`) | none |
| deposit (DPK) composition | Tabel 22 (`Tabel 22-22a-22b Komposisi DPK`) | Tabel 14 (`tabel 14 Komposisi DPK`) |
| equivalent rate of return on deposits | Tabel 17 section I (`Tabel 17-17a-17b Tk Imbalan`) | Tabel 36 *Dana Pihak Ketiga* (`tabel36 Ekuivalen Imbln BUS UUS`) |
| equivalent financing rate by contract | Tabel 17 section II | Tabel 36 *Pembiayaan* |
| average margin by use x debtor size | Tabel 18 (`Tabel 18-18a-18b Margin JP-UMKM`) | not published |
| average margin by economic sector | Tabel 19 (`Tabel 19-19a-19b Margin SE`) | not published |
| ratios (CAR, ROA, NPF, NPF net, FDR and its parts, BOPO) | Tabel 1 (1a BUS, 1b UUS) | Tabel 38 (`tabel 38 Kinerja BUS UUS`) |
| total assets, number of banks | Tabel 2 | Tabel 6 (TOTAL AKTIVA) |
| DPK and financing to non-bank parties (balance sheet) | Tabel 6 / 6a / 6b | Tabel 6 |
| NPF by collectibility | (Tabel 11 NPF rows) | Tabel 26 (`tabel 26 Pembiayaan BUS UUS NPF`) |

Tabel 1 of the 2018 edition has a different layout and is not read; the 2024/2025 editions cover all its months.

## 2. Conventions common to all five files

- Tidy long CSV, UTF-8. `date` is the first day of the month (YYYY-MM-01) and refers to the end-of-month position.
  Rates are the monthly figures OJK publishes.
- `bank_type`:
  - `BUS` is *Bank Umum Syariah* (stand-alone Islamic commercial banks).
  - `UUS` is *Unit Usaha Syariah* (Islamic windows of conventional banks).
  - `BUS_UUS` is both combined, as published in the un-lettered block.
  - The sector file (`ojk_islamic_financing_by_sector.csv`) writes the combined type as `BUSUUS`. I kept `BUS_UUS`
    here so that existing column conventions do not change; map one to the other when merging.
- Units are in the column names or in `unit`:
  - `_rp_bn` is Rp billion (*miliar Rp*), nominal, not deflated, not seasonally adjusted.
  - `rate_pct` is percent per year.
  - Old tables publish fractions (0.0766), which are converted to percent.
- `currency`:
  - `all` = Rupiah + foreign currency.
  - `IDR` = Rupiah.
  - `FX` = foreign currency (*valas*).
  - `unspecified` = old Tabel 36, which does not state the currency (see section 5).
- Provenance columns:
  - `source_file`, `source_sheet` and `source_table`.
  - `source_cell` gives the 1-based row and column of the cell in the sheet; for contracts it is
    `fin:rRcC;npf:rRcC`, and for derived rows it describes how the value was built.
  - `label_id` is the Indonesian row label (with its parent rows), and `label_en` is its English translation.
- `quality_flag` vocabulary:
  - `parsed_from_text`: the cell was text, for example `'335.552 r'` = 335,552 with a revised marker, or
    `'9,546 r)'`.
  - `dash`: published as "-" (not available).
  - `corrected:diff|sum|scale1000|missing`: a source error was corrected (section 6). The published value is quoted
    in `note`.
  - `component_…`: a harmonised sum that contains such a cell.
  - `zero_published`: a rate published as exactly 0. This occurs only where the category has no outstanding
    balance, for example salam, syndicated ijarah, FX rows or *badan internasional*. Treat it as "not
    applicable", not as a zero price.
  - `outlier_gt50pct` and `negative_rate`: kept as published, but flagged.
  - `computed`: derived.
  - `fallback_tabel22_sum`: see the aggregates section.

## 3. The five outputs

### (a) `data/clean/ojk_contracts.csv`: financing and NPF by contract (*akad*)
11,561 rows. Key: `date, bank_type, currency, contract_code`. Values: `financing_rp_bn`, `npf_rp_bn`.

- `contract_code`, with `contract_group` and `level` describing the hierarchy:
  - `profit_sharing` (group) = `mudharabah` + `musyarakah` + `other_profit_sharing`.
  - `receivables` (group, *piutang*) = `murabahah` + `qardh` + `istishna`.
  - `ijarah` (group, includes leasing receivables) = `ijarah_syndicated` + `ijarah_channeling` +
    `ijarah_executing` + `ijarah_other`.
  - `salam`.
  - `total`.
  - Old format only: `other` (*Lainnya*, 0 in every month).
- Coverage:
  - New format: BUS, UUS and BUS_UUS, `currency` `all` (Tabel 11) and `IDR` (Tabel 12), 2014-06..2025-06, 122
    months each (2023-01..11 missing).
  - Old format: BUS_UUS, `currency=all`, financing only, 2009-01..2014-05.
- **Multijasa is not published as a contract** in any SPS edition, old or new. In the new tables it is part of
  ijarah. **Salam** is 0 in every month.
- **NPF by contract** exists only from 2014-06 (new format).
- Old *Akad Musyarakah* equals new musyarakah plus `other_profit_sharing`; see the overlap checks in section 7.
  This is noted on the old rows.
- Mar 2012 (old): the Tabel 18 total of 104,238.6 (equal to old Tabel 6 *Pembiayaan*) disagrees with Tabels 20, 22
  and 26 (109,115.7). I kept Tabel 18 because its contract rows add up to it. The disagreement is noted on the row.
- 26 rows have `financing_rp_bn` missing (published "-" or blank, for example UUS syndicated ijarah and salam in
  some months); their NPF cell is present.

### (b) `data/clean/ojk_deposits.csv`: DPK composition
23,350 rows. Key: `date, bank_type, series, series_code, fund_type, instrument, currency, tenor`. Value:
`deposits_rp_bn`.

- `series = reported` holds every published row:
  - New Tabel 22 groups (`fund_type`):
    - `wadiah` (*Dana Simpanan Wadiah*).
    - `investment_non_profit_sharing` (*Dana Investasi Non Profit Sharing*, i.e. mudharabah deposits).
    - `investment_profit_sharing`, which is 0 throughout.
  - Each group is split by `instrument` (demand = *giro*, savings = *tabungan*, time = *deposito*), then by currency,
    and for time deposits by tenor (`1m, 3m, 6m, 12m, gt12m`).
  - Old Tabel 14 rows: *Giro iB - Akad Wadiah* (`fund_type=all_labelled_wadiah`), savings (wadiah/mudharabah),
    *Deposito iB - Akad Mudharabah* by tenor, and the total.
- `series = harmonised` is one consistent set over 2009-2025 (`series_code`):

  | series_code | content | new format (2014-06+) | old format (2009-01..2014-05) |
  |---|---|---|---|
  | `h_total` | total DPK | sum of the three Tabel 22 groups | Tabel 14 Total |
  | `h_demand` | all demand deposits | wadiah + mudharabah giro | *Giro iB - Akad Wadiah* (see note) |
  | `h_demand_w` | **wadiah demand deposits** | Tabel 22 wadiah giro | not separable |
  | `h_demand_m` | mudharabah demand deposits | giro of both investment groups | not separable |
  | `h_sav`, `h_sav_w`, `h_sav_m` | savings: all, wadiah, **mudharabah** | Tabel 22 | Tabel 14 |
  | `h_time` | **mudharabah time deposits** | Tabel 22 | Tabel 14 |
  | `h_time_1m … h_time_gt12m` | **time deposits by tenor** | Rupiah + FX, both investment groups | Tabel 14 |

  In the new format a harmonised value is only formed when all its components are present (no partial sums).
- Coverage:
  - Harmonised: BUS_UUS 2009-01..2025-06 (187 months).
  - BUS and UUS: 2014-06..2025-06 (122 months).
  - Reported rows: same coverage.
- **Old *Giro iB - Akad Wadiah* is all demand deposits, not only wadiah.**
  - On the 12 overlap months it equals new wadiah + mudharabah giro exactly (gap 0.000).
  - It exceeds new wadiah giro by 1,632-2,058 Rp bn on average (13-20%).
  - So wadiah demand deposits as such start in 2014-06. Before that, use `h_demand`.
- Jan 2025: the published Rupiah time-deposit row (non-profit-sharing group) equals the sum of the 1-12 month rows
  only. The >12-month row (1,049.5 Rp bn for BUS_UUS) is outside it. It is kept as published and noted.
  `h_time_*` are built from the tenor rows, so they are not affected.

### (c) `data/clean/ojk_deposit_returns.csv`: equivalent rate of return on deposits
9,971 rows. Key: `date, bank_type, fund_type, instrument, currency, tenor`. Value: `rate_pct` (percent per year,
*tingkat imbalan / ekuivalen bagi hasil*).

- New Tabel 17 section I, for BUS, UUS and BUS_UUS, 2014-06..2025-06:
  - Giro iB wadiah, giro iB mudharabah, tabungan iB wadiah, tabungan iB mudharabah and deposito iB mudharabah.
  - Each at the instrument level, then **Rupiah** and FX.
  - The deposito is also split by tenor 1, 3, 6, 12 and >12 months, in **Rupiah** and FX.
  - Plus the all-DPK rate (`fund_type=all`).
- Old Tabel 36, BUS_UUS, 2009-01..2014-05:
  - Giro iB, tabungan iB (not split by contract) and deposito iB by the same 5 tenors.
  - `currency=unspecified`.
- 479 FX cells are exactly 0 and flagged `zero_published`. No Rupiah cell is 0.

### (d) `data/clean/ojk_margins.csv`: financing rates
46,546 rows. Key: `date, bank_type, dimension, category_code, sub_category, currency`. Value: `rate_pct`.

- `dimension = contract`:
  - New Tabel 17 section II gives the equivalent rate by contract (same codes as (a)) in all currencies, Rupiah and
    FX, for BUS, UUS and BUS_UUS from 2014-06.
  - Old Tabel 36 gives mudharabah, musyarakah, murabahah, salam, istishna, ijarah and qardh, BUS_UUS, 2009-01..2014-05.
- `dimension = use_size` (new Tabel 18), 2014-06+, BUS, UUS and BUS_UUS:
  - `category_code`: working_capital, investment, consumption.
  - `sub_category`: debtor size (`all`, `msme` = UMKM, `non_msme`).
  - Working capital and investment are split by size, each in all currencies, Rupiah and FX. Consumption is
    published only for all sizes (with Rupiah/FX).
- `dimension = sector` (new Tabel 19), 2014-06+:
  - 18 business sectors and 6 non-business categories (same classification as the sector file's new19).
  - All currencies, Rupiah and FX.
  - No total row is published.
- **Margins by use, size and sector are not published in the old format.** They start in 2014-06.
- 11,127 cells are exactly 0 (`zero_published`): FX rows, salam, `other_profit_sharing`, syndicated and executing
  ijarah, and *badan internasional*.
- 36 cells above 50% are kept but flagged `outlier_gt50pct`. They are small categories:
  - *jasa perorangan yang melayani rumah tangga*: 31-55% in almost every month.
  - *badan internasional*: 2015-05..2016-04.
- Other notable values, kept as published:
  - Rupiah channeling ijarah is 30-35% in 2018-05..2021-01.
  - The old ijarah rate is about 0.1-1% until the method change in Oct 2012 (footnote 1 of Tabel 36).

### (e) `data/clean/ojk_aggregates.csv`: headline aggregates
5,350 rows. Key: `date, bank_type, indicator`. Columns: `value` and `unit`.

| indicator | content | BUS, UUS | BUS_UUS |
|---|---|---|---|
| `total_assets_rp_bn` | Tabel 2 *Total Aset*; old Tabel 6 TOTAL AKTIVA | 2014-06+ | 2009-01+ |
| `financing_rp_bn` | total financing, contracts table (Tabel 11 / old 18) | 2014-06+ | 2009-01+ |
| `npf_rp_bn` | NPF, Tabel 11 *Total NPF*; old Tabel 26 *Non Lancar* | 2014-06+ | 2009-01+ |
| `npf_gross_pct_computed` | 100 x NPF / financing | 2014-06+ | 2009-01+ |
| `npf_gross_pct_reported` | Tabel 1a/1b; old Tabel 38 | 2014-06+ | 2009-01..2014-05 |
| `npf_net_pct_reported` | Tabel 1a/1b | 2014-06+ | none |
| `dpk_rp_bn` | Tabel 6/6a/6b *Dana Pihak Ketiga*; old Tabel 14 Total | 2014-06+ | 2009-01+ |
| `fdr_pct_computed` | 100 x financing / DPK | 2014-06+ | 2009-01+ |
| `fdr_pct_reported` | Tabel 1a/1b; old Tabel 38 | 2014-06+ | 2009-01..2014-05 |
| `fdr_financing_nonbank_rp_bn`, `fdr_dpk_rp_bn` | FDR numerator and denominator, Tabel 1 | 2014-06+ | none |
| `financing_nonbank_rp_bn` | Tabel 6: profit-sharing + receivables + ijarah to non-bank parties + salam | 2014-06+ | 2014-06+ |
| `car_pct`, `roa_pct`, `bopo_pct` | Tabel 1; old Tabel 38 (old CAR is BUS only) | 2014-06+ | ROA and BOPO 2009-01..2014-05 |
| `number_of_banks` | Tabel 2: BUS count; number of conventional banks with a UUS | 2014-06+ | none |

- BUS DPK in Feb 2022 comes from the Tabel 22 sum, because Tabel 6a has no column for that month. It is flagged
  `fallback_tabel22_sum`.
- The 2022 columns of Tabel 6a carry no month labels. They are mapped as Jan, Mar..Dec 2022 by the identity
  BUS = Tabel 6 − Tabel 6b, which holds with a gap of 0.000 on every 2022 month carried by Tabel 6a (DPK and non-bank
  financing).
- Old TOTAL AKTIVA includes inter-office assets. It nevertheless matches new *Total Aset* to within 114 Rp bn
  (relative 4.5e-4) on the overlap months.

## 4. Coverage summary

Every series below is missing 2023-01..2023-11 (no archived 2023 edition).
- BUS and UUS separately: all five outputs 2014-06..2025-06, 122 months.
- BUS_UUS:
  - contracts (all currencies), harmonised deposits, deposit returns, contract margins, assets, financing, NPF
    (Rp bn and %), DPK and computed FDR: 2009-01..2025-06, 187 months.
  - Rupiah contracts (Tabel 12), margins by use, size and sector, and NPF by contract: 2014-06..2025-06.
- Not available from open OJK sources:
  - a BUS/UUS split before 2014-06, for any of these tables;
  - wadiah vs mudharabah demand deposits before 2014-06;
  - deposit returns by contract for giro and tabungan before 2014-06;
  - multijasa as a separate contract.

## 5. Breaks and comparability

1. **Format switch at 2014-06.**
   - Volumes are continuous. At the overlap, contract totals, deposit totals, savings, time deposits and tenors
     match to within 0.5 Rp bn (section 7).
   - **Rates have level breaks.**
     - Old deposit tenor rates (`currency=unspecified`) track the deposit-weighted Rupiah+FX average of the new
       rates more closely than the Rupiah rate alone. Mean absolute gaps are 0.12-0.47 pp against 0.16-0.74 pp for
       Rupiah alone, for tenors from 1 to 12 months.
     - Old giro and tabungan rates are on average 0.6-0.9 pp below the new Rupiah wadiah/mudharabah rates. For
       savings vs wadiah the sign varies (−1.25 to +0.46 pp).
     - The **old mudharabah financing rate is about 8 pp above the new one** (mean gap 7.8-8.1 pp). This looks like a
       definitional change.
     - Other contract rates differ by 0.1-1.2 pp on average.
   - Treat 2014-06 as a break (dummy or separate segments) in any rate regression.
2. **May 2014: LSMK revision.** The old tables carry the footnote "Revisi data BUS-UUS mulai bulan Mei 2014
   berdasarkan LSMK". The 2015_06 edition revised Mar-May 2014; for example, BOPO for May 2014 is 91.82 against 76.5
   in the 2014_12 edition.
3. **Ijarah rate method change in Oct 2012** (old Tabel 36 footnote).
4. Old *Akad Musyarakah* includes other profit-sharing financing (sections 3a and 7).
5. Conversions and mergers move volumes between BUS and UUS, as documented in `data_ojk_sector.md` and
   `ojk_conversion_events.csv`:
   - Bank Aceh, 2016-09;
   - Bank NTB, 2018-09;
   - BSI merger, 2021-02 (no BUS/UUS shift);
   - Bank Riau Kepri, 2022-08.
6. Nov 2024 (both BUS and UUS): Rupiah 12-month and >12-month time deposits jump to 2-37 times their Oct and Dec
   levels (for example, BUS >12-month 19,900.8 against 2,713.0 and 538.1), and the 1-month row drops. The blocks are
   internally consistent (BUS + UUS = BUS+UUS), so this is kept as published, but it is very likely a reporting
   anomaly. The tenor totals are unaffected.

## 6. Corrections of source errors (61 cells, all flagged, published value in `note`)

Each correction is derived from an accounting identity, either between blocks (BUS + UUS = BUS+UUS) or within a
block (components = total).

| month | cells | problem | fix |
|---|---|---|---|
| 2019-07 | UUS, 28 deposit rows (Tabel 22b) | the July column repeats June 2019 in every row; UUS DPK disagrees with Tabel 6b by 1,524.2 | Tabel 22 − Tabel 22a |
| 2017-11 | BUS_UUS Rupiah time deposits (Tabel 22) | published 80.069: the BUS FDR (80.069046%) pasted into the cell | Tabel 22a + 22b = 184,507.9, which equals the sum of the tenor rows |
| 2017-11 | BUS_UUS 3-month Rupiah return (Tabel 17); construction margin, all currencies (Tabel 19); consumption FX margin (Tabel 18) | same 80.069 figure | set to missing |
| 2020-06 | BUS_UUS and UUS FX 1-month time deposits | published 11.690 and 5.253 (decimal-separator error) | x1000; FX tenors then equal the FX total to within 10.1 |
| 2022-05 | BUS_UUS FX 1-month time deposits | 13,802.5 against 22a + 22b = 10,739.2; tenors exceeded the FX total by 3,063.2 | 22a + 22b |
| 2024-12 | UUS Rupiah 1-month and 6-month time deposits | the 6-month row repeats the 3-month row (31,950.1) and 1-month is short by 20,549.2 | Tabel 22 − 22a (48,779.7; 11,400.9) |
| 2021-10 | UUS Rupiah murabahah, receivables and total (Tabel 12b) | 1,370.9 below Tabel 12 − 12a; the implied UUS FX murabahah would be 1,540 against about 170 in Sep and Nov | Tabel 12 − 12a |
| 2010-02 | BUS_UUS NPF, old Tabel 26 | *Non Lancar* 1,053.7 omits *Macet*; components sum to 2,242.7 | sum of components; the ratio then matches Tabel 38 (gap 0.008 pp) |
| 2011-01..2012-06 (17 months) | old >12-month deposit rate | 33.7-50.7% while the other tenors are 4-9% and the stock is Rp 5-50 bn | set to missing |
| 2010-04..06 | old murabahah (3 months), mudharabah (Apr) and ijarah (Jun) financing rates | 73-121% against 15-19% (0.5% for ijarah) in neighbouring months | set to missing |

Not corrected, because the identity cannot tell which side is wrong. Each is kept as published and documented
here:

- **Deposits, new format:** remaining gaps of at most 300 Rp bn (relative 1.6e-3).
  - 2017-07: UUS rows; BUS + UUS − BUS_UUS reaches 109.5 on the total.
  - 2016-08 and 2021-03: Rupiah + FX vs instrument rows, up to 145.
  - 2025-04: the FX tenor split differs across blocks, by up to 878 on the 3-month row. Each block adds up
    internally.
- **Tabel 22 total vs Tabel 6 DPK:** UUS is about 410 Rp bn below Tabel 6b from 2019-11 to 2020-04 (max 413.7), and
  BUS is 100.3 below in 2017-11. The Tabel 6 value is used for `dpk_rp_bn`.
- **Tabel 1 FDR denominator vs Tabel 22:** gaps of 5,700-6,400 Rp bn in 2014-10 (BUS), 2021-11 (BUS), 2025-02 and
  2025-04 (UUS). Reported FDR is kept as published; the computed FDR uses Tabel 6.
- **Ijarah components vs ijarah total:** max 16.9 (all currencies, 2020-05) and 87.6 (Rupiah UUS, 2019-07). NPF
  components: max 3.4 (all currencies) and 14.3 (Rupiah).
- **Old DPK in Mar 2012:** Tabel 14 total 119,638.7 against old Tabel 6 114,317.7. Tabel 14 is kept because its
  rows add up to it, and the Tabel 38 FDR (87.1%) is consistent with it. Noted on the row.

## 7. Validation (numbers printed by the build)

**Column-to-month mapping**
- Year-end columns equal their December column: max |gap| = 0 in every table and edition (for example, 538 cells in
  Tabel 11 of 2025_06).
- Two December columns that repeat November were replaced by the year-end column: old Tabel 18, 14 and 26 for
  Dec 2012.
- The June 2015 column of the 2015_06 edition repeats May in every row of Tabel 6, 14, 18, 26 and 36, and was
  dropped.
- Stale-column scan of the final outputs (a month equal to the previous one in all non-zero rows): 0 found after
  the corrections.

**Revisions between editions (overlapping cells that differ by more than 1e-6)**

| comparison | contracts | deposits | returns | margins | aggregates |
|---|---|---|---|---|---|
| 2024_12 vs 2025_06 | 0 of 19,931 | 0 of 15,622 | 0 of 8,658 | 0 of 41,934 | 0 of 3,846 |
| 2018_12 vs 2025_06 | 0 of 9,887 | 0 of 7,729 | 0 of 4,290 | 0 of 20,776 | 0 of 1,072 |
| 2014_12 vs 2015_06, before 2014-06 | 0 of 90 | 6 of 110 | 0 of 70 | 0 of 70 | 2 of 160 |

The 6 deposit cells are the garbled 2014-03 and 2014-05 tenor rows (max 74,978). The 2 aggregate cells are the
revised May 2014 BOPO (15.3 pp) and a 0.033 difference in Dec 2009 assets.

**Accounting identities after correction (Rp bn)**
- **Contracts, all currencies:**
  - Sum of contracts vs total: max 0.0000 over 431 date x bank-type cells.
  - Profit-sharing and receivables components vs group: 0.0000.
  - BUS + UUS vs BUS_UUS total: 0.0000 over 122 months.
  - NPF sum vs total: max 0.024.
- **Contracts, Rupiah:**
  - Sum vs total: 0.0000.
  - BUS + UUS vs BUS_UUS: 0.0000 (it was 1,370.9 before the Oct 2021 correction).
  - NPF: max 0.75.
- **Deposits:**
  - Groups vs instruments: 0 for BUS_UUS wadiah, BUS non-profit-sharing and UUS wadiah; max 60.1 elsewhere
    (BUS wadiah, 2017-07).
  - Harmonised demand + savings + time vs total: max 60.1, mean 0.18, over 431 cells.
  - Savings wadiah + mudharabah vs savings: 0.0000.
  - Tenor sum vs time deposits, new format: max 1,049.7 (the Jan 2025 >12-month case), mean 8.7.
  - Tenor sum vs time deposits, old format: max 0.41 over 65 months.
  - BUS + UUS vs BUS_UUS total DPK: max 109.5 (2017-07), mean 1.0. It was 1,524.2 before the Jul 2019 correction.
  - Sum of Tabel 22 groups vs Tabel 6 DPK: max 413.7, mean 13.8, over 365 cells; 16 cells have a gap above 1.
- **Old format, 2009-01..2014-05:**
  - Tabel 18 contracts vs total: 0.0000.
  - Tabel 14 giro + tabungan + deposito vs total: 0.0000.
  - Old Tabel 18 total vs old Tabel 6 *Pembiayaan*: max 178.4 (Apr 2014); only one month has a gap above 0.01.
  - Old Tabel 14 total vs old Tabel 6 DPK: max 5,321.0 (Mar 2012, see section 6); 2 months have a gap above 1.
- **Aggregates:**
  - Total assets BUS + UUS vs BUS_UUS: max 18.0 (2017-07); DPK, financing and NPF: 0.0000.
  - Reported FDR vs its own Tabel 1 components: max 0.98 pp.
  - Reported gross NPF vs computed: max 0.020 pp over 309 cells, both formats; it was 2.52 pp before the Feb 2010
    correction.
  - Reported FDR vs computed FDR: max 5.78 pp (Apr 2014, old format), mean 0.054.
  - Tabel 6 non-bank financing vs Tabel 11 total: max 2,137.5 (Dec 2022), relative 1.25e-2. These are different
    concepts: Tabel 6 is financing to non-bank parties only.

**Old format vs new format on overlapping months (BUS_UUS; 2014_12: 7 months, 2015_06: 12 months)**
- **Contracts** (old Tabel 18 vs new Tabel 11), |gap| in Rp bn:
  - mudharabah, murabahah, salam, istishna, ijarah, qardh and total: 0.000.
  - musyarakah: max 120.7, mean 53.3. The gap is exactly new `other_profit_sharing`: old musyarakah − (new
    musyarakah + other profit-sharing) is at most 6e-7 over 12 months. The gap is 120.7 in 2014-07 and falls to 1.3
    in 2015-05; the check is in `code/py/ojk_mech_ovl2.py`.
- **Deposits** (2015_06 edition vs harmonised series), max |gap| in Rp bn:
  - total 0.26, savings 0.26, time 0.000;
  - tenors 0.36-0.48;
  - old giro vs all giro 0.000;
  - old giro vs wadiah giro: mean 2,058 (the label issue above).
  - The 2014_12 edition's tenor split fails, with max gaps of 5,486-46,744, which is why the 2015_06 edition is
    preferred.
- **Deposit returns:**
  - Old tenor rates vs new Rupiah rates: mean |gap| 0.19-0.65 pp for 1-12 months, 1.76 pp for >12 months.
  - Against new FX rates: 3.1-4.1 pp.
  - Against the deposit-weighted Rupiah+FX average: 0.12-0.40 pp.
  - Old giro vs new Rupiah giro wadiah: 0.62 pp; vs mudharabah: 0.91 pp.
  - Old tabungan vs new Rupiah wadiah: 0.68 pp; vs mudharabah: 0.90 pp.
- **Financing rates** (old Tabel 36 vs new Tabel 17 all-currency), mean |gap| in pp:
  - mudharabah 7.77, musyarakah 0.77, murabahah 1.21, istishna 0.50, ijarah 0.07, qardh 0.81.
- **Aggregates:**
  - Assets: max 113.9 (relative 4.5e-4).
  - DPK: max 124.2.
  - Financing: max 0.16.
  - NPF: max 0.58.
  - NPF %: max 0.17 pp.
  - FDR %: max 4.1 pp (one month).
  - CAR (BUS): max 0.44 pp.

**Independent spot check (`check_ojk_mechanisms.py`)**
- 250 random rows per output (contracts, reported deposits, returns, margins; seed 20261029) were re-read from the
  workbooks with openpyxl/xlrd using `source_cell`.
- Result: 1,000 of 1,000 match. The one corrected row in the sample matched its published value as quoted in
  `note`.
- The printed workbook labels agree with `label_id`.

**Output sanity**
- No duplicate keys in any file.
- Negative values: none, except one old ijarah rate of −0.005% (Apr 2014, flagged).
- Missing values:
  - contracts: 26 financing cells;
  - returns: 22 (18 corrected to missing, 4 published "-");
  - margins: 83 (7 corrected, 76 "-");
  - aggregates: 0.

## 8. Files

- Outputs:
  - `data/clean/ojk_contracts.csv`
  - `data/clean/ojk_deposits.csv`
  - `data/clean/ojk_deposit_returns.csv`
  - `data/clean/ojk_margins.csv`
  - `data/clean/ojk_aggregates.csv`
- Scripts:
  - `code/py/build_ojk_mechanisms.py` (build and validation).
  - `code/py/check_ojk_mechanisms.py` (independent cell check).
- Small inspection helpers written while auditing, not part of the build:
  - by this run: `code/py/ojk_mech_sheets.py`, `ojk_mech_grid.py`, `ojk_mech_cols2.py`, `ojk_mech_show.py`,
    `ojk_mech_diag.py`, `ojk_mech_oldrev.py`, `ojk_mech_t26.py`, `ojk_mech_ovl_rates.py`, `ojk_mech_ovl2.py`;
  - by the interrupted run: the other `ojk_mech_*.py` files.
- Running the scripts creates `code/py/__pycache__`.
