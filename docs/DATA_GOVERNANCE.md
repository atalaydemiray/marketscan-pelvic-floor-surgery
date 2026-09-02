# Data governance

## What may be committed

- Analysis code with no MarketScan records or embedded unpublished results.
- Study-design and protocol documentation.
- Aggregate input schemas with column names only.
- Public external inputs with a documented source, such as the NCHS mortality table.
- Tests that use code contracts or synthetic data.

## What must not be committed

- Person-level, claim-level, or enrollment-level MarketScan data.
- Any parquet, SAS, Stata, R data, or similar extract derived from MarketScan.
- Disclosure-screened aggregate inputs, publication tables, figures, manuscripts, run logs, or
  validation reports before DataMed/Merative clearance.
- Small cells or information that could reconstruct suppressed cells.
- Credentials, server configuration, authentication material, or transfer manifests containing
  sensitive paths.

## Operating model

All person-level work runs inside the licensed Yale environment. Only disclosure-reviewed aggregate
outputs may leave that environment for the internal manuscript workflow. A personal GitHub
repository is not the licensed data environment. Repository history must therefore remain code-only
until explicit publication clearance permits release of specified aggregate outputs.

Before public release, inspect the complete Git history, not only the current checkout. If a
restricted file was ever committed, stop and rebuild a clean repository rather than relying on an
ordinary deletion commit.
