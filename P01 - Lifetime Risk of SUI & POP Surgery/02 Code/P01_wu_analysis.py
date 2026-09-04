#!/usr/bin/env python3
"""Build the active P01 Wu-comparable tables and figures from aggregate CSVs.

This analysis intentionally uses the annual open-cohort records exactly as
counted in the Wu-comparable server export. It reports inclusive SUI, inclusive
POP, and their union. Cumulative risk is calculated with a deterministic
single-decrement-plus-mortality life table; confidence limits use a delta-method
variance based on the age-specific binomial event risks.
"""

from __future__ import annotations

import csv
import html
import math
import shutil
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
PAPER = HERE.parent
PROJECT = PAPER.parent
INPUT = PAPER / "03 Data" / "Wu Comparable 2026-09-01"
DATA = PAPER / "03 Data" / "Analysis 2026-09-04"
FIGURES = PAPER / "04 Figures" / "Analysis 2026-09-04"
AUDIT = PROJECT / "04 Logs" / "Server Audit Aggregates 2026-09-04"
DATA.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

QX_FILE = HERE / "nchs2019_female_qx.csv"
# Source: Arias E, Xu JQ. United States Life Tables, 2019. National Vital
# Statistics Reports. 2022;70(19), Table 3, female qx.
# https://stacks.cdc.gov/view/cdc/231916
DATABASES = ("CCAE", "MDCR")
ENDPOINTS = {
    "SUI": "sui_operations",
    "POP": "pop_operations",
    "Either": "any_operations",
}
WU_BANDS = ((18, 29), (30, 39), (40, 49), (50, 59), (60, 69), (70, 79), (80, 89))
COMPOSITION_BANDS = (
    (18, 29),
    (30, 34),
    (35, 39),
    (40, 44),
    (45, 49),
    (50, 54),
    (55, 59),
    (60, 64),
    (65, 69),
    (70, 74),
    (75, 79),
)
WU_RATES = {
    "SUI": (0.1, 1.7, 3.4, 3.1, 3.3, 3.4, 1.8),
    "POP": (0.2, 1.4, 2.4, 2.8, 3.6, 3.8, 1.7),
    "Either": (0.3, 2.5, 4.6, 4.5, 5.1, 5.3, 2.6),
}
WU_LIFETIME = {"SUI": 13.6, "POP": 12.6, "Either": 20.0}

INK = "#17212B"
BLUE = "#2E6FA7"
GOLD = "#C08428"
PURPLE = "#76548F"
GREY = "#77818A"
LIGHT = "#DDE3E8"
COLORS = {"SUI": BLUE, "POP": GOLD, "Either": INK}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def as_int(value: str) -> int:
    return int(float(value))


def write_rows(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total <= 0:
        return math.nan, math.nan
    p = successes / total
    den = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / den
    half = z * math.sqrt(p * (1.0 - p) / total + z * z / (4.0 * total * total)) / den
    return center - half, center + half


def band_for(age: int) -> str:
    for lo, hi in WU_BANDS:
        if lo <= age <= hi:
            return f"{lo}-{hi}"
    raise ValueError(age)


def pool_age() -> dict[int, dict[str, int]]:
    pooled: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for db in DATABASES:
        for row in read_rows(INPUT / f"{db}_wu_by_age.csv"):
            age = as_int(row["age"])
            for field in ("person_years", "sui_operations", "pop_operations", "any_operations", "both_same_year"):
                pooled[age][field] += as_int(row[field])
    return dict(sorted(pooled.items()))


def pool_year_age() -> dict[tuple[int, int], dict[str, int]]:
    pooled: dict[tuple[int, int], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for db in DATABASES:
        for row in read_rows(INPUT / f"{db}_wu_by_year_age.csv"):
            key = (as_int(row["study_year"]), as_int(row["age"]))
            for field in ("person_years", "sui_operations", "pop_operations", "any_operations", "both_same_year"):
                pooled[key][field] += as_int(row[field])
    return dict(sorted(pooled.items()))


def mortality_hazards() -> dict[int, float]:
    qx = {as_int(r["age"]): float(r["qx"]) for r in read_rows(QX_FILE)}
    return {age: -math.log1p(-prob) for age, prob in qx.items()}


def cumulative_risk(probabilities: dict[int, float], mu: dict[int, float], max_age: int = 80) -> float:
    event_free_alive = 1.0
    cumulative = 0.0
    for age in range(18, max_age):
        p = min(max(probabilities.get(age, 0.0), 0.0), 1.0 - 1e-12)
        lam = -math.log1p(-p)
        total = lam + mu[age]
        if total > 0:
            cumulative += event_free_alive * lam / total * (1.0 - math.exp(-total))
            event_free_alive *= math.exp(-total)
    return cumulative


def lifetime_with_ci(age_data: dict[int, dict[str, int]], field: str, mu: dict[int, float]) -> tuple[float, float, float]:
    probs = {age: values[field] / values["person_years"] for age, values in age_data.items()}
    estimate = cumulative_risk(probs, mu)
    variance = 0.0
    for age in range(18, 80):
        values = age_data.get(age)
        if not values or values["person_years"] <= 0:
            continue
        p = probs[age]
        n = values["person_years"]
        step = max(1e-9, min(1e-6, max(p, 1e-6) * 1e-3))
        upper_probs = dict(probs)
        lower_probs = dict(probs)
        upper_probs[age] = min(p + step, 1.0 - 1e-12)
        lower_probs[age] = max(p - step, 0.0)
        denom = upper_probs[age] - lower_probs[age]
        derivative = (cumulative_risk(upper_probs, mu) - cumulative_risk(lower_probs, mu)) / denom
        variance += derivative * derivative * p * (1.0 - p) / n
    se = math.sqrt(max(variance, 0.0))
    if estimate <= 0.0 or estimate >= 1.0 or se == 0.0:
        return estimate, max(0.0, estimate - 1.96 * se), min(1.0, estimate + 1.96 * se)
    logit = math.log(estimate / (1.0 - estimate))
    se_logit = se / (estimate * (1.0 - estimate))
    logistic = lambda x: 1.0 / (1.0 + math.exp(-x))
    return estimate, logistic(logit - 1.959963984540054 * se_logit), logistic(logit + 1.959963984540054 * se_logit)


def aggregate_years(
    year_age: dict[tuple[int, int], dict[str, int]], years: set[int]
) -> dict[int, dict[str, int]]:
    result: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for (year, age), values in year_age.items():
        if year not in years:
            continue
        for field, value in values.items():
            result[age][field] += value
    return dict(result)


def wu_reestimated(endpoint: str, mu: dict[int, float]) -> tuple[float, float]:
    probabilities = {}
    for age in range(18, 90):
        index = next(i for i, (lo, hi) in enumerate(WU_BANDS) if lo <= age <= hi)
        probabilities[age] = WU_RATES[endpoint][index] / 1000.0
    adjusted = cumulative_risk(probabilities, mu)
    unadjusted = cumulative_risk(probabilities, {age: 0.0 for age in mu})
    return adjusted, unadjusted


def directly_standardized_annual_rates(
    age_data: dict[int, dict[str, int]],
    year_age: dict[tuple[int, int], dict[str, int]],
) -> dict[int, dict[str, float]]:
    total_py = sum(values["person_years"] for values in age_data.values())
    weights = {age: values["person_years"] / total_py for age, values in age_data.items()}
    result: dict[int, dict[str, float]] = defaultdict(dict)
    years = sorted({year for year, _age in year_age})
    for year in years:
        for endpoint, field in ENDPOINTS.items():
            result[year][endpoint] = 1000.0 * sum(
                weights[age] * year_age[(year, age)][field] / year_age[(year, age)]["person_years"]
                for age in weights
            )
    return dict(result)


def age_partition_rows(age_data: dict[int, dict[str, int]]) -> list[dict[str, str | int]]:
    """Build disclosure-safe mutually exclusive components of the union rate.

    The supplied phenotype flags are annual. The overlap category therefore
    means SUI and POP were both recorded in the same eligible woman-year; it
    does not imply that the procedures occurred on the same day.
    """
    rows: list[dict[str, str | int]] = []
    for lo, hi in COMPOSITION_BANDS:
        values: dict[str, int] = defaultdict(int)
        for age in range(lo, hi + 1):
            if age not in age_data:
                raise AssertionError(f"Missing age {age} from P01 age data")
            for field, value in age_data[age].items():
                values[field] += value
        both = values["both_same_year"]
        sui_only = values["sui_operations"] - both
        pop_only = values["pop_operations"] - both
        either = values["any_operations"]
        if min(sui_only, pop_only, both) < 0 or sui_only + pop_only + both != either:
            raise AssertionError((lo, hi, sui_only, pop_only, both, either))
        if any(0 < count < 11 for count in (sui_only, pop_only, both)):
            raise AssertionError(f"Protected P01 age-partition cell in ages {lo}-{hi}")
        person_years = values["person_years"]
        rows.append({
            "age_band": f"{lo}-{hi}",
            "person_years": person_years,
            "sui_only_operation_person_years": sui_only,
            "pop_only_operation_person_years": pop_only,
            "both_same_year_operation_person_years": both,
            "either_operation_person_years": either,
            "sui_only_rate_per_1000": f"{1000.0 * sui_only / person_years:.3f}",
            "pop_only_rate_per_1000": f"{1000.0 * pop_only / person_years:.3f}",
            "both_same_year_rate_per_1000": f"{1000.0 * both / person_years:.3f}",
            "either_rate_per_1000": f"{1000.0 * either / person_years:.3f}",
            "both_share_of_either_percent": f"{100.0 * both / either:.1f}",
        })
    return rows


def make_sensitivity_tables(
    age_data: dict[int, dict[str, int]],
    year_age: dict[tuple[int, int], dict[str, int]],
    mu: dict[int, float],
) -> None:
    eras = (
        ("2014-2019", set(range(2014, 2020))),
        ("2020-2021", {2020, 2021}),
        ("2022-2024", {2022, 2023, 2024}),
    )
    era_rows = []
    for label, years in eras:
        era_age = aggregate_years(year_age, years)
        for endpoint, field in ENDPOINTS.items():
            estimate, lower, upper = lifetime_with_ci(era_age, field, mu)
            era_rows.append({
                "period": label,
                "endpoint": endpoint,
                "estimate_percent": f"{100 * estimate:.2f}",
                "ci95_lower_percent": f"{100 * lower:.2f}",
                "ci95_upper_percent": f"{100 * upper:.2f}",
            })
    write_rows(DATA / "Table5_period_specific_cumulative_risk.csv", era_rows, list(era_rows[0]))

    base_probs = {
        endpoint: {age: values[field] / values["person_years"] for age, values in age_data.items()}
        for endpoint, field in ENDPOINTS.items()
    }
    sensitivity_rows = []
    for endpoint in ("SUI", "POP", "Either"):
        base = cumulative_risk(base_probs[endpoint], mu)
        sensitivity_rows.append({
            "endpoint": endpoint,
            "specification": "Primary pooled 2014-2024 schedule",
            "estimate_percent": f"{100 * base:.2f}",
            "difference_from_primary_points": "0.00",
        })

        seam = dict(base_probs[endpoint])
        for age in range(65, 69):
            seam[age] = base_probs[endpoint][64] + (
                base_probs[endpoint][69] - base_probs[endpoint][64]
            ) * (age - 64) / 5.0
        seam_value = cumulative_risk(seam, mu)
        sensitivity_rows.append({
            "endpoint": endpoint,
            "specification": "Linear interpolation of ages 65-68 between ages 64 and 69",
            "estimate_percent": f"{100 * seam_value:.2f}",
            "difference_from_primary_points": f"{100 * (seam_value - base):+.2f}",
        })

        aligned = {
            age: 0.5 * (base_probs[endpoint][age] + base_probs[endpoint].get(age + 1, base_probs[endpoint][age]))
            for age in base_probs[endpoint]
        }
        aligned_value = cumulative_risk(aligned, mu)
        sensitivity_rows.append({
            "endpoint": endpoint,
            "specification": "Half-year age alignment sensitivity",
            "estimate_percent": f"{100 * aligned_value:.2f}",
            "difference_from_primary_points": f"{100 * (aligned_value - base):+.2f}",
        })

        mortality_85 = cumulative_risk(base_probs[endpoint], {age: 0.85 * value for age, value in mu.items()})
        sensitivity_rows.append({
            "endpoint": endpoint,
            "specification": "Mortality hazards scaled to 85% of US female life table",
            "estimate_percent": f"{100 * mortality_85:.2f}",
            "difference_from_primary_points": f"{100 * (mortality_85 - base):+.2f}",
        })

    no_bulking_path = AUDIT / "p01_no_bulking_lifetime_risk.csv"
    if no_bulking_path.exists():
        for row in read_rows(no_bulking_path):
            endpoint = "SUI" if row["endpoint"].startswith("SUI") else "Either"
            value = float(row["cumulative_risk_percent"]) / 100.0
            base = cumulative_risk(base_probs[endpoint], mu)
            sensitivity_rows.append({
                "endpoint": endpoint,
                "specification": "Exclude urethral bulking (CPT 51715)",
                "estimate_percent": f"{100 * value:.2f}",
                "difference_from_primary_points": f"{100 * (value - base):+.2f}",
            })
    write_rows(DATA / "Table6_deterministic_sensitivity_analysis.csv", sensitivity_rows, list(sensitivity_rows[0]))

    washout_rows = []
    for years in (1, 3, 5, 7, 10):
        washout_age: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for database in DATABASES:
            for row in read_rows(PAPER / "03 Data" / f"{database}_washout{years:02d}.csv"):
                year = as_int(row["study_year"])
                age = as_int(row["age_at_index"])
                if 2014 <= year <= 2024 and 18 <= age <= 89:
                    washout_age[age]["person_years"] += as_int(row["py"])
                    washout_age[age]["any_operations"] += as_int(row["n_union"])
        estimate, lower, upper = lifetime_with_ci(washout_age, "any_operations", mu)
        washout_rows.append({
            "washout_years": years,
            "woman_years": sum(row["person_years"] for row in washout_age.values()),
            "qualifying_operation_person_years": sum(row["any_operations"] for row in washout_age.values()),
            "either_estimate_percent": f"{100 * estimate:.2f}",
            "ci95_lower_percent": f"{100 * lower:.2f}",
            "ci95_upper_percent": f"{100 * upper:.2f}",
        })
    write_rows(DATA / "Table7_washout_sensitivity.csv", washout_rows, list(washout_rows[0]))

    either_sensitivity = {
        row["specification"]: float(row["estimate_percent"])
        for row in sensitivity_rows
        if row["endpoint"] == "Either"
    }
    washout_by_year = {
        as_int(row["washout_years"]): float(row["either_estimate_percent"])
        for row in washout_rows
    }
    tornado_rows = [
        {
            "analysis_choice": "Prior-surgery washout",
            "low_specification": "10-year washout",
            "low_estimate_percent": f"{washout_by_year[10]:.2f}",
            "primary_specification": "5-year washout",
            "primary_estimate_percent": f"{washout_by_year[5]:.2f}",
            "high_specification": "1-year washout",
            "high_estimate_percent": f"{washout_by_year[1]:.2f}",
        },
        {
            "analysis_choice": "Urethral bulking",
            "low_specification": "Exclude CPT 51715",
            "low_estimate_percent": f"{either_sensitivity['Exclude urethral bulking (CPT 51715)']:.2f}",
            "primary_specification": "Include CPT 51715",
            "primary_estimate_percent": f"{washout_by_year[5]:.2f}",
            "high_specification": "Include CPT 51715",
            "high_estimate_percent": f"{washout_by_year[5]:.2f}",
        },
        {
            "analysis_choice": "Mortality hazards",
            "low_specification": "US female life table",
            "low_estimate_percent": f"{washout_by_year[5]:.2f}",
            "primary_specification": "US female life table",
            "primary_estimate_percent": f"{washout_by_year[5]:.2f}",
            "high_specification": "85% of life-table hazards",
            "high_estimate_percent": f"{either_sensitivity['Mortality hazards scaled to 85% of US female life table']:.2f}",
        },
        {
            "analysis_choice": "Age alignment",
            "low_specification": "Year-attained age",
            "low_estimate_percent": f"{washout_by_year[5]:.2f}",
            "primary_specification": "Year-attained age",
            "primary_estimate_percent": f"{washout_by_year[5]:.2f}",
            "high_specification": "Half-year alignment",
            "high_estimate_percent": f"{either_sensitivity['Half-year age alignment sensitivity']:.2f}",
        },
        {
            "analysis_choice": "Ages 65-68 schedule",
            "low_specification": "Observed rates",
            "low_estimate_percent": f"{washout_by_year[5]:.2f}",
            "primary_specification": "Observed rates",
            "primary_estimate_percent": f"{washout_by_year[5]:.2f}",
            "high_specification": "Linear interpolation",
            "high_estimate_percent": f"{either_sensitivity['Linear interpolation of ages 65-68 between ages 64 and 69']:.2f}",
        },
    ]
    write_rows(DATA / "Figure4_deterministic_tornado_data.csv", tornado_rows, list(tornado_rows[0]))


def make_tables(age_data: dict[int, dict[str, int]], year_age: dict[tuple[int, int], dict[str, int]], mu: dict[int, float]) -> None:
    by_band: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for age, values in age_data.items():
        band = band_for(age)
        for field, value in values.items():
            by_band[band][field] += value

    table1 = []
    total_py = sum(v["person_years"] for v in by_band.values())
    for lo, hi in WU_BANDS:
        band = f"{lo}-{hi}"
        values = by_band[band]
        table1.append({
            "age_band": band,
            "person_years": values["person_years"],
            "percent_person_time": f"{100.0 * values['person_years'] / total_py:.1f}",
            "qualifying_operation_person_years": values["any_operations"],
            "rate_per_1000": f"{1000.0 * values['any_operations'] / values['person_years']:.2f}",
        })
    table1.append({
        "age_band": "Total",
        "person_years": total_py,
        "percent_person_time": "100.0",
        "qualifying_operation_person_years": sum(v["any_operations"] for v in by_band.values()),
        "rate_per_1000": f"{1000.0 * sum(v['any_operations'] for v in by_band.values()) / total_py:.2f}",
    })
    write_rows(DATA / "Table1_cohort_by_age.csv", table1, list(table1[0]))

    table2 = []
    for band_index, (lo, hi) in enumerate(WU_BANDS):
        band = f"{lo}-{hi}"
        values = by_band[band]
        for endpoint, field in ENDPOINTS.items():
            events = values[field]
            py = values["person_years"]
            lower, upper = wilson(events, py)
            table2.append({
                "age_band": band,
                "endpoint": endpoint,
                "person_years": py,
                "operations": events,
                "rate_per_1000": f"{1000.0 * events / py:.3f}",
                "ci95_lower_per_1000": f"{1000.0 * lower:.3f}",
                "ci95_upper_per_1000": f"{1000.0 * upper:.3f}",
                "wu_2007_2011_rate_per_1000": f"{WU_RATES[endpoint][band_index]:.1f}",
            })
    write_rows(DATA / "Table2_age_specific_rates.csv", table2, list(table2[0]))

    table3 = []
    for endpoint, field in ENDPOINTS.items():
        estimate, lower, upper = lifetime_with_ci(age_data, field, mu)
        wu_adjusted, wu_unadjusted = wu_reestimated(endpoint, mu)
        table3.append({
            "endpoint": endpoint,
            "current_estimate_percent": f"{100.0 * estimate:.2f}",
            "ci95_lower_percent": f"{100.0 * lower:.2f}",
            "ci95_upper_percent": f"{100.0 * upper:.2f}",
            "wu_published_percent": f"{WU_LIFETIME[endpoint]:.1f}",
            "wu_rates_current_recursion_percent": f"{100.0 * wu_adjusted:.2f}",
            "wu_rates_without_mortality_percent": f"{100.0 * wu_unadjusted:.2f}",
            "like_for_like_difference_points": f"{100.0 * (estimate - wu_adjusted):.2f}",
        })
    write_rows(DATA / "Table3_lifetime_risk.csv", table3, list(table3[0]))

    partition = age_partition_rows(age_data)
    write_rows(DATA / "Figure3_age_partition_data.csv", partition, list(partition[0]))

    either_row = next(row for row in table3 if row["endpoint"] == "Either")
    wu_published = float(either_row["wu_published_percent"])
    wu_without_mortality = float(either_row["wu_rates_without_mortality_percent"])
    wu_harmonized = float(either_row["wu_rates_current_recursion_percent"])
    current = float(either_row["current_estimate_percent"])
    ladder_rows = [
        {
            "stage": "Wu et al. published estimate",
            "estimate_percent": f"{wu_published:.2f}",
            "change_from_prior_points": "",
            "interpretation": "Published benchmark",
        },
        {
            "stage": "Wu rounded age-band rates, no competing mortality",
            "estimate_percent": f"{wu_without_mortality:.2f}",
            "change_from_prior_points": f"{wu_without_mortality - wu_published:+.2f}",
            "interpretation": "Reconstruction and rounding",
        },
        {
            "stage": "Wu rates under current recursion and mortality input",
            "estimate_percent": f"{wu_harmonized:.2f}",
            "change_from_prior_points": f"{wu_harmonized - wu_without_mortality:+.2f}",
            "interpretation": "Harmonized calculation",
        },
        {
            "stage": "Current 2014-2024 rate schedule",
            "estimate_percent": f"{current:.2f}",
            "change_from_prior_points": f"{current - wu_harmonized:+.2f}",
            "interpretation": "Like-for-like rate-schedule difference",
        },
    ]
    write_rows(DATA / "Figure5_wu_comparison_ladder_data.csv", ladder_rows, list(ladder_rows[0]))

    annual: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for (year, _age), values in year_age.items():
        for field, value in values.items():
            annual[year][field] += value
    standardized = directly_standardized_annual_rates(age_data, year_age)
    table4 = []
    for year in sorted(annual):
        values = annual[year]
        row = {"study_year": year, "person_years": values["person_years"]}
        for endpoint, field in ENDPOINTS.items():
            row[f"{endpoint.lower()}_operations"] = values[field]
            row[f"{endpoint.lower()}_rate_per_1000"] = f"{1000.0 * values[field] / values['person_years']:.3f}"
            row[f"{endpoint.lower()}_age_standardized_rate_per_1000"] = f"{standardized[year][endpoint]:.3f}"
        table4.append(row)
    write_rows(DATA / "Table4_annual_crude_rates.csv", table4, list(table4[0]))
    make_sensitivity_tables(age_data, year_age, mu)


def make_figures() -> None:
    def text(x: float, y: float, value: str, size: int = 12, anchor: str = "start",
             color: str = INK, weight: int = 400, rotate: int | None = None) -> str:
        transform = f' transform="rotate({rotate} {x:.1f} {y:.1f})"' if rotate is not None else ""
        return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Helvetica,Arial,sans-serif" '
                f'font-size="{size}" text-anchor="{anchor}" fill="{color}" font-weight="{weight}"{transform}>'
                f'{html.escape(value)}</text>')

    def save_svg(path: Path, width: int, height: int, parts: list[str], title: str) -> None:
        content = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}" role="img" aria-label="{html.escape(title)}">',
            f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>',
            *parts,
            "</svg>",
        ]
        path.write_text("\n".join(content) + "\n")

    rates = read_rows(DATA / "Table2_age_specific_rates.csv")
    labels = [f"{lo}-{hi}" for lo, hi in WU_BANDS]
    width, height = 1180, 480
    parts = [
        text(44, 34, "Figure 1. Age-specific pelvic floor operation rates", 18, weight=700),
        text(44, 56, "2014-2024 compared with Wu et al. 2007-2011; rates per 1,000 eligible woman-years", 12, color=GREY),
    ]
    left, top, bottom, panel_width, gap = 74, 100, 380, 310, 60
    y_max = 6.0
    for panel, endpoint in enumerate(("SUI", "POP", "Either")):
        panel_left = left + panel * (panel_width + gap)
        panel_right = panel_left + panel_width
        y = lambda value: bottom - (bottom - top) * value / y_max
        x = lambda index: panel_left + index * panel_width / (len(labels) - 1)
        rows = [r for r in rates if r["endpoint"] == endpoint]
        current = [float(r["rate_per_1000"]) for r in rows]
        lower = [float(r["ci95_lower_per_1000"]) for r in rows]
        upper = [float(r["ci95_upper_per_1000"]) for r in rows]
        for tick in range(0, 7):
            parts.append(f'<line x1="{panel_left}" y1="{y(tick):.1f}" x2="{panel_right}" y2="{y(tick):.1f}" stroke="{LIGHT}" stroke-width="1"/>')
            if panel == 0:
                parts.append(text(panel_left - 10, y(tick) + 4, str(tick), 10, anchor="end", color=GREY))
        parts.append(text((panel_left + panel_right) / 2, 88, endpoint, 14, anchor="middle", weight=700))
        current_points = " ".join(f"{x(i):.1f},{y(value):.1f}" for i, value in enumerate(current))
        wu_points = " ".join(f"{x(i):.1f},{y(value):.1f}" for i, value in enumerate(WU_RATES[endpoint]))
        parts.append(f'<polyline points="{wu_points}" fill="none" stroke="{GREY}" stroke-width="1.8" stroke-dasharray="6 5"/>')
        parts.append(f'<polyline points="{current_points}" fill="none" stroke="{COLORS[endpoint]}" stroke-width="2.5"/>')
        for i, value in enumerate(current):
            parts.append(f'<line x1="{x(i):.1f}" y1="{y(lower[i]):.1f}" x2="{x(i):.1f}" y2="{y(upper[i]):.1f}" stroke="{COLORS[endpoint]}" stroke-width="1.2"/>')
            parts.append(f'<line x1="{x(i)-4:.1f}" y1="{y(lower[i]):.1f}" x2="{x(i)+4:.1f}" y2="{y(lower[i]):.1f}" stroke="{COLORS[endpoint]}" stroke-width="1.2"/>')
            parts.append(f'<line x1="{x(i)-4:.1f}" y1="{y(upper[i]):.1f}" x2="{x(i)+4:.1f}" y2="{y(upper[i]):.1f}" stroke="{COLORS[endpoint]}" stroke-width="1.2"/>')
            parts.append(f'<circle cx="{x(i):.1f}" cy="{y(value):.1f}" r="4" fill="{COLORS[endpoint]}" stroke="#FFFFFF" stroke-width="1.5"/>')
            parts.append(f'<rect x="{x(i)-3.5:.1f}" y="{y(WU_RATES[endpoint][i])-3.5:.1f}" width="7" height="7" fill="#FFFFFF" stroke="{GREY}" stroke-width="1.4"/>')
            parts.append(text(x(i), bottom + 20, labels[i], 9, anchor="end", color=GREY, rotate=-45))
        parts.append(f'<line x1="{panel_left}" y1="{bottom}" x2="{panel_right}" y2="{bottom}" stroke="{INK}" stroke-width="1"/>')
    parts.append(text(18, (top + bottom) / 2, "Operations per 1,000", 11, anchor="middle", rotate=-90))
    parts.append(f'<line x1="420" y1="420" x2="448" y2="420" stroke="{INK}" stroke-width="2.5"/>')
    parts.append(f'<circle cx="434" cy="420" r="4" fill="{INK}"/>')
    parts.append(text(456, 424, "2014-2024 (95% Wilson CI)", 10, color=GREY))
    parts.append(f'<line x1="655" y1="420" x2="683" y2="420" stroke="{GREY}" stroke-width="1.8" stroke-dasharray="6 5"/>')
    parts.append(f'<rect x="666" y="416.5" width="7" height="7" fill="#FFFFFF" stroke="{GREY}" stroke-width="1.4"/>')
    parts.append(text(691, 424, "Wu et al. 2007-2011", 10, color=GREY))
    parts.append(text(width / 2, 458, "Inclusive SUI and POP rates overlap; Either is their union.", 10, anchor="middle", color=GREY))
    save_svg(FIGURES / "Figure1_age_specific_rates.svg", width, height, parts, "Age-specific pelvic floor operation rates")

    annual = read_rows(DATA / "Table4_annual_crude_rates.csv")
    years = [as_int(r["study_year"]) for r in annual]
    width, height = 860, 500
    left, right, top, bottom = 84, 802, 92, 402
    y_max = 3.0
    x = lambda year: left + (right - left) * (year - min(years)) / (max(years) - min(years))
    y = lambda value: bottom - (bottom - top) * value / y_max
    parts = [
        text(42, 34, "Figure 2. Annual crude pelvic floor operation rates, 2014-2024", 17, weight=700),
        text(42, 56, "Operations per 1,000 eligible woman-years; descriptive temporal pattern", 12, color=GREY),
    ]
    for tick in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
        parts.append(f'<line x1="{left}" y1="{y(tick):.1f}" x2="{right}" y2="{y(tick):.1f}" stroke="{LIGHT}" stroke-width="1"/>')
        parts.append(text(left - 10, y(tick) + 4, f"{tick:.1f}", 10, anchor="end", color=GREY))
    for year in years:
        parts.append(text(x(year), bottom + 21, str(year), 9, anchor="middle", color=GREY))
    for endpoint, marker in (("Either", "circle"), ("POP", "square"), ("SUI", "triangle")):
        values = [float(r[f"{endpoint.lower()}_rate_per_1000"]) for r in annual]
        points = " ".join(f"{x(year):.1f},{y(value):.1f}" for year, value in zip(years, values))
        parts.append(f'<polyline points="{points}" fill="none" stroke="{COLORS[endpoint]}" stroke-width="2.5"/>')
        for year, value in zip(years, values):
            cx, cy = x(year), y(value)
            if marker == "circle":
                parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="{COLORS[endpoint]}" stroke="#FFFFFF" stroke-width="1.2"/>')
            elif marker == "square":
                parts.append(f'<rect x="{cx-3.5:.1f}" y="{cy-3.5:.1f}" width="7" height="7" fill="{COLORS[endpoint]}" stroke="#FFFFFF" stroke-width="1.2"/>')
            else:
                parts.append(f'<path d="M{cx:.1f},{cy-4.5:.1f} L{cx-4.2:.1f},{cy+3.5:.1f} L{cx+4.2:.1f},{cy+3.5:.1f} Z" fill="{COLORS[endpoint]}" stroke="#FFFFFF" stroke-width="1.2"/>')
    parts.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="{INK}" stroke-width="1"/>')
    parts.append(text(22, (top + bottom) / 2, "Operations per 1,000", 11, anchor="middle", rotate=-90))
    legend_x = 230
    for endpoint in ("Either", "POP", "SUI"):
        parts.append(f'<line x1="{legend_x}" y1="435" x2="{legend_x+28}" y2="435" stroke="{COLORS[endpoint]}" stroke-width="2.5"/>')
        parts.append(text(legend_x + 36, 439, endpoint, 10, color=GREY))
        legend_x += 150
    parts.append(text(width / 2, 476, "Annual values are descriptive.", 10, anchor="middle", color=GREY))
    save_svg(FIGURES / "Figure2_annual_crude_rates.svg", width, height, parts, "Annual crude pelvic floor operation rates")

    partition = read_rows(DATA / "Figure3_age_partition_data.csv")
    width, height = 1240, 650
    left, right, top, bottom = 92, 936, 96, 478
    labels = [row["age_band"] for row in partition]
    x = lambda index: left + (right - left) * index / (len(labels) - 1)
    y_max = 4.0
    y = lambda value: bottom - (bottom - top) * value / y_max
    sui_only = [float(row["sui_only_rate_per_1000"]) for row in partition]
    pop_only = [float(row["pop_only_rate_per_1000"]) for row in partition]
    both = [float(row["both_same_year_rate_per_1000"]) for row in partition]
    level_1 = sui_only
    level_2 = [a + b for a, b in zip(sui_only, pop_only)]
    level_3 = [a + b + c for a, b, c in zip(sui_only, pop_only, both)]

    def area_polygon(lower: list[float], upper: list[float]) -> str:
        upper_points = [(x(index), y(value)) for index, value in enumerate(upper)]
        lower_points = [(x(index), y(value)) for index, value in reversed(list(enumerate(lower)))]
        return " ".join(f"{px:.1f},{py:.1f}" for px, py in upper_points + lower_points)

    parts = [
        text(44, 34, "Figure 3. Age-specific operation rate, partitioned by annual outcome", 18, weight=700),
        text(44, 57, "Mutually exclusive components sum to the either-operation rate", 12, color=GREY),
    ]
    for tick in (0, 1, 2, 3, 4):
        parts.append(f'<line x1="{left}" y1="{y(tick):.1f}" x2="{right}" y2="{y(tick):.1f}" stroke="{LIGHT}" stroke-width="1"/>')
        parts.append(text(left - 12, y(tick) + 4, str(tick), 10, anchor="end", color=GREY))
    zero = [0.0] * len(partition)
    parts.append(f'<polygon points="{area_polygon(zero, level_1)}" fill="{BLUE}" fill-opacity="0.90"/>')
    parts.append(f'<polygon points="{area_polygon(level_1, level_2)}" fill="{GOLD}" fill-opacity="0.92"/>')
    parts.append(f'<polygon points="{area_polygon(level_2, level_3)}" fill="{PURPLE}" fill-opacity="0.92"/>')
    for boundary in (level_1, level_2):
        points = " ".join(f"{x(index):.1f},{y(value):.1f}" for index, value in enumerate(boundary))
        parts.append(f'<polyline points="{points}" fill="none" stroke="#FFFFFF" stroke-width="2.0"/>')
    envelope = " ".join(f"{x(index):.1f},{y(value):.1f}" for index, value in enumerate(level_3))
    parts.append(f'<polyline points="{envelope}" fill="none" stroke="{INK}" stroke-width="3.0"/>')
    for index, label in enumerate(labels):
        parts.append(text(x(index), bottom + 22, label, 9, anchor="middle", color=GREY))
    parts.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="{INK}" stroke-width="1"/>')
    parts.append(text(22, (top + bottom) / 2, "Operations per 1,000 woman-years", 11, anchor="middle", rotate=-90))
    parts.append(text((left + right) / 2, bottom + 52, "Age band (years)", 11, anchor="middle", color=GREY))

    legend_x = 982
    legend_items = (
        (INK, "Either (envelope)", "all qualifying operation-person-years"),
        (PURPLE, "Both outcomes in year", "6.2% at 18-29; 34.9% at 75-79"),
        (GOLD, "POP only", "POP recorded without SUI that year"),
        (BLUE, "SUI only", "SUI recorded without POP that year"),
    )
    for index, (color, label, detail) in enumerate(legend_items):
        legend_y = 120 + index * 82
        parts.append(f'<rect x="{legend_x}" y="{legend_y-13}" width="18" height="18" rx="3" fill="{color}"/>')
        parts.append(text(legend_x + 28, legend_y + 1, label, 12, weight=700))
        parts.append(text(legend_x + 28, legend_y + 23, detail, 9, color=GREY))
    parts.append(text(44, 570, "The overlap category means both flags occurred in the same eligible woman-year; it does not establish same-day surgery.", 10, color=GREY))
    parts.append(text(44, 591, "Ages 18-29 are combined for disclosure control. The 65-69 denominator reflects the commercial-to-Medicare coverage seam.", 10, color=GREY))
    parts.append(text(44, 612, "Rates are descriptive and are not population incidence rates.", 10, color=GREY))
    save_svg(FIGURES / "Figure3_age_partition.svg", width, height, parts, "Age-specific operation rate partitioned by annual outcome")

    tornado = read_rows(DATA / "Figure4_deterministic_tornado_data.csv")
    width, height = 1160, 630
    left, right, top, bottom = 350, 1072, 116, 442
    x_min, x_max = 10.6, 12.0
    x = lambda value: left + (right - left) * (value - x_min) / (x_max - x_min)
    primary = 11.34
    ci_low, ci_high = 11.21, 11.47
    row_gap = 61
    parts = [
        text(44, 34, "Figure 4. Deterministic sensitivity analysis of lifetime risk", 18, weight=700),
        text(44, 57, "Either SUI or POP operation by age 80; one analysis choice varied at a time", 12, color=GREY),
        f'<rect x="{x(ci_low):.1f}" y="{top-18}" width="{x(ci_high)-x(ci_low):.1f}" height="{bottom-top+36}" fill="{LIGHT}" fill-opacity="0.62"/>',
        f'<line x1="{x(primary):.1f}" y1="{top-18}" x2="{x(primary):.1f}" y2="{bottom+18}" stroke="{INK}" stroke-width="2" stroke-dasharray="6 5"/>',
    ]
    for tick in (10.6, 10.8, 11.0, 11.2, 11.4, 11.6, 11.8, 12.0):
        parts.append(f'<line x1="{x(tick):.1f}" y1="{top-18}" x2="{x(tick):.1f}" y2="{bottom+18}" stroke="{LIGHT}" stroke-width="1"/>')
        parts.append(text(x(tick), bottom + 43, f"{tick:.1f}", 9, anchor="middle", color=GREY))
    for index, row in enumerate(tornado):
        row_y = top + index * row_gap
        low = float(row["low_estimate_percent"])
        high = float(row["high_estimate_percent"])
        parts.append(text(44, row_y - 3, row["analysis_choice"], 12, weight=700))
        parts.append(text(44, row_y + 17, f"{row['low_specification']} to {row['high_specification']}", 9, color=GREY))
        parts.append(f'<line x1="{x(low):.1f}" y1="{row_y}" x2="{x(high):.1f}" y2="{row_y}" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>')
        if low < primary:
            parts.append(f'<line x1="{x(low):.1f}" y1="{row_y}" x2="{x(primary):.1f}" y2="{row_y}" stroke="{GOLD}" stroke-width="8" stroke-linecap="round"/>')
        if high > primary:
            parts.append(f'<line x1="{x(primary):.1f}" y1="{row_y}" x2="{x(high):.1f}" y2="{row_y}" stroke="{BLUE}" stroke-width="8" stroke-linecap="round"/>')
        parts.append(f'<circle cx="{x(low):.1f}" cy="{row_y}" r="5" fill="{GOLD if low < primary else INK}" stroke="#FFFFFF" stroke-width="1.5"/>')
        parts.append(f'<circle cx="{x(high):.1f}" cy="{row_y}" r="5" fill="{BLUE if high > primary else INK}" stroke="#FFFFFF" stroke-width="1.5"/>')
        parts.append(text(x(low) - 8, row_y - 10, f"{low:.2f}", 9, anchor="end", color=GOLD if low < primary else INK, weight=700))
        parts.append(text(x(high) + 8, row_y - 10, f"{high:.2f}", 9, color=BLUE if high > primary else INK, weight=700))
    parts.append(text(x(primary) + 8, 94, "Primary 11.34%", 10, color=INK, weight=700))
    parts.append(text((x(ci_low) + x(ci_high)) / 2, 513, "Primary sampling 95% CI: 11.21%-11.47%", 9, anchor="middle", color=GREY))
    parts.append(text((left + right) / 2, 544, "Estimated cumulative risk to age 80 (%)", 11, anchor="middle", color=GREY))
    parts.append(text(44, 592, "Ranges are deterministic one-at-a-time analyses and do not form a joint uncertainty interval.", 10, color=GREY))
    save_svg(FIGURES / "Figure4_deterministic_tornado.svg", width, height, parts, "Deterministic sensitivity analysis tornado plot")

    ladder = read_rows(DATA / "Figure5_wu_comparison_ladder_data.csv")
    width, height = 1240, 660
    left, right, top, bottom = 104, 1136, 100, 434
    x_positions = (150, 440, 735, 1030)
    y_min, y_max = 10.0, 21.0
    y = lambda value: bottom - (bottom - top) * (value - y_min) / (y_max - y_min)
    colors = (GREY, GREY, GOLD, BLUE)
    parts = [
        text(44, 34, "Figure 5. Accounting bridge from Wu et al.'s 20.0% estimate to 11.34%", 18, weight=700),
        text(44, 57, "Published benchmark, reconstructed inputs, harmonized calculation, and current rate schedule", 12, color=GREY),
    ]
    for tick in (10, 12, 14, 16, 18, 20):
        parts.append(f'<line x1="{left}" y1="{y(tick):.1f}" x2="{right}" y2="{y(tick):.1f}" stroke="{LIGHT}" stroke-width="1"/>')
        parts.append(text(left - 12, y(tick) + 4, f"{tick}%", 10, anchor="end", color=GREY))
    values = [float(row["estimate_percent"]) for row in ladder]
    for index, (row, value, color) in enumerate(zip(ladder, values, colors)):
        px, py = x_positions[index], y(value)
        parts.append(f'<line x1="{px-62}" y1="{py:.1f}" x2="{px+62}" y2="{py:.1f}" stroke="{color}" stroke-width="7" stroke-linecap="round"/>')
        parts.append(f'<circle cx="{px}" cy="{py:.1f}" r="7" fill="{color}" stroke="#FFFFFF" stroke-width="2"/>')
        parts.append(text(px, py - 17, f"{value:.2f}%", 15, anchor="middle", color=color, weight=700))
        if index < len(values) - 1:
            next_x, next_y = x_positions[index + 1], y(values[index + 1])
            parts.append(f'<line x1="{px+64}" y1="{py:.1f}" x2="{next_x-64}" y2="{next_y:.1f}" stroke="{INK}" stroke-width="2"/>')
            delta = float(ladder[index + 1]["change_from_prior_points"])
            delta_color = BLUE if delta < 0 else GREY
            parts.append(text((px + next_x) / 2, (py + next_y) / 2 - 10, f"{delta:+.2f} points", 11, anchor="middle", color=delta_color, weight=700))
    stage_lines = (
        ("Wu et al.", "published estimate", "20.0%"),
        ("Reconstruct Wu's rounded", "age-band rates without", "competing mortality"),
        ("Apply current recursion", "and 2019 mortality to", "the same Wu rates"),
        ("Replace with current", "2014-2024 rate schedule", "using the same recursion"),
    )
    for px, lines in zip(x_positions, stage_lines):
        for line_index, line in enumerate(lines):
            parts.append(text(px, 468 + line_index * 18, line, 10, anchor="middle", color=INK if line_index == 0 else GREY, weight=700 if line_index == 0 else 400))
    bracket_y = 540
    parts.append(f'<line x1="{x_positions[0]}" y1="{bracket_y}" x2="{x_positions[-1]}" y2="{bracket_y}" stroke="{INK}" stroke-width="1.5"/>')
    parts.append(f'<line x1="{x_positions[0]}" y1="{bracket_y-7}" x2="{x_positions[0]}" y2="{bracket_y+7}" stroke="{INK}" stroke-width="1.5"/>')
    parts.append(f'<line x1="{x_positions[-1]}" y1="{bracket_y-7}" x2="{x_positions[-1]}" y2="{bracket_y+7}" stroke="{INK}" stroke-width="1.5"/>')
    parts.append(text((x_positions[0] + x_positions[-1]) / 2, bracket_y - 9, "Published benchmark-to-current gap: -8.66 percentage points", 11, anchor="middle", weight=700))
    parts.append(text(44, 584, "Wu et al. reported a competing-mortality adjustment. The 20.08%-to-18.15% step harmonizes the rounded published rates", 9, color=GREY))
    parts.append(text(44, 602, "under our explicit recursion; it is not evidence that Wu omitted mortality. The like-for-like rate-schedule difference is -6.81 points.", 9, color=GREY))
    parts.append(text(44, 620, "All differences are descriptive; periods, insured populations, coverage, coding, and practice may differ.", 9, color=GREY))
    save_svg(FIGURES / "Figure5_wu_comparison_ladder.svg", width, height, parts, "Accounting bridge from Wu et al. published estimate to current estimate")


def write_summary() -> None:
    totals = [r for r in read_rows(INPUT / "P01_wu_totals.csv") if r["database"] == "Pooled"][0]
    lifetime = read_rows(DATA / "Table3_lifetime_risk.csv")
    lookup = {r["endpoint"]: r for r in lifetime}
    lines = [
        "P01 Wu-comparable rerun summary",
        "Run date: 2026-09-04",
        "",
        f"Eligible woman-years: {as_int(totals['person_years']):,}",
        f"Qualifying operation-person-years: {as_int(totals['any_operations']):,}",
        f"Unique operated women: {as_int(totals['unique_operated_women']):,}",
        f"Repeat qualifying woman-years: {as_int(totals['any_operations']) - as_int(totals['unique_operated_women']):,}",
        f"Inclusive SUI operation-person-years: {as_int(totals['sui_operations']):,}",
        f"Inclusive POP operation-person-years: {as_int(totals['pop_operations']):,}",
        f"Same-year SUI and POP overlap: {as_int(totals['both_same_year']):,}",
        "",
        "Cumulative risk to age 80, competing mortality included:",
    ]
    for endpoint in ("SUI", "POP", "Either"):
        row = lookup[endpoint]
        lines.append(
            f"- {endpoint}: {row['current_estimate_percent']}% "
            f"(95% CI {row['ci95_lower_percent']}-{row['ci95_upper_percent']}%); "
            f"Wu et al. published {row['wu_published_percent']}%; "
            f"Wu age-band rates under the current recursion {row['wu_rates_current_recursion_percent']}%"
        )
    lines.extend((
        "",
        "Method note: deterministic age-specific competing-risk life table with delta-method confidence limits.",
    ))
    (DATA / "P01_wu_summary.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    shutil.copy2(INPUT / "P01_wu_totals.csv", DATA / "P01_wu_totals.csv")
    age_data = pool_age()
    year_age = pool_year_age()
    mu = mortality_hazards()
    make_tables(age_data, year_age, mu)
    make_figures()
    write_summary()

    totals = [r for r in read_rows(INPUT / "P01_wu_totals.csv") if r["database"] == "Pooled"][0]
    assert as_int(totals["person_years"]) == 47_258_198
    assert as_int(totals["any_operations"]) == 102_440
    assert as_int(totals["unique_operated_women"]) == 102_107
    print((DATA / "P01_wu_summary.txt").read_text())


if __name__ == "__main__":
    main()
