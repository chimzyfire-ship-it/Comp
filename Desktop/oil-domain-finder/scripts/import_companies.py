"""Command-line interface for durable, no-key company CSV imports."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from services.company_import import InputValidationError, export_run, get_run_summary, import_companies


DEFAULT_DATABASE = REPOSITORY_ROOT / "data" / "company_runs.sqlite3"


def main() -> int:
    """Run the selected import, export, or status command."""
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    import_parser = subcommands.add_parser("import", help="Import a company CSV into SQLite")
    import_parser.add_argument("input", type=Path, help="CSV with a company_name column")
    import_parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    import_parser.add_argument("--batch-size", type=int, default=1_000)
    import_parser.add_argument("--export", type=Path, help="Optional CSV export path for this run")

    export_parser = subcommands.add_parser("export", help="Export a prior import run")
    export_parser.add_argument("run_id")
    export_parser.add_argument("output", type=Path)
    export_parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)

    status_parser = subcommands.add_parser("status", help="Show a prior import summary")
    status_parser.add_argument("run_id")
    status_parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)

    arguments = parser.parse_args()
    try:
        if arguments.command == "import":
            summary = import_companies(arguments.input, arguments.database, arguments.batch_size)
            print(_format_summary(summary))
            if arguments.export:
                count = export_run(arguments.database, summary.run_id, arguments.export)
                print(f"Exported {count} records to {arguments.export}")
        elif arguments.command == "export":
            count = export_run(arguments.database, arguments.run_id, arguments.output)
            print(f"Exported {count} records to {arguments.output}")
        else:
            print(_format_summary(get_run_summary(arguments.database, arguments.run_id)))
    except InputValidationError as error:
        parser.error(str(error))
    return 0


def _format_summary(summary: object) -> str:
    return "\n".join(f"{key}: {value}" for key, value in vars(summary).items())


if __name__ == "__main__":
    raise SystemExit(main())
