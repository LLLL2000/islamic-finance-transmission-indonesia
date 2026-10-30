# DJPPR sovereign investor base (supplementary module)

Builder: `djppr`. Build script: `code/py/build_djppr.py`. It reruns end to end from the raw files:
`python -I code/py/build_djppr.py`. Add `--fetch` to GET any missing raw file from web.archive.org first.
The script prints every validation number quoted below. Two consecutive runs produced byte-identical CSVs
(md5 `92cb42d5…` daily, `abb72174…` monthly).

Outputs

| file | content | rows |
|---|---|---|
| `data/clean/djppr_holdings_daily.csv` | daily holdings of tradable Rupiah SBN by holder x instrument (SUN, SBSN, SBN = SUN + SBSN), 2015-12-01 to 2022-06-28 | 77,088 |
| `data/clean/djppr_nonresident_maturity_monthly.csv` | monthly non-resident holdings by maturity bucket x instrument, 2017-01 to 2022-05 | 1,170 |

## 1. Sources

All files are Internet Archive copies of files that DJPPR (Directorate General of Budget Financing and Risk
Management, Ministry of Finance) published as open downloads under
`https://djppr.kemenkeu.go.id/uploads/files/dmodata/in/5Statistik/`. I found them with the CDX API, using
`http://web.archive.org/cdx/search/cdx?url=djppr.kemenkeu.go.id/uploads/files/dmodata/in/5Statistik/*&output=json&limit=2000`.
The unlimited query returned HTTP 504 three times and worked once `limit=2000` was added. That listing has 160
rows.

Each file was fetched with a plain GET of `https://web.archive.org/web/<ts>id_/<original URL>`. The script checks
the SHA-1 of every local file against the CDX digest, and all 12 match. Files marked "new" were downloaded in
this run. The other files were already in `data/raw/djppr/`, and their digests show they are byte-identical to
the archived captures listed here.

| local file (`data/raw/djppr/`) | wayback ts | original URL (after `.../5Statistik/`) | used for |
|---|---|---|---|
| DJPPR_SBN_Ownership_2007_2015.xlsx | 20220701010702 | `6Kepemilikan_SBN_yang_dapat_Diperdagangkan/Kepemilikan%20SBN%20Domestik%20yang%20Dapat%20Diperdagangkan_2007-2015_Updates.xlsx` | daily 2015-12-01..30, sheet `Des` |
| DJPPR_SBN_Ownership_Daily_2016.xlsx | 20220701010650 | `6Kepemilikan_SBN_yang_dapat_Diperdagangkan/122016/Kepemilikan%20SBN%20Harian%20-SBNOwnership%20Daily(18).xlsx` | daily 2015-12-31 + 2016 |
| DJPPR_SBN_Ownership_Daily_2017.xlsx (new) | 20220701010639 | `6Kepemilikan_SBN_yang_dapat_Diperdagangkan/122017/SBN%20Ownership%20Daily%202017.xlsx` | daily 2017 |
| DJPPR_SBN_Ownership_Daily_2018.xlsx (new) | 20220701010559 | `6Kepemilikan_SBN_yang_dapat_Diperdagangkan/122018/SBN%20Ownership%20Daily%202018_Desember(1).xlsx` | daily 2018 |
| DJPPR_SBN_Ownership_Daily_2019.xlsx (new) | 20220701010625 | `6Kepemilikan_SBN_yang_dapat_Diperdagangkan/2019/SBN%20Ownership%20Daily%202019_desember%20(1).xlsx` | daily 2019 |
| DJPPR_SBN_Ownership_Daily_2020.xlsx (new) | 20220701010611 | `6Kepemilikan_SBN_yang_dapat_Diperdagangkan/2020/SBN%20Ownership%20Daily%202020_Desember_(1).xlsx` | daily 2020 |
| DJPPR_SBN_Ownership_Daily_2021.xlsx | 20220701010547 | `6Kepemilikan_SBN_yang_dapat_Diperdagangkan/2021/SBN%20Ownership%20Daily%202021_31%20Desember.xlsx` | daily 2021 |
| DJPPR_SBN_Ownership_Daily_2022H1.xlsx | 20220701010536 | `6Kepemilikan_SBN_yang_dapat_Diperdagangkan/2022/SBN%20Ownership%20Daily%202022_Jun(15).xlsx` | daily 2022-01..06-28 |
| DJPPR_SBN_NonResident_byMaturity_2017_May2022.xlsx | 20220701010731 | `Kepemilikan_SBN_Rupiah_oleh_Asing/Posisi%20Kepemilikan%20SBN%20oleh%20Non-Residen-%20Per%20Sektor%20Maturity_2017%20-%20Mei%202022.xlsx` | monthly output |
| DJPPR_SBN_NonResident_byMaturity_2008_2016.xlsx | 20220701010741 | `Kepemilikan_SBN_Rupiah_oleh_Asing/Posisi%20Kepemilikan%20SBN%20oleh%20Non-Residen%20-%20Per%20Sektor%20Maturity_2008-2016.xlsx` | not exported (see 3.4) |
| DJPPR_Outstanding_SBN_2021.xls | 20220726143658 | `1Posisi_Utang/2Posisi_SUN/2021/Outstanding%20SBN%20as%20of%20December%2031,%202021.xls` | external check only |
| DJPPR_SBN_Ownership_2003_2006.xlsx (new) | 20220701010715 | `6Kepemilikan_SBN_yang_dapat_Diperdagangkan/Kepemilikan%20SBN%20Domestik%20yang%20Dapat%20Diperdagangkan_2003-2006.xlsx` | downloaded only, outside the window |

To form an archived URL, put `https://web.archive.org/web/<ts>id_/https://djppr.kemenkeu.go.id/uploads/files/dmodata/in/5Statistik/`
in front of the path in the table. The CDX listing has no other captures of the daily-ownership folder: one file
per year from 2016 to 2022, with the 2022 file ending on 28 June 2022. Daily data after June 2022 is therefore
not available from this source.

## 2. Daily holdings: `djppr_holdings_daily.csv`

### Source layout
Each yearly workbook has one sheet per month. The sheet names change across years (`JAN`, `Jan'20`, `Okt `
with a trailing space, `Agustus`, and so on).

- Block A, "Dalam Triliun Rupiah", holds the values. Row 4 (row 3 in 2016 `OCT`) gives the dates. The next row
  gives a 3-column group per date: `SUN`, `SBSN`, `TOTAL`.
- Block B holds the same table as percentage shares. It is used only for check V6.
- An English-label copy of the table sits to the right, headed `INSTITUTION`. It has no values. Its labels are
  kept in `holder_label_en_djppr`.
- Some sheets have stray scratch numbers to the right of that copy, outside the table. They are ignored and
  listed in the log: 2017 `NOV` col CC, 2018 `Sept` col BM, 2020 `Juni`/`September`/`Desember`, 2021
  `Mei`/`Juni`.

The script locates labels by text and stops with an error on any unknown holder label, non-date header,
non-numeric value, or missing block. Six dates appear in two sheets, because some sheets open with the
previous month's last day. The two copies are identical (max abs difference 0.000000), and the copy from the
date's own month is kept.

The 2007-2015 file's `Des` sheet gives daily data for December 2015. It reports **SBN only, with no SUN/SBSN
split and no conventional/Islamic bank split**. It also lists `Sekuritas` (securities companies) separately.
Rows for 2015-12-01..30 come from this file, with `instrument = SBN` and `instrument_split_available = False`.
2015-12-31 comes from the first column of the 2016 file, which has the split. On 2015-12-31 both files agree
on all 12 comparable holders: max abs gap 0.000000 Rp tn [V0]. The comparison uses Lain-lain + Sekuritas from
the 2015 file against Lain-lain from the 2016 file.

### Columns
`date` (daily, YYYY-MM-DD); `holder` (harmonised code); `holder_en`; `holder_label_id` (original Indonesian
label); `holder_label_en_djppr` (DJPPR's own English label); `level` (0 total, 1 sector, 2 sub-sector,
3 memo); `parent`; `row_type`; `instrument` (`SUN` conventional government bonds, `SBSN` sukuk negara,
`SBN` = TOTAL column = SUN + SBSN); `holdings_rp_tn` (Rp trillion, face value as reported); `instrument_split_available`;
`qa_flag`; `source_file`; `source_sheet`; `source_cell`.

`row_type` takes three values:
- `reported`: additive. Level-2 rows add up to their level-1 parent, and level-1 rows add up to total.
- `memo`: an "of which" line, not additive.
- `derived`: built by the script, not in the source.

### Harmonised holders

| holder | Indonesian label(s) | notes |
|---|---|---|
| total | TOTAL | tradable Rupiah SBN outstanding |
| banks | BANK* | *includes SBN used in monetary operations with BI (repo) |
| banks_conventional | Bank Konvensional | |
| banks_islamic | Bank Syariah | SUN is always 0. Only SBSN is ever non-zero (V9). |
| state_institutions | Institusi Negara (2015 file: Institusi Pemerintah) | equals bi_net on every date |
| bi_net | Bank Indonesia (net, tidak termasuk SBN yang digunakan dalam operasi moneter dengan Bank) | |
| bi_gross (memo) | - Bank Indonesia (gross) | |
| bi_monetary_ops (memo) | - SBN yang digunakan dalam operasi moneter dengan Bank | = bi_gross - bi_net; can be negative (see 4) |
| nonbanks | NON-BANK | |
| mutual_funds | Reksadana | |
| insurance | Asuransi | reported to 2019-12-31 only |
| pension_funds | Dana Pensiun | reported to 2019-12-31 only |
| insurance_pension | Asuransi dan Dana Pensiun | reported from 2020-01-02. For 2015-12..2019-12 it is **derived** as insurance + pension_funds. |
| nonresidents | Non Residen (2015 file: Asing) | |
| nonresidents_foreign_gov_cb (memo) | - Termasuk Pemerintah & Bank Sentral Negara Asing | |
| individuals | Individu | |
| others | Lain-lain | securities companies, corporates, foundations. For Dec 2015 it is **derived** as Lain-lain + Sekuritas. |
| securities_companies, others_excl_securities (memo) | Sekuritas, Lain-lain | Dec 2015 file only |

**Classification break:** insurance and pension funds are merged from January 2020. For a consistent
2015-12..2022-06 series, use `insurance_pension`. The separate `insurance` and `pension_funds` rows stop at
2019-12-31. Footnote wording varies cosmetically: in the 2016 `JUN`-`DEC` sheets the non-resident footnote ends
with "dari internasional". The 2015 file's BI footnote says that SUN repo to BI has been included since
8 Feb 2008. Its "Bank Indonesia" value on 2015-12-31 equals the 2016 file's *net* figure, so it is mapped to
`bi_net`.

### Coverage
- 1,596 trading dates from 2015-12-01 to 2022-06-28, in 79 months. There are no weekend dates.
- Days per month range from 13 (2018-06) to 23.
- Every gap longer than 4 days falls on Eid/Christmas/New Year holidays: 2016-07-01→07-11, 2018-06-08→06-20,
  2019-05-31→06-10, 2022-04-28→05-09, and others (V8c). I did not check the dates against an official holiday
  calendar.
- 2015-12 is SBN only (19 dates). The SUN/SBSN split starts 2015-12-31, with 1,577 dates.

### QA repairs applied (all flagged in `qa_flag`, which records the source value)

Before repair, as published, the identities hold almost everywhere. The exceptions are a few TOTAL-column cells
and some blank cells:

1. **SBN cell inconsistent with SUN + SBSN: 11 cells, replaced by SUN + SBSN.** In each case the SUN and SBSN
   cells satisfy their own adding-up checks, and the TOTAL cell is stale.
   - 2017-01-03, `banks_conventional` and `banks_islamic` (2017 `JAN` D7:D8). The TOTAL cells repeat the
     2015-12-31 values 334.908 and 15.162. This is why V2 fails by 81.29 Rp tn.
   - 2017-03-29, `bi_monetary_ops` (125.755, should be 104.535). This is why V3b fails by 21.22.
   - 2016-09-09..09-21, `nonresidents_foreign_gov_cb`. TOTAL stays at 117.669 while SUN moves.
2. **Blank Islamic-bank SUN cell where the bank's TOTAL equals its SBSN: 53 cells, set to 0.** They fall
   between 2019-12-05 and 2022-04-13.
3. **2016-11-01, `nonresidents_foreign_gov_cb` SBSN is blank** (2016 `NOV` C17). Kept missing. Its SBN cell
   equals SUN only, so that is also set to missing. Neighbouring days show about 4.9 Rp tn.
4. **2022-06-28, the last column of the 2022 file: SBSN not filled in.** SBSN cells are blank or 0, and every
   TOTAL equals SUN. All SBSN and SBN values for that date are set to missing (30 cells). The SUN values are kept
   and pass V1/V2/V3/V4.

After these repairs, 32 values are missing: the 30 on 2022-06-28 plus the 2 for the 2016-11-01 memo row. 96 rows
carry a `qa_flag`.

### Validation (daily). Tolerance is 0.0015 Rp tn, against 3-decimal display rounding.

| check | before repair | after repair (output) |
|---|---|---|
| V1 banks + state_institutions + nonbanks = total (per date x instrument) | max gap 0.000000, 0/4,788 | 0.000000, 0/4,788 |
| V2 banks_conventional + banks_islamic = banks | max 81.294, 1/4,731 (2017-01-03 SBN) | 0.000000, 0/4,731 |
| V3a bi_net = state_institutions | 0.000000, 0/4,788 | 0.000000 |
| V3b bi_gross - bi_monetary_ops = bi_net | max 21.220, 1/4,731 (2017-03-29 SBN) | 0.000000, 0/4,731 |
| V4 mutual funds + insurance&pension + non-residents + individuals + others = nonbanks | max 0.010, 2/4,788 | **0.010, 2/4,788**: 2018-04-05 SUN and SBN, components exceed NON-BANK by Rp 10 bn. Unresolved, left as published. |
| V5 SUN + SBSN = SBN, all holders x dates | max 74.214, 11/24,628 | 0.000000, 0/25,601 |
| V5b SUN + SBSN = SBN for the total row | 0.000000, 0/1,577 | 0.000000, 0/1,577 |
| V6 % block vs value/total x 100 | 46 of 73,518 cells off by more than 0.01 pp (max 19.11 pp): bi_net SBSN 2016-09-08/09, nonresidents SBSN 2016-10-07..11, foreign_gov_cb SBSN 2016-11..12. 210 % cells are blank/#REF!/#DIV/0!. The Rp tn block is internally consistent on those dates, so the % block is the faulty one. It is not used in the output. | |
| V10 re-read of 400 random unflagged output rows from the cited workbook cell | | 0 mismatches |

**External check (total outstanding per instrument).** The holdings TOTAL by instrument was compared with
DJPPR's *Outstanding SBN 2021* workbook. Each of its 51 sheets is one as-of date. The comparison uses section
"I. Tradable Securities", lines "Total Rupiah Denominated" of SUN and of SBSN. For the 50 dates that are
ownership dates, the max abs gap is 0.0000 Rp tn for SUN and 0.0004 Rp tn for SBSN, with 0 of 100 cells above
0.0015. The 2021-03-11 sheet has no ownership column, because that day was a holiday. The holders therefore sum
to total outstanding tradable Rupiah SUN and SBSN.

## 3. Monthly non-resident holdings by maturity: `djppr_nonresident_maturity_monthly.csv`

### Source layout
`DJPPR_SBN_NonResident_byMaturity_2017_May2022.xlsx` has one sheet per year (`2017` … `2022`; `2021 ` has a
trailing space). Each sheet has three blocks: SBN, SBSN, SUN. In 2018 the order is SBN, "SUN", SBSN. Each block
has the header "Sektor/Sector", one column per month (the header is the observation date), and rows `0-1`,
`>1-2`, `>2-5`, `>5-10`, `>10`, `Total`. Units are **Rp billion**. DJPPR calls the buckets "Sektor Maturity".
They are presumably years of remaining maturity, but the file does not say whether maturity is remaining or
original. That is an assumption.

### Columns
`date` (first day of month); `obs_date` (date in the block header as printed); `instrument`; `maturity_bucket`
(`y00_01`, `y01_02`, `y02_05`, `y05_10`, `y10_plus`, `total`); `maturity_label_id`; `maturity_en`;
`holdings_rp_bn` (cleaned); `holdings_rp_bn_source` (as published); `daily_match_date` (the date in the daily
file whose non-resident holdings equal this Total within 0.5 Rp bn, preferring `obs_date`);
`gap_vs_daily_last_trading_day_rp_bn` (Total minus daily non-resident holdings on the month's last trading day);
`qa_flag`; `source_file`; `source_sheet`; `source_cell`.

### Problems found and how they are handled
1. **Two working columns dropped (2019 sheet).**
   - Col H: the SBSN header reads `MEI CEK`. Its SBSN Total, 13,624.759, equals the daily non-resident SBSN on
     2019-05-31. Its SBN cell is June SUN plus that figure.
   - Col O: the SBSN header reads `Nov cek`. Its SBSN Total is 25,660.255, which matches no daily value in
     Nov/Dec 2019.

   Both columns duplicate a date in the SBN and SUN blocks. With them dropped, each month appears exactly once.
2. **2018: the block titled SUN actually holds SBN, and the SBN block double-counts SBSN. Corrected; 144 rows
   flagged.**
   - The Indonesian title says "Kepemilikan SUN …". The English subtitle says "Ownership of IDR Tradable
     Government Securities (SUN)", the SBN wording. Other years say "Government Debt Securities (SUN)".
   - For all 12 months, the "SUN" Total equals the daily non-resident **SBN** within 0.5 Rp bn on a date of that
     month, and equals no daily SUN value [M7].
   - The published "SBN" block equals "SUN" + SBSN, which counts SBSN twice.
   - Corrections: SUN = published SUN - published SBSN, bucket by bucket; SBN = published SUN block; SBSN is
     unchanged. After correction all 36 Totals for 2018 match the daily file. Before correction, 0 of the 24 SUN
     and SBN Totals did.
   - One assumption remains: that the bucket rows of the mislabelled block are SBN buckets. The daily file has
     no maturity split, so this cannot be checked bucket by bucket.
   - Example: Dec 2018 non-resident SBN = 893.25 Rp tn (corrected) against 912.29 as published.
3. **Header dates that are not the data date.** `daily_match_date` records the actual date.
   - 2017-09-30 (a Saturday) is 2017-09-29 data.
   - 2018-03-31, 06-30 and 09-30 (SBN) are 03-29, 06-29 and 09-28 data.
   - 2018-01-29 (SUN/SBSN) is 2018-01-31 data.
   - 2020-05-31 (a Sunday) is 2020-05-29 data.
   - **2022-03-22 is 2022-03-31 data** for all three instruments.
4. **Totals that match no daily value in their month: 7 month x instrument cells, flagged
   `total_not_equal_to_any_daily_value_in_month`, values left as published.**
   - 2019-05 SBSN equals daily 2019-05-29, not 05-31. As a result SBN (05-31 SUN + 05-29 SBSN) is off by
     -174.641 Rp bn from the 05-31 daily SBN. The 05-31 SBSN buckets are in dropped col H.
   - 2019-06 SBSN and SBN are -0.620 bn from the daily figure, just over the 0.5 tolerance.
   - 2019-11 SBSN and SBN are +95.722 bn.
   - 2021-04 SUN is +1,099.943 bn and SBSN is -1,099.943 bn against daily 2021-04-30, while SBN matches. About
     Rp 1.1 tn is classified as SUN in the monthly file but as SBSN in the daily file. I could not determine
     which is right.
5. **The 2008-2016 file is SBN only.** It has a single block, "Kepemilikan SBN …", with no SUN/SBSN split, so as
   instructed it is **not exported** [M5]. Its own quirks, for reference: Dec-09/Dec-10/Dec-11/Dec-12/Jan-13/Feb-13
   headers are text, Jan 2014 is missing, and Apr and May 2013 carry identical values.

### Validation (monthly)

| check | result |
|---|---|
| M1 buckets sum to Total (195 month x instrument) | max gap 0.0000 Rp bn as published and after correction |
| M2 SUN + SBSN = SBN by bucket (390 cells) | max gap 0.0000 Rp bn as published and after correction. The published file is internally consistent even where it is wrong (2018). |
| M3 month coverage 2017-01..2022-05 | 65 of 65 months, none missing |
| M4 Total equals daily non-resident holdings (±0.5 Rp bn) on a date of the same month | **188/195 after correction** (164/195 as published); 173 on the header date itself, 15 on another date (item 3) |
| M6 negative values | 0 |
| M8 re-read of 400 random rows from the cited cell | 0 mismatches |

## 4. Caveats for users
- `bi_monetary_ops` is negative in 934 rows, 884 of them SBSN, between 2016-06-27 and 2022-06-27. Here "net" BI
  holdings exceed "gross". This is as published. Do not treat it as a holding.
- DJPPR's "Bank Syariah" line reports only SBSN. The file does not say whether it covers Islamic windows (UUS)
  as well as stand-alone Islamic banks (BUS). Assume it cannot be matched to OJK's BUS/UUS split without further
  evidence.
- Holdings are face (nominal) values of **tradable Rupiah** SBN only. Non-tradable and FX-denominated SBN are
  excluded.
- For the full sample, use `insurance_pension` and `others`, not the split rows.
- Values cover only up to 2022-06-28, the last archived daily file, and SBSN only up to 2022-06-27.
