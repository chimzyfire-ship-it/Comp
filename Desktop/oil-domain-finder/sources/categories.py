"""The business categories supported by the worldwide company search."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompanyCategory:
    """A user-facing category and its Wikidata industry item."""

    key: str
    label: str
    wikidata_qid: str


CATEGORIES: tuple[CompanyCategory, ...] = (
    CompanyCategory("oil_and_gas", "Oil & Gas", "Q862571"),
    CompanyCategory("renewable_energy", "Renewable Energy", "Q12705"),
    CompanyCategory("technology", "Technology", "Q11661"),
    CompanyCategory("financial_services", "Financial Services", "Q837171"),
    CompanyCategory("healthcare", "Healthcare", "Q31207"),
    CompanyCategory("manufacturing", "Manufacturing", "Q13235160"),
)


def get_category(key: str) -> CompanyCategory:
    """Return a configured category or raise a clear programming error."""
    for category in CATEGORIES:
        if category.key == key:
            return category
    raise ValueError(f"Unknown company category: {key}")
