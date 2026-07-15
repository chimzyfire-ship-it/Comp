"""No-key, structured company-domain discovery from Wikidata."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from sources.base import BaseSource, ProgressCallback, SearchResult
from sources.categories import CompanyCategory, get_category


WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"
SOURCE_NAME = "Wikidata (official website)"
USER_AGENT = "CompanyDomainFinder/1.0 (https://github.com/chimzyfire-ship-it/Comp)"


class WikidataUnavailableError(RuntimeError):
    """Raised when Wikidata cannot provide a usable company list."""


class WikidataSource(BaseSource):
    """Retrieve category companies with Wikidata's official-website property."""

    is_live = True
    # A thousand records materially improves category coverage while keeping a
    # single interactive query within the public service's practical limits.
    timeout = 60.0
    max_results = 1_000

    def search(
        self, category_key: str, progress_callback: ProgressCallback | None = None
    ) -> list[SearchResult]:
        """Return structured company websites from one bounded public query."""
        category = get_category(category_key)
        self._report(progress_callback, f"Finding {category.label} company websites worldwide...", 20)
        payload = self._download(self._query(category))
        self._report(progress_callback, "Validating company records...", 70)
        results = self._parse_results(payload)
        if not results:
            raise WikidataUnavailableError(f"Wikidata returned no {category.label} company websites.")
        self._report(progress_callback, f"Found {len(results)} clean company domains", 90)
        return results

    def _query(self, category: CompanyCategory) -> str:
        """Build a bounded worldwide query for one industry hierarchy."""
        return f"""
            SELECT DISTINCT ?company ?companyLabel ?website ?countryLabel WHERE {{
              ?company wdt:P452 ?industry;
                       wdt:P856 ?website.
              ?industry wdt:P279* wd:{category.wikidata_qid}.
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

        unique: dict[str, SearchResult] = {}
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
            unique.setdefault(website.casefold(), result)
        return sorted(unique.values(), key=lambda result: (result.company_name.casefold(), result.website))

    @staticmethod
    def _report(callback: ProgressCallback | None, message: str, progress: int) -> None:
        if callback:
            callback(message, progress)


def _binding_value(binding: dict[str, Any], key: str) -> str:
    value = binding.get(key, {})
    return str(value.get("value") or "").strip() if isinstance(value, dict) else ""


def _website_origin(value: str) -> str:
    parsed = urlparse(value)
    hostname = (parsed.hostname or "").casefold().rstrip(".")
    if parsed.scheme not in {"http", "https"} or not hostname:
        return ""
    # A domain is the useful output here, not a protocol variant. Normalizing
    # both HTTP and HTTPS to one HTTPS domain prevents repeated result rows.
    try:
        port = parsed.port
    except ValueError:
        return ""
    port_suffix = f":{port}" if port and port not in {80, 443} else ""
    return f"https://{hostname}{port_suffix}"
