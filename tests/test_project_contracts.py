from __future__ import annotations

import csv
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ProjectContracts(unittest.TestCase):
    def test_public_mortality_input(self) -> None:
        path = ROOT / "P01 - Lifetime Risk of SUI & POP Surgery/02 Code/nchs2019_female_qx.csv"
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([int(row["age"]) for row in rows], list(range(18, 90)))
        self.assertTrue(all(0 < float(row["qx"]) < 1 for row in rows))

    def test_p01_cross_database_integrity_contract(self) -> None:
        code = (ROOT / "P01 - Lifetime Risk of SUI & POP Surgery/02 Code/P01_wu_export.R").read_text()
        self.assertIn("COUNT(DISTINCT (ENROLID, study_year))", code)
        self.assertIn("pooled_distinct$duplicate_woman_years == 0", code)
        self.assertIn("COUNT(DISTINCT CASE WHEN incident_sui=1 OR incident_pop=1", code)

    def test_p02_clinical_code_contract(self) -> None:
        code = (ROOT / "P02 - Obliterative vs Reconstructive POP Surgery/02 Code/P02_server_analysis.R").read_text()
        obl_match = re.search(r"OBLITERATIVE\s*<-\s*c\((.*?)\)", code, re.S)
        rec_match = re.search(r"RECONSTRUCTIVE\s*<-\s*c\((.*?)\)", code, re.S)
        self.assertIsNotNone(obl_match)
        self.assertIsNotNone(rec_match)
        obliterative = set(re.findall(r'"(\d{5})"', obl_match.group(1)))
        reconstructive = set(re.findall(r'"(\d{5})"', rec_match.group(1)))
        self.assertEqual(obliterative, {"57106", "57110", "57120", "58275", "58280"})
        self.assertTrue(obliterative.isdisjoint(reconstructive))
        self.assertEqual(len(reconstructive), 23)

    def test_p03_treatment_and_window_contract(self) -> None:
        code = (ROOT / "P03 - Sling vs Urethral Bulking Temporal Trends/02 Code/P03_server_analysis.R").read_text()
        self.assertIn("list_contains(s.codes, '57288')", code)
        self.assertIn("list_contains(s.codes, '51715')", code)
        self.assertIn("procedure_category='Bulking'", code)
        self.assertIn("for (window_days in c(90L, 180L))", code)
        self.assertIn("'Hybrid'", code)

    def test_no_monte_carlo_in_p01(self) -> None:
        code = (ROOT / "P01 - Lifetime Risk of SUI & POP Surgery/02 Code/P01_wu_analysis.py").read_text().lower()
        self.assertNotIn("monte carlo", code)
        self.assertIn("delta-method", code)

    def test_no_restricted_artifacts(self) -> None:
        banned_suffixes = {
            ".parquet", ".feather", ".fst", ".rds", ".rda", ".sas7bdat", ".xpt",
            ".dta", ".sav", ".docx", ".pdf", ".png", ".tif", ".tiff",
        }
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts:
                continue
            self.assertNotIn(path.suffix.lower(), banned_suffixes, str(path))
            if path.suffix.lower() == ".csv":
                self.assertEqual(path.name, "nchs2019_female_qx.csv")
            self.assertFalse(any(part in {"03 Data", "04 Figures", "05 Manuscript"} for part in path.parts), str(path))


if __name__ == "__main__":
    unittest.main()
