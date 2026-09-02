# Aggregate input schemas

These files are produced inside the licensed environment. Values are not distributed. Column names
are listed so authorized users can reproduce the local analysis after disclosure review.

## P01

Expected directory: `P01 - Lifetime Risk of SUI & POP Surgery/03 Data/Wu Comparable 2026-09-01/`

| Files | Columns |
|---|---|
| `CCAE_wu_by_age.csv`, `MDCR_wu_by_age.csv` | `age`, `person_years`, `sui_operations`, `pop_operations`, `any_operations`, `both_same_year` |
| `CCAE_wu_by_year_age.csv`, `MDCR_wu_by_year_age.csv` | `study_year`, `age`, `person_years`, `sui_operations`, `pop_operations`, `any_operations`, `both_same_year` |
| `CCAE_wu_by_band.csv`, `MDCR_wu_by_band.csv` | `age_band`, `person_years`, `contributing_women`, `sui_operations`, `pop_operations`, `any_operations`, `both_same_year` |
| `CCAE_wu_totals.csv`, `MDCR_wu_totals.csv`, `P01_wu_totals.csv` | `database`, `person_years`, `contributing_women`, `unique_operated_women`, `sui_operations`, `pop_operations`, `any_operations`, `both_same_year` |

## P02

Expected directory: `P02 - Obliterative vs Reconstructive POP Surgery/03 Data/Server Aggregates 2026-09-01/`

| File | Columns |
|---|---|
| `pooled_denominators.csv` | `study_year`, `age5`, `broad_age`, `woman_years`, `woman_years_suppressed` |
| `pooled_first_by_age.csv` | `age5`, `procedure_group`, `women`, `mixed_code_dates`, suppression flags |
| `pooled_first_by_broad_age.csv` | `broad_age`, `procedure_group`, `women`, `mixed_code_dates`, suppression flags |
| `pooled_first_by_database.csv` | `event_database`, `procedure_group`, `women`, `mixed_code_dates`, suppression flags |
| `pooled_first_by_year.csv` | `study_year`, `procedure_group`, `women`, `mixed_code_dates`, suppression flags |
| `pooled_first_by_year_age.csv` | `study_year`, `age5`, `procedure_group`, `women`, `mixed_code_dates`, suppression flags |
| `pooled_first_by_year_broad_age.csv` | `study_year`, `broad_age`, `procedure_group`, `women`, `mixed_code_dates`, suppression flags |
| `pooled_total_burden.csv` | `study_year`, `age5`, `procedure_group`, `operation_dates`, `mixed_code_dates`, suppression flags |
| `pooled_total_burden_by_year.csv` | `study_year`, `procedure_group`, `operation_dates`, `mixed_code_dates`, suppression flags |
| `pooled_totals.csv` | first-observed total and group counts, mixed-code count, suppression flags |
| `pooled_code_contribution.csv` | `code`, `claim_rows`, `operation_dates`, suppression flags |

## P03

Expected directory: `P03 - Sling vs Urethral Bulking Temporal Trends/03 Data/Server Aggregates 2026-09-01/`

| File family | Columns |
|---|---|
| `pooled_denominators.csv` | `study_year`, `age5`, `woman_years`, `woman_years_suppressed` |
| `pooled_first_by_database.csv` | `event_database`, `pop_context`, `procedure_category`, `women`, `women_suppressed` |
| `pooled_first_by_period.csv` | `study_period`, `pop_context`, `procedure_category`, `women`, `women_suppressed` |
| `pooled_first_by_period_age.csv` | `study_period`, `age5`, `pop_context`, `procedure_category`, `women`, `women_suppressed` |
| `pooled_first_by_year.csv` | `study_year`, `pop_context`, `procedure_category`, `women`, `women_suppressed` |
| `pooled_first_by_year_age.csv` | `study_year`, `age5`, `pop_context`, `procedure_category`, `women`, `women_suppressed` |
| `pooled_first_totals.csv` | `pop_context`, `procedure_category`, `women`, `women_suppressed` |
| `pooled_total_burden_090d*.csv`, `pooled_total_burden_180d*.csv` | time/age/context fields as applicable, `burden_category`, `treatment_units`, `contributing_injection_dates`, suppression flags |

`SUPPRESSED` represents any exact count below 11. Downstream code must propagate missingness and
must not reconstruct those cells by subtraction.
