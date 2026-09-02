# P03 analysis plan

## Research question

How did the relative use of midurethral sling procedures (CPT 57288) and urethral bulking procedures
(CPT 51715) change from 2014 through 2024, particularly between 2014–2019 and 2020–2024?

The estimand is descriptive temporal change. The timing of FDA activity, the COVID-19 pandemic, and
2020 Bulkamid approval overlaps; their effects cannot be separated with this design. The manuscript
must not attribute a causal effect to any one factor.

## Source cohort and observation unit

Use the same eligible Commercial and Medicare Database woman-years as P01. Identify qualifying
patient-day episodes containing CPT 57288 or 51715 and join them to the woman’s eligible calendar
year. Ages are grouped in 5-year bands from 18–24 through 85–89.

## Procedure categories

- **Sling:** CPT 57288 without same-day CPT 51715.
- **Bulking:** CPT 51715 without same-day CPT 57288.
- **Hybrid:** both CPT 57288 and 51715 on the same date. Hybrid episodes remain separate and are not
  forced into either treatment group.

Each episode is also classified as isolated SUI or concomitant POP surgery using same-day qualifying
POP procedure information. Isolated SUI is primary; concomitant POP is secondary.

## Primary woman-level estimand

For each woman, retain the first observed sling, bulking, or hybrid episode during 2014–2024. Report
annual and period-specific treatment shares among first observed procedures, overall and by 5-year
age group. Primary inference focuses on isolated SUI episodes. Secondary tables repeat the analysis
for procedures with concomitant POP surgery.

## Secondary total-burden estimand

Count all observed sling and hybrid episodes. Repeated bulking-only injections are collapsed into
treatment courses: a new course begins when the injection is the first observed injection or occurs
more than 90 days after the preceding bulking-only injection. Repeat the analysis with 180 days as a
sensitivity analysis. The course date and calendar year are assigned from the first injection in the
course.

Report procedure-course counts and crude rates per 1,000 eligible woman-years. This burden estimand
is distinct from the primary first-procedure choice estimand and will not be mixed in one denominator.

## Period comparison

The prespecified periods are 2014–2019 and 2020–2024. Report:

- sling, bulking, and hybrid shares in each period;
- absolute percentage-point change and relative change in the bulking share;
- crude procedure or treatment-course rates per 1,000 eligible woman-years;
- age-specific changes in 5-year bands; and
- annual estimates to show whether a period average masks a gradual or abrupt pattern.

Confidence intervals are descriptive Wilson intervals for shares; crude rates are reported without
model-based confidence intervals. No segmented regression or intervention-effect model is used.

## Planned outputs

1. Cohort and episode flow.
2. First observed procedure category by calendar year and period.
3. First observed procedure category by 5-year age group and period.
4. Isolated versus concomitant POP stratification.
5. Total procedure burden using 90-day bulking courses.
6. Sensitivity table using 180-day courses.
7. Selected 2014-2019, 2019-2020, 2020-2024, and 2014-2024 temporal changes.
8. Figure 1: annual bulking share among nonhybrid first observed isolated-SUI procedures.
9. Figure 2: annual crude sling and bulking rates per 1,000 woman-years.
10. Figure 3: pre-2020 versus post-2020 bulking share by 5-year age group.
11. Figure 4: first-procedure versus 90-day total-burden bulking shares.

## Limitations to preserve

Claims do not identify treatment preference, symptom severity, urethral mobility, intrinsic sphincter
deficiency, product brand for all injections, or reasons for repeat treatment. “First observed” need
not be the first lifetime procedure. The 90-day and 180-day rules approximate treatment courses and
must be reported as operational definitions. Same-day POP surgery may not capture staged related
procedures. The changing MarketScan contributor mix and the 2020 disruption limit temporal
interpretation. The study cannot isolate FDA, COVID-19, or product-approval effects.

## Governance

Atalay confirmed on 1 September 2026 that P03 had already been cleared with DataMed/Yujia. Licensed
person-level data remain on the Yale server; only disclosure-safe aggregates may be transferred.
The manuscript remains subject to DataMed review at least 30 days before journal submission.
