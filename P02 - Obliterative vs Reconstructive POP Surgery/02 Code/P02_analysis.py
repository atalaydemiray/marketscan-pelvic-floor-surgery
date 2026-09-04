#!/usr/bin/env python3
"""Build P02 publication tables and figures from disclosure-screened aggregates."""

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
GREY = "#6F7C86"
LIGHT = "#DDE4E9"
PALE = "#F3F6F8"
PURPLE = "#76548F"
OLIVE = "#708238"
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


def pct(value: float) -> str:
    return f"{100 * value:.2f}"


def rate(value: int, denominator: int) -> float:
    return 1000 * value / denominator


def make_tables() -> dict[str, float | int]:
    totals = read_rows("pooled_totals.csv")[0]
    total = integer(totals["first_observed_women"])
    obl = integer(totals["obliterative"])
    rec = integer(totals["reconstructive"])
    mixed = integer(totals["mixed_code_dates"])
    assert None not in (total, obl, rec, mixed)
    assert (total, obl, rec, mixed) == (67_162, 3_032, 64_130, 1_148)
    assert obl + rec == total

    denominator_rows = read_rows("pooled_denominators.csv")
    total_py = sum(integer(r["woman_years"]) or 0 for r in denominator_rows)
    assert total_py == 47_258_198
    year_py: dict[int, int] = defaultdict(int)
    age_py: dict[str, int] = defaultdict(int)
    for row in denominator_rows:
        n = integer(row["woman_years"])
        assert n is not None
        year_py[int(row["study_year"])] += n
        age_group = "18-29" if row["age5"] in {"18-24", "25-29"} else row["age5"]
        age_py[age_group] += n

    overall = []
    for label, n, show_interval in (
        ("Any qualifying POP procedure", total, False),
        ("Obliterative", obl, True),
        ("Reconstructive", rec, True),
        ("Of which: mixed obliterative/reconstructive code date", mixed, True),
    ):
        lo_share, hi_share = wilson(n, total) if show_interval else (math.nan, math.nan)
        overall.append({
            "measure": label,
            "count": n,
            "share_percent": "Not applicable" if not show_interval else f"{100 * n / total:.2f}",
            "share_ci95_lower_percent": "Not applicable" if not show_interval else f"{100 * lo_share:.2f}",
            "share_ci95_upper_percent": "Not applicable" if not show_interval else f"{100 * hi_share:.2f}",
            "rate_per_1000_woman_years": f"{rate(n, total_py):.3f}",
        })
    write_rows("Table1_overall_summary.csv", overall)

    age_cells: dict[tuple[str, str], dict[str, str]] = {}
    for row in read_rows("pooled_first_by_age_publication.csv"):
        age_cells[(row["age_publication"], row["procedure_group"])] = row
    age_table = []
    for age in AGE_ORDER:
        o = integer(age_cells[(age, "Obliterative")]["women"])
        r = integer(age_cells[(age, "Reconstructive")]["women"])
        py = age_py[age]
        assert o is not None and r is not None
        n = o + r
        lo, hi = wilson(o, n)
        age_table.append({
            "age_group": age, "woman_years": py, "obliterative": o, "reconstructive": r,
            "total_first_observed": n, "obliterative_share_percent": f"{100 * o / n:.2f}",
            "share_ci95_lower_percent": f"{100 * lo:.2f}", "share_ci95_upper_percent": f"{100 * hi:.2f}",
            "obliterative_rate_per_1000": f"{rate(o, py):.3f}",
            "reconstructive_rate_per_1000": f"{rate(r, py):.3f}",
        })
    write_rows("Table2_first_procedure_by_age.csv", age_table)

    year_cells: dict[tuple[int, str], dict[str, str]] = {}
    for row in read_rows("pooled_first_by_year.csv"):
        year_cells[(int(row["study_year"]), row["procedure_group"])] = row
    broad_cells = {
        (int(row["study_year"]), row["broad_age"], row["procedure_group"]): integer(row["women"])
        for row in read_rows("pooled_first_by_year_broad_age.csv")
    }
    broad_order = ("<65", "65-74", "75-84", "85-89")
    broad_totals = {
        age: sum(
            broad_cells[(year, age, group)] or 0
            for year in sorted(year_py) for group in ("Obliterative", "Reconstructive")
        )
        for age in broad_order
    }
    standard_total = sum(broad_totals.values())
    standard_weights = {age: broad_totals[age] / standard_total for age in broad_order}

    annual = []
    standardized_share_by_year: dict[int, float] = {}
    for year in sorted(year_py):
        o = integer(year_cells[(year, "Obliterative")]["women"])
        r = integer(year_cells[(year, "Reconstructive")]["women"])
        assert o is not None and r is not None
        n, py = o + r, year_py[year]
        lo, hi = wilson(o, n)
        standardized_share = sum(
            standard_weights[age] * (broad_cells[(year, age, "Obliterative")] or 0) /
            ((broad_cells[(year, age, "Obliterative")] or 0) +
             (broad_cells[(year, age, "Reconstructive")] or 0))
            for age in broad_order
        )
        standardized_share_by_year[year] = standardized_share
        standardized_variance = sum(
            standard_weights[age] ** 2 *
            ((broad_cells[(year, age, "Obliterative")] or 0) /
             ((broad_cells[(year, age, "Obliterative")] or 0) +
              (broad_cells[(year, age, "Reconstructive")] or 0))) *
            (1 - (broad_cells[(year, age, "Obliterative")] or 0) /
             ((broad_cells[(year, age, "Obliterative")] or 0) +
              (broad_cells[(year, age, "Reconstructive")] or 0))) /
            ((broad_cells[(year, age, "Obliterative")] or 0) +
             (broad_cells[(year, age, "Reconstructive")] or 0))
            for age in broad_order
        )
        std_se = math.sqrt(standardized_variance)
        annual.append({
            "study_year": year, "woman_years": py, "obliterative": o, "reconstructive": r,
            "total_first_observed": n, "obliterative_share_percent": f"{100 * o / n:.2f}",
            "share_ci95_lower_percent": f"{100 * lo:.2f}", "share_ci95_upper_percent": f"{100 * hi:.2f}",
            "age_standardized_obliterative_share_percent": f"{100 * standardized_share:.2f}",
            "age_standardized_ci95_lower_percent": f"{100 * max(0.0, standardized_share - 1.959963984540054 * std_se):.2f}",
            "age_standardized_ci95_upper_percent": f"{100 * min(1.0, standardized_share + 1.959963984540054 * std_se):.2f}",
            "obliterative_rate_per_1000": f"{rate(o, py):.3f}",
            "reconstructive_rate_per_1000": f"{rate(r, py):.3f}",
            "total_rate_per_1000": f"{rate(n, py):.3f}",
        })
    write_rows("Table3_annual_first_procedure.csv", annual)

    annual_lookup = {int(row["study_year"]): row for row in annual}
    temporal = []
    for start_year, end_year in TEMPORAL_COMPARISONS:
        start, end = annual_lookup[start_year], annual_lookup[end_year]
        start_o, start_r = int(start["obliterative"]), int(start["reconstructive"])
        end_o, end_r = int(end["obliterative"]), int(end["reconstructive"])
        start_share = start_o / (start_o + start_r)
        end_share = end_o / (end_o + end_r)
        difference, diff_lower, diff_upper = newcombe_difference(
            start_o, start_o + start_r, end_o, end_o + end_r
        )
        ratio, ratio_lower, ratio_upper = risk_ratio_interval(
            start_o, start_o + start_r, end_o, end_o + end_r
        )
        temporal.append({
            "comparison": f"{start_year}-{end_year}",
            "start_year": start_year,
            "end_year": end_year,
            "start_obliterative_share_percent": f"{100 * start_share:.2f}",
            "end_obliterative_share_percent": f"{100 * end_share:.2f}",
            "absolute_change_percentage_points": f"{100 * difference:.2f}",
            "absolute_change_ci95_lower_points": f"{100 * diff_lower:.2f}",
            "absolute_change_ci95_upper_points": f"{100 * diff_upper:.2f}",
            "share_ratio": f"{ratio:.2f}",
            "share_ratio_ci95_lower": f"{ratio_lower:.2f}",
            "share_ratio_ci95_upper": f"{ratio_upper:.2f}",
            "relative_change_percent": f"{100 * (ratio - 1):.1f}",
            "start_age_standardized_share_percent": start["age_standardized_obliterative_share_percent"],
            "end_age_standardized_share_percent": end["age_standardized_obliterative_share_percent"],
            "age_standardized_change_points": f"{100 * (standardized_share_by_year[end_year] - standardized_share_by_year[start_year]):.2f}",
            "start_obliterative_rate_per_1000": start["obliterative_rate_per_1000"],
            "end_obliterative_rate_per_1000": end["obliterative_rate_per_1000"],
            "start_reconstructive_rate_per_1000": start["reconstructive_rate_per_1000"],
            "end_reconstructive_rate_per_1000": end["reconstructive_rate_per_1000"],
            "start_total_rate_per_1000": start["total_rate_per_1000"],
            "end_total_rate_per_1000": end["total_rate_per_1000"],
        })
    write_rows("Table4_temporal_change_summary.csv", temporal)

    burden_cells: dict[tuple[int, str], dict[str, str]] = {}
    for row in read_rows("pooled_eligible_year_procedure_dates_by_year.csv"):
        burden_cells[(int(row["study_year"]), row["procedure_group"])] = row
    burden = []
    for year in sorted(year_py):
        o = integer(burden_cells[(year, "Obliterative")]["operation_dates"])
        r = integer(burden_cells[(year, "Reconstructive")]["operation_dates"])
        assert o is not None and r is not None
        burden.append({
            "study_year": year, "woman_years": year_py[year], "obliterative_operation_dates": o,
            "reconstructive_operation_dates": r, "all_operation_dates": o + r,
            "obliterative_rate_per_1000": f"{rate(o, year_py[year]):.3f}",
            "reconstructive_rate_per_1000": f"{rate(r, year_py[year]):.3f}",
            "all_rate_per_1000": f"{rate(o + r, year_py[year]):.3f}",
        })
    write_rows("Table5_eligible_year_procedure_dates.csv", burden)

    codes = []
    obl_codes = {"57106", "57110", "57120", "58275", "58280"}
    for row in read_rows("pooled_code_contribution.csv"):
        codes.append({
            "cpt": row["code"],
            "classification": "Obliterative" if row["code"] in obl_codes else "Reconstructive",
            "operation_dates": row["operation_dates"],
            "suppressed": row["operation_dates_suppressed"],
        })
    write_rows("Table6_code_contribution.csv", codes)

    definition_rows = read_rows("pooled_definition_reconciliation.csv")
    write_rows("Table7_parent_definition_reconciliation.csv", definition_rows)
    sensitivity_rows = []
    for row in read_rows("pooled_parent_definition_sensitivity.csv"):
        first = integer(row["first_procedures"])
        obliterative = integer(row["obliterative"])
        assert first is not None and obliterative is not None
        sensitivity_rows.append({
            **row,
            "obliterative_share_percent": f"{100 * obliterative / first:.2f}",
        })
    write_rows("Table8_parent_definition_sensitivity.csv", sensitivity_rows)

    broad = {
        (age, group): sum(
            broad_cells[(year, age, group)] or 0 for year in sorted(year_py)
        ) for age in broad_order for group in ("Obliterative", "Reconstructive")
    }
    broad_shares = {}
    for age in ("<65", "65-74", "75-84", "85-89"):
        o, r = broad[(age, "Obliterative")], broad[(age, "Reconstructive")]
        assert o is not None and r is not None
        broad_shares[age] = o / (o + r)

    first_year_share = float(annual[0]["obliterative_share_percent"])
    last_year_share = float(annual[-1]["obliterative_share_percent"])
    metrics = {
        "total_py": total_py, "total": total, "obl": obl, "rec": rec, "mixed": mixed,
        "overall_share": obl / total, "mixed_share_all": mixed / total, "mixed_share_obl": mixed / obl,
        "first_year_share": first_year_share, "last_year_share": last_year_share,
        "first_last_pp": last_year_share - first_year_share,
        "first_last_relative": 100 * (last_year_share / first_year_share - 1),
        "broad_75_84": broad_shares["75-84"], "broad_85_89": broad_shares["85-89"],
        "first_year_standardized": float(annual[0]["age_standardized_obliterative_share_percent"]),
        "last_year_standardized": float(annual[-1]["age_standardized_obliterative_share_percent"]),
    }
    return metrics


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


def make_figures() -> None:
    with (OUTPUT / "Table2_first_procedure_by_age.csv").open(newline="") as handle:
        age = list(csv.DictReader(handle))

    width, height = 1080, 540
    left, right, top, bottom = 82, 1030, 94, 430
    y_max = 50.0
    xstep = (right - left) / len(age)
    y = lambda v: bottom - (bottom - top) * v / y_max
    parts = [
        svg_text(42, 34, "Figure 1. Obliterative share of eligible-year POP procedures by age", 18, weight=700),
        svg_text(42, 58, "Pooled CCAE and MDCR, 2014-2024; Wilson 95% confidence intervals", 12, color=GREY),
    ]
    for tick in range(0, 51, 10):
        parts.append(f'<line x1="{left}" y1="{y(tick):.1f}" x2="{right}" y2="{y(tick):.1f}" stroke="{LIGHT}"/>')
        parts.append(svg_text(left - 10, y(tick) + 4, str(tick), 10, anchor="end", color=GREY))
    for i, row in enumerate(age):
        cx = left + (i + 0.5) * xstep
        parts.append(svg_text(cx, bottom + 20, row["age_group"], 9, anchor="end", color=GREY, rotate=-45))
        if row["obliterative_share_percent"] == "SUPPRESSED":
            parts.append(f'<rect x="{cx-7:.1f}" y="{bottom-7:.1f}" width="14" height="7" fill="{PALE}" stroke="{GREY}"/>')
            parts.append(svg_text(cx, bottom - 13, "S", 9, anchor="middle", color=GREY, weight=700))
            continue
        p = float(row["obliterative_share_percent"])
        lo = float(row["share_ci95_lower_percent"])
        hi = float(row["share_ci95_upper_percent"])
        barw = xstep * 0.55
        parts.append(f'<rect x="{cx-barw/2:.1f}" y="{y(p):.1f}" width="{barw:.1f}" height="{bottom-y(p):.1f}" fill="{GOLD}"/>')
        parts.append(f'<line x1="{cx:.1f}" y1="{y(lo):.1f}" x2="{cx:.1f}" y2="{y(hi):.1f}" stroke="{INK}" stroke-width="1.4"/>')
        parts.append(f'<line x1="{cx-4:.1f}" y1="{y(lo):.1f}" x2="{cx+4:.1f}" y2="{y(lo):.1f}" stroke="{INK}"/>')
        parts.append(f'<line x1="{cx-4:.1f}" y1="{y(hi):.1f}" x2="{cx+4:.1f}" y2="{y(hi):.1f}" stroke="{INK}"/>')
    parts.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="{INK}"/>')
    parts.append(svg_text(22, (top + bottom) / 2, "Obliterative share (%)", 11, anchor="middle", rotate=-90))
    parts.append(svg_text(width / 2, 516, "Ages 18-24 and 25-29 are combined to protect the smaller cell.", 10, anchor="middle", color=GREY))
    save_svg("Figure1_obliterative_share_by_age.svg", width, height, parts, "Obliterative share by age")

    with (OUTPUT / "Table3_annual_first_procedure.csv").open(newline="") as handle:
        annual = list(csv.DictReader(handle))
    years = [int(r["study_year"]) for r in annual]
    width, height = 1120, 520
    parts = [
        svg_text(42, 34, "Figure 2. Annual eligible-year obliterative and reconstructive POP procedures", 18, weight=700),
        svg_text(42, 58, "Panel A: obliterative share; Panel B: crude rates per 1,000 eligible woman-years", 12, color=GREY),
    ]
    panels = [(70, 520), (620, 1070)]
    top, bottom = 105, 415
    x = lambda year, l, r: l + (r - l) * (year - min(years)) / (max(years) - min(years))
    # Panel A
    l, r = panels[0]
    y1 = lambda v: bottom - (bottom - top) * v / 7.0
    for tick in range(0, 8):
        parts.append(f'<line x1="{l}" y1="{y1(tick):.1f}" x2="{r}" y2="{y1(tick):.1f}" stroke="{LIGHT}"/>')
        parts.append(svg_text(l - 8, y1(tick) + 4, str(tick), 9, anchor="end", color=GREY))
    vals = [float(row["obliterative_share_percent"]) for row in annual]
    standardized_vals = [float(row["age_standardized_obliterative_share_percent"]) for row in annual]
    points = " ".join(f'{x(yv,l,r):.1f},{y1(v):.1f}' for yv, v in zip(years, vals))
    parts.append(f'<polyline points="{points}" fill="none" stroke="{GOLD}" stroke-width="2.6"/>')
    for yr, val in zip(years, vals):
        parts.append(f'<circle cx="{x(yr,l,r):.1f}" cy="{y1(val):.1f}" r="4" fill="{GOLD}" stroke="#FFF"/>')
    standardized_points = " ".join(
        f'{x(yv,l,r):.1f},{y1(v):.1f}' for yv, v in zip(years, standardized_vals)
    )
    parts.append(f'<polyline points="{standardized_points}" fill="none" stroke="{PURPLE}" stroke-width="2.2" stroke-dasharray="6 4"/>')
    parts.append(svg_text((l + r) / 2, 88, "A. Obliterative share (%)", 13, anchor="middle", weight=700))
    # Panel B
    l2, r2 = panels[1]
    ymax = 2.5
    y2 = lambda v: bottom - (bottom - top) * v / ymax
    for tick in (0, 0.5, 1.0, 1.5, 2.0, 2.5):
        parts.append(f'<line x1="{l2}" y1="{y2(tick):.1f}" x2="{r2}" y2="{y2(tick):.1f}" stroke="{LIGHT}"/>')
        parts.append(svg_text(l2 - 8, y2(tick) + 4, f"{tick:.1f}", 9, anchor="end", color=GREY))
    for field, color in (("reconstructive_rate_per_1000", BLUE), ("obliterative_rate_per_1000", GOLD)):
        vals2 = [float(row[field]) for row in annual]
        pts = " ".join(f'{x(yv,l2,r2):.1f},{y2(v):.1f}' for yv, v in zip(years, vals2))
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        for yr, val in zip(years, vals2):
            parts.append(f'<circle cx="{x(yr,l2,r2):.1f}" cy="{y2(val):.1f}" r="3.5" fill="{color}"/>')
    parts.append(svg_text((l2 + r2) / 2, 88, "B. Crude rates per 1,000", 13, anchor="middle", weight=700))
    for panel_l, panel_r in panels:
        parts.append(f'<line x1="{panel_l}" y1="{bottom}" x2="{panel_r}" y2="{bottom}" stroke="{INK}"/>')
        for yr in years:
            parts.append(svg_text(x(yr, panel_l, panel_r), bottom + 20, str(yr), 8, anchor="middle", color=GREY))
    parts.append(f'<line x1="150" y1="462" x2="178" y2="462" stroke="{GOLD}" stroke-width="2.6"/>')
    parts.append(svg_text(186, 466, "Crude share", 10, color=GREY))
    parts.append(f'<line x1="280" y1="462" x2="308" y2="462" stroke="{PURPLE}" stroke-width="2.2" stroke-dasharray="6 4"/>')
    parts.append(svg_text(316, 466, "Age-standardized share", 10, color=GREY))
    parts.append(f'<line x1="720" y1="462" x2="748" y2="462" stroke="{BLUE}" stroke-width="2.5"/>')
    parts.append(svg_text(756, 466, "Reconstructive", 10, color=GREY))
    parts.append(f'<line x1="860" y1="462" x2="888" y2="462" stroke="{GOLD}" stroke-width="2.5"/>')
    parts.append(svg_text(896, 466, "Obliterative", 10, color=GREY))
    parts.append(svg_text(width / 2, 505, "Annual values are descriptive.", 10, anchor="middle", color=GREY))
    save_svg("Figure2_annual_share_and_rates.svg", width, height, parts, "Annual POP procedure-group shares and rates")

    broad_order = ("<65", "65-74", "75-84", "85-89")
    broad_cells = {
        (int(row["study_year"]), row["broad_age"], row["procedure_group"]): integer(row["women"])
        for row in read_rows("pooled_first_by_year_broad_age.csv")
    }
    broad_values: dict[str, list[float]] = {}
    for broad_age in broad_order:
        broad_values[broad_age] = []
        for year in years:
            o = broad_cells[(year, broad_age, "Obliterative")]
            r = broad_cells[(year, broad_age, "Reconstructive")]
            assert o is not None and r is not None
            broad_values[broad_age].append(100 * o / (o + r))

    width, height = 980, 540
    left, right, top, bottom = 86, 930, 98, 420
    y_max = 60.0
    x3 = lambda year: left + (right - left) * (year - min(years)) / (max(years) - min(years))
    y3 = lambda value: bottom - (bottom - top) * value / y_max
    parts = [
        svg_text(42, 34, "Figure 3. Annual obliterative share by age group", 18, weight=700),
        svg_text(42, 58, "First qualifying procedure per enrollee occurring in an eligible woman-year", 12, color=GREY),
    ]
    for tick in range(0, 61, 10):
        parts.append(f'<line x1="{left}" y1="{y3(tick):.1f}" x2="{right}" y2="{y3(tick):.1f}" stroke="{LIGHT}"/>')
        parts.append(svg_text(left - 10, y3(tick) + 4, str(tick), 10, anchor="end", color=GREY))
    styles = {
        "<65": (BLUE, ""),
        "65-74": (OLIVE, "7 4"),
        "75-84": (GOLD, ""),
        "85-89": (PURPLE, "3 3"),
    }
    for broad_age in broad_order:
        color, dash = styles[broad_age]
        values = broad_values[broad_age]
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        points = " ".join(f'{x3(year):.1f},{y3(value):.1f}' for year, value in zip(years, values))
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.7"{dash_attr}/>')
        for year, value in zip(years, values):
            parts.append(f'<circle cx="{x3(year):.1f}" cy="{y3(value):.1f}" r="3.8" fill="{color}" stroke="#FFF"/>')
    for year in years:
        parts.append(svg_text(x3(year), bottom + 21, str(year), 9, anchor="middle", color=GREY))
    parts.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="{INK}"/>')
    parts.append(svg_text(22, (top + bottom) / 2, "Obliterative share (%)", 11, anchor="middle", rotate=-90))
    legend_x = 200
    for broad_age in broad_order:
        color, dash = styles[broad_age]
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        parts.append(f'<line x1="{legend_x}" y1="466" x2="{legend_x+28}" y2="466" stroke="{color}" stroke-width="2.7"{dash_attr}/>')
        parts.append(svg_text(legend_x + 36, 470, broad_age, 10, color=GREY))
        legend_x += 155
    parts.append(svg_text(width / 2, 518, "Shares use reportable broad age strata; annual values are descriptive.", 10, anchor="middle", color=GREY))
    save_svg("Figure3_annual_obliterative_share_by_age.svg", width, height, parts, "Annual obliterative share by broad age group")


def write_summary(m: dict[str, float | int]) -> None:
    lines = [
        "P02 analysis summary",
        "Run date: 2026-09-04",
        "",
        f"Eligible woman-years: {m['total_py']:,}",
        f"Enrollees with a first qualifying explicit-code POP procedure occurring in an eligible woman-year: {m['total']:,}",
        f"Obliterative: {m['obl']:,} ({100*m['overall_share']:.2f}%)",
        f"Reconstructive: {m['rec']:,} ({100*(1-m['overall_share']):.2f}%)",
        f"Mixed-code dates classified as obliterative: {m['mixed']:,} ({100*m['mixed_share_all']:.2f}% of all first procedures; {100*m['mixed_share_obl']:.1f}% of obliterative-classified first procedures)",
        f"Obliterative share: {m['first_year_share']:.2f}% in 2014 and {m['last_year_share']:.2f}% in 2024; absolute change {m['first_last_pp']:.2f} percentage points and relative change {m['first_last_relative']:.1f}%.",
        f"Directly age-standardized obliterative share: {m['first_year_standardized']:.2f}% in 2014 and {m['last_year_standardized']:.2f}% in 2024.",
        f"Obliterative share by broad age: {100*m['broad_75_84']:.2f}% at 75-84 and {100*m['broad_85_89']:.2f}% at 85-89",
        "",
        "All results are descriptive. Person-level resolution occurred after unioning CCAE and MDCR records.",
        "Nonzero cells below 11 were removed from the transfer set; redundant margins were excluded or ages were collapsed so protected cells are not recoverable by subtraction.",
    ]
    (OUTPUT / "P02_analysis_summary.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    metrics = make_tables()
    make_figures()
    write_summary(metrics)
    print((OUTPUT / "P02_analysis_summary.txt").read_text())


if __name__ == "__main__":
    main()
