# Runtime and dependencies

Producing environment, verified 4 September 2026:

| Stage | Runtime |
|---|---|
| Secure server aggregation | R 4.5.2, DBI, DuckDB 1.5.5; 4 GB DuckDB memory limit, 2 threads, disk-backed temporary directory |
| Local statistical analysis | Python 3.14.6; standard library |
| Publication packaging | Apple system Python 3.9.6, Pillow 11.3.0, Google Chrome headless renderer |
| Manuscript construction | Apple system Python 3.9.6, python-docx 1.2.0, lxml 6.1.0 |

The statistical scripts and CI target Python 3.11 or newer; the publication
builder was also exercised under Apple system Python 3.9.6. Install
non-standard local dependencies with:

```bash
python3 -m pip install -r requirements.txt
```

Server scripts require read access to the governed derived parquet layer. The run logs record UTC timestamps and the executed scripts enforce the locked denominator and reconciliation counts. Package versions in another licensed environment may differ; record them with the released computational archive.
