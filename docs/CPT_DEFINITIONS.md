# Procedure-code definitions

The lists below are the explicit CPT sets used by the study scripts. They do not reproduce the unavailable library-side hysterectomy/diagnosis logic behind the supplied P01 `incident_pop` and P03 `is_pop_surgery` flags.

## P01 SUI

51715, 51840, 51841, 51845, 51990, 51992, 57220, 57288, 57289, 58152, 58267, 58293.

CPT 51715 is urethral bulking and is retained for comparability with Wu et al. Codes 58152, 58267, and 58293 are classified as SUI only.

## P01 explicit POP

56810, 57106, 57107, 57109, 57110, 57111, 57112, 57120, 57200, 57210, 57230, 57240, 57250, 57260, 57265, 57267, 57268, 57270, 57280, 57282, 57283, 57284, 57285, 57423, 57425, 58400.

The supplied P01 POP flag also includes hysterectomy with a same-day primary POP diagnosis and excludes oncologic/obstetric hysterectomy. The exact trigger lists used by the data library are not available in this repository.

## P02 obliterative

57106, 57110, 57120, 58275, 58280.

## P02 reconstructive

56810, 57107, 57109, 57111, 57112, 57200, 57210, 57230, 57240, 57250, 57260, 57265, 57267, 57268, 57270, 57280, 57282, 57283, 57284, 57285, 57423, 57425, 58400.

P02 follows the clinical grouping requested by Koray Görkem Saçıntı. If an obliterative and reconstructive code occur on the same date, the date is classified as obliterative and flagged as mixed. The primary definition uses procedure codes without an indication diagnosis requirement.

## P03

- Sling: 57288 without same-day 51715.
- Urethral bulking: 51715 without same-day 57288.
- Hybrid: both codes on the same date.

Same-day POP context is derived from the supplied `is_pop_surgery` flag.

## Lifecycle validation

The 40 distinct codes used across P01–P03 were checked against the October-release CMS National Physician Fee Schedule Relative Value Files for every year from 2014 through 2024. Thirty-eight were active in every study-year file. CPT 58293 and 57112 were active through 2020 and absent from the 2021–2024 files; they remain in the historical code sets so the definition is stable across the study window. The code-level result is in [`cpt_lifecycle_2014_2024.csv`](cpt_lifecycle_2014_2024.csv). CMS describes the RVU files and provides each annual release on its [PFS Relative Value Files page](https://www.cms.gov/medicare/payment/fee-schedules/physician/pfs-relative-value-files).
