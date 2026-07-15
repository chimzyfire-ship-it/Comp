"""Regression coverage for clean, category-specific result handling."""

from __future__ import annotations

import unittest

from sources.base import SearchResult
from sources.engine import SearchEngine


class SearchEngineTests(unittest.TestCase):
    def test_merge_duplicates_keeps_one_row_per_domain(self) -> None:
        results = [
            SearchResult("Parent Corp", "https://example.com", "US", "Wikidata"),
            SearchResult("Parent Corp Europe", "https://example.com", "UK", "Wikidata"),
            SearchResult("Other Corp", "https://other.example", "CA", "Wikidata"),
        ]

        merged = SearchEngine._merge_duplicates(results)

        self.assertEqual([result.website for result in merged], ["https://example.com", "https://other.example"])
