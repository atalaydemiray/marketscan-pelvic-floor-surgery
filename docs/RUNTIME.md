# Runtime and dependencies

## Secure server

- R 4.x
- DBI
- duckdb
- Read access to the governed analytic parquet files
- Sufficient DuckDB temporary storage; the scripts set a 4 GB memory limit and two threads

## Local aggregate analysis

- Python 3.11 or newer
- Standard library only for the P01, P02, and P03 analysis scripts
- Pillow for publication PNG/TIFF packaging
- python-docx and lxml for the internal manuscript and DOCX validation workflow

Install optional local dependencies with:

```bash
python3 -m pip install -r requirements.txt
```

No package version was embedded in the licensed data extracts. Before final publication release,
record the actual R, DuckDB, and Python versions used in the manuscript supplement or archived
computational environment.
