"""Source-neutral company search orchestration."""

from __future__ import annotations

import importlib
import pkgutil
from sources import __path__ as SOURCES_PATH
from sources.base import BaseSource, ProgressCallback, SearchResult


class SearchEngineError(RuntimeError):
    """Raised when no live source can return verified company websites."""


class SearchEngine:
    """Run available sources, merge their results, and remove duplicates."""

    def search(
        self, category_key: str, progress_callback: ProgressCallback | None = None
    ) -> list[SearchResult]:
        """Search all available live sources and report an honest failure if none work."""
        self._report(progress_callback, "Searching...", 10)
        sources = [source for source in self._enabled_sources() if source.is_live]
        if not sources:
            raise SearchEngineError("No live, no-key search source is available.")

        results: list[SearchResult] = []
        failures: list[str] = []
        for index, source in enumerate(sources, start=1):
            try:
                results.extend(source.search(category_key, progress_callback))
            except Exception as error:
                failures.append(str(error) or source.__class__.__name__)
                continue
            results = self._merge_duplicates(results)
            self._report(progress_callback, f"Found {len(results)} companies", 10 + 70 * index // max(1, len(sources)))

        merged = self._merge_duplicates(results)
        if not merged:
            detail = failures[0] if failures else "No relevant company websites were found."
            raise SearchEngineError(detail)
        self._report(progress_callback, f"Found {len(merged)} companies", 90)
        self._report(progress_callback, "Search Complete", 100)
        return merged

    @staticmethod
    def _enabled_sources() -> list[BaseSource]:
        """Load source modules automatically, so the GUI never selects a source."""
        for module in pkgutil.iter_modules(SOURCES_PATH):
            if not module.name.startswith("_") and module.name not in {"base", "engine"}:
                importlib.import_module(f"sources.{module.name}")
        instances = [source() for source in BaseSource.__subclasses__()]
        return [source for source in instances if source.is_enabled]

    @staticmethod
    def _merge_duplicates(results: list[SearchResult]) -> list[SearchResult]:
        """Keep one clean row per official website domain."""
        merged: dict[str, SearchResult] = {}
        for result in results:
            key = result.website.casefold()
            existing = merged.get(key)
            if existing is None:
                merged[key] = result
                continue
            merged[key] = SearchResult(
                company_name=existing.company_name,
                website=existing.website or result.website,
                location=existing.location,
                source=existing.source or result.source,
                registry_url=existing.registry_url or result.registry_url,
            )
        return list(merged.values())

    @staticmethod
    def _report(callback: ProgressCallback | None, message: str, progress: int) -> None:
        if callback:
            callback(message, progress)
