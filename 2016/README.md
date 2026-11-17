# LCC analysis rebuilt on the 2016 LC MARC files

Data: `BooksAll.2016.part01–43.utf8.gz` (10,543,015 records). The previous run used the 2014 files (kept in `../2014/`).
Open `index.html` via a web server (e.g. `python3 -m http.server`).

## Scope (v2)
**Every valid LC subclass is analysed: 238 subclasses, 9,500,598 records** (valid LC call number, year 1400–2020). The 2014 list of 202 subclasses is no longer a filter. 34 subclasses were added (PZ 298,785; KK 106,512; NA 75,410; KN 52,571; TT 32,676; BQ 29,167; KP, U, JA, H, JF, KM, KT, J, L, KU, V, … and a few tiny ones). Their Jefferson statuses are **provisional** and listed in `scripts/meta_2016.csv` (rows not in `scripts/meta_2016_204only.csv`); please review them.
Bare class letters (H, J, L, U, V, A, C: general works with no subclass letter) are subclasses of their own. 3-letter K law codes fold into their 2-letter parent (KKH → KK, KBP → KB).

## What was wrong in the 2014 tables (fixed here)
1. **E (American history) and F (US local / Latin American history) were never counted** (only E185 and E99 were). Now E = 112,551 and F = 254,587 records. Status MERGED, Memory — *provisional*.
2. **Non-LC call numbers were folded into real classes**: MLC (698k) counted as ML, MIC (125k) as M, LAW as LA, etc. Now only valid LC subclasses count (same `valid_class` rule as history_class_share.py; field 050, else 090).
3. **E18 matched all of E180–E189 (25.8k)**; now E185 only (9.2k), as its label says.
4. **The 2014 subclass list omitted real subclasses** (PZ, NA, TT, BQ, KK, KN, …, 715k records). They are now included. Note: pandas reads the text "NA" (Architecture) as a missing value unless `keep_default_na=False` is set; the scripts here set it. Whether this explains the absence of NA from the 2014 list is not verified.
5. The 2014 `subclass_rankings_over_time.csv` did not match the 2014 cumulative table; it is regenerated.

## Data limitation: recent years are incomplete
The 2016 file is a snapshot, so recent publication years are only partly catalogued: records per year are about 205,000–216,000 in 2009–2011, then 191,867 (2012), 159,590 (2013), 129,045 (2014), 75,905 (2015), 22,518 (2016) and 903 for 2017–2020. This most likely reflects cataloguing lag (not checked against outside publication counts). Nothing was removed or corrected, and every 2020 total, sigmoid fit and inflection year uses these years.
`scripts/07_sensitivity_cutoff.py` refits everything on 1400–2011 and 1400–2008 (`output/sensitivity_cutoff_report.txt`, `sensitivity_cutoff_*.csv`): inflection years move earlier by a median of 1.3 years (2011 cutoff) and 3.2 years (2008 cutoff), so absolute inflection years depend on the cutoff. The Jeffersonian vs absent comparison keeps its direction and significance (gap +2.2 y, p=0.0025 with the 2011 cutoff; +1.6 y, p=0.0039 with all years; median growth 211x vs 414x). The note is added to all pages by `scripts/08_add_data_notes.py`.

## Reproduce
```
python3 scripts/01_extract_marc_2016.py  <parts_dir> <work_dir> 2
python3 scripts/02_build_tables.py <work_dir>/subclass_raw_records.csv scripts/meta_2016.csv <tables_dir>
python3 scripts/03_update_dashboard.py <old index.html> <tables_dir> <work_dir>/class_raw_records.csv <work_dir>/extraction_summary.csv <out_dir>
python3 scripts/04_update_secondary_pages.py <old pages dir> <tables_dir> <out_dir>
python3 scripts/07_sensitivity_cutoff.py <tables_dir> <sens_dir> 2011 2008     # refits on truncated years
python3 scripts/06_make_figures.py <tables_dir> <out_dir> <sens_dir>   # 3 PNG figures + decade-growth page
python3 scripts/05_unify_nav.py <out_dir>                        # same top navigation bar on all five pages
python3 scripts/08_add_data_notes.py <out_dir> <sens_dir>        # incomplete-years note on all five pages
python3 scripts/09_add_meta.py <out_dir>                         # title/description/Open Graph/JSON-LD + accessibility (skip link, landmarks, chart labels)
python3 scripts/history_class_share.py <parts_dir>/*.gz        # independent C–F check
```
Run on the 2014 raw file + `meta_2014.csv`, `02_build_tables.py` reproduces the old cumulative table and Test D. `output/key_changes.csv` compares old and new counts and inflection years.
Tests 3 and 4 of the earlier paper (structural inheritance r=0.611 etc.) are not regenerated: their scripts are not in the folder.

## Linked pages
Alluvial, bubble animation, cumulative share and Jefferson split are regenerated from the same tables. E and F sit under Jefferson `Ch.4 American` (MERGED, provisional) in the 'E/F — History of the Americas' node. The 34 added subclasses sit under `Not in Jefferson` except NA (Ch.30–31 Architecture & Arts, DIRECT), BQ (Ch.17 Religion), J/JA/JF/JJ (Ch.24 Politics & Commerce) and KA/KK (Ch.18–23 Law), all provisional.
