#!/usr/bin/env python3
"""Build P03 publication tables and figures from disclosure-screened aggregates."""

from __future__ import annotations

import csv
import html
import math
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
PAPER = HERE.parent
INPUT = PAPER / "03 Data" / "Server Aggregates 2026-09-04"
OUTPUT = PAPER / "03 Data" / "Analysis 2026-09-04"
FIGURES = PAPER / "04 Figures" / "Analysis 2026-09-04"
OUTPUT.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

INK = "#18232D"
BLUE = "#2E6FA7"
GOLD = "#C08428"
PURPLE = "#76548F"
GREY = "#6F7C86"
LIGHT = "#DDE4E9"
PALE = "#F3F6F8"
AGE_ORDER = ["18-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80-84", "85-89"]
TEMPORAL_COMPARISONS = ((2014, 2019), (2019, 2020), (2020, 2024), (2014, 2024))


def read_rows(name: str) -> list[dict[str, str]]:
    with (INPUT / name).open(newline="") as handle:
        return list(csv.DictReader(handle))


def integer(value: str | None) -> int | None:
    if value in (None, "", "SUPPRESSED"):
        return None
    return int(float(value))


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    p = successes / total
    den = 1 + z * z / total
    center = (p + z * z / (2 * total)) / den
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / den
    return center - half, center + half


def newcombe_difference(
    first_successes: int, first_total: int, second_successes: int, second_total: int
) -> tuple[float, float, float]:
    """Newcombe-Wilson interval for two independent proportions (second-first)."""
    p0 = first_successes / first_total
    p1 = second_successes / second_total
    l0, u0 = wilson(first_successes, first_total)
    l1, u1 = wilson(second_successes, second_total)
    difference = p1 - p0
    lower = difference - math.sqrt((p1 - l1) ** 2 + (u0 - p0) ** 2)
    upper = difference + math.sqrt((u1 - p1) ** 2 + (p0 - l0) ** 2)
    return difference, lower, upper


def risk_ratio_interval(
    first_successes: int, first_total: int, second_successes: int, second_total: int,
    z: float = 1.959963984540054,
) -> tuple[float, float, float]:
    p0 = first_successes / first_total
    p1 = second_successes / second_total
    ratio = p1 / p0
    standard_error = math.sqrt((1 - p1) / second_successes + (1 - p0) / first_successes)
    return (
        ratio,
        math.exp(math.log(ratio) - z * standard_error),
        math.exp(math.log(ratio) + z * standard_error),
    )


def write_rows(name: str, rows: list[dict], fields: list[str] | None = None) -> None:
    if not rows:
        raise ValueError(f"No rows for {name}")
    fields = fields or list(rows[0])
    with (OUTPUT / name).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def svg_text(x: float, y: float, value: str, size: int = 12, anchor: str = "start",
             color: str = INK, weight: int = 400, rotate: int | None = None) -> str:
    transform = f' transform="rotate({rotate} {x:.1f} {y:.1f})"' if rotate is not None else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" fill="{color}" font-weight="{weight}"{transform}>'
            f'{html.escape(value)}</text>')


def save_svg(name: str, width: int, height: int, parts: list[str], title: str) -> None:
    body = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">',
            f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>', *parts, "</svg>"]
    (FIGURES / name).write_text("\n".join(body) + "\n")


def make_tables() -> dict[str, float | int]:
    denominator_rows = read_rows("pooled_denominators.csv")
    year_py: dict[int, int] = defaultdict(int)
    total_py = 0
    for row in denominator_rows:
        n = integer(row["woman_years"])
        assert n is not None
        year_py[int(row["study_year"])] += n
        total_py += n
    assert total_py == 47_258_198

    overall_cells = {
        (r["pop_context"], r["procedure_category"]): integer(r["women"])
        for r in read_rows("pooled_first_totals.csv")
    }
    assert sum(value for value in overall_cells.values() if value is not None) == 56_257
    overall = []
    for context in ("Isolated SUI", "Concomitant POP"):
        sling = overall_cells[(context, "Sling")]
        bulking = overall_cells[(context, "Bulking")]
        hybrid = overall_cells[(context, "Hybrid")]
        assert None not in (sling, bulking, hybrid)
        nonhybrid = sling + bulking
        for category, count in (("Sling", sling), ("Bulking", bulking)):
            lo, hi = wilson(count, nonhybrid)
            overall.append({
                "pop_context": context,
                "procedure_category": category,
                "women": count,
                "nonhybrid_denominator": nonhybrid,
                "share_among_sling_or_bulking_percent": f"{100 * count / nonhybrid:.2f}",
                "share_ci95_lower_percent": f"{100 * lo:.2f}",
                "share_ci95_upper_percent": f"{100 * hi:.2f}",
                "rate_per_1000_eligible_woman_years": f"{1000 * count / total_py:.3f}",
            })
        overall.append({
            "pop_context": context,
            "procedure_category": "Hybrid",
            "women": hybrid,
            "nonhybrid_denominator": "Not applicable",
            "share_among_sling_or_bulking_percent": "Not applicable",
            "share_ci95_lower_percent": "Not applicable",
            "share_ci95_upper_percent": "Not applicable",
            "rate_per_1000_eligible_woman_years": f"{1000 * hybrid / total_py:.3f}",
        })
    write_rows("Table1_first_qualifying_procedure_in_eligible_year.csv", overall)

    period_cells = {
        (r["study_period"], r["pop_context"], r["procedure_category"]): integer(r["women"])
        for r in read_rows("pooled_first_by_period.csv")
    }
    age_cells = {
        (r["study_period"], r["age_publication"], r["procedure_category"]): integer(r["women"])
        for r in read_rows("pooled_first_by_period_age_publication.csv")
    }
    age_totals = {
        age: sum((age_cells[(period, age, category)] or 0)
                 for period in ("2014-2019", "2020-2024")
                 for category in ("Sling", "Bulking"))
        for age in AGE_ORDER
    }
    standard_total = sum(age_totals.values())
    standard_weights = {age: age_totals[age] / standard_total for age in AGE_ORDER}

    standardized_period = {}
    for period in ("2014-2019", "2020-2024"):
        standardized_period[period] = sum(
            standard_weights[age] * (age_cells[(period, age, "Bulking")] or 0) /
            ((age_cells[(period, age, "Sling")] or 0) + (age_cells[(period, age, "Bulking")] or 0))
            for age in AGE_ORDER
        )

    period_table = []
    period_metrics = {}
    for context in ("Isolated SUI", "Concomitant POP"):
        values = {}
        for period in ("2014-2019", "2020-2024"):
            sling = period_cells[(period, context, "Sling")]
            bulking = period_cells[(period, context, "Bulking")]
            assert sling is not None and bulking is not None
            n = sling + bulking
            lo, hi = wilson(bulking, n)
            values[period] = (sling, bulking, n, bulking / n, lo, hi)
        pre, post = values["2014-2019"], values["2020-2024"]
        difference, diff_lo, diff_hi = newcombe_difference(pre[1], pre[2], post[1], post[2])
        ratio, ratio_lo, ratio_hi = risk_ratio_interval(pre[1], pre[2], post[1], post[2])
        row = {
            "pop_context": context,
            "pre_sling": pre[0], "pre_bulking": pre[1],
            "pre_bulking_share_percent": f"{100 * pre[3]:.2f}",
            "pre_ci95_lower_percent": f"{100 * pre[4]:.2f}",
            "pre_ci95_upper_percent": f"{100 * pre[5]:.2f}",
            "post_sling": post[0], "post_bulking": post[1],
            "post_bulking_share_percent": f"{100 * post[3]:.2f}",
            "post_ci95_lower_percent": f"{100 * post[4]:.2f}",
            "post_ci95_upper_percent": f"{100 * post[5]:.2f}",
            "absolute_change_percentage_points": f"{100 * difference:.2f}",
            "absolute_change_ci95_lower_points": f"{100 * diff_lo:.2f}",
            "absolute_change_ci95_upper_points": f"{100 * diff_hi:.2f}",
            "share_ratio": f"{ratio:.2f}",
            "share_ratio_ci95_lower": f"{ratio_lo:.2f}",
            "share_ratio_ci95_upper": f"{ratio_hi:.2f}",
            "relative_change_percent": f"{100 * (ratio - 1):.1f}",
        }
        if context == "Isolated SUI":
            row.update({
                "pre_age_standardized_share_percent": f"{100 * standardized_period['2014-2019']:.2f}",
                "post_age_standardized_share_percent": f"{100 * standardized_period['2020-2024']:.2f}",
                "age_standardized_change_points": f"{100 * (standardized_period['2020-2024'] - standardized_period['2014-2019']):.2f}",
            })
        else:
            row.update({
                "pre_age_standardized_share_percent": "Not estimated",
                "post_age_standardized_share_percent": "Not estimated",
                "age_standardized_change_points": "Not estimated",
            })
        period_table.append(row)
        period_metrics[context] = (pre, post, difference, diff_lo, diff_hi, ratio, ratio_lo, ratio_hi)
    write_rows("Table2_period_comparison.csv", period_table)

    year_cells = {
        (int(r["study_year"]), r["pop_context"], r["procedure_category"]): integer(r["women"])
        for r in read_rows("pooled_first_by_year.csv")
    }
    annual = []
    for year in sorted(year_py):
        sling = year_cells[(year, "Isolated SUI", "Sling")]
        bulking = year_cells[(year, "Isolated SUI", "Bulking")]
        assert sling is not None and bulking is not None
        n = sling + bulking
        lo, hi = wilson(bulking, n)
        annual.append({
            "study_year": year, "woman_years": year_py[year],
            "sling": sling, "bulking": bulking, "nonhybrid_total": n,
            "bulking_share_percent": f"{100 * bulking / n:.2f}",
            "share_ci95_lower_percent": f"{100 * lo:.2f}",
            "share_ci95_upper_percent": f"{100 * hi:.2f}",
            "sling_rate_per_1000": f"{1000 * sling / year_py[year]:.3f}",
            "bulking_rate_per_1000": f"{1000 * bulking / year_py[year]:.3f}",
        })
    write_rows("Table3_annual_eligible_year_isolated.csv", annual)

    age_table = []
    for age in AGE_ORDER:
        pre_s = age_cells[("2014-2019", age, "Sling")]
        pre_b = age_cells[("2014-2019", age, "Bulking")]
        post_s = age_cells[("2020-2024", age, "Sling")]
        post_b = age_cells[("2020-2024", age, "Bulking")]
        assert None not in (pre_s, pre_b, post_s, post_b)
        pre_n, post_n = pre_s + pre_b, post_s + post_b
        pre_lo, pre_hi = wilson(pre_b, pre_n)
        post_lo, post_hi = wilson(post_b, post_n)
        difference, diff_lo, diff_hi = newcombe_difference(pre_b, pre_n, post_b, post_n)
        age_table.append({
            "age_group": age,
            "pre_sling": pre_s, "pre_bulking": pre_b,
            "pre_bulking_share_percent": f"{100 * pre_b / pre_n:.2f}",
            "pre_ci95_lower_percent": f"{100 * pre_lo:.2f}",
            "pre_ci95_upper_percent": f"{100 * pre_hi:.2f}",
            "post_sling": post_s, "post_bulking": post_b,
            "post_bulking_share_percent": f"{100 * post_b / post_n:.2f}",
            "post_ci95_lower_percent": f"{100 * post_lo:.2f}",
            "post_ci95_upper_percent": f"{100 * post_hi:.2f}",
            "absolute_change_percentage_points": f"{100 * difference:.2f}",
            "change_ci95_lower_points": f"{100 * diff_lo:.2f}",
            "change_ci95_upper_points": f"{100 * diff_hi:.2f}",
        })
    write_rows("Table4_age_period_isolated.csv", age_table)

    annual_lookup = {int(row["study_year"]): row for row in annual}
    temporal = []
    for start_year, end_year in TEMPORAL_COMPARISONS:
        start, end = annual_lookup[start_year], annual_lookup[end_year]
        start_s, start_b = int(start["sling"]), int(start["bulking"])
        end_s, end_b = int(end["sling"]), int(end["bulking"])
        difference, diff_lo, diff_hi = newcombe_difference(
            start_b, start_s + start_b, end_b, end_s + end_b
        )
        ratio, ratio_lo, ratio_hi = risk_ratio_interval(
            start_b, start_s + start_b, end_b, end_s + end_b
        )
        temporal.append({
            "comparison": f"{start_year}-{end_year}",
            "start_bulking_share_percent": start["bulking_share_percent"],
            "end_bulking_share_percent": end["bulking_share_percent"],
            "absolute_change_percentage_points": f"{100 * difference:.2f}",
            "change_ci95_lower_points": f"{100 * diff_lo:.2f}",
            "change_ci95_upper_points": f"{100 * diff_hi:.2f}",
            "share_ratio": f"{ratio:.2f}",
            "share_ratio_ci95_lower": f"{ratio_lo:.2f}",
            "share_ratio_ci95_upper": f"{ratio_hi:.2f}",
            "relative_change_percent": f"{100 * (ratio - 1):.1f}",
        })
    write_rows("Table5_temporal_change_summary.csv", temporal)

    burden90 = {r["burden_category"]: r for r in read_rows("pooled_total_burden_090d_totals.csv")}
    burden180 = {r["burden_category"]: r for r in read_rows("pooled_total_burden_180d_totals.csv")}
    burden_table = []
    for category in ("Sling episode", "Bulking course"):
        a, b = burden90[category], burden180[category]
        n90, n180 = integer(a["treatment_units"]), integer(b["treatment_units"])
        d90, d180 = integer(a["contributing_injection_dates"]), integer(b["contributing_injection_dates"])
        assert None not in (n90, n180, d90, d180)
        burden_table.append({
            "burden_category": category,
            "units_90_day": n90, "contributing_dates_90_day": d90,
            "units_180_day": n180, "contributing_dates_180_day": d180,
            "absolute_unit_difference_180_minus_90": n180 - n90,
            "relative_difference_percent": f"{100 * (n180 / n90 - 1):.2f}",
        })
    write_rows("Table6_all_period_burden_90_vs_180_days.csv", burden_table)

    burden_year = {
        (int(r["study_year"]), r["burden_category"]): integer(r["treatment_units"])
        for r in read_rows("pooled_total_burden_090d_by_year.csv")
    }
    burden_annual = []
    for year in sorted(year_py):
        sling = burden_year[(year, "Sling episode")]
        bulking = burden_year[(year, "Bulking course")]
        assert sling is not None and bulking is not None
        burden_annual.append({
            "study_year": year,
            "sling_episodes": sling,
            "bulking_courses_90_day": bulking,
            "bulking_share_of_sling_plus_bulking_units_percent": f"{100 * bulking / (sling + bulking):.2f}",
        })
    write_rows("Table7_annual_all_period_burden_90_day_isolated.csv", burden_annual)

    sensitivity_cells = {
        (r["study_period"], r["pop_context"], r["procedure_category"]): integer(r["women"])
        for r in read_rows("pooled_first_period_sensitivity.csv")
    }
    sensitivity = []
    for period in ("2014-2019", "2020-2024"):
        primary_s = period_cells[(period, "Isolated SUI", "Sling")]
        primary_b = period_cells[(period, "Isolated SUI", "Bulking")]
        all_s = sensitivity_cells[(period, "Isolated SUI", "Sling")]
        all_b = sensitivity_cells[(period, "Isolated SUI", "Bulking")]
        assert None not in (primary_s, primary_b, all_s, all_b)
        sensitivity.append({
            "study_period": period,
            "primary_eligible_year_sling": primary_s,
            "primary_eligible_year_bulking": primary_b,
            "primary_bulking_share_percent": f"{100 * primary_b / (primary_s + primary_b):.2f}",
            "all_period_first_sling": all_s,
            "all_period_first_bulking": all_b,
            "all_period_first_bulking_share_percent": f"{100 * all_b / (all_s + all_b):.2f}",
        })
    write_rows("Table8_first_procedure_scope_sensitivity.csv", sensitivity)

    pre, post, difference, diff_lo, diff_hi, ratio, ratio_lo, ratio_hi = period_metrics["Isolated SUI"]
    overall_hybrid = overall_cells[("Isolated SUI", "Hybrid")] + overall_cells[("Concomitant POP", "Hybrid")]
    b90_iso = integer(burden90["Bulking course"]["treatment_units"])
    b180_iso = integer(burden180["Bulking course"]["treatment_units"])
    injections_iso = integer(burden90["Bulking course"]["contributing_injection_dates"])
    assert None not in (b90_iso, b180_iso, injections_iso)
    assert (b90_iso, b180_iso, injections_iso) == (7_476, 7_135, 8_018)
    assert integer(burden90["Sling episode"]["treatment_units"]) == 33_845
    return {
        "total_py": total_py,
        "total_first": sum(v for v in overall_cells.values() if v is not None),
        "overall_hybrid": overall_hybrid,
        "pre_share": pre[3], "post_share": post[3],
        "pp_change": difference, "pp_lo": diff_lo, "pp_hi": diff_hi,
        "ratio": ratio, "ratio_lo": ratio_lo, "ratio_hi": ratio_hi,
        "standardized_pre": standardized_period["2014-2019"],
        "standardized_post": standardized_period["2020-2024"],
        "share_2014": float(annual[0]["bulking_share_percent"]) / 100,
        "share_2019": float([r for r in annual if r["study_year"] == 2019][0]["bulking_share_percent"]) / 100,
        "share_2024": float(annual[-1]["bulking_share_percent"]) / 100,
        "b90_iso": b90_iso, "b180_iso": b180_iso, "injections_iso": injections_iso,
    }


def make_figures() -> None:
    with (OUTPUT / "Table3_annual_eligible_year_isolated.csv").open(newline="") as handle:
        annual = list(csv.DictReader(handle))
    years = [int(r["study_year"]) for r in annual]

    width, height = 900, 500
    left, right, top, bottom = 82, 850, 94, 395
    y_max = 40.0
    x = lambda year: left + (right - left) * (year - min(years)) / (max(years) - min(years))
    y = lambda value: bottom - (bottom - top) * value / y_max
    parts = [
        svg_text(42, 34, "Figure 1. Annual bulking share among eligible-year isolated SUI procedures", 18, weight=700),
        svg_text(42, 58, "First qualifying procedure per enrollee; bulking divided by sling plus bulking", 12, color=GREY),
    ]
    for tick in range(0, 41, 5):
        parts.append(f'<line x1="{left}" y1="{y(tick):.1f}" x2="{right}" y2="{y(tick):.1f}" stroke="{LIGHT}"/>')
        parts.append(svg_text(left - 10, y(tick) + 4, str(tick), 10, anchor="end", color=GREY))
    values = [float(r["bulking_share_percent"]) for r in annual]
    points = " ".join(f'{x(yr):.1f},{y(v):.1f}' for yr, v in zip(years, values))
    parts.append(f'<polyline points="{points}" fill="none" stroke="{GOLD}" stroke-width="3"/>')
    for yr, val, row in zip(years, values, annual):
        parts.append(f'<circle cx="{x(yr):.1f}" cy="{y(val):.1f}" r="4.5" fill="{GOLD}" stroke="#FFF"/>')
        parts.append(svg_text(x(yr), bottom + 21, str(yr), 9, anchor="middle", color=GREY))
    parts.append(f'<line x1="{x(2020):.1f}" y1="{top}" x2="{x(2020):.1f}" y2="{bottom}" stroke="{GREY}" stroke-dasharray="6 5"/>')
    parts.append(svg_text(x(2020) + 8, top + 16, "2020", 10, color=GREY))
    parts.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="{INK}"/>')
    parts.append(svg_text(22, (top + bottom) / 2, "Bulking share (%)", 11, anchor="middle", rotate=-90))
    parts.append(svg_text(width / 2, 468, "Descriptive temporal change around 2020; no specific cause is identified.", 10, anchor="middle", color=GREY))
    save_svg("Figure1_annual_bulking_share.svg", width, height, parts, "Annual eligible-year bulking share among isolated SUI procedures")

    width, height = 900, 500
    left, right, top, bottom = 82, 850, 94, 395
    y_max = max(max(float(r["sling_rate_per_1000"]) for r in annual), max(float(r["bulking_rate_per_1000"]) for r in annual)) * 1.15
    y = lambda value: bottom - (bottom - top) * value / y_max
    parts = [
        svg_text(42, 34, "Figure 2. Annual crude rates of eligible-year isolated SUI procedures", 18, weight=700),
        svg_text(42, 58, "Rates per 1,000 eligible woman-years", 12, color=GREY),
    ]
    for i in range(6):
        tick = y_max * i / 5
        parts.append(f'<line x1="{left}" y1="{y(tick):.1f}" x2="{right}" y2="{y(tick):.1f}" stroke="{LIGHT}"/>')
        parts.append(svg_text(left - 10, y(tick) + 4, f"{tick:.2f}", 9, anchor="end", color=GREY))
    for field, color in (("sling_rate_per_1000", BLUE), ("bulking_rate_per_1000", GOLD)):
        vals = [float(r[field]) for r in annual]
        pts = " ".join(f'{x(yr):.1f},{y(v):.1f}' for yr, v in zip(years, vals))
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.8"/>')
        for yr, val in zip(years, vals):
            parts.append(f'<circle cx="{x(yr):.1f}" cy="{y(val):.1f}" r="4" fill="{color}"/>')
    for yr in years:
        parts.append(svg_text(x(yr), bottom + 21, str(yr), 9, anchor="middle", color=GREY))
    parts.append(f'<line x1="{x(2020):.1f}" y1="{top}" x2="{x(2020):.1f}" y2="{bottom}" stroke="{GREY}" stroke-dasharray="6 5"/>')
    parts.append(svg_text(x(2020) + 8, top + 16, "2020", 10, color=GREY))
    parts.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="{INK}"/>')
    parts.append(svg_text(22, (top + bottom) / 2, "Rate per 1,000", 11, anchor="middle", rotate=-90))
    parts.append(f'<line x1="320" y1="450" x2="350" y2="450" stroke="{BLUE}" stroke-width="2.8"/>')
    parts.append(svg_text(360, 454, "Sling", 10, color=GREY))
    parts.append(f'<line x1="470" y1="450" x2="500" y2="450" stroke="{GOLD}" stroke-width="2.8"/>')
    parts.append(svg_text(510, 454, "Bulking", 10, color=GREY))
    parts.append(svg_text(width / 2, 482, "2020 is shown as a descriptive reference point.", 10, anchor="middle", color=GREY))
    save_svg("Figure2_annual_first_procedure_rates.svg", width, height, parts, "Annual eligible-year isolated SUI procedure rates")

    with (OUTPUT / "Table4_age_period_isolated.csv").open(newline="") as handle:
        age = list(csv.DictReader(handle))
    width, height = 1080, 560
    left, right, top, bottom = 90, 1030, 100, 438
    y_max = 90.0
    y = lambda value: bottom - (bottom - top) * value / y_max
    xstep = (right - left) / len(age)
    parts = [
        svg_text(42, 34, "Figure 3. Bulking share before and after 2020 by age group", 18, weight=700),
        svg_text(42, 58, "Eligible-year isolated SUI procedures; ages 18-29 combined; hybrids excluded", 12, color=GREY),
    ]
    for tick in range(0, 91, 15):
        parts.append(f'<line x1="{left}" y1="{y(tick):.1f}" x2="{right}" y2="{y(tick):.1f}" stroke="{LIGHT}"/>')
        parts.append(svg_text(left - 10, y(tick) + 4, str(tick), 10, anchor="end", color=GREY))
    for i, row in enumerate(age):
        cx = left + (i + 0.5) * xstep
        parts.append(svg_text(cx, bottom + 20, row["age_group"], 9, anchor="end", color=GREY, rotate=-45))
        pre = float(row["pre_bulking_share_percent"])
        post = float(row["post_bulking_share_percent"])
        parts.append(f'<line x1="{cx:.1f}" y1="{y(pre):.1f}" x2="{cx:.1f}" y2="{y(post):.1f}" stroke="{LIGHT}" stroke-width="3"/>')
        parts.append(f'<circle cx="{cx:.1f}" cy="{y(pre):.1f}" r="4.5" fill="{BLUE}"/>')
        parts.append(f'<circle cx="{cx:.1f}" cy="{y(post):.1f}" r="5" fill="{GOLD}"/>')
    parts.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="{INK}"/>')
    parts.append(svg_text(22, (top + bottom) / 2, "Bulking share (%)", 11, anchor="middle", rotate=-90))
    parts.append(f'<circle cx="390" cy="500" r="4.5" fill="{BLUE}"/>')
    parts.append(svg_text(405, 504, "2014-2019", 10, color=GREY))
    parts.append(f'<circle cx="530" cy="500" r="5" fill="{GOLD}"/>')
    parts.append(svg_text(545, 504, "2020-2024", 10, color=GREY))
    parts.append(svg_text(width / 2, 540, "Intervals and changes are reported in Table 4; age-stratum comparisons are exploratory.", 10, anchor="middle", color=GREY))
    save_svg("Figure3_age_period_bulking_share.svg", width, height, parts, "Pre- versus post-2020 bulking share by age")

    with (OUTPUT / "Table7_annual_all_period_burden_90_day_isolated.csv").open(newline="") as handle:
        burden_annual = list(csv.DictReader(handle))
    burden_by_year = {int(row["study_year"]): row for row in burden_annual}
    width, height = 920, 520
    left, right, top, bottom = 82, 870, 96, 405
    y_max = 42.0
    x4 = lambda year: left + (right - left) * (year - min(years)) / (max(years) - min(years))
    y4 = lambda value: bottom - (bottom - top) * value / y_max
    parts = [
        svg_text(42, 34, "Figure 4. Eligible-year first-procedure and all-period burden shares", 18, weight=700),
        svg_text(42, 58, "Isolated SUI; burden includes all observed 2014-2024 procedures among ever-eligible women", 12, color=GREY),
    ]
    for tick in range(0, 43, 7):
        parts.append(f'<line x1="{left}" y1="{y4(tick):.1f}" x2="{right}" y2="{y4(tick):.1f}" stroke="{LIGHT}"/>')
        parts.append(svg_text(left - 10, y4(tick) + 4, str(tick), 10, anchor="end", color=GREY))
    series = (
        ("Eligible-year first procedure", [float(row["bulking_share_percent"]) for row in annual], BLUE, ""),
        ("All-period treatment burden", [float(burden_by_year[year]["bulking_share_of_sling_plus_bulking_units_percent"]) for year in years], GOLD, "7 4"),
    )
    for _label, values, color, dash in series:
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        points = " ".join(f'{x4(year):.1f},{y4(value):.1f}' for year, value in zip(years, values))
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.8"{dash_attr}/>')
        for year, value in zip(years, values):
            parts.append(f'<circle cx="{x4(year):.1f}" cy="{y4(value):.1f}" r="4" fill="{color}" stroke="#FFF"/>')
    for year in years:
        parts.append(svg_text(x4(year), bottom + 21, str(year), 9, anchor="middle", color=GREY))
    parts.append(f'<line x1="{x4(2020):.1f}" y1="{top}" x2="{x4(2020):.1f}" y2="{bottom}" stroke="{GREY}" stroke-dasharray="3 4"/>')
    parts.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="{INK}"/>')
    parts.append(svg_text(22, (top + bottom) / 2, "Bulking share (%)", 11, anchor="middle", rotate=-90))
    parts.append(f'<line x1="210" y1="454" x2="242" y2="454" stroke="{BLUE}" stroke-width="2.8"/>')
    parts.append(svg_text(250, 458, "Eligible-year first procedure", 10, color=GREY))
    parts.append(f'<line x1="490" y1="454" x2="522" y2="454" stroke="{GOLD}" stroke-width="2.8" stroke-dasharray="7 4"/>')
    parts.append(svg_text(530, 458, "All-period burden (90-day courses)", 10, color=GREY))
    parts.append(svg_text(width / 2, 502, "2020 is a descriptive reference point; hybrid episodes are excluded.", 10, anchor="middle", color=GREY))
    save_svg("Figure4_first_vs_burden_bulking_share.svg", width, height, parts, "Eligible-year first procedure and all-period burden bulking shares")


def write_summary(m: dict[str, float | int]) -> None:
    lines = [
        "P03 analysis summary",
        "Run date: 2026-09-04",
        "",
        f"Eligible woman-years: {m['total_py']:,}",
        f"Enrollee-level first qualifying sling, bulking, or hybrid procedure occurring in an eligible woman-year: {m['total_first']:,}",
        f"Hybrid first procedures: {m['overall_hybrid']:,}; hybrid detail is excluded from redundant period, year, and age tables.",
        f"Isolated-SUI bulking share among sling or bulking: {100*m['pre_share']:.2f}% in 2014-2019 and {100*m['post_share']:.2f}% in 2020-2024.",
        f"Absolute change: {100*m['pp_change']:.2f} points (95% CI {100*m['pp_lo']:.2f} to {100*m['pp_hi']:.2f}); share ratio {m['ratio']:.2f} (95% CI {m['ratio_lo']:.2f} to {m['ratio_hi']:.2f}).",
        f"Directly age-standardized shares: {100*m['standardized_pre']:.2f}% and {100*m['standardized_post']:.2f}% using the pooled isolated-procedure age distribution.",
        f"Annual isolated-SUI bulking share: {100*m['share_2014']:.2f}% in 2014, {100*m['share_2019']:.2f}% in 2019, and {100*m['share_2024']:.2f}% in 2024.",
        f"Isolated-SUI bulking burden: {m['b90_iso']:,} 90-day courses from {m['injections_iso']:,} injection dates; {m['b180_iso']:,} courses at 180 days.",
        "",
        "Interpretation is descriptive temporal change around 2020. FDA activity, COVID-19, and Bulkamid approval are not separated or assigned causal effects.",
        "Nonzero cells below 11 were removed from the transfer set; redundant margins were excluded or ages were collapsed so protected cells are not recoverable by subtraction.",
    ]
    (OUTPUT / "P03_analysis_summary.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    metrics = make_tables()
    make_figures()
    write_summary(metrics)
    print((OUTPUT / "P03_analysis_summary.txt").read_text())


if __name__ == "__main__":
    main()
