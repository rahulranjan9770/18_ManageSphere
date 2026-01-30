"""Web search module for live internet integration."""

from .web_search import (
    WebSearchService,
    WebSearchResult,
    web_search_service,
    search_web,
    get_web_search_status
)

__all__ = [
    'WebSearchService',
    'WebSearchResult', 
    'web_search_service',
    'search_web',
    'get_web_search_status'
]
