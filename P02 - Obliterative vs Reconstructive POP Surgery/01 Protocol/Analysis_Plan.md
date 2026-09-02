# P02 analysis plan

## Research question

Among women in the existing MarketScan open cohort who undergo a first observed qualifying POP
operation from 2014 through 2024, how does selection of obliterative versus reconstructive surgery
vary by age and calendar year?

This is a descriptive utilization study. It does not compare complications, recurrence, reoperation,
or effectiveness unless a separate outcome protocol is approved.

## Source cohort

Use the same Commercial and Medicare Database analytic woman-years as P01: women aged 18 to 89 who
meet that paper’s annual enrollment and washout criteria. Join qualifying operation dates to an
eligible calendar year. The primary population is each woman’s first observed qualifying POP
operation during 2014–2024. “First observed” is used because earlier operations outside observable
coverage may not be captured.

## Procedure classification locked by Koray

### Obliterative

- Partial or complete vaginectomy/colpectomy: CPT 57106 and 57110.
- Vaginal hysterectomy with total or partial colpectomy: CPT 58275 and 58280.
- Le Fort colpocleisis: CPT 57120.

### Reconstructive

All other qualifying POP CPT codes: 56810, 57107, 57109, 57111, 57112, 57200, 57210, 57230,
57240, 57250, 57260, 57265, 57267, 57268, 57270, 57280, 57282, 57283, 57284, 57285, 57423,
57425, and 58400.

If an operation date contains both groups, classify the episode as obliterative because at least one
of Koray’s five defining obliterative procedures occurred; tabulate the frequency of mixed-code dates
as a data-quality check.

## Primary estimand

The annual proportion of first observed qualifying POP operations that are obliterative rather than
reconstructive, overall and by 5-year age group (18–24, 25–29, …, 85–89).

## Secondary estimands

- Crude annual rates of first observed obliterative and reconstructive operations per 1,000 eligible
  woman-years.
- Procedure-group distribution within broader clinically readable age categories: younger than 65,
  65–74, 75–84, and 85–89 years.
- Database-specific estimates for the Commercial and Medicare Databases.
- Total procedure burden, counting all observed qualifying operation dates, clearly separated from
  the woman-level first-operation analysis.

## Statistical analysis

Report counts, column percentages, crude rates per 1,000 woman-years, and Wilson 95% confidence
intervals for procedure shares.
Plot annual procedure-group shares and age-specific shares. Pool database-specific aggregates by
summing numerators and denominators; do not transfer person-level records. No causal or comparative-
effectiveness language will be used.

## Planned outputs

1. Cohort flow and procedure-code contribution table.
2. First observed procedure group by 5-year age group.
3. Annual first observed procedure counts, rates, and shares.
4. Selected 2014-2019, 2019-2020, 2020-2024, and 2014-2024 temporal changes.
5. Total procedure burden by year and group.
6. Figure 1: obliterative share by age group.
7. Figure 2: annual obliterative share and reconstructive/obliterative rates.
8. Figure 3: annual obliterative share by reportable broad age group.

## Limitations to preserve

Claims do not provide validated clinical indications, examination findings, frailty, sexual function
preferences, or operative intent. The five-code definition is a procedure classification supplied by
the clinical lead. CPT 58275 and 58280 were not part of the P01 POP code list, so their addition must
be disclosed. The MarketScan Databases are convenience samples of insured populations. Procedure
choice is confounded by age, health status, anatomy, concomitant surgery, and patient preferences;
descriptive differences must not be interpreted as treatment effects.

## Governance

Atalay confirmed on 1 September 2026 that P02 had already been cleared with DataMed/Yujia. Licensed
person-level data remain on the Yale server; only disclosure-safe aggregates may be transferred.
The manuscript remains subject to DataMed review at least 30 days before journal submission.
