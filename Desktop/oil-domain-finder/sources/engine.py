"""Source-neutral company search orchestration."""

from __future__ import annotations

import importlib
import pkgutil
from sources import __path__ as SOURCES_PATH
from sources.base import BaseSource, ProgressCallback, SearchResult


class SearchEngine:
    """Run available sources, merge their results, and remove duplicates."""

    def search(self, progress_callback: ProgressCallback | None = None) -> list[SearchResult]:
        """Search all available live sources, or use the built-in sample fallback."""
        self._report(progress_callback, "Searching...", 10)
        sources = self._enabled_sources()
        live_sources = [source for source in sources if source.is_live]
        selected_sources = live_sources or [source for source in sources if not source.is_live]

        results: list[SearchResult] = []
        for index, source in enumerate(selected_sources, start=1):
            try:
                results.extend(source.search(progress_callback))
            except Exception:
                # A temporarily unavailable source should not stop a simple search.
                continue
            results = self._merge_duplicates(results)
            self._report(progress_callback, f"Found {len(results)} companies", 10 + 70 * index // max(1, len(selected_sources)))

        # Keep the app useful if live sources are temporarily unavailable.
        if not results and live_sources:
            results = self._run_demo_fallback(sources)

        merged = self._merge_duplicates(results)
        self._report(progress_callback, f"Found {len(merged)} companies", 90)
        self._report(progress_callback, "Search Complete", 100)
        return merged

    @staticmethod
    def _enabled_sources() -> list[BaseSource]:
        """Load source modules automatically, so the GUI never selects a source."""
        for module in pkgutil.iter_modules(SOURCES_PATH):
            if not module.name.startswith("_") and module.name not in {"base", "engine"}:
                importlib.import_module(f"sources.{module.name}")
        return [source() for source in BaseSource.__subclasses__() if source().is_enabled]

    @staticmethod
    def _run_demo_fallback(sources: list[BaseSource]) -> list[SearchResult]:
        """Use a non-live source when no live result could be retrieved."""
        for source in sources:
            if not source.is_live:
                return source.search()
        return []

    @staticmethod
    def _merge_duplicates(results: list[SearchResult]) -> list[SearchResult]:
        """Merge duplicate company names and locations, retaining useful fields."""
        merged: dict[tuple[str, str], SearchResult] = {}
        for result in results:
            key = (result.company_name.casefold(), result.location.casefold())
            existing = merged.get(key)
            if existing is None:
                merged[key] = result
                continue
            merged[key] = SearchResult(
                company_name=existing.company_name,
                website=existing.website or result.website,
                location=existing.location,
                registry_url=existing.registry_url or result.registry_url,
            )
        return list(merged.values())

    @staticmethod
    def _report(callback: ProgressCallback | None, message: str, progress: int) -> None:
        if callback:
            callback(message, progress)
