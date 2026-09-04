# P02 analysis plan: obliterative versus reconstructive POP procedures

Final analytic specification, 4 September 2026.

## Aim and design

Describe how the share of qualifying POP procedures classified as obliterative rather than reconstructive varies by age and calendar year in the same 2014–2024 annual eligible woman-year cohort used by P01. This is a utilization study, not a comparison of effectiveness or safety.

Eligibility requires female sex, age 18–89 years, three preceding enrollment years, 12 monthly enrollment indicators in the index year, and the parent five-year SUI/POP-operation washout. Eligibility is reassessed annually. Records from the Commercial and Medicare databases are unioned before person-level duplicate resolution. Calendar year is assigned from service date, not claim `YEAR`.

## Procedure classification

- Obliterative: CPT 57106, 57110, 57120, 58275, 58280.
- Reconstructive: CPT 56810, 57107, 57109, 57111, 57112, 57200, 57210, 57230, 57240, 57250, 57260, 57265, 57267, 57268, 57270, 57280, 57282, 57283, 57284, 57285, 57423, 57425, 58400.

One service-date episode is created per ENROLID after cross-database deduplication. A date containing codes from both groups is classified as obliterative and separately flagged as mixed. The classification follows Koray Görkem Saçıntı’s requested clinical grouping without adding a diagnosis requirement to the primary analysis.

Annual CMS RVU files show that CPT 57112 was active through 2020 and absent in 2021–2024; all other P02 codes were active throughout the study period. The fixed historical code set is retained.

The P02 explicit-code definition differs from P01: it adds 58275 and 58280 but does not include P01’s hysterectomy-with-primary-POP-diagnosis channel when no explicit P02 code is present. The difference is reconciled in a dedicated table. A sensitivity analysis adds the parent hysterectomy channel as reconstructive unless an obliterative code is present.

## Estimands

Primary: for each ENROLID, the first qualifying explicit-code procedure that occurs in an eligible woman-year during 2014–2024. This is not necessarily the first observed procedure anywhere in the available claims and is not first lifetime surgery. Codes 58275 and 58280 were not part of the parent washout set, which is an acknowledged asymmetry.

Primary outcomes:

1. obliterative share among qualifying procedures overall;
2. age-specific obliterative share, using age 18–29 followed by five-year bands;
3. annual crude and directly age-standardized obliterative shares; and
4. crude procedure-group rates per 1,000 eligible woman-years.

Secondary outcomes:

1. qualifying procedure dates occurring inside eligible woman-years;
2. parent-definition augmented sensitivity; and
3. first-procedure scope sensitivity using all visible 2014–2024 dates among ever-eligible enrollees.

## Statistical analysis

Shares and crude rates are descriptive. Wilson intervals are used for one-sample shares. Temporal comparisons are 2014–2019, 2019–2020, 2020–2024, and 2014–2024. Absolute differences use Newcombe-Wilson intervals and share ratios use log-scale intervals. Annual shares are directly standardized to the pooled distribution of qualifying procedures across four broad age groups: younger than 65, 65–74, 75–84, and 85–89 years.

Nonzero counts below 11 are masked before transfer. Ages 18–24 and 25–29 are combined on the server, and redundant margins are excluded from the transfer bundle so protected cells cannot be recovered by subtraction. Structural zeros remain zero.

## Interpretation limits

Claims do not identify operative intent, prolapse severity, frailty, sexual-function goals, or clinical indication. CPT 57106 and 57110 can be used outside prolapse care, particularly at younger ages. The age 65–68 insurance transition creates sparse, selected person-time; age-specific rates are therefore not population incidence. ENROLID can change after employer change. Temporal comparisons are descriptive and can reflect contributor mix and health-care delivery as well as clinical practice.
