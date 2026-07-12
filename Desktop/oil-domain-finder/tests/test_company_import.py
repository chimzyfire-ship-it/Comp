"""Tests for the local CSV import and checkpoint foundation."""

from __future__ import annotations

import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from services.company_import import InputValidationError, export_run, import_companies


class CompanyImportTests(unittest.TestCase):
    def test_import_deduplicates_normalized_rows_and_exports_checkpoints(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "companies.csv"
            input_path.write_text(
                "company_name,location,website\n"
                "Acme Oil,US,acme.example\n"
                "  acme oil  , us ,https://different.example/path\n"
                "Harbor Gas,GB,\n"
                ",CA,bad.example\n",
                encoding="utf-8",
            )
            database = root / "runs.sqlite3"
            summary = import_companies(input_path, database, batch_size=2)
            output_path = root / "export.csv"

            self.assertEqual(summary.input_rows, 4)
            self.assertEqual(summary.accepted_rows, 3)
            self.assertEqual(summary.stored_records, 2)
            self.assertEqual(summary.duplicate_rows, 1)
            self.assertEqual(summary.invalid_rows, 1)
            self.assertEqual(summary.new_companies, 2)
            self.assertEqual(export_run(database, summary.run_id, output_path), 2)

            with output_path.open(newline="", encoding="utf-8") as output_file:
                rows = list(csv.DictReader(output_file))
            self.assertEqual(rows[0]["website"], "https://acme.example")
            self.assertEqual(rows[0]["status"], "provided_website")
            self.assertEqual(rows[1]["status"], "pending_discovery")

    def test_missing_company_name_header_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "companies.csv"
            input_path.write_text("name,location\nAcme,US\n", encoding="utf-8")

            with self.assertRaisesRegex(InputValidationError, "company_name"):
                import_companies(input_path, root / "runs.sqlite3")


if __name__ == "__main__":
    unittest.main()
