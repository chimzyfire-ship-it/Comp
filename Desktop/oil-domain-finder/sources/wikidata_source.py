"""No-key, structured oil-and-gas company websites from Wikidata."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from sources.base import BaseSource, ProgressCallback, SearchResult


WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
PETROLEUM_INDUSTRY_QID = "Q862571"
SOURCE_NAME = "Wikidata (official website)"
USER_AGENT = "OilDomainFinder/0.1 (https://github.com/chimzyfire-ship-it/Comp)"


class WikidataUnavailableError(RuntimeError):
    """Raised when Wikidata cannot provide a usable company list."""


class WikidataSource(BaseSource):
    """Retrieve oil-and-gas entities with Wikidata's official-website property."""

    is_live = True
    timeout = 30.0
    max_results = 250

    def search(self, progress_callback: ProgressCallback | None = None) -> list[SearchResult]:
        """Return structured company websites from one bounded public query."""
        self._report(progress_callback, "Getting verified company websites...", 20)
        payload = self._download(self._query())
        self._report(progress_callback, "Validating company records...", 70)
        results = self._parse_results(payload)
        if not results:
            raise WikidataUnavailableError("Wikidata returned no oil-and-gas company websites.")
        self._report(progress_callback, f"Found {len(results)} company websites", 90)
        return results

    def _query(self) -> str:
        """Build a bounded query for entities in the petroleum-industry hierarchy."""
        return f"""
            SELECT DISTINCT ?company ?companyLabel ?website ?countryLabel WHERE {{
              ?company wdt:P452 ?industry;
                       wdt:P856 ?website.
              ?industry wdt:P279* wd:{PETROLEUM_INDUSTRY_QID}.
              OPTIONAL {{ ?company wdt:P17 ?country. }}
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language \"en\". }}
            }}
            LIMIT {self.max_results}
        """

    def _download(self, query: str) -> dict[str, Any]:
        request = Request(
            f"{WIKIDATA_SPARQL_URL}?{urlencode({'query': query, 'format': 'json'})}",
            headers={
                "Accept": "application/sparql-results+json",
                "User-Agent": USER_AGENT,
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
            raise WikidataUnavailableError("Wikidata is temporarily unavailable. Please try again later.") from error
        if not isinstance(payload, dict):
            raise WikidataUnavailableError("Wikidata returned an unreadable response.")
        return payload

    @staticmethod
    def _parse_results(payload: dict[str, Any]) -> list[SearchResult]:
        bindings = payload.get("results", {}).get("bindings", [])
        if not isinstance(bindings, list):
            raise WikidataUnavailableError("Wikidata returned an unreadable response.")

        unique: dict[tuple[str, str], SearchResult] = {}
        for binding in bindings:
            if not isinstance(binding, dict):
                continue
            company_name = _binding_value(binding, "companyLabel")
            website = _website_origin(_binding_value(binding, "website"))
            location = _binding_value(binding, "countryLabel")
            item_url = _binding_value(binding, "company")
            if not company_name or not website:
                continue
            result = SearchResult(company_name, website, location, SOURCE_NAME, item_url)
            unique.setdefault((company_name.casefold(), website.casefold()), result)
        return list(unique.values())

    @staticmethod
    def _report(callback: ProgressCallback | None, message: str, progress: int) -> None:
        if callback:
            callback(message, progress)


def _binding_value(binding: dict[str, Any], key: str) -> str:
    value = binding.get(key, {})
    return str(value.get("value") or "").strip() if isinstance(value, dict) else ""


def _website_origin(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc.casefold()}"
