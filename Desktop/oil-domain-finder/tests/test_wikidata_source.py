"""Offline regression tests for the structured no-key Wikidata source."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from sources.categories import CATEGORIES
from sources.wikidata_source import SOURCE_NAME, WikidataSource


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

    def test_every_category_query_is_bounded_and_uses_its_industry_hierarchy(self) -> None:
        source = WikidataSource()

        for category in CATEGORIES:
            with self.subTest(category=category.key):
                query = source._query(category)
                self.assertIn(f"wd:{category.wikidata_qid}", query)
                self.assertIn("wdt:P856", query)
                self.assertIn("LIMIT 1000", query)

    def test_unknown_category_is_rejected_before_a_network_request(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown company category"):
            WikidataSource().search("not-a-category")

    def test_http_and_https_variants_are_returned_once_as_one_domain(self) -> None:
        payload = {
            "results": {
                "bindings": [
                    {
                        "company": {"value": "https://www.wikidata.org/entity/Q1"},
                        "companyLabel": {"value": "Example One"},
                        "website": {"value": "http://example.test/about"},
                    },
                    {
                        "company": {"value": "https://www.wikidata.org/entity/Q2"},
                        "companyLabel": {"value": "Example Two"},
                        "website": {"value": "https://example.test/contact"},
                    },
                ]
            }
        }

        results = WikidataSource()._parse_results(payload)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].website, "https://example.test")


if __name__ == "__main__":
    unittest.main()
