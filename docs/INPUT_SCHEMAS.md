# Input schemas and provenance boundary

This repository does not distribute values. The schemas below let authorized analysts reconstruct the untracked local inputs after the server-side disclosure screen.

## Licensed derived parquet layer

Server scripts expect `/data/MarketScan_data/cohort/analytic` with `CCAE_` and `MDCR_` versions of:

- `final_analysis.parquet`: `study_year`, `ENROLID`, `index_date`, `age_at_index`, `incident_sui`, `incident_pop`, and related supplied flags.
- `eligible_cohort.parquet`: `study_year`, `ENROLID`, `index_date`, `age_at_index`, `lookback_years_enrolled`, and enrollment fields.
- `surgery_events.parquet`: `ENROLID`, `svcdate`, `codes`, claim `YEAR`, `is_sui_surgery`, `is_pop_surgery`, and related diagnosis/procedure flags.

The Yale data library created this layer. Its raw-claims extraction program is not shipped here. Event calendar year is always `year(svcdate)`; claim `YEAR` is retained only for auditing.

## P01

Expected local directory: `P01 - Lifetime Risk of SUI & POP Surgery/03 Data/Wu Comparable 2026-09-01/`

| Files | Columns |
|---|---|
| `CCAE_wu_by_age.csv`, `MDCR_wu_by_age.csv` | `age`, `person_years`, `sui_operations`, `pop_operations`, `any_operations`, `both_same_year` |
| `CCAE_wu_by_year_age.csv`, `MDCR_wu_by_year_age.csv` | `study_year`, `age`, the same five count fields |
| `CCAE_wu_totals.csv`, `MDCR_wu_totals.csv`, `P01_wu_totals.csv` | `database`, `person_years`, `contributing_women`, `unique_operated_women`, `sui_operations`, `pop_operations`, `any_operations`, `both_same_year` |

Washout sensitivities use the internal `CCAE_washout01/03/05/07/10.csv` and MDCR equivalents with `study_year`, `age_at_index`, `py`, and `n_union`. An optional disclosure-screened `04 Logs/Server Audit Aggregates 2026-09-04/p01_no_bulking_lifetime_risk.csv` adds the exact no-bulking sensitivity.

## P02

Expected local directory: `P02 - Obliterative vs Reconstructive POP Surgery/03 Data/Server Aggregates 2026-09-04/`

| File | Required fields |
|---|---|
| `pooled_denominators.csv` | `study_year`, `age5`, `broad_age`, `woman_years` plus suppression flag |
| `pooled_totals.csv` | total, obliterative, reconstructive, mixed-code counts plus flags |
| `pooled_first_by_age_publication.csv` | `age_publication`, `procedure_group`, `women` plus flag; ages 18–29 combined |
| `pooled_first_by_year.csv` | `study_year`, `procedure_group`, `women` plus flag |
| `pooled_first_by_year_broad_age.csv` | `study_year`, `broad_age`, `procedure_group`, `women` plus flag |
| `pooled_eligible_year_procedure_dates_by_year.csv` | `study_year`, `procedure_group`, `operation_dates` plus flag |
| `pooled_code_contribution.csv` | `code`, `operation_dates` plus flag |
| `pooled_definition_reconciliation.csv` | definition group, operation dates, women, flags |
| `pooled_parent_definition_sensitivity.csv` | definition, first procedures, obliterative, flags |

## P03

Expected local directory: `P03 - Sling vs Urethral Bulking Temporal Trends/03 Data/Server Aggregates 2026-09-04/`

| File | Required fields |
|---|---|
| `pooled_denominators.csv` | `study_year`, `age5`, `woman_years` plus flag |
| `pooled_first_totals.csv` | `pop_context`, `procedure_category`, `women` plus flag |
| `pooled_first_by_period.csv` | period/context/category nonhybrid counts plus flags |
| `pooled_first_by_year.csv` | annual isolated nonhybrid counts plus flags |
| `pooled_first_by_period_age_publication.csv` | isolated nonhybrid period counts; ages 18–29 combined |
| `pooled_first_period_sensitivity.csv` | all-period first nonhybrid counts by period/context |
| `pooled_total_burden_090d_totals.csv`, `pooled_total_burden_180d_totals.csv` | isolated sling/bulking treatment units and contributing dates |
| `pooled_total_burden_090d_by_year.csv`, `pooled_total_burden_180d_by_year.csv` | the same burden fields by service-date year |

## Disclosure contract

`SUPPRESSED` represents a nonzero count below 11. Structural zeros remain numeric zero. The export calculates flags from the original values before blanking, combines ages where necessary, and omits redundant margins and hybrid detail. The transfer script fails if a visible nonzero count is below 11, a flag disagrees with masking, or a publication table still contains a protected cell.
