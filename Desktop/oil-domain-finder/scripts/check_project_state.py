"""Validate the repository's project-state documentation contract."""

from __future__ import annotations

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROJECT_STATE = REPOSITORY_ROOT / "docs" / "PROJECT_STATE.md"
README = REPOSITORY_ROOT / "README.md"
README_REFERENCE = "docs/PROJECT_STATE.md"


def main() -> int:
    """Return non-zero when the project-state document is missing or unlinked."""
    problems: list[str] = []
    if not PROJECT_STATE.is_file():
        problems.append("missing docs/PROJECT_STATE.md")
    if not README.is_file():
        problems.append("missing README.md")
    elif README_REFERENCE not in README.read_text(encoding="utf-8"):
        problems.append("README.md does not reference docs/PROJECT_STATE.md")

    if problems:
        print("Project-state documentation check failed: " + "; ".join(problems), file=sys.stderr)
        return 1

    print("Project-state documentation check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
