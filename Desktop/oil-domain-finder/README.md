# Oil Domain Finder

A desktop MVP for collecting publicly available oil and gas company websites,
without API keys.

Current implementation details, constraints, and the required documentation
workflow are maintained in [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md).

## Requirements

- Python 3.11
- macOS Monterey or Windows

## Run locally

```bash
python3.11 -m venv .venv
```

Activate the virtual environment:

```bash
# macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install dependencies and launch:

```bash
pip install -r requirements.txt
python main.py
```

Run the offline regression tests:

```bash
python -m unittest discover -s tests
```

## Import a company list locally

The importer needs no API key and performs no network requests. Its CSV schema
is documented in [docs/COMPANY_INPUT_SCHEMA.md](docs/COMPANY_INPUT_SCHEMA.md).

```bash
python scripts/import_companies.py import path/to/companies.csv --export exports/companies.csv
```

The command stores durable run/checkpoint records in `data/company_runs.sqlite3`.
Use the printed `run_id` to export or inspect a previous run:

```bash
python scripts/import_companies.py status RUN_ID
python scripts/import_companies.py export RUN_ID exports/companies.csv
```

## Validate project documentation

```bash
python scripts/check_project_state.py
```
