"""Offline regression tests for the structured no-key Wikidata source."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from sources.wikidata_source import PETROLEUM_INDUSTRY_QID, SOURCE_NAME, WikidataSource


FIXTURE = Path(__file__).parent / "fixtures" / "wikidata_oil_companies.json"


class WikidataSourceTests(unittest.TestCase):
    def test_fixture_returns_deduplicated_official_website_records(self) -> None:
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

        results = WikidataSource()._parse_results(payload)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].company_name, "Acme Oil")
        self.assertEqual(results[0].website, "https://www.acme-oil.example")
        self.assertEqual(results[0].location, "Exampleland")
        self.assertEqual(results[0].source, SOURCE_NAME)

    def test_query_is_bounded_to_the_petroleum_industry_hierarchy(self) -> None:
        query = WikidataSource()._query()

        self.assertIn(f"wd:{PETROLEUM_INDUSTRY_QID}", query)
        self.assertIn("wdt:P856", query)
        self.assertIn("LIMIT 250", query)


if __name__ == "__main__":
    unittest.main()
