# P03 analysis plan: temporal trends in sling versus urethral bulking

Final analytic specification, 4 September 2026.

## Aim and design

Describe whether use of urethral bulking relative to sling procedures changed between 2014–2019 and 2020–2024 in the annual eligible woman-year cohort shared with P01. The timing overlaps FDA activity, the COVID-19 pandemic, and Bulkamid approval; the design does not separate or causally attribute these effects.

Eligibility requires female sex, age 18–89 years, three preceding enrollment years, 12 monthly enrollment indicators in the index year, and the parent five-year SUI/POP-operation washout. Eligibility is reassessed annually. Commercial and Medicare records are unioned before person-level resolution. Calendar year is assigned from service date.

## Procedure categories

- Sling: CPT 57288 without same-day CPT 51715.
- Urethral bulking: CPT 51715 without same-day CPT 57288.
- Hybrid: CPT 57288 and 51715 on the same date.

Both procedure codes were active in every annual CMS RVU file from 2014 through 2024.

Hybrid dates remain a separate category and are excluded from sling-versus-bulking shares. Same-day POP context uses the library-supplied `is_pop_surgery` flag. Isolated SUI is primary and concomitant POP is secondary.

## Estimands

Primary: for each ENROLID, the first qualifying sling, bulking, or hybrid procedure occurring in an eligible woman-year during 2014–2024. This excludes visible procedures in non-eligible years, including years inside the post-operation washout, and is not first lifetime treatment.

The primary contrast is the bulking share among nonhybrid isolated-SUI procedures in 2014–2019 versus 2020–2024. Annual and age-specific shares, crude rates per 1,000 eligible woman-years, and the concomitant-POP stratum are also reported. Ages are grouped as 18–29 and then five-year bands through 85–89.

Secondary burden: all observed 2014–2024 sling, bulking, and hybrid dates among women who contributed at least one eligible woman-year, regardless of whether the procedure year itself was eligible. Repeated bulking-only dates are collapsed into a treatment course when consecutive injections are no more than 90 days apart; 180 days is the sensitivity window. The burden is reported as procedure counts and shares, not as rates over the parent eligible woman-year denominator.

An all-period first-procedure sensitivity repeats person-level classification over all visible 2014–2024 dates among ever-eligible women.

## Statistical analysis

Wilson intervals are used for one-period shares. Period, annual, and age-stratum absolute changes use Newcombe-Wilson intervals; share ratios use log-scale intervals. Selected annual contrasts are 2014–2019, 2019–2020, 2020–2024, and 2014–2024. Period shares for isolated SUI are directly standardized to the pooled distribution of nonhybrid isolated procedures across publication age groups. Age-stratum comparisons are exploratory and unadjusted for multiplicity.

Nonzero counts below 11 are masked before transfer. Ages 18–24 and 25–29 are combined on the server; redundant hybrid and margin tables are excluded so protected cells cannot be recovered by subtraction. Structural zeros remain zero.

## Interpretation limits

Claims do not provide symptom severity, urethral mobility, intrinsic sphincter deficiency, treatment preference, or product brand for every injection. CPT 51715 can occasionally reflect a non-stress indication, particularly in the youngest group. ENROLID can change after employer change. Same-day POP coding does not identify staged care. The course windows are operational definitions. All temporal results are descriptive.
