from __future__ import annotations

import csv
import importlib.util
import math
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(relative_path: str, name: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


P01 = load_module(
    "P01 - Lifetime Risk of SUI & POP Surgery/02 Code/P01_wu_analysis.py", "p01_analysis"
)
P02 = load_module(
    "P02 - Obliterative vs Reconstructive POP Surgery/02 Code/P02_analysis.py", "p02_analysis"
)
P03 = load_module(
    "P03 - Sling vs Urethral Bulking Temporal Trends/02 Code/P03_analysis.py", "p03_analysis"
)


class NumericalMethods(unittest.TestCase):
    def test_closed_form_one_age_matches_input_probability(self) -> None:
        probabilities = {age: 0.0 for age in range(18, 90)}
        mortality = {age: 0.0 for age in range(18, 90)}
        probabilities[18] = 0.10
        self.assertAlmostEqual(P01.cumulative_risk(probabilities, mortality, max_age=19), 0.10, places=14)

    def test_closed_form_event_plus_mortality_known_answer(self) -> None:
        probabilities = {age: 0.0 for age in range(18, 90)}
        mortality = {age: 0.0 for age in range(18, 90)}
        probabilities[18] = 0.10
        mortality[18] = -math.log(0.80)
        event_hazard = -math.log(0.90)
        expected = event_hazard / (event_hazard + mortality[18]) * (
            1 - math.exp(-(event_hazard + mortality[18]))
        )
        self.assertAlmostEqual(P01.cumulative_risk(probabilities, mortality, max_age=19), expected, places=14)

    def test_wilson_interval_known_answer(self) -> None:
        lower, upper = P02.wilson(5, 10)
        self.assertAlmostEqual(lower, 0.2365930905, places=9)
        self.assertAlmostEqual(upper, 0.7634069095, places=9)

    def test_newcombe_difference_uses_integer_counts(self) -> None:
        difference, lower, upper = P03.newcombe_difference(10, 100, 20, 100)
        self.assertAlmostEqual(difference, 0.10, places=14)
        self.assertLess(lower, difference)
        self.assertGreater(upper, difference)
        self.assertGreater(lower, 0.0)

    def test_risk_ratio_interval(self) -> None:
        ratio, lower, upper = P03.risk_ratio_interval(10, 100, 20, 100)
        self.assertAlmostEqual(ratio, 2.0, places=14)
        self.assertLess(lower, ratio)
        self.assertGreater(upper, ratio)


class ProjectContracts(unittest.TestCase):
    def test_public_mortality_input(self) -> None:
        path = ROOT / "P01 - Lifetime Risk of SUI & POP Surgery/02 Code/nchs2019_female_qx.csv"
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([int(row["age"]) for row in rows], list(range(18, 90)))
        self.assertTrue(all(0 < float(row["qx"]) < 1 for row in rows))
        code = (ROOT / "P01 - Lifetime Risk of SUI & POP Surgery/02 Code/P01_wu_analysis.py").read_text()
        self.assertIn("https://stacks.cdc.gov/view/cdc/231916", code)

    def test_public_cpt_lifecycle_matrix(self) -> None:
        path = ROOT / "docs/cpt_lifecycle_2014_2024.csv"
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 40)
        self.assertEqual(len({row["cpt"] for row in rows}), 40)
        limited = {row["cpt"]: row["active_years_in_cms_rvu"] for row in rows
                   if row["active_years_in_cms_rvu"] != "2014-2024"}
        self.assertEqual(limited, {"58293": "2014-2020", "57112": "2014-2020"})

    def test_p01_locked_cross_database_contract(self) -> None:
        code = (ROOT / "P01 - Lifetime Risk of SUI & POP Surgery/02 Code/P01_wu_export.R").read_text()
        for text in (
            "COUNT(DISTINCT (ENROLID, study_year))",
            "pooled_distinct$duplicate_woman_years == 0",
            "pooled$person_years == 47258198",
            "pooled$any_operations == 102440",
            "pooled$unique_operated_women == 102107",
        ):
            self.assertIn(text, code)

    def test_p02_clinical_and_calendar_contract(self) -> None:
        code = (ROOT / "P02 - Obliterative vs Reconstructive POP Surgery/02 Code/P02_server_analysis.R").read_text()
        obl_match = re.search(r"OBLITERATIVE\s*<-\s*c\((.*?)\)", code, re.S)
        rec_match = re.search(r"RECONSTRUCTIVE\s*<-\s*c\((.*?)\)", code, re.S)
        self.assertIsNotNone(obl_match)
        self.assertIsNotNone(rec_match)
        obliterative = set(re.findall(r'"(\d{5})"', obl_match.group(1)))
        reconstructive = set(re.findall(r'"(\d{5})"', rec_match.group(1)))
        self.assertEqual(obliterative, {"57106", "57110", "57120", "58275", "58280"})
        self.assertEqual(len(reconstructive), 23)
        self.assertTrue(obliterative.isdisjoint(reconstructive))
        self.assertIn("YEAR(CAST(svcdate AS DATE)) AS svc_year", code)
        self.assertIn("s.svc_year=e.study_year", code)
        self.assertIn("== 67162", code)

        local_code = (ROOT / "P02 - Obliterative vs Reconstructive POP Surgery/02 Code/P02_analysis.py").read_text()
        self.assertIn("standardized_share_by_year", local_code)
        self.assertNotIn("float(end['age_standardized_obliterative_share_percent'])", local_code)

    def test_p03_treatment_scope_and_window_contract(self) -> None:
        code = (ROOT / "P03 - Sling vs Urethral Bulking Temporal Trends/02 Code/P03_server_analysis.R").read_text()
        for text in (
            "list_contains(s.codes,'57288')",
            "list_contains(s.codes,'51715')",
            "p03_period_episodes",
            "for (window_days in c(90L, 180L))",
            "s.svc_year=e.study_year",
            "Secondary burden courses used all observed 2014-2024 events among ever-eligible women.",
        ):
            self.assertIn(text, code)

    def test_disclosure_export_contract(self) -> None:
        code = (ROOT / "P02 - Obliterative vs Reconstructive POP Surgery/02 Code/P02_P03_disclosure_export.R").read_text()
        self.assertIn("original <- x", code)
        self.assertIn("original[[count_col]] > 0", code)
        self.assertIn("age_publication", code)
        self.assertIn("fully_reportable_files", code)
        self.assertIn("!any(!is.na(values) & values > 0 & values < THRESHOLD)", code)
        self.assertNotIn("pooled_first_by_database.csv", code)

    def test_no_removed_complex_analysis_in_p01(self) -> None:
        code = (ROOT / "P01 - Lifetime Risk of SUI & POP Surgery/02 Code/P01_wu_analysis.py").read_text().lower()
        self.assertNotIn("monte carlo", code)
        self.assertIn("delta-method", code)

    def test_builder_is_deterministic_and_does_not_self_feed(self) -> None:
        code = (ROOT / "04 Logs/build_publication_packages.py").read_text()
        self.assertIn("--force-device-scale-factor=2", code)
        self.assertIn("TemporaryDirectory", code)
        self.assertNotIn("Quick Look", code)
        self.assertNotIn("image.save(figure_source", code)

    def test_repository_states_provenance_boundary(self) -> None:
        readme = (ROOT / "README.md").read_text()
        self.assertIn("from the derived parquet layer onward", readme)
        self.assertIn("does not claim raw-claims-to-results reproducibility", readme)

    def test_no_restricted_artifacts_are_tracked_or_in_history(self) -> None:
        banned_suffixes = {
            ".parquet", ".feather", ".fst", ".rds", ".rda", ".sas7bdat", ".xpt",
            ".dta", ".sav", ".docx", ".pdf", ".png", ".tif", ".tiff",
        }
        tracked = subprocess.run(
            ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
        ).stdout.decode().split("\0")
        history = subprocess.run(
            ["git", "log", "--all", "--name-only", "--pretty=format:"],
            cwd=ROOT, check=True, capture_output=True, text=True,
        ).stdout.splitlines()
        for name in {item for item in tracked + history if item}:
            path = Path(name)
            self.assertNotIn(path.suffix.lower(), banned_suffixes, name)
            if path.suffix.lower() == ".csv":
                self.assertIn(path.name, {"nchs2019_female_qx.csv", "cpt_lifecycle_2014_2024.csv"})
            self.assertFalse(any(part in {"03 Data", "04 Figures", "05 Manuscript"} for part in path.parts), name)


if __name__ == "__main__":
    unittest.main()
