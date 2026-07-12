"""Public-web search source for oil and gas company websites."""

from __future__ import annotations

import base64
from html.parser import HTMLParser
import re
from urllib.error import URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from sources.base import BaseSource, ProgressCallback, SearchResult


SEARCH_URL = "https://html.duckduckgo.com/html/?"
BING_SEARCH_URL = "https://www.bing.com/search?"
SEARCH_QUERIES = (
    '"oil and gas company" "official website"',
    '"petroleum company" "official website"',
    '"natural gas company" "official website"',
    '"drilling company" "official website"',
)
IGNORED_DOMAINS = (
    "linkedin.com",
    "facebook.com",
    "wikipedia.org",
    "youtube.com",
    "instagram.com",
    "x.com",
    "twitter.com",
    "yelp.com",
    "yellowpages.com",
    "zoominfo.com",
    "crunchbase.com",
    "dnb.com",
    "opencorporates.com",
    "bbb.org",
    "chamberofcommerce.com",
    "businessyab.com",
    "mapquest.com",
    "reuters.com",
    "bloomberg.com",
    "ft.com",
    "wsj.com",
    "cnn.com",
    "bbc.com",
    "nytimes.com",
    "cnbc.com",
    "apnews.com",
    "oilprice.com",
    "liveoilprices.com",
    "businessinsider.com",
    "cmegroup.com",
    "oilmonster.com",
    "oilpriceapi.com",
    "iea.org",
)
IGNORED_TITLE_TERMS = (
    "price",
    "market",
    "futures",
    "chart",
    "news",
    "report",
    "quotes",
    "analysis",
    "today",
    "investment",
)


class SearchUnavailableError(RuntimeError):
    """Raised when public search results cannot be reached."""


class _ResultParser(HTMLParser):
    """Extract ordinary result links and titles from the lightweight search page."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[tuple[str, str]] = []
        self._href = ""
        self._title_parts: list[str] = []
        self._result_containers: list[bool] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "div":
            self._result_containers.append("result--ad" in (attributes.get("class") or ""))
        if tag == "a" and "result__a" in (attributes.get("class") or ""):
            if not any(self._result_containers):
                self._href = attributes.get("href") or ""
                self._title_parts = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._title_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href:
            title = " ".join(self._title_parts).strip()
            if title:
                self.results.append((title, self._href))
            self._href = ""
            self._title_parts = []
        if tag == "div" and self._result_containers:
            self._result_containers.pop()


class _BingResultParser(HTMLParser):
    """Extract organic result titles and links from a public Bing results page."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[tuple[str, str]] = []
        self._in_result = False
        self._in_heading = False
        self._href = ""
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "li" and "b_algo" in (attributes.get("class") or ""):
            self._in_result = True
        elif tag == "h2" and self._in_result:
            self._in_heading = True
        elif tag == "a" and self._in_heading:
            self._href = attributes.get("href") or ""
            self._title_parts = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._title_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href:
            title = " ".join(self._title_parts).strip()
            if title:
                self.results.append((title, self._href))
            self._href = ""
            self._title_parts = []
        elif tag == "h2":
            self._in_heading = False
        elif tag == "li":
            self._in_result = False


class SearchEngineSource(BaseSource):
    """Find public company websites through multiple general web searches."""

    is_live = True
    timeout = 10.0
    max_results_per_query = 8

    def search(self, progress_callback: ProgressCallback | None = None) -> list[SearchResult]:
        """Search public web results and return unique company websites."""
        results: list[SearchResult] = []
        for index, query in enumerate(SEARCH_QUERIES, start=1):
            self._report(progress_callback, "Searching...", 10 + index * 70 // len(SEARCH_QUERIES))
            results.extend(self._search_query(query))
        return self._deduplicate(results)

    def _search_query(self, query: str) -> list[SearchResult]:
        """Search a public result page, trying an alternate page if needed."""
        result_links = self._bing_results(query)
        if not result_links:
            result_links = self._duckduckgo_results(query)
        return self._company_results(result_links)

    def _bing_results(self, query: str) -> list[tuple[str, str]]:
        page = self._download(f"{BING_SEARCH_URL}{urlencode({'q': query})}")
        parser = _BingResultParser()
        parser.feed(page)
        return [(title, self._decode_bing_link(link)) for title, link in parser.results]

    def _duckduckgo_results(self, query: str) -> list[tuple[str, str]]:
        page = self._download(f"{SEARCH_URL}{urlencode({'q': query})}")
        parser = _ResultParser()
        parser.feed(page)
        return parser.results

    def _download(self, url: str) -> str:
        request = Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; OilDomainFinder/1.0)"},
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except (URLError, TimeoutError, OSError) as error:
            raise SearchUnavailableError("Public search is unavailable.") from error

    def _company_results(self, result_links: list[tuple[str, str]]) -> list[SearchResult]:
        companies: list[SearchResult] = []
        for title, link in result_links:
            website = self._official_website(link)
            company_name = self._company_name(title)
            if website and company_name and not self._is_non_company_title(title):
                companies.append(SearchResult(company_name, website, ""))
            if len(companies) >= self.max_results_per_query:
                break
        return companies

    @staticmethod
    def _decode_bing_link(link: str) -> str:
        """Resolve the public destination embedded in a Bing result link."""
        parsed = urlparse(link)
        if parsed.netloc.casefold().endswith("bing.com") and parsed.path.startswith("/ck/"):
            encoded = parse_qs(parsed.query).get("u", [""])[0]
            if encoded.startswith("a1"):
                try:
                    return base64.urlsafe_b64decode(encoded[2:] + "===").decode("utf-8")
                except (ValueError, UnicodeDecodeError):
                    return ""
        return link

    @staticmethod
    def _official_website(link: str) -> str:
        """Return a safe public website URL, or blank for excluded destinations."""
        if link.startswith("//"):
            link = f"https:{link}"
        parsed = urlparse(link)
        if "duckduckgo.com" in parsed.netloc:
            link = parse_qs(parsed.query).get("uddg", [""])[0]
            parsed = urlparse(link)
        domain = parsed.netloc.casefold().removeprefix("www.")
        if (
            parsed.scheme not in {"http", "https"}
            or not domain
            or parsed.path.casefold().endswith(".pdf")
            or any(part in {"news", "article", "articles"} for part in parsed.path.casefold().split("/"))
            or any(domain == ignored or domain.endswith(f".{ignored}") for ignored in IGNORED_DOMAINS)
            or domain.startswith("news.")
        ):
            return ""
        return f"{parsed.scheme}://{parsed.netloc}"

    @staticmethod
    def _company_name(title: str) -> str:
        """Use the leading result-title segment as the company name."""
        name = re.split(r"\s+(?:\||-|–|—)\s+", title, maxsplit=1)[0]
        name = re.sub(r"\s+(?:official\s+site|home)$", "", name, flags=re.IGNORECASE)
        return " ".join(name.split())[:120]

    @staticmethod
    def _is_non_company_title(title: str) -> bool:
        """Exclude common market and editorial result titles."""
        normalized = title.casefold()
        return any(term in normalized for term in IGNORED_TITLE_TERMS)

    @staticmethod
    def _deduplicate(results: list[SearchResult]) -> list[SearchResult]:
        unique: dict[tuple[str, str], SearchResult] = {}
        for result in results:
            unique.setdefault((result.company_name.casefold(), result.website.casefold()), result)
        return list(unique.values())

    @staticmethod
    def _report(callback: ProgressCallback | None, message: str, progress: int) -> None:
        if callback:
            callback(message, progress)
