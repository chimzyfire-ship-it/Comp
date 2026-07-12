"""OpenCorporates company-search client.

The client deliberately uses only Python's standard library so it is portable on
the supported macOS and Windows installations.  Website values are returned only
when the OpenCorporates response explicitly supplies a website field.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = "https://api.opencorporates.com/v0.4/companies/search"
DEFAULT_KEYWORDS = ("oil", "petroleum", "energy", "gas", "drilling")


class OpenCorporatesError(RuntimeError):
    """Raised when OpenCorporates cannot provide a usable search response."""


class OpenCorporatesConnectionError(OpenCorporatesError):
    """Raised when the OpenCorporates API cannot be reached."""


@dataclass(frozen=True)
class CompanyRecord:
    """Raw company information normalized by this service."""

    name: str
    jurisdiction: str
    registry_url: str
    website: str = ""


ProgressCallback = Callable[[str, int], None]


class OpenCorporatesService:
    """Search the public OpenCorporates API for oil and gas companies."""

    def __init__(self, timeout: float = 15.0, api_token: str | None = None) -> None:
        self.timeout = timeout
        # An environment variable keeps the account token out of source control.
        self.api_token = api_token if api_token is not None else os.environ.get("OPENCORPORATES_API_TOKEN", "")

    def search(
        self,
        keywords: tuple[str, ...] = DEFAULT_KEYWORDS,
        results_per_keyword: int = 20,
        progress_callback: ProgressCallback | None = None,
    ) -> list[CompanyRecord]:
        """Return unique companies matching *keywords*.

        ``results_per_keyword`` is capped at the API's usual 100-record page
        limit.  Calls the callback with a human-readable stage and percentage.
        """
        if not keywords:
            return []
        if not self.api_token:
            raise OpenCorporatesError(
                "An OpenCorporates API token is required. Set OPENCORPORATES_API_TOKEN and try again."
            )

        limit = max(1, min(results_per_keyword, 100))
        results: list[CompanyRecord] = []
        seen: set[tuple[str, str]] = set()
        self._report(progress_callback, "Connecting...", 5)

        for index, keyword in enumerate(keywords):
            self._report(progress_callback, "Searching...", 10 + index * 70 // len(keywords))
            response = self._request(keyword, limit)
            self._report(progress_callback, "Processing...", 20 + index * 70 // len(keywords))
            for company in self._companies_from_response(response):
                key = (company.name.casefold(), company.jurisdiction.casefold())
                if key not in seen:
                    seen.add(key)
                    results.append(company)

        self._report(progress_callback, "Finished", 100)
        return results

    def _request(self, keyword: str, limit: int) -> dict[str, Any]:
        url = f"{API_URL}?{urlencode({'q': keyword, 'per_page': limit, 'api_token': self.api_token})}"
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "OilDomainFinder/1.0"})
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code == 401:
                raise OpenCorporatesError(
                    "OpenCorporates rejected the API token. Check OPENCORPORATES_API_TOKEN and try again."
                ) from error
            raise OpenCorporatesError(
                f"OpenCorporates could not complete the search (HTTP {error.code})."
            ) from error
        except URLError as error:
            raise OpenCorporatesConnectionError(
                "Unable to connect to OpenCorporates. Check your internet connection and try again."
            ) from error
        except (TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as error:
            raise OpenCorporatesError("OpenCorporates returned an unreadable response. Please try again.") from error
        except OSError as error:
            raise OpenCorporatesConnectionError(
                "Unable to connect to OpenCorporates. Check your internet connection and try again."
            ) from error
        if not isinstance(payload, dict):
            raise OpenCorporatesError("OpenCorporates returned an unreadable response. Please try again.")
        return payload

    @staticmethod
    def _companies_from_response(response: dict[str, Any]) -> list[CompanyRecord]:
        result_data = response.get("results", {})
        companies = result_data.get("companies", []) if isinstance(result_data, dict) else []
        parsed: list[CompanyRecord] = []
        for entry in companies:
            company = entry.get("company", entry) if isinstance(entry, dict) else {}
            if not isinstance(company, dict):
                continue
            name = str(company.get("name") or "").strip()
            if not name:
                continue
            jurisdiction = str(company.get("jurisdiction_code") or company.get("jurisdiction") or "").strip()
            registry_url = str(company.get("opencorporates_url") or company.get("registry_url") or "").strip()
            # Do not treat company_url as a website: it commonly identifies a registry page.
            website = str(company.get("website") or "").strip()
            parsed.append(CompanyRecord(name, jurisdiction, registry_url, website))
        return parsed

    @staticmethod
    def _report(callback: ProgressCallback | None, message: str, progress: int) -> None:
        if callback:
            callback(message, progress)
