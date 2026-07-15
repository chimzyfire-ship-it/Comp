# Company Domain Finder

A desktop app for collecting clean, structured company domains worldwide,
without API keys. Choose one of six categories: Oil & Gas, Renewable Energy,
Technology, Financial Services, Healthcare, or Manufacturing.

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

Choose a category and click **Search**. The app makes one bounded worldwide
request to Wikidata's public query service and shows one row per normalized
official website domain, labelled `Wikidata (official website)`. It does not
show demo data when the source is unavailable.

## Windows: one-click installation

The GitHub Actions **Build Windows app** workflow creates a single
`CompanyDomainFinder-Setup.exe` download. Send that file to the Windows user.
They double-click it, follow the standard Windows install prompt, and open
**Company Domain Finder** from the Start menu. They do not need Python, a
terminal, an API key, or any setup steps beyond the installer prompt.

For a local Windows build, double-click `scripts\build_windows.bat`, then
compile `installer\CompanyDomainFinder.iss` with Inno Setup.

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
