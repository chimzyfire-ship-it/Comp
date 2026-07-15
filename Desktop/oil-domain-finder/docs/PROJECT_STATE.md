# Project State: Company Domain Finder

Last verified: 2026-07-14

## Product goal and intended users

Company Domain Finder is an early desktop MVP for finding publicly available
official website domains for companies in six categories: Oil & Gas, Renewable
Energy, Technology, Financial Services, Healthcare, and Manufacturing. Its intended users are researchers,
business-development teams, and other operators who need a starting list of
company websites and domains without relying on paid enrichment APIs.

**Product constraint:** the target tool must be usable without API keys. Any
source requiring an API token is incompatible with the intended production
workflow.

The current product is a small interactive search, not yet a bulk-processing
system. The stated longer-term need to discover websites for as many as 500,000
companies is not implemented.

## Architecture and technology stack

- Python 3.11 application launched by `main.py`.
- PySide6/Qt desktop GUI (`app/gui/main_window.py` and
  `app/gui/styles.py`); PySide6 is the sole declared third-party dependency in
  `requirements.txt`.
- Source-provider pattern: `sources.base.BaseSource` defines the contract,
  `sources.engine.SearchEngine` discovers enabled source modules, runs live
  sources, and merges results.
- Network clients use the Python standard library (`urllib`, `html.parser`),
  rather than an HTTP library.
- The search worker runs in a Qt `QThread`, keeping the GUI event loop
  responsive while a search runs.
- The primary live source is Wikidata Query Service, using its structured
  `official website` property (`P856`) and the selected industry hierarchy,
  with a descriptive User-Agent and one bounded worldwide query per search.

## Implemented functionality

- Desktop window with a six-category selector, Search button, progress
  indicator, status text, and result table: `app/gui/main_window.py`.
- Central Qt stylesheet: `app/gui/styles.py`.
- Source-neutral result model and provider interface:
  `sources/base.py`.
- Source discovery, selection, failure isolation, and result merging:
  `sources/engine.py`. Duplicate companies are currently keyed by normalized
  company name plus location; provider-level web results are keyed by name plus
  website.
- Structured no-key discovery source: `sources/wikidata_source.py`. It issues
  one bounded Wikidata SPARQL query (up to 1,000 records) for the selected industry hierarchy and
  entities with an official website, normalizes the website origin, removes
  duplicate domains, and retains Wikidata entity provenance. A live check on
  2026-07-14 returned non-empty clean results for every category (Oil & Gas
  233, Renewable Energy 166, Technology 223, Financial Services 236,
  Healthcare 212, Manufacturing 222).
- The token-gated OpenCorporates integration, sample-data source, and fragile
  Bing/DuckDuckGo HTML scraper were removed to uphold the no-API-key constraint
  and prevent misleading or unstructured results from being presented as
  successful discovery.
- Every result now carries its source name and displays it in the GUI Source
  column: `sources/base.py`, `sources/engine.py`, and
  `sources/search_engine_source.py`.
- Offline structured-source regression tests and JSON fixture:
  `tests/test_wikidata_source.py` and
  `tests/fixtures/wikidata_oil_companies.json`.
- Local no-key bulk-input foundation: `services/company_import.py` and
  `scripts/import_companies.py`. It imports a documented CSV schema into
  SQLite, normalizes and deduplicates company/location keys, records invalid
  input rows, creates per-run checkpoints, commits bounded batches, and exports
  a prior run without any network request.
- CSV schema documentation and import regression tests:
  `docs/COMPANY_INPUT_SCHEMA.md` and `tests/test_company_import.py`.
- Windows packaging support: `scripts/build_windows.bat`,
  `installer/CompanyDomainFinder.iss`, and `.github/workflows/build-windows.yml`.
  The GitHub workflow produces one `CompanyDomainFinder-Setup.exe` installer;
  Windows users need neither Python nor a terminal.
- Startup entry point: `main.py`.

Placeholder package directories exist for future database, exporter, scraper,
source, and utility work under `app/`; no implementations were found there.

## Data flow, inputs, outputs, and storage

| Stage | Current behavior |
| --- | --- |
| Inputs | A selected category (Oil & Gas, Renewable Energy, Technology, Financial Services, Healthcare, or Manufacturing), or a UTF-8 CSV with required `company_name` and optional `location`/`website` columns. The exact CSV contract is in `docs/COMPANY_INPUT_SCHEMA.md`. |
| Discovery/enrichment | Queries Wikidata entities classified within the selected industry hierarchy and reads their `official website` property. It normalizes website origins, removes duplicate domains, and preserves the Wikidata entity URL as provenance. |
| Output | Shows company name, website, location, and `Wikidata (official website)` in the in-memory Qt table, with one row per domain. The importer exports a run's canonical company records and checkpoint states as CSV. When the source is unavailable, the GUI reports that failure instead of displaying sample data. |
| Storage | The importer creates a local SQLite database (default `data/company_runs.sqlite3`) with import runs, canonical companies, per-run checkpoints, and invalid-row diagnostics. The database and CSV exports remain ignored generated output. |

## Run locally

Requirements: Python 3.11 and macOS Monterey or Windows. The project README
documents these same steps.

```bash
python3.11 -m venv .venv
source .venv/bin/activate       # macOS
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

The current Wikidata source needs no API key. Choose a category and click
**Search** to run the bounded structured worldwide query. If the source is
unavailable, the application reports that outcome rather than substituting demo
data.

Validate the documentation contract with:

```bash
python scripts/check_project_state.py
```

Run offline regression tests with:

```bash
python -m unittest discover -s tests
```

Import a no-key company CSV and export its stored run:

```bash
python scripts/import_companies.py import path/to/companies.csv --export exports/companies.csv
```

The command prints a `run_id`. Use it to inspect or re-export a checkpointed
run:

```bash
python scripts/import_companies.py status RUN_ID
python scripts/import_companies.py export RUN_ID exports/companies.csv
```

For a non-technical Windows user, trigger the **Build Windows app** GitHub
Actions workflow and download its single `CompanyDomainFinder-Setup.exe`
artifact. They double-click it and open the installed app from the Start menu.
Python, an API key, and command-line setup are not required on that Windows
computer.

## Current limitations and free-source constraints

- Wikidata is community-maintained, so it has incomplete coverage and can
  contain stale or incorrect official-website statements. The source reports
  Wikidata provenance but does not independently validate ownership, redirects,
  DNS, or TLS.
- Wikidata Query Service is public and intentionally constrained. Its current
  documented endpoint has a 60-second query timeout and per-client processing
  limits; it is appropriate for the app's one bounded interactive query, not
  for a 500,000-row bulk resolver. Respect its changing service limits and
  User-Agent policy.
- The product does not validate DNS, redirects, TLS, ownership, or company-to-
  domain matches. It can emit false positives and blank websites.
- The GUI search remains a small, one-worker interactive flow; it does not yet
  use the local importer, accept a company file, or persist live-search
  findings. The importer itself stores only supplied websites and pending
  discovery checkpoints; it does not prove ownership or discover new domains.
- There is focused regression coverage for CSV importing, category-query
  construction, structured result parsing, and duplicate-domain cleanup. There
  is no lint/type-check configuration, lockfile, container configuration, or
  application logging implementation.

## Responsible 500,000-company strategy without paid APIs

This is a proposed next architecture, not current functionality. Start from a
lawfully obtained company input file or open/public registry bulk datasets,
and comply with each source's license, robots rules, published API limits, and
terms. Do not scale direct scraping of general search result pages beyond what
those services explicitly permit.

1. Import and normalize the input in deterministic batches (for example,
   1,000--10,000 records), assigning every row a stable input ID and a run ID.
2. Canonicalize names, jurisdictions, known URLs, and candidate registries;
   deduplicate before any lookup using normalized name/location keys plus a
   separately normalized registrable-domain key.
3. Persist a local SQLite or DuckDB job store with input rows, candidates,
   source provenance, attempts, timestamps, status, and a content/version hash.
   Cache both successful and negative/unsupported-source outcomes with an
   expiry, so reruns do not repeat requests.
4. Prefer permitted bulk downloads and public registries that do not require
   authentication or an API key for candidate discovery. Use only documented,
   permitted lookup endpoints where available; send a clear User-Agent/contact
   and retain attribution/provenance.
5. Use bounded worker pools per source, token-bucket rate limits, per-domain
   concurrency caps, request timeouts, exponential backoff with jitter, and a
   finite retry budget. Treat 429/403/CAPTCHA responses as a stop/slow-down
   signal rather than a reason to evade controls.
6. Checkpoint each completed batch transactionally. On restart, resume only
   pending or retry-eligible rows; make processing idempotent through stable
   record and request keys.
7. Validate and score candidates separately (URL normalization, redirects and
   DNS only where allowed, corroborating registry/website signals), preserve
   evidence and confidence, and route uncertain matches to review rather than
   asserting an official domain.
8. Export partitioned CSV/Parquet files plus an audit manifest; track source
   coverage, error/429 rates, duplicate rates, and low-confidence outcomes.
   Pilot on a small sample and calculate permitted throughput before planning a
   500,000-row run.

## Known bugs, risks, and next priorities

1. Each category query covers only entities that contributors have classified
   in the selected Wikidata industry hierarchy and supplied with an official
   website. It is a high-confidence worldwide seed source, not a complete
   global company directory.
2. The live query returns at most 1,000 raw Wikidata records per category click;
   protocol variants and exact duplicate domains are normalized into one row. It does not yet support
   user filters, cached snapshots, pagination, or freshness timestamps.
3. There is no test coverage yet for engine error aggregation, network retries,
   GUI thread behavior, or the Windows packaging workflow.
4. The local importer does not yet have a permitted no-key resolver that can
   process its `pending_discovery` checkpoints. It is intentionally offline;
   integrating a bulk resolver requires separately verifying its data license,
   rate limits, and permissible use.
5. Users cannot yet choose sources or query parameters beyond the six supported
   categories, import a company file
   through the GUI, or view prior SQLite runs in the desktop application.

Recommended next implementation priority: add a simple GUI export button and
cache the latest successful Wikidata result set locally, so a non-technical
user can save results without using the command line. In parallel, evaluate a
separately licensed bulk company dataset for the importer; defer
500,000-company execution until its measured rate limits and data terms support
it.

## Changelog

### 2026-07-12

- Audited the existing MVP and created this project-state document as the
  repository's single source of truth.
- Added a repository rule requiring this document to be updated alongside
  meaningful code, configuration, architecture, or behavior changes.
- Added a lightweight check that confirms this document exists and is linked
  from the README.
- Recorded the no-API-key product constraint and marked the legacy
  OpenCorporates integration as incompatible with the intended release.
- Configured the project for publication to
  `https://github.com/chimzyfire-ship-it/Comp`.
- Removed the API-key and demo-data paths; results now show their source and
  report failed/no-credible searches instead of masquerading as success.
- Added offline regression coverage for Bing parsing, relevance filtering, and
  DuckDuckGo fallback. A live smoke test confirmed that unrelated educational
  results are now rejected.
- Added the local CSV-to-SQLite import/export foundation, including normalized
  deduplication, per-run checkpoints, bounded commits, invalid-row diagnostics,
  documented input schema, and regression coverage. It makes no network
  requests and requires no API key.
- Replaced fragile general-search scraping with a bounded structured Wikidata
  official-website query. Added offline fixtures/tests, live end-to-end
  verification, and a Windows executable build workflow for non-technical
  users.

### 2026-07-14

- Renamed the application to Company Domain Finder and added a category selector
  for Oil & Gas, Renewable Energy, Technology, Financial Services, Healthcare,
  and Manufacturing.
- Made the structured Wikidata query category-aware and changed live result
  cleanup to retain one row per normalized official website domain.
- Added automated coverage for all six category query configurations and clean
  domain deduplication.
- Added an Inno Setup definition and Windows workflow step that produce one
  double-click installer (`CompanyDomainFinder-Setup.exe`) instead of requiring
  an unpacked application folder.

### 2026-07-15

- Raised the single-search Wikidata limit from 250 to 1,000 records after live
  verification showed the Oil & Gas category returning 946 clean domains at
  the higher limit. Domain normalization now also merges HTTP and HTTPS
  variants of the same host into one HTTPS result row.
