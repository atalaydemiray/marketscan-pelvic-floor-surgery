#!/usr/bin/env python3
"""Build journal-agnostic publication table and figure packages for P01-P03.

The analysis CSVs remain the single source of truth. Main and supplementary
table files are byte-for-byte copies. Figure SVGs remain vector originals;
PNG and TIFF exports are tightly cropped, RGB, and tagged at 300 dpi.
"""

from __future__ import annotations

import hashlib
import os
import signal
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-09-04"
TARGET_WIDTH = 2400
TARGET_DPI = (300, 300)

PAPERS = {
    "P01": {
        "paper": ROOT / "P01 - Lifetime Risk of SUI & POP Surgery",
        "data_source": "Analysis 2026-09-04",
        "figure_source": "Analysis 2026-09-04",
        "main_tables": [
            "Table1_cohort_by_age.csv",
            "Table2_age_specific_rates.csv",
            "Table3_lifetime_risk.csv",
        ],
        "supplementary_tables": [
            ("Table4_annual_crude_rates.csv", "Supplementary_Table_S1_annual_crude_and_standardized_rates.csv"),
            ("Table5_period_specific_cumulative_risk.csv", "Supplementary_Table_S2_period_specific_cumulative_risk.csv"),
            ("Table6_deterministic_sensitivity_analysis.csv", "Supplementary_Table_S3_deterministic_sensitivity.csv"),
            ("Table7_washout_sensitivity.csv", "Supplementary_Table_S4_washout_sensitivity.csv"),
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
        "data_source": "Analysis 2026-09-04",
        "figure_source": "Analysis 2026-09-04",
        "main_tables": [
            "Table1_overall_summary.csv",
            "Table2_first_procedure_by_age.csv",
            "Table3_annual_first_procedure.csv",
            "Table4_temporal_change_summary.csv",
        ],
        "supplementary_tables": [
            ("Table5_eligible_year_procedure_dates.csv", "Supplementary_Table_S1_eligible_year_procedure_dates.csv"),
            ("Table6_code_contribution.csv", "Supplementary_Table_S2_code_contribution.csv"),
            ("Table7_parent_definition_reconciliation.csv", "Supplementary_Table_S3_parent_definition_reconciliation.csv"),
            ("Table8_parent_definition_sensitivity.csv", "Supplementary_Table_S4_parent_definition_sensitivity.csv"),
        ],
        "figures": [
            (
                "Figure1_obliterative_share_by_age.svg",
                "Obliterative share of the first qualifying POP procedure per enrollee occurring in an eligible woman-year, with Wilson 95% confidence intervals.",
            ),
            (
                "Figure2_annual_share_and_rates.svg",
                "Annual obliterative share and crude obliterative and reconstructive rates per 1,000 eligible woman-years; values are descriptive.",
            ),
            (
                "Figure3_annual_obliterative_share_by_age.svg",
                "Annual obliterative share among eligible-year first qualifying POP procedures in four broad age groups; values are descriptive.",
            ),
        ],
    },
    "P03": {
        "paper": ROOT / "P03 - Sling vs Urethral Bulking Temporal Trends",
        "data_source": "Analysis 2026-09-04",
        "figure_source": "Analysis 2026-09-04",
        "main_tables": [
            "Table1_first_qualifying_procedure_in_eligible_year.csv",
            "Table2_period_comparison.csv",
            "Table3_annual_eligible_year_isolated.csv",
            "Table4_age_period_isolated.csv",
            "Table5_temporal_change_summary.csv",
        ],
        "supplementary_tables": [
            ("Table6_all_period_burden_90_vs_180_days.csv", "Supplementary_Table_S1_bulking_course_sensitivity.csv"),
            ("Table7_annual_all_period_burden_90_day_isolated.csv", "Supplementary_Table_S2_annual_90_day_burden.csv"),
            ("Table8_first_procedure_scope_sensitivity.csv", "Supplementary_Table_S3_first_procedure_scope_sensitivity.csv"),
        ],
        "figures": [
            (
                "Figure1_annual_bulking_share.svg",
                "Annual bulking share among eligible-year first qualifying isolated-SUI sling or bulking procedures; hybrid procedures are excluded and 2020 is descriptive.",
            ),
            (
                "Figure2_annual_first_procedure_rates.svg",
                "Annual crude rates of eligible-year first qualifying isolated-SUI sling and urethral bulking procedures per 1,000 eligible woman-years.",
            ),
            (
                "Figure3_age_period_bulking_share.svg",
                "Bulking share among eligible-year isolated-SUI procedures in 2014-2019 versus 2020-2024; ages 18-29 are combined and older ages use 5-year groups.",
            ),
            (
                "Figure4_first_vs_burden_bulking_share.svg",
                "Annual bulking shares for eligible-year first procedures and all-period treatment burden using 90-day bulking courses; 2020 is descriptive.",
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


def chrome_binary() -> Path:
    candidates = [
        os.environ.get("CHROME_BIN"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    raise FileNotFoundError("A Chrome/Chromium executable is required for deterministic SVG rasterization")


def render_svg(source: Path) -> Image.Image:
    """Render SVG with a fixed headless-browser viewport into a temporary PNG."""
    with tempfile.TemporaryDirectory(prefix="marketscan-svg-") as temp_directory:
        png = Path(temp_directory) / "render.png"
        profile = Path(temp_directory) / "chrome-profile"
        command = [
            str(chrome_binary()),
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            "--disable-background-networking",
            "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=1000",
            "--force-device-scale-factor=2",
            "--window-size=1400,1100",
            f"--user-data-dir={profile}",
            f"--screenshot={png}",
            source.resolve().as_uri(),
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        deadline = time.monotonic() + 30
        last_size = -1
        stable_checks = 0
        while time.monotonic() < deadline:
            if png.exists() and png.stat().st_size > 0:
                current_size = png.stat().st_size
                stable_checks = stable_checks + 1 if current_size == last_size else 0
                last_size = current_size
                if stable_checks >= 3:
                    break
            if process.poll() is not None and not png.exists():
                break
            time.sleep(0.1)
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
        try:
            _stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            _stdout, stderr = process.communicate()
        if not png.exists() or png.stat().st_size == 0:
            raise RuntimeError(f"SVG rendering failed for {source}: {stderr.strip()}")
        image = flattened_rgb(png)
        image.load()
        return image


def publication_raster(source: Path) -> Image.Image:
    image = render_svg(source)
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


def build_paper(code: str, spec: dict) -> list[str]:
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
        "- Nonzero counts below 11 remain masked; redundant margins were excluded or age groups were collapsed to prevent recovery by subtraction.",
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

        image = publication_raster(svg_source)
        stem = Path(svg_name).stem
        png_target = figure_output / f"{stem}.png"
        tif_target = figure_output / f"{stem}.tif"
        image.save(png_target, format="PNG", dpi=TARGET_DPI, optimize=True)
        image.save(tif_target, format="TIFF", dpi=TARGET_DPI, compression="tiff_lzw")

        legend_lines.extend([f"## Figure {index}", "", legend, ""])
        lines.append(
            f"- Figure {index}: `{svg_target.relative_to(ROOT)}` plus PNG/TIFF "
            f"({image.width} x {image.height} pixels; 300 dpi)"
        )

    (figure_output / "FIGURE_LEGENDS.md").write_text("\n".join(legend_lines), encoding="utf-8")
    lines.append("")
    return lines


def main() -> None:
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
    for code in PAPERS:
        spec = PAPERS[code]
        manifest.extend(build_paper(code, spec))

    output = ROOT / "04 Logs" / f"PUBLICATION_TABLES_FIGURES_MANIFEST_{DATE}.md"
    output.write_text("\n".join(manifest), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
