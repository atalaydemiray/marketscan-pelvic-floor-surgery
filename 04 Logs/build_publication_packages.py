#!/usr/bin/env python3
"""Build journal-agnostic publication table and figure packages for P01-P03.

The analysis CSVs remain the single source of truth. Main and supplementary
table files are byte-for-byte copies. Figure SVGs remain vector originals;
PNG and TIFF exports are tightly cropped, RGB, and tagged at 300 dpi.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-09-02"
TARGET_WIDTH = 2400
TARGET_DPI = (300, 300)

PAPERS = {
    "P01": {
        "paper": ROOT / "P01 - Lifetime Risk of SUI & POP Surgery",
        "data_source": "Wu Comparable 2026-09-01",
        "figure_source": "Wu Comparable 2026-09-01",
        "main_tables": [
            "Table1_cohort_by_age.csv",
            "Table2_age_specific_rates.csv",
            "Table3_lifetime_risk.csv",
        ],
        "supplementary_tables": [
            ("Table4_annual_crude_rates.csv", "Supplementary_Table_S1_annual_crude_rates.csv"),
        ],
        "figures": [
            (
                "Figure1_age_specific_rates.svg",
                "Age-specific qualifying SUI, POP, and either-operation rates in 2014-2024, with 95% Wilson confidence intervals, compared descriptively with Wu et al. 2007-2011.",
            ),
            (
                "Figure2_annual_crude_rates.svg",
                "Annual descriptive rates of qualifying SUI, POP, and either operation per 1,000 eligible woman-years, 2014-2024.",
            ),
        ],
    },
    "P02": {
        "paper": ROOT / "P02 - Obliterative vs Reconstructive POP Surgery",
        "data_source": "Analysis 2026-09-02",
        "figure_source": "Analysis 2026-09-02",
        "main_tables": [
            "Table1_overall_summary.csv",
            "Table2_first_procedure_by_age.csv",
            "Table3_annual_first_procedure.csv",
            "Table4_temporal_change_summary.csv",
        ],
        "supplementary_tables": [
            ("Table5_total_procedure_burden.csv", "Supplementary_Table_S1_total_procedure_burden.csv"),
            ("Table6_code_contribution.csv", "Supplementary_Table_S2_code_contribution.csv"),
        ],
        "figures": [
            (
                "Figure1_obliterative_share_by_age.svg",
                "Obliterative share of first observed qualifying POP procedures by 5-year age group, with Wilson 95% confidence intervals.",
            ),
            (
                "Figure2_annual_share_and_rates.svg",
                "Annual obliterative share and crude obliterative and reconstructive rates per 1,000 eligible woman-years; values are descriptive.",
            ),
            (
                "Figure3_annual_obliterative_share_by_age.svg",
                "Annual obliterative share among first observed qualifying POP procedures in four reportable broad age groups; values are descriptive.",
            ),
        ],
    },
    "P03": {
        "paper": ROOT / "P03 - Sling vs Urethral Bulking Temporal Trends",
        "data_source": "Analysis 2026-09-02",
        "figure_source": "Analysis 2026-09-02",
        "main_tables": [
            "Table1_overall_first_observed.csv",
            "Table2_period_comparison.csv",
            "Table3_annual_first_observed_isolated.csv",
            "Table4_age_period_isolated.csv",
            "Table5_temporal_change_summary.csv",
        ],
        "supplementary_tables": [
            ("Table6_total_burden_90_vs_180_days.csv", "Supplementary_Table_S1_bulking_course_sensitivity.csv"),
            ("Table7_annual_total_burden_90_day_isolated.csv", "Supplementary_Table_S2_annual_90_day_burden.csv"),
        ],
        "figures": [
            (
                "Figure1_annual_bulking_share.svg",
                "Annual bulking share among first observed isolated-SUI sling or bulking procedures; hybrid procedures are excluded and 2020 is descriptive.",
            ),
            (
                "Figure2_annual_first_procedure_rates.svg",
                "Annual crude rates of first observed isolated-SUI sling and urethral bulking procedures per 1,000 eligible woman-years.",
            ),
            (
                "Figure3_age_period_bulking_share.svg",
                "Bulking share among first observed isolated-SUI sling or bulking procedures in 2014-2019 versus 2020-2024 by 5-year age group.",
            ),
            (
                "Figure4_first_vs_burden_bulking_share.svg",
                "Annual bulking shares for first observed isolated-SUI procedures and total procedure burden using 90-day bulking courses; 2020 is descriptive.",
            ),
        ],
    },
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def flattened_rgb(path: Path) -> Image.Image:
    with Image.open(path) as opened:
        rgba = opened.convert("RGBA")
    background = Image.new("RGBA", rgba.size, "white")
    background.alpha_composite(rgba)
    return background.convert("RGB")


def publication_raster(source: Path) -> Image.Image:
    image = flattened_rgb(source)
    white = Image.new("RGB", image.size, "white")
    bbox = ImageChops.difference(image, white).getbbox()
    if bbox is None:
        raise ValueError(f"No visible content in {source}")
    padding = max(36, round(max(image.size) * 0.018))
    left = max(0, bbox[0] - padding)
    top = max(0, bbox[1] - padding)
    right = min(image.width, bbox[2] + padding)
    bottom = min(image.height, bbox[3] + padding)
    cropped = image.crop((left, top, right, bottom))
    target_height = round(cropped.height * TARGET_WIDTH / cropped.width)
    return cropped.resize((TARGET_WIDTH, target_height), Image.Resampling.LANCZOS)


def build_paper(code: str, spec: dict, thumbnail_dir: Path | None) -> list[str]:
    paper: Path = spec["paper"]
    data_source = paper / "03 Data" / spec["data_source"]
    figure_source = paper / "04 Figures" / spec["figure_source"]
    data_output = paper / "03 Data" / f"Publication Ready {DATE}"
    main_output = data_output / "Main Tables"
    supplementary_output = data_output / "Supplementary Tables"
    figure_output = paper / "04 Figures" / f"Publication Ready {DATE}"
    for directory in (main_output, supplementary_output, figure_output):
        directory.mkdir(parents=True, exist_ok=True)

    lines = [f"## {code}", ""]
    table_lines = [
        f"# {code} publication table package",
        "",
        f"Date: {DATE}",
        "",
        "Main and supplementary CSVs are byte-for-byte copies of the verified analysis tables.",
        "",
        "## Main tables",
        "",
    ]
    for name in spec["main_tables"]:
        source = data_source / name
        target = main_output / name
        shutil.copy2(source, target)
        if digest(source) != digest(target):
            raise AssertionError(f"Copy mismatch: {target}")
        table_lines.append(f"- {target.name}")
        lines.append(f"- Main table: `{target.relative_to(ROOT)}`")

    table_lines.extend(["", "## Supplementary tables", ""])
    for source_name, target_name in spec["supplementary_tables"]:
        source = data_source / source_name
        target = supplementary_output / target_name
        shutil.copy2(source, target)
        if digest(source) != digest(target):
            raise AssertionError(f"Copy mismatch: {target}")
        table_lines.append(f"- {target.name} (source: {source_name})")
        lines.append(f"- Supplementary table: `{target.relative_to(ROOT)}`")

    table_lines.extend([
        "",
        "## Notes",
        "",
        "- Counts and denominators retain the estimand labels used in the manuscript.",
        "- SUPPRESSED cells remain suppressed and were not reconstructed.",
        "- Exact journal styling can be applied after the target journal is selected.",
        "",
    ])
    (data_output / "README.md").write_text("\n".join(table_lines), encoding="utf-8")

    legend_lines = [
        f"# {code} figure legends",
        "",
        f"Date: {DATE}",
        "",
        "Vector SVG, 300-dpi PNG, and 300-dpi LZW-compressed TIFF versions are supplied.",
        "",
    ]
    for index, (svg_name, legend) in enumerate(spec["figures"], start=1):
        svg_source = figure_source / svg_name
        svg_target = figure_output / svg_name
        shutil.copy2(svg_source, svg_target)

        rendered_candidate = thumbnail_dir / f"{svg_name}.png" if thumbnail_dir is not None else None
        if rendered_candidate is not None and rendered_candidate.exists():
            raster_source = rendered_candidate
        else:
            raster_source = figure_source / f"{Path(svg_name).stem}.png"
        if not raster_source.exists():
            raise FileNotFoundError(f"Missing rendered SVG preview: {raster_source}")

        image = publication_raster(raster_source)
        stem = Path(svg_name).stem
        png_target = figure_output / f"{stem}.png"
        tif_target = figure_output / f"{stem}.tif"
        image.save(png_target, format="PNG", dpi=TARGET_DPI, optimize=True)
        image.save(tif_target, format="TIFF", dpi=TARGET_DPI, compression="tiff_lzw")
        image.save(figure_source / f"{stem}.png", format="PNG", dpi=TARGET_DPI, optimize=True)

        legend_lines.extend([f"## Figure {index}", "", legend, ""])
        lines.append(
            f"- Figure {index}: `{svg_target.relative_to(ROOT)}` plus PNG/TIFF "
            f"({image.width} x {image.height} pixels; 300 dpi)"
        )

    (figure_output / "FIGURE_LEGENDS.md").write_text("\n".join(legend_lines), encoding="utf-8")
    lines.append("")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--thumbnail-dir",
        type=Path,
        help="Directory containing Quick Look PNGs named <figure>.svg.png.",
    )
    parser.add_argument(
        "--papers",
        nargs="+",
        choices=tuple(PAPERS),
        default=list(PAPERS),
        help="Paper codes to build (default: all).",
    )
    args = parser.parse_args()
    thumbnail_dir = args.thumbnail_dir.resolve() if args.thumbnail_dir else None

    manifest = [
        "# MarketScan publication tables and figures manifest",
        "",
        f"Date: {DATE}",
        "",
        "Status: BUILT; validation is recorded separately.",
        "",
        "This package is journal-agnostic. Final column width, font, and file-naming requirements should be checked against the selected journal before submission.",
        "",
    ]
    for code in args.papers:
        spec = PAPERS[code]
        manifest.extend(build_paper(code, spec, thumbnail_dir))

    output = ROOT / "04 Logs" / f"PUBLICATION_TABLES_FIGURES_MANIFEST_{DATE}.md"
    output.write_text("\n".join(manifest), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
