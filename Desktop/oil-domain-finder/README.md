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

## Validate project documentation

```bash
python scripts/check_project_state.py
```
