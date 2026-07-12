"""Adapter that makes the OpenCorporates client a source-engine provider."""

from services.opencorporates import OpenCorporatesService
from sources.base import BaseSource, ProgressCallback, SearchResult


class OpenCorporatesSource(BaseSource):
    """Retrieve companies from the live corporate-records service when ready."""

    is_live = True

    @property
    def is_enabled(self) -> bool:
        """Use the live source only when its private credentials are available."""
        return bool(OpenCorporatesService().api_token)

    def search(self, progress_callback: ProgressCallback | None = None) -> list[SearchResult]:
        """Return normalized live company results."""
        return [
            SearchResult(
                company_name=company.name,
                website=company.website,
                location=company.jurisdiction,
                registry_url=company.registry_url,
            )
            for company in OpenCorporatesService().search()
        ]
