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
INPUT = PAPER / "03 Data" / "Server Aggregates 2026-09-01"
OUTPUT = PAPER / "03 Data" / "Analysis 2026-09-02"
FIGURES = PAPER / "04 Figures" / "Analysis 2026-09-02"
OUTPUT.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

INK = "#18232D"
BLUE = "#2E6FA7"
GOLD = "#C08428"
PURPLE = "#76548F"
GREY = "#6F7C86"
LIGHT = "#DDE4E9"
PALE = "#F3F6F8"
AGE_ORDER = ["18-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80-84", "85-89"]
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
    age_period_py: dict[tuple[str, str], int] = defaultdict(int)
    total_py = 0
    for row in denominator_rows:
        n = integer(row["woman_years"])
        assert n is not None
        year = int(row["study_year"])
        period = "2014-2019" if year <= 2019 else "2020-2024"
        year_py[year] += n
        age_period_py[(period, row["age5"])] += n
        total_py += n
    assert total_py > 0
    period_py = {
        "2014-2019": sum(v for y, v in year_py.items() if y <= 2019),
        "2020-2024": sum(v for y, v in year_py.items() if y >= 2020),
    }

    overall_input = read_rows("pooled_first_totals.csv")
    overall_cells = {(r["pop_context"], r["procedure_category"]): integer(r["women"])
                     for r in overall_input}
    overall = []
    for context in ("Isolated SUI", "Concomitant POP"):
        sling = overall_cells[(context, "Sling")]
        bulking = overall_cells[(context, "Bulking")]
        hybrid = overall_cells[(context, "Hybrid")]
        assert sling is not None and bulking is not None and hybrid is not None
        nonhybrid = sling + bulking
        for category, count in (("Sling", sling), ("Bulking", bulking)):
            lo, hi = wilson(count, nonhybrid)
            overall.append({
                "pop_context": context, "procedure_category": category, "women": count,
                "nonhybrid_denominator": nonhybrid, "share_among_sling_or_bulking_percent": f"{100 * count / nonhybrid:.2f}",
                "share_ci95_lower_percent": f"{100 * lo:.2f}", "share_ci95_upper_percent": f"{100 * hi:.2f}",
                "rate_per_1000_woman_years": f"{1000 * count / total_py:.3f}",
            })
        overall.append({
            "pop_context": context, "procedure_category": "Hybrid", "women": hybrid,
            "nonhybrid_denominator": "Not applicable", "share_among_sling_or_bulking_percent": "Not applicable",
            "share_ci95_lower_percent": "Not applicable", "share_ci95_upper_percent": "Not applicable",
            "rate_per_1000_woman_years": f"{1000 * hybrid / total_py:.3f}",
        })
    write_rows("Table1_overall_first_observed.csv", overall)

    period_cells = {(r["study_period"], r["pop_context"], r["procedure_category"]): integer(r["women"])
                    for r in read_rows("pooled_first_by_period.csv")}
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
            values[period] = (sling, bulking, bulking / n, lo, hi)
        pre, post = values["2014-2019"], values["2020-2024"]
        period_table.append({
            "pop_context": context,
            "pre_sling": pre[0], "pre_bulking": pre[1], "pre_bulking_share_percent": f"{100 * pre[2]:.2f}",
            "pre_ci95_lower_percent": f"{100 * pre[3]:.2f}", "pre_ci95_upper_percent": f"{100 * pre[4]:.2f}",
            "post_sling": post[0], "post_bulking": post[1], "post_bulking_share_percent": f"{100 * post[2]:.2f}",
            "post_ci95_lower_percent": f"{100 * post[3]:.2f}", "post_ci95_upper_percent": f"{100 * post[4]:.2f}",
            "absolute_change_percentage_points": f"{100 * (post[2] - pre[2]):.2f}",
            "relative_change_percent": f"{100 * (post[2] / pre[2] - 1):.1f}",
            "pre_bulking_rate_per_1000": f"{1000 * pre[1] / period_py['2014-2019']:.3f}",
            "post_bulking_rate_per_1000": f"{1000 * post[1] / period_py['2020-2024']:.3f}",
        })
        period_metrics[context] = (pre, post)
    write_rows("Table2_period_comparison.csv", period_table)

    year_cells = {(int(r["study_year"]), r["pop_context"], r["procedure_category"]): integer(r["women"])
                  for r in read_rows("pooled_first_by_year.csv")}
    annual = []
    for year in sorted(year_py):
        sling = year_cells[(year, "Isolated SUI", "Sling")]
        bulking = year_cells[(year, "Isolated SUI", "Bulking")]
        assert sling is not None and bulking is not None
        n = sling + bulking
        lo, hi = wilson(bulking, n)
        hybrid = year_cells.get((year, "Isolated SUI", "Hybrid"))
        annual.append({
            "study_year": year, "woman_years": year_py[year], "sling": sling, "bulking": bulking,
            "hybrid": hybrid if hybrid is not None else "SUPPRESSED", "nonhybrid_total": n,
            "bulking_share_percent": f"{100 * bulking / n:.2f}",
            "share_ci95_lower_percent": f"{100 * lo:.2f}", "share_ci95_upper_percent": f"{100 * hi:.2f}",
            "sling_rate_per_1000": f"{1000 * sling / year_py[year]:.3f}",
            "bulking_rate_per_1000": f"{1000 * bulking / year_py[year]:.3f}",
        })
    write_rows("Table3_annual_first_observed_isolated.csv", annual)

    age_cells = {(r["study_period"], r["age5"], r["pop_context"], r["procedure_category"]): integer(r["women"])
                 for r in read_rows("pooled_first_by_period_age.csv")}
    age_table = []
    for age in AGE_ORDER:
        row = {"age_group": age}
        computable = True
        shares = {}
        for period, prefix in (("2014-2019", "pre"), ("2020-2024", "post")):
            sling = age_cells.get((period, age, "Isolated SUI", "Sling"))
            bulking = age_cells.get((period, age, "Isolated SUI", "Bulking"))
            row[f"{prefix}_sling"] = sling if sling is not None else "SUPPRESSED"
            row[f"{prefix}_bulking"] = bulking if bulking is not None else "SUPPRESSED"
            if sling is None or bulking is None:
                computable = False
                row[f"{prefix}_bulking_share_percent"] = "SUPPRESSED"
                row[f"{prefix}_ci95_lower_percent"] = "SUPPRESSED"
                row[f"{prefix}_ci95_upper_percent"] = "SUPPRESSED"
            else:
                n = sling + bulking
                lo, hi = wilson(bulking, n)
                shares[prefix] = bulking / n
                row[f"{prefix}_bulking_share_percent"] = f"{100 * shares[prefix]:.2f}"
                row[f"{prefix}_ci95_lower_percent"] = f"{100 * lo:.2f}"
                row[f"{prefix}_ci95_upper_percent"] = f"{100 * hi:.2f}"
        row["absolute_change_percentage_points"] = f"{100 * (shares['post'] - shares['pre']):.2f}" if computable else "SUPPRESSED"
        age_table.append(row)
    write_rows("Table4_age_period_isolated.csv", age_table)

    burden90 = {(r["pop_context"], r["burden_category"]): r
                for r in read_rows("pooled_total_burden_090d_totals.csv")}
    burden180 = {(r["pop_context"], r["burden_category"]): r
                 for r in read_rows("pooled_total_burden_180d_totals.csv")}
    burden_table = []
    for context in ("Isolated SUI", "Concomitant POP"):
        for category in ("Sling episode", "Bulking course", "Hybrid episode"):
            a, b = burden90[(context, category)], burden180[(context, category)]
            n90, n180 = integer(a["treatment_units"]), integer(b["treatment_units"])
            inj90, inj180 = integer(a["contributing_injection_dates"]), integer(b["contributing_injection_dates"])
            assert None not in (n90, n180, inj90, inj180)
            burden_table.append({
                "pop_context": context, "burden_category": category,
                "units_90_day": n90, "contributing_dates_90_day": inj90,
                "rate_90_day_per_1000": f"{1000 * n90 / total_py:.3f}",
                "units_180_day": n180, "contributing_dates_180_day": inj180,
                "rate_180_day_per_1000": f"{1000 * n180 / total_py:.3f}",
                "absolute_unit_difference_180_minus_90": n180 - n90,
                "relative_difference_percent": f"{100 * (n180 / n90 - 1):.2f}",
            })
    write_rows("Table6_total_burden_90_vs_180_days.csv", burden_table)

    burden_year = {(int(r["study_year"]), r["pop_context"], r["burden_category"]): integer(r["treatment_units"])
                   for r in read_rows("pooled_total_burden_090d_by_year.csv")}
    burden_annual = []
    for year in sorted(year_py):
        sling = burden_year[(year, "Isolated SUI", "Sling episode")]
        bulking = burden_year[(year, "Isolated SUI", "Bulking course")]
        assert sling is not None and bulking is not None
        burden_annual.append({
            "study_year": year, "woman_years": year_py[year], "sling_episodes": sling,
            "bulking_courses_90_day": bulking,
            "sling_rate_per_1000": f"{1000 * sling / year_py[year]:.3f}",
            "bulking_course_rate_per_1000": f"{1000 * bulking / year_py[year]:.3f}",
            "bulking_share_of_sling_plus_bulking_units_percent": f"{100 * bulking / (sling + bulking):.2f}",
        })
    write_rows("Table7_annual_total_burden_90_day_isolated.csv", burden_annual)

    annual_lookup = {int(row["study_year"]): row for row in annual}
    burden_lookup = {int(row["study_year"]): row for row in burden_annual}
    temporal = []
    for start_year, end_year in TEMPORAL_COMPARISONS:
        start, end = annual_lookup[start_year], annual_lookup[end_year]
        start_burden, end_burden = burden_lookup[start_year], burden_lookup[end_year]
        start_share = float(start["bulking_share_percent"])
        end_share = float(end["bulking_share_percent"])
        start_burden_share = float(start_burden["bulking_share_of_sling_plus_bulking_units_percent"])
        end_burden_share = float(end_burden["bulking_share_of_sling_plus_bulking_units_percent"])
        temporal.append({
            "comparison": f"{start_year}-{end_year}",
            "start_year": start_year,
            "end_year": end_year,
            "start_first_bulking_share_percent": f"{start_share:.2f}",
            "end_first_bulking_share_percent": f"{end_share:.2f}",
            "absolute_first_share_change_percentage_points": f"{end_share - start_share:.2f}",
            "relative_first_share_change_percent": f"{100 * (end_share / start_share - 1):.1f}",
            "start_sling_rate_per_1000": start["sling_rate_per_1000"],
            "end_sling_rate_per_1000": end["sling_rate_per_1000"],
            "start_bulking_rate_per_1000": start["bulking_rate_per_1000"],
            "end_bulking_rate_per_1000": end["bulking_rate_per_1000"],
            "start_burden_bulking_share_percent": f"{start_burden_share:.2f}",
            "end_burden_bulking_share_percent": f"{end_burden_share:.2f}",
            "absolute_burden_share_change_percentage_points": f"{end_burden_share - start_burden_share:.2f}",
        })
    write_rows("Table5_temporal_change_summary.csv", temporal)

    pre, post = period_metrics["Isolated SUI"]
    overall_hybrid = overall_cells[("Isolated SUI", "Hybrid")] + overall_cells[("Concomitant POP", "Hybrid")]
    b90_iso = integer(burden90[("Isolated SUI", "Bulking course")]["treatment_units"])
    b180_iso = integer(burden180[("Isolated SUI", "Bulking course")]["treatment_units"])
    injections_iso = integer(burden90[("Isolated SUI", "Bulking course")]["contributing_injection_dates"])
    assert None not in (b90_iso, b180_iso, injections_iso)
    return {
        "total_py": total_py,
        "total_first": sum(v for v in overall_cells.values() if v is not None),
        "overall_hybrid": overall_hybrid,
        "pre_share": pre[2], "post_share": post[2],
        "pp_change": post[2] - pre[2], "relative_change": post[2] / pre[2] - 1,
        "share_2014": float(annual[0]["bulking_share_percent"]) / 100,
        "share_2019": float([r for r in annual if r["study_year"] == 2019][0]["bulking_share_percent"]) / 100,
        "share_2024": float(annual[-1]["bulking_share_percent"]) / 100,
        "b90_iso": b90_iso, "b180_iso": b180_iso, "injections_iso": injections_iso,
    }


def make_figures() -> None:
    with (OUTPUT / "Table3_annual_first_observed_isolated.csv").open(newline="") as handle:
        annual = list(csv.DictReader(handle))
    years = [int(r["study_year"]) for r in annual]

    width, height = 900, 500
    left, right, top, bottom = 82, 850, 94, 395
    y_max = 40.0
    x = lambda year: left + (right - left) * (year - min(years)) / (max(years) - min(years))
    y = lambda value: bottom - (bottom - top) * value / y_max
    parts = [
        svg_text(42, 34, "Figure 1. Annual bulking share among first observed isolated SUI procedures", 18, weight=700),
        svg_text(42, 58, "Bulking divided by sling plus bulking; hybrid procedures excluded", 12, color=GREY),
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
    save_svg("Figure1_annual_bulking_share.svg", width, height, parts, "Annual bulking share among isolated SUI procedures")

    width, height = 900, 500
    left, right, top, bottom = 82, 850, 94, 395
    y_max = max(max(float(r["sling_rate_per_1000"]) for r in annual), max(float(r["bulking_rate_per_1000"]) for r in annual)) * 1.15
    y = lambda value: bottom - (bottom - top) * value / y_max
    parts = [
        svg_text(42, 34, "Figure 2. Annual crude rates of first observed isolated SUI procedures", 18, weight=700),
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
    save_svg("Figure2_annual_first_procedure_rates.svg", width, height, parts, "Annual first observed isolated SUI procedure rates")

    with (OUTPUT / "Table4_age_period_isolated.csv").open(newline="") as handle:
        age = list(csv.DictReader(handle))
    width, height = 1080, 560
    left, right, top, bottom = 90, 1030, 100, 438
    y_max = 90.0
    y = lambda value: bottom - (bottom - top) * value / y_max
    xstep = (right - left) / len(age)
    parts = [
        svg_text(42, 34, "Figure 3. Bulking share before and after 2020 by 5-year age group", 18, weight=700),
        svg_text(42, 58, "First observed isolated SUI procedures; hybrids excluded", 12, color=GREY),
    ]
    for tick in range(0, 91, 15):
        parts.append(f'<line x1="{left}" y1="{y(tick):.1f}" x2="{right}" y2="{y(tick):.1f}" stroke="{LIGHT}"/>')
        parts.append(svg_text(left - 10, y(tick) + 4, str(tick), 10, anchor="end", color=GREY))
    for i, row in enumerate(age):
        cx = left + (i + 0.5) * xstep
        parts.append(svg_text(cx, bottom + 20, row["age_group"], 9, anchor="end", color=GREY, rotate=-45))
        if row["pre_bulking_share_percent"] == "SUPPRESSED" or row["post_bulking_share_percent"] == "SUPPRESSED":
            parts.append(svg_text(cx, bottom - 10, "S", 9, anchor="middle", color=GREY, weight=700))
            continue
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
    parts.append(svg_text(width / 2, 540, "S = one or more component counts suppressed because the cell contained fewer than 11 women.", 10, anchor="middle", color=GREY))
    save_svg("Figure3_age_period_bulking_share.svg", width, height, parts, "Pre- versus post-2020 bulking share by age")

    with (OUTPUT / "Table7_annual_total_burden_90_day_isolated.csv").open(newline="") as handle:
        burden_annual = list(csv.DictReader(handle))
    burden_by_year = {int(row["study_year"]): row for row in burden_annual}
    width, height = 920, 520
    left, right, top, bottom = 82, 870, 96, 405
    y_max = 42.0
    x4 = lambda year: left + (right - left) * (year - min(years)) / (max(years) - min(years))
    y4 = lambda value: bottom - (bottom - top) * value / y_max
    parts = [
        svg_text(42, 34, "Figure 4. First-procedure and total-burden bulking shares", 18, weight=700),
        svg_text(42, 58, "Isolated SUI; total burden collapses repeat bulking within 90 days", 12, color=GREY),
    ]
    for tick in range(0, 43, 7):
        parts.append(f'<line x1="{left}" y1="{y4(tick):.1f}" x2="{right}" y2="{y4(tick):.1f}" stroke="{LIGHT}"/>')
        parts.append(svg_text(left - 10, y4(tick) + 4, str(tick), 10, anchor="end", color=GREY))
    series = (
        ("First observed procedure", [float(row["bulking_share_percent"]) for row in annual], BLUE, ""),
        ("Total procedure burden", [float(burden_by_year[year]["bulking_share_of_sling_plus_bulking_units_percent"]) for year in years], GOLD, "7 4"),
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
    parts.append(svg_text(250, 458, "First observed procedure", 10, color=GREY))
    parts.append(f'<line x1="490" y1="454" x2="522" y2="454" stroke="{GOLD}" stroke-width="2.8" stroke-dasharray="7 4"/>')
    parts.append(svg_text(530, 458, "Total burden (90-day courses)", 10, color=GREY))
    parts.append(svg_text(width / 2, 502, "2020 is a descriptive reference point; hybrid episodes are excluded.", 10, anchor="middle", color=GREY))
    save_svg("Figure4_first_vs_burden_bulking_share.svg", width, height, parts, "First observed and total burden bulking shares")


def write_summary(m: dict[str, float | int]) -> None:
    lines = [
        "P03 analysis summary",
        "Run date: 2026-09-02",
        "",
        f"Eligible woman-years: {m['total_py']:,}",
        f"Women with a first observed sling, bulking, or hybrid procedure: {m['total_first']:,}",
        f"Hybrid first procedures: {m['overall_hybrid']:,}; annual small cells remain suppressed.",
        f"Isolated-SUI bulking share among sling or bulking: {100*m['pre_share']:.2f}% in 2014-2019 and {100*m['post_share']:.2f}% in 2020-2024.",
        f"Absolute change: {100*m['pp_change']:.2f} percentage points; relative change: {100*m['relative_change']:.1f}%.",
        f"Annual isolated-SUI bulking share: {100*m['share_2014']:.2f}% in 2014, {100*m['share_2019']:.2f}% in 2019, and {100*m['share_2024']:.2f}% in 2024.",
        f"Isolated-SUI bulking burden: {m['b90_iso']:,} 90-day courses from {m['injections_iso']:,} injection dates; {m['b180_iso']:,} courses at 180 days.",
        "",
        "Interpretation is descriptive temporal change around 2020. FDA activity, COVID-19, and Bulkamid approval are not separated or assigned causal effects.",
        "Cells below 11 remain suppressed and were not reconstructed.",
    ]
    (OUTPUT / "P03_analysis_summary.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    metrics = make_tables()
    make_figures()
    write_summary(metrics)
    print((OUTPUT / "P03_analysis_summary.txt").read_text())


if __name__ == "__main__":
    main()
