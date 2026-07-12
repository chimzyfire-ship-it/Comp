"""Local, resumable company-list storage for no-key discovery workflows."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import sqlite3
from typing import Iterable
from urllib.parse import urlparse
from uuid import uuid4


class InputValidationError(ValueError):
    """Raised when an input CSV does not meet the documented schema."""


@dataclass(frozen=True)
class ImportSummary:
    """Counts and identity for one durable CSV import run."""

    run_id: str
    input_rows: int
    accepted_rows: int
    stored_records: int
    duplicate_rows: int
    invalid_rows: int
    new_companies: int
    existing_companies: int


def import_companies(input_path: Path, database_path: Path, batch_size: int = 1_000) -> ImportSummary:
    """Import a company CSV into SQLite, committing each bounded batch.

    Each run retains its own checkpoint rows, so a later discovery worker can
    resume pending companies without repeating input normalization or deduping.
    """
    if batch_size < 1:
        raise InputValidationError("batch_size must be at least 1")
    if not input_path.is_file():
        raise InputValidationError(f"Input CSV does not exist: {input_path}")

    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    try:
        _initialize_database(connection)
        run_id = str(uuid4())
        connection.execute(
            "INSERT INTO import_runs (run_id, input_path, started_at, status) VALUES (?, ?, ?, 'importing')",
            (run_id, str(input_path), _timestamp()),
        )
        summary = _import_rows(connection, input_path, run_id, batch_size)
        connection.execute(
            """UPDATE import_runs
               SET finished_at = ?, status = 'completed', input_rows = ?, accepted_rows = ?,
                   stored_records = ?, duplicate_rows = ?, invalid_rows = ?,
                   new_companies = ?, existing_companies = ?
               WHERE run_id = ?""",
            (
                _timestamp(),
                summary.input_rows,
                summary.accepted_rows,
                summary.stored_records,
                summary.duplicate_rows,
                summary.invalid_rows,
                summary.new_companies,
                summary.existing_companies,
                run_id,
            ),
        )
        connection.commit()
        return summary
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def export_run(database_path: Path, run_id: str, output_path: Path) -> int:
    """Export one run's canonical records and checkpoint states to CSV."""
    if not database_path.is_file():
        raise InputValidationError(f"Database does not exist: {database_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    try:
        run_exists = connection.execute("SELECT 1 FROM import_runs WHERE run_id = ?", (run_id,)).fetchone()
        if not run_exists:
            raise InputValidationError(f"Unknown run ID: {run_id}")
        rows = connection.execute(
            """SELECT companies.company_name, companies.location, companies.provided_website,
                      run_companies.status, run_companies.attempt_count, run_companies.last_error
                 FROM run_companies
                 JOIN companies ON companies.company_id = run_companies.company_id
                WHERE run_companies.run_id = ?
                ORDER BY companies.company_id""",
            (run_id,),
        )
        with output_path.open("w", encoding="utf-8", newline="") as output_file:
            writer = csv.writer(output_file)
            writer.writerow(("company_name", "location", "website", "status", "attempt_count", "last_error"))
            count = 0
            for row in rows:
                writer.writerow(row)
                count += 1
        return count
    finally:
        connection.close()


def get_run_summary(database_path: Path, run_id: str) -> ImportSummary:
    """Load a completed import summary for CLI status reporting."""
    if not database_path.is_file():
        raise InputValidationError(f"Database does not exist: {database_path}")
    connection = sqlite3.connect(database_path)
    try:
        row = connection.execute(
            """SELECT run_id, input_rows, accepted_rows, stored_records, duplicate_rows,
                      invalid_rows, new_companies, existing_companies
                 FROM import_runs WHERE run_id = ?""",
            (run_id,),
        ).fetchone()
        if not row:
            raise InputValidationError(f"Unknown run ID: {run_id}")
        return ImportSummary(*row)
    finally:
        connection.close()


def _import_rows(
    connection: sqlite3.Connection, input_path: Path, run_id: str, batch_size: int
) -> ImportSummary:
    counters = _Counters()
    with input_path.open("r", encoding="utf-8-sig", newline="") as input_file:
        reader = csv.DictReader(input_file)
        _validate_headers(reader.fieldnames)
        for row_number, row in enumerate(reader, start=2):
            counters.input_rows += 1
            try:
                company_name, location, website = _normalize_row(row)
            except InputValidationError as error:
                counters.invalid_rows += 1
                connection.execute(
                    "INSERT INTO import_errors (run_id, row_number, message) VALUES (?, ?, ?)",
                    (run_id, row_number, str(error)),
                )
            else:
                counters.accepted_rows += 1
                _store_company(connection, run_id, company_name, location, website, counters)

            if counters.input_rows % batch_size == 0:
                connection.commit()
        connection.commit()
    return ImportSummary(run_id, **counters.as_dict())


def _store_company(
    connection: sqlite3.Connection,
    run_id: str,
    company_name: str,
    location: str,
    website: str,
    counters: "_Counters",
) -> None:
    normalized_name = _normalize_key(company_name)
    normalized_location = _normalize_key(location)
    existing = connection.execute(
        """SELECT company_id, provided_website FROM companies
             WHERE normalized_name = ? AND normalized_location = ?""",
        (normalized_name, normalized_location),
    ).fetchone()
    if existing:
        company_id, existing_website = existing
        counters.existing_companies += 1
        if website and not existing_website:
            connection.execute(
                "UPDATE companies SET provided_website = ?, updated_at = ? WHERE company_id = ?",
                (website, _timestamp(), company_id),
            )
    else:
        cursor = connection.execute(
            """INSERT INTO companies
               (company_name, location, provided_website, normalized_name, normalized_location, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (company_name, location, website, normalized_name, normalized_location, _timestamp(), _timestamp()),
        )
        company_id = cursor.lastrowid
        counters.new_companies += 1

    status = "provided_website" if website else "pending_discovery"
    inserted = connection.execute(
        """INSERT OR IGNORE INTO run_companies
           (run_id, company_id, status, attempt_count, updated_at)
           VALUES (?, ?, ?, 0, ?)""",
        (run_id, company_id, status, _timestamp()),
    ).rowcount
    if inserted:
        counters.stored_records += 1
    else:
        counters.duplicate_rows += 1


def _validate_headers(fieldnames: Iterable[str] | None) -> None:
    if not fieldnames or "company_name" not in fieldnames:
        raise InputValidationError("CSV must contain a company_name column")


def _normalize_row(row: dict[str, str | None]) -> tuple[str, str, str]:
    company_name = " ".join((row.get("company_name") or "").split())
    if not company_name:
        raise InputValidationError("company_name is required")
    location = " ".join((row.get("location") or "").split())
    website = _normalize_website(row.get("website") or "")
    return company_name, location, website


def _normalize_website(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if "://" not in value:
        value = f"https://{value}"
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise InputValidationError("website must be a valid http(s) URL or domain")
    return f"{parsed.scheme}://{parsed.netloc.casefold()}"


def _normalize_key(value: str) -> str:
    return " ".join(value.casefold().split())


def _timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class _Counters:
    input_rows: int = 0
    accepted_rows: int = 0
    stored_records: int = 0
    duplicate_rows: int = 0
    invalid_rows: int = 0
    new_companies: int = 0
    existing_companies: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "input_rows": self.input_rows,
            "accepted_rows": self.accepted_rows,
            "stored_records": self.stored_records,
            "duplicate_rows": self.duplicate_rows,
            "invalid_rows": self.invalid_rows,
            "new_companies": self.new_companies,
            "existing_companies": self.existing_companies,
        }


def _initialize_database(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA journal_mode = WAL;
        CREATE TABLE IF NOT EXISTS import_runs (
            run_id TEXT PRIMARY KEY,
            input_path TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL,
            input_rows INTEGER NOT NULL DEFAULT 0,
            accepted_rows INTEGER NOT NULL DEFAULT 0,
            stored_records INTEGER NOT NULL DEFAULT 0,
            duplicate_rows INTEGER NOT NULL DEFAULT 0,
            invalid_rows INTEGER NOT NULL DEFAULT 0,
            new_companies INTEGER NOT NULL DEFAULT 0,
            existing_companies INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS companies (
            company_id INTEGER PRIMARY KEY,
            company_name TEXT NOT NULL,
            location TEXT NOT NULL DEFAULT '',
            provided_website TEXT NOT NULL DEFAULT '',
            normalized_name TEXT NOT NULL,
            normalized_location TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (normalized_name, normalized_location)
        );
        CREATE TABLE IF NOT EXISTS run_companies (
            run_id TEXT NOT NULL REFERENCES import_runs(run_id),
            company_id INTEGER NOT NULL REFERENCES companies(company_id),
            status TEXT NOT NULL,
            attempt_count INTEGER NOT NULL DEFAULT 0,
            last_error TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            PRIMARY KEY (run_id, company_id)
        );
        CREATE TABLE IF NOT EXISTS import_errors (
            error_id INTEGER PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES import_runs(run_id),
            row_number INTEGER NOT NULL,
            message TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_run_companies_status ON run_companies (run_id, status);
        """
    )
