# P01 active Wu-comparable analysis plan

Final analytic specification: 4 September 2026. Core Wu-comparable design locked 2 September 2026.

## Objective

Estimate age-specific rates and period cumulative risk to age 80 for qualifying stress urinary
incontinence (SUI) surgery, pelvic organ prolapse (POP) surgery, and either operation using the
annual open-cohort structure of Wu et al.

## Cohort and observation unit

- Merative MarketScan Commercial and Medicare Databases, 2014-2024.
- Women aged 18-89 with three preceding enrollment years, all 12 monthly enrollment indicators in
  the index year, and the supplied five-year prior-surgery washout.
- Observation unit: eligible woman-year. Eligibility is reassessed each calendar year, so a woman
  may contribute more than one woman-year and may requalify after a prior eligible year.
- Pooled denominator: 47,258,198 eligible woman-years.
- Cross-database integrity rule: union CCAE and MDCR before calculating distinct-person counts and
  fail if a person-year occurs in both databases.

## Outcomes

Use the protocol's locked CPT definitions. SUI and POP are inclusive endpoints; a same-year episode
can contribute to both. The “either” endpoint is the union and is counted once per eligible
woman-year. The 102,440 union count is therefore qualifying operation-person-years, not women.
CPT lifecycle review against annual CMS RVU files found CPT 58293 and 57112 active through 2020 and
absent thereafter; all other explicit P01 codes were active throughout 2014–2024. The fixed historical
definition is retained.

## Statistical analysis

1. Calculate age-specific and age-band-specific rates per 1,000 eligible woman-years.
2. Calculate Wilson 95% confidence intervals for binomial operation risks and express them per 1,000.
3. Produce annual crude rates for 2014-2024.
4. Directly age-standardize annual rates to the pooled single-year age distribution.
5. Combine single-year operation risks for ages 18-79 with single-year female mortality from the
   2019 United States life table in a deterministic competing-risk recursion.
6. Obtain lifetime-risk confidence limits with the delta method; the interval reflects binomial
   sampling variation only.
7. Reapply the current recursion to Wu et al.'s published age-band rates for a like-for-like
   descriptive comparison; do not treat the external study as a formal concurrent comparator.
8. Report period, washout, bulking-exclusion, insurance-seam, age-alignment, and mortality
   sensitivities.

## Locked validation checks

- 47,258,198 eligible woman-years.
- 102,440 qualifying operation-person-years.
- 102,107 combined unique operated women.
- 333 additional qualifying woman-years after annual requalification.
- 58,458 inclusive SUI operation-person-years.
- 71,511 inclusive POP operation-person-years.
- 27,529 same-year SUI and POP overlaps.
- Zero duplicate person-years across CCAE and MDCR.

## Interpretation limits

MarketScan is a convenience sample and not nationally representative. The analysis is a period life
table based on cross-sectional age-specific rates. Repeated woman-years are not independent, and the
delta-method interval does not model within-woman correlation. General-population mortality is
applied to an insured cohort. Results describe the probability implied by 2014-2024 utilization
rates among women with an observed five-year operation-free interval, not first-ever lifetime
surgery, an individual forecast, or a causal effect. The sparse commercial-to-Medicare transition
at ages 65-68 and the year-attained age definition are evaluated in sensitivity analyses.
