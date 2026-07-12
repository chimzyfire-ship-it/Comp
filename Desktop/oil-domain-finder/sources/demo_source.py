"""Built-in sample results used when no live source is available."""

from sources.base import BaseSource, ProgressCallback, SearchResult


class DemoSource(BaseSource):
    """Provide sample companies so the app remains useful out of the box."""

    _COMPANIES = (
        ("ExxonMobil", "exxonmobil.com", "USA"),
        ("Shell", "shell.com", "UK"),
        ("Chevron", "chevron.com", "USA"),
        ("TotalEnergies", "totalenergies.com", "France"),
        ("BP", "bp.com", "UK"),
        ("Eni", "eni.com", "Italy"),
        ("ConocoPhillips", "conocophillips.com", "USA"),
        ("Equinor", "equinor.com", "Norway"),
        ("Petrobras", "petrobras.com.br", "Brazil"),
        ("ADNOC", "adnoc.ae", "UAE"),
    )

    def search(self, progress_callback: ProgressCallback | None = None) -> list[SearchResult]:
        """Return the preserved sample company list."""
        return [SearchResult(name, website, location) for name, website, location in self._COMPANIES]
