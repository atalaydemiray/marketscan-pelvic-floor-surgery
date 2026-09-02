# MarketScan pelvic floor surgery studies

Reproducible analysis code for three retrospective studies using the Merative MarketScan Commercial
Claims and Encounters and Medicare Supplemental Databases:

1. Wu-comparable lifetime risk of SUI or POP surgery.
2. Obliterative versus reconstructive POP surgery.
3. Temporal trends in sling versus urethral bulking procedures.

## Repository status

This repository is prepared for a private GitHub remote and eventual public release after manuscript
publication and DataMed/Merative clearance. It intentionally contains **no MarketScan-derived data,
aggregate result tables, figures, or manuscripts**. Those governed files remain in the internal
project package. The public NCHS female mortality input is the only tracked CSV.

## Reproducibility workflow

```text
licensed MarketScan parquet files on Yale server
        |
        v
P01/P02/P03 server-side R scripts
        |
        v
disclosure review and small-cell suppression
        |
        v
untracked aggregate CSV inputs on the authorized local system
        |
        v
Python analysis scripts -> tables and SVG figures
        |
        v
internal manuscript and publication-package builders
```

The server scripts assume the governed Yale path
`/data/MarketScan_data/cohort/analytic`. The Python scripts use relative project paths matching this
repository's paper folders. Required aggregate filenames and columns are documented in
[`docs/INPUT_SCHEMAS.md`](docs/INPUT_SCHEMAS.md).

## Running the analyses

On the Yale server, run only the relevant R script. P02 and P03 aggregate outputs must pass through
`P02_P03_disclosure_export.R` before transfer. Never move person-level files off the licensed server.

After placing disclosure-cleared aggregate CSVs in the documented untracked directories:

```bash
python3 'P01 - Lifetime Risk of SUI & POP Surgery/02 Code/P01_wu_analysis.py'
python3 'P02 - Obliterative vs Reconstructive POP Surgery/02 Code/P02_analysis.py'
python3 'P03 - Sling vs Urethral Bulking Temporal Trends/02 Code/P03_analysis.py'
```

The pure analysis scripts use the Python standard library. Publication rasterization requires Pillow;
the internal DOCX builders additionally require python-docx and lxml. Server extraction requires R,
DBI, and duckdb.

## Automated checks

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile \
  'P01 - Lifetime Risk of SUI & POP Surgery/02 Code/P01_wu_analysis.py' \
  'P02 - Obliterative vs Reconstructive POP Surgery/02 Code/P02_analysis.py' \
  'P03 - Sling vs Urethral Bulking Temporal Trends/02 Code/P03_analysis.py'
```

Continuous integration checks Python syntax, R syntax, locked design constants, the public mortality
input, and the absence of restricted data artifacts.

## Governance

Read [`docs/DATA_GOVERNANCE.md`](docs/DATA_GOVERNANCE.md) before adding files. Public release must
follow [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md). MarketScan data are not distributed
and cannot be obtained from this repository.

## Citation and license

Authorship order, target journals, citation metadata, and an open-source license will be added after
coauthor agreement and publication clearance. Until then, the code is all rights reserved.
