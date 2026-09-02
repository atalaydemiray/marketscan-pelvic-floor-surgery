# P01 study design

## Objective

Estimate age-specific rates and period cumulative risk to age 80 for qualifying stress urinary
incontinence (SUI) surgery, pelvic organ prolapse (POP) surgery, and either operation using the
annual open-cohort structure of Wu et al.

## Cohort and observation unit

- Merative MarketScan Commercial and Medicare Supplemental Databases, 2014-2024.
- Women aged 18-89 who satisfy the annual enrollment and prior-surgery washout criteria.
- Observation unit: eligible woman-year. Eligibility is reassessed each calendar year.
- CCAE and MDCR are unioned before distinct-person counts are calculated, and the export fails if a
  person-year appears in both databases.

## Outcomes and analysis

SUI and POP are inclusive endpoints; “either” is their union. Age-specific risks are combined with
single-year female mortality from the 2019 United States life table in a deterministic competing-risk
recursion. Confidence limits use the delta method. Monte Carlo simulation is not used. Current
estimates are compared descriptively with Wu et al.; the external study is not a concurrent control.

## Interpretation limits

MarketScan is a convenience sample and not nationally representative. The period life table combines
cross-sectional age-specific rates. Repeated woman-years are not independent, and the confidence
interval does not model within-woman correlation. General-population mortality is applied to an
insured cohort.
