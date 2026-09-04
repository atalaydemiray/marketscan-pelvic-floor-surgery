# MarketScan pelvic floor surgery studies

Analysis code for three companion retrospective studies using one 2014–2024 annual eligible woman-year cohort from the Merative™ MarketScan® Commercial Database and Merative™ MarketScan® Medicare Database:

1. Wu-comparable cumulative probability of SUI or POP surgery.
2. Obliterative versus reconstructive POP procedures.
3. Temporal trends in sling versus urethral bulking procedures.

## Reproducibility boundary

The executable pipeline begins with study-derived parquet files under the licensed Yale environment. The Yale data library created those files and the `incident_sui`, `incident_pop`, and `is_pop_surgery` flags. The library-side raw-claims extraction program is not in this repository and was not independently re-executed by the investigators. Accordingly, this repository reproduces all server aggregation, disclosure screening, statistical calculations, tables, and figures **from the derived parquet layer onward**; it does not claim raw-claims-to-results reproducibility.

No MarketScan-derived data files, transferred aggregate tables, figures, or manuscripts are tracked. Exact disclosure-safe design constants remain in code assertions so a rerun cannot silently drift from the reviewed analysis. The only CSVs in Git are public reference inputs: the NCHS 2019 female mortality schedule and the CMS-based CPT lifecycle matrix. The repository remains private and can be considered for public release only after publication review.

## Workflow

```text
licensed derived parquet layer on Yale server
        |
        v
P01/P02/P03 server-side R aggregation
        |
        v
P02/P03 lean disclosure export and machine checks
        |
        v
untracked disclosure-cleared aggregate inputs
        |
        v
Python statistical analyses -> CSV tables + SVG figures
        |
        v
deterministic SVG rasterization -> publication PNG/TIFF
```

P02 and P03 assign calendar year from `svcdate`, not the source claim `YEAR`, and union Commercial and Medicare records before person-level resolution. P03’s secondary burden follows all observed 2014–2024 procedures among ever-eligible women and reports counts/shares rather than rates over the parent risk-set denominator.

## Running

Inside the licensed environment:

```bash
Rscript 'P01 - Lifetime Risk of SUI & POP Surgery/02 Code/P01_wu_export.R'
Rscript 'P02 - Obliterative vs Reconstructive POP Surgery/02 Code/P02_server_analysis.R'
Rscript 'P03 - Sling vs Urethral Bulking Temporal Trends/02 Code/P03_server_analysis.R'
Rscript 'P02 - Obliterative vs Reconstructive POP Surgery/02 Code/P02_P03_disclosure_export.R'
```

Only the named disclosure-screened outputs should be placed in the untracked input directories documented in [INPUT_SCHEMAS.md](docs/INPUT_SCHEMAS.md). Explicit procedure sets are documented in [CPT_DEFINITIONS.md](docs/CPT_DEFINITIONS.md). Then run:

```bash
python3 'P01 - Lifetime Risk of SUI & POP Surgery/02 Code/P01_wu_analysis.py'
python3 'P02 - Obliterative vs Reconstructive POP Surgery/02 Code/P02_analysis.py'
python3 'P03 - Sling vs Urethral Bulking Temporal Trends/02 Code/P03_analysis.py'
python3 '04 Logs/build_publication_packages.py'
```

The analysis scripts use the Python standard library. Publication rasterization additionally requires Pillow and a local Chrome/Chromium executable. Rasterization uses a fixed headless viewport, writes only to the dated publication directory, and never feeds a processed raster back into its source.

## Checks

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
python3 -m py_compile \
  'P01 - Lifetime Risk of SUI & POP Surgery/02 Code/P01_wu_analysis.py' \
  'P02 - Obliterative vs Reconstructive POP Surgery/02 Code/P02_analysis.py' \
  'P03 - Sling vs Urethral Bulking Temporal Trends/02 Code/P03_analysis.py' \
  '04 Logs/build_publication_packages.py'
```

Continuous integration parses all R/Python scripts, checks the code-set and cohort contracts, verifies the 72-row NCHS mortality input and the public 2014–2024 CPT lifecycle matrix, exercises the cumulative-risk and interval functions against known answers, and inspects tracked files and Git history for restricted artifact types. Locked empirical totals remain enforced by the executed internal scripts; they are not replaced by positivity checks.

## Data safety and release

Read [DATA_GOVERNANCE.md](docs/DATA_GOVERNANCE.md) before adding files and [RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) before any public release. Licensed data cannot be obtained from this repository.

## Reference input

Arias E, Xu JQ. United States Life Tables, 2019. *National Vital Statistics Reports*. 2022;70(19):1–59. Table 3, female mortality probabilities. https://stacks.cdc.gov/view/cdc/231916

Authorship order, target journals, citation metadata, and an open-source license will be added after coauthor agreement and publication clearance. Until then, the code is all rights reserved.

Merative and MarketScan are trademarks of Merative Corporation in the United States, other countries, or both.
