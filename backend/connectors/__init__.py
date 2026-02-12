"""Data connectors for external research APIs."""

from .semantic_scholar import fetch_author_data
from .github_connector import fetch_github_data
from .figshare import fetch_figshare_data
from .google_scholar import fetch_scholar_data
from .affiliations import fetch_affiliations

__all__ = [
    "fetch_author_data", "fetch_github_data", "fetch_figshare_data",
    "fetch_scholar_data", "fetch_affiliations",
]
