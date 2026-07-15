"""Shared contracts for company search sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable


ProgressCallback = Callable[[str, int], None]


@dataclass(frozen=True)
class SearchResult:
    """A company found by a search source."""

    company_name: str
    website: str
    location: str
    source: str
    registry_url: str = ""

    def table_values(self) -> tuple[str, str, str, str]:
        """Return values in the order used by the existing results table."""
        return (self.company_name, self.website, self.location, self.source)


class BaseSource(ABC):
    """Interface implemented by every company search source."""

    is_live = False

    @property
    def is_enabled(self) -> bool:
        """Whether this source can run in the current environment."""
        return True

    @abstractmethod
    def search(
        self, category_key: str, progress_callback: ProgressCallback | None = None
    ) -> list[SearchResult]:
        """Return company results from this source."""
