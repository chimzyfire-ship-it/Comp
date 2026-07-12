"""Offline regression tests for public-search result filtering."""

from __future__ import annotations

from pathlib import Path
import unittest

from sources.search_engine_source import _BingResultParser, SearchEngineSource


FIXTURE = Path(__file__).parent / "fixtures" / "bing_results.html"


class SearchEngineSourceTests(unittest.TestCase):
    def test_bing_fixture_keeps_only_relevant_company_result(self) -> None:
        parser = _BingResultParser()
        parser.feed(FIXTURE.read_text(encoding="utf-8"))

        results = SearchEngineSource()._company_results(parser.results, "Bing")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].company_name, "Acme Energy")
        self.assertEqual(results[0].website, "https://www.acme-energy.example")
        self.assertEqual(results[0].source, "Bing")

    def test_duckduckgo_is_used_when_bing_results_are_not_relevant(self) -> None:
        source = SearchEngineSource()
        source._bing_results = lambda query: [("Anime characters with purple hair", "https://anime.example")]
        source._duckduckgo_results = lambda query: [("Harbor Oil and Gas - Home", "https://harbor.example")]

        results = source._search_query('"oil and gas company"')

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].company_name, "Harbor Oil and Gas")
        self.assertEqual(results[0].source, "DuckDuckGo")

    def test_educational_drilling_page_is_not_a_company_result(self) -> None:
        results = SearchEngineSource()._company_results(
            [("What Is Drilling? Types, Skills, and Industry Applications", "https://example.org")],
            "Bing",
        )

        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
