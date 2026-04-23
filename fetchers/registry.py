"""Fetcher registry - maps source_type to fetcher class."""

from typing import Dict, Type, Optional
from . import BaseFetcher
from .direct import DirectFetcher
from .git_release import GitReleaseFetcher


# Registry: source_type -> Fetcher class
FETCHER_REGISTRY: Dict[str, Type[BaseFetcher]] = {
    "direct": DirectFetcher,         # Direct APK URL
    "git_release": GitReleaseFetcher,  # Auto-detect from URL
}


def get_fetcher(source_type: str) -> Optional[BaseFetcher]:
    """Get fetcher instance by source type."""
    fetcher_class = FETCHER_REGISTRY.get(source_type)
    if fetcher_class:
        return fetcher_class()
    return None


def register_fetcher(source_type: str, fetcher_class: Type[BaseFetcher]) -> None:
    """Register a new fetcher type."""
    FETCHER_REGISTRY[source_type] = fetcher_class


__all__ = [
    "BaseFetcher",
    "ApkInfo", 
    "DirectFetcher",
    "GitReleaseFetcher",
    "get_fetcher",
    "register_fetcher",
    "FETCHER_REGISTRY",
]