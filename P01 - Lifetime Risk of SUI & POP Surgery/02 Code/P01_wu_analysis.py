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
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
PAPER = HERE.parent
DATA = PAPER / "03 Data" / "Wu Comparable 2026-09-01"
FIGURES = PAPER / "04 Figures" / "Wu Comparable 2026-09-01"
FIGURES.mkdir(parents=True, exist_ok=True)

QX_FILE = HERE / "nchs2019_female_qx.csv"
DATABASES = ("CCAE", "MDCR")
ENDPOINTS = {
    "SUI": "sui_operations",
    "POP": "pop_operations",
    "Either": "any_operations",
}
WU_BANDS = ((18, 29), (30, 39), (40, 49), (50, 59), (60, 69), (70, 79), (80, 89))
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
        for row in read_rows(DATA / f"{db}_wu_by_age.csv"):
            age = as_int(row["age"])
            for field in ("person_years", "sui_operations", "pop_operations", "any_operations", "both_same_year"):
                pooled[age][field] += as_int(row[field])
    return dict(sorted(pooled.items()))


def pool_year_age() -> dict[tuple[int, int], dict[str, int]]:
    pooled: dict[tuple[int, int], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for db in DATABASES:
        for row in read_rows(DATA / f"{db}_wu_by_year_age.csv"):
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
        table3.append({
            "endpoint": endpoint,
            "current_estimate_percent": f"{100.0 * estimate:.2f}",
            "ci95_lower_percent": f"{100.0 * lower:.2f}",
            "ci95_upper_percent": f"{100.0 * upper:.2f}",
            "wu_2007_2011_percent": f"{WU_LIFETIME[endpoint]:.1f}",
            "absolute_difference_percentage_points": f"{100.0 * estimate - WU_LIFETIME[endpoint]:.2f}",
        })
    write_rows(DATA / "Table3_lifetime_risk.csv", table3, list(table3[0]))

    annual: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for (year, _age), values in year_age.items():
        for field, value in values.items():
            annual[year][field] += value
    table4 = []
    for year in sorted(annual):
        values = annual[year]
        row = {"study_year": year, "person_years": values["person_years"]}
        for endpoint, field in ENDPOINTS.items():
            row[f"{endpoint.lower()}_operations"] = values[field]
            row[f"{endpoint.lower()}_rate_per_1000"] = f"{1000.0 * values[field] / values['person_years']:.3f}"
        table4.append(row)
    write_rows(DATA / "Table4_annual_crude_rates.csv", table4, list(table4[0]))


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


def write_summary() -> None:
    totals = [r for r in read_rows(DATA / "P01_wu_totals.csv") if r["database"] == "Pooled"][0]
    lifetime = read_rows(DATA / "Table3_lifetime_risk.csv")
    lookup = {r["endpoint"]: r for r in lifetime}
    lines = [
        "P01 Wu-comparable rerun summary",
        "Run date: 2026-09-02",
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
            f"Wu et al. {row['wu_2007_2011_percent']}%"
        )
    lines.extend((
        "",
        "Method note: deterministic age-specific competing-risk life table with delta-method confidence limits.",
    ))
    (DATA / "P01_wu_summary.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    age_data = pool_age()
    year_age = pool_year_age()
    mu = mortality_hazards()
    make_tables(age_data, year_age, mu)
    make_figures()
    write_summary()

    totals = [r for r in read_rows(DATA / "P01_wu_totals.csv") if r["database"] == "Pooled"][0]
    assert as_int(totals["person_years"]) > 0
    assert as_int(totals["any_operations"]) >= as_int(totals["unique_operated_women"])
    print((DATA / "P01_wu_summary.txt").read_text())


if __name__ == "__main__":
    main()
