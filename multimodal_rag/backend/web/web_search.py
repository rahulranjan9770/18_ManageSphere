"""
Live Web Search Integration for Multimodal RAG System.
Provides real-time web search capabilities to supplement document-based knowledge.
"""

import asyncio
import aiohttp
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import quote_plus
import json

from backend.utils.logger import logger


# Source credibility tiers (higher = more trusted)
SOURCE_CREDIBILITY = {
    # Academic & Scientific (Highest trust)
    'arxiv.org': 0.95,
    'nature.com': 0.95,
    'sciencedirect.com': 0.90,
    'ncbi.nlm.nih.gov': 0.95,
    'ieee.org': 0.90,
    'acm.org': 0.90,
    'scholar.google.com': 0.85,
    'researchgate.net': 0.80,
    
    # Encyclopedias & Reference
    'wikipedia.org': 0.80,
    'britannica.com': 0.85,
    
    # Major News (Reputable)
    'bbc.com': 0.80,
    'bbc.co.uk': 0.80,
    'reuters.com': 0.85,
    'apnews.com': 0.85,
    'nytimes.com': 0.75,
    'theguardian.com': 0.75,
    'washingtonpost.com': 0.75,
    
    # Government & Official
    'gov': 0.90,
    'edu': 0.85,
    'org': 0.70,
    
    # Tech Knowledge
    'github.com': 0.75,
    'stackoverflow.com': 0.75,
    'docs.python.org': 0.85,
    'developer.mozilla.org': 0.85,
    
    # General/Medium trust
    'medium.com': 0.55,
    'quora.com': 0.50,
    
    # Default for unknown sources
    'default': 0.40,
}


@dataclass
class WebSearchResult:
    """A single web search result."""
    title: str
    url: str
    snippet: str
    source_name: str  # e.g., "Wikipedia", "News Article"
    timestamp: Optional[str] = None
    relevance_score: float = 0.5
    credibility_score: float = 0.5  # NEW: Credibility of the source
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source_name": self.source_name,
            "timestamp": self.timestamp,
            "relevance_score": self.relevance_score,
            "credibility_score": self.credibility_score
        }


class WebSearchService:
    """
    Service for performing live web searches.
    Supports multiple providers for reliable results:
    1. Serper.dev (Google results) - requires SERPER_API_KEY
    2. Tavily (AI-optimized) - requires TAVILY_API_KEY  
    3. DuckDuckGo (fallback, no key required)
    """
    
    def __init__(self):
        self.enabled = True
        self.max_results = 5  # Restored for capability
        self.timeout = 10  # Balanced for speed/quality (was 15s)
        self.cache: Dict[str, Tuple[List[WebSearchResult], datetime]] = {}
        self.cache_ttl = 300  # 5 minutes cache
        
        # Load .env file and get API keys
        import os
        try:
            from dotenv import load_dotenv
            load_dotenv()  # Load from .env file
        except ImportError:
            pass  # dotenv not installed, use system env vars
        
        self.serper_api_key = os.environ.get('SERPER_API_KEY', '')
        self.tavily_api_key = os.environ.get('TAVILY_API_KEY', '')
        
        # Determine best available provider
        if self.serper_api_key:
            self.primary_provider = 'serper'
            logger.logger.info("Web search using Serper.dev (Google results)")
        elif self.tavily_api_key:
            self.primary_provider = 'tavily'
            logger.logger.info("Web search using Tavily AI Search")
        else:
            self.primary_provider = 'duckduckgo'
            logger.logger.info("Web search using DuckDuckGo (fallback)")
        
    async def search(self, query: str, num_results: int = 5) -> List[WebSearchResult]:
        """
        Perform a web search and return results.
        Tries multiple providers for reliable results.
        """
        if not self.enabled:
            return []
        
        # Check cache
        cache_key = f"{query}:{num_results}"
        if cache_key in self.cache:
            results, cached_time = self.cache[cache_key]
            age = (datetime.now() - cached_time).total_seconds()
            if age < self.cache_ttl:
                logger.logger.info(f"Web search cache hit for: {query}")
                return results
        
        results = []
        
        try:
            # Try providers in order of preference
            if self.serper_api_key:
                results = await self._search_serper(query, num_results)
                if results:
                    logger.logger.info(f"Serper returned {len(results)} results")
            
            if not results and self.tavily_api_key:
                results = await self._search_tavily(query, num_results)
                if results:
                    logger.logger.info(f"Tavily returned {len(results)} results")
            
            if not results:
                # Fallback to DuckDuckGo
                results = await self._search_duckduckgo(query, num_results)
                if results:
                    logger.logger.info(f"DuckDuckGo returned {len(results)} results")
            
            if results:
                self.cache[cache_key] = (results, datetime.now())
                return results
            
            logger.logger.warning(f"No web results found for: {query}")
            return []
            
        except Exception as e:
            logger.logger.error(f"Web search error: {e}")
            return []
    
    async def _search_serper(self, query: str, num_results: int) -> List[WebSearchResult]:
        """
        Search using Serper.dev API (provides Google Search results).
        Free tier: 2,500 queries/month
        Get API key at: https://serper.dev
        """
        results = []
        url = "https://google.serper.dev/search"
        
        headers = {
            "X-API-KEY": self.serper_api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "q": query,
            "num": num_results,
            "gl": "us",
            "hl": "en"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=self.timeout) as response:
                    if response.status != 200:
                        logger.logger.warning(f"Serper returned status {response.status}")
                        return []
                    
                    data = await response.json()
                    
                    # Parse organic results
                    organic = data.get('organic', [])
                    for i, item in enumerate(organic[:num_results]):
                        source_url = item.get('link', '')
                        source_name = self._extract_source_name(source_url)
                        credibility = self._calculate_credibility(source_url)
                        
                        # Google results have better relevance - boost score
                        base_relevance = 1.0 - (i * 0.08)
                        relevance = base_relevance * (0.8 + 0.2 * credibility)
                        
                        results.append(WebSearchResult(
                            title=item.get('title', 'No title'),
                            url=source_url,
                            snippet=item.get('snippet', 'No description available'),
                            source_name=source_name,
                            timestamp=datetime.now().isoformat(),
                            relevance_score=max(0.4, relevance),
                            credibility_score=credibility
                        ))
                    
                    # Sort by credibility + relevance
                    results.sort(key=lambda x: (x.credibility_score * 0.6 + x.relevance_score * 0.4), reverse=True)
                    
        except asyncio.TimeoutError:
            logger.logger.warning("Serper search timed out")
        except Exception as e:
            logger.logger.error(f"Serper search error: {e}")
        
        return results
    
    async def _search_tavily(self, query: str, num_results: int) -> List[WebSearchResult]:
        """
        Search using Tavily API (AI-optimized search).
        Free tier: 1,000 queries/month
        Get API key at: https://tavily.com
        """
        results = []
        url = "https://api.tavily.com/search"
        
        payload = {
            "api_key": self.tavily_api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": num_results,
            "include_answer": False,
            "include_raw_content": False
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=self.timeout) as response:
                    if response.status != 200:
                        logger.logger.warning(f"Tavily returned status {response.status}")
                        return []
                    
                    data = await response.json()
                    
                    for i, item in enumerate(data.get('results', [])[:num_results]):
                        source_url = item.get('url', '')
                        source_name = self._extract_source_name(source_url)
                        credibility = self._calculate_credibility(source_url)
                        
                        # Tavily provides relevance scores
                        tavily_score = item.get('score', 0.5)
                        relevance = tavily_score * (0.8 + 0.2 * credibility)
                        
                        results.append(WebSearchResult(
                            title=item.get('title', 'No title'),
                            url=source_url,
                            snippet=item.get('content', 'No description available')[:500],
                            source_name=source_name,
                            timestamp=datetime.now().isoformat(),
                            relevance_score=max(0.4, relevance),
                            credibility_score=credibility
                        ))
                    
                    results.sort(key=lambda x: (x.credibility_score * 0.6 + x.relevance_score * 0.4), reverse=True)
                    
        except asyncio.TimeoutError:
            logger.logger.warning("Tavily search timed out")
        except Exception as e:
            logger.logger.error(f"Tavily search error: {e}")
        
        return results
    
    
    async def _search_duckduckgo(self, query: str, num_results: int) -> List[WebSearchResult]:
        """
        Search using DuckDuckGo HTML interface.
        """
        results = []
        encoded_query = quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=self.timeout) as response:
                    if response.status != 200:
                        logger.logger.warning(f"DuckDuckGo returned status {response.status}")
                        return []
                    
                    html = await response.text()
                    results = self._parse_duckduckgo_html(html, num_results)
                    
        except asyncio.TimeoutError:
            logger.logger.warning("DuckDuckGo search timed out")
        except Exception as e:
            logger.logger.error(f"DuckDuckGo search error: {e}")
        
        return results
    
    def _parse_duckduckgo_html(self, html: str, num_results: int) -> List[WebSearchResult]:
        """
        Parse DuckDuckGo HTML response to extract search results.
        """
        results = []
        
        # Pattern to find search result blocks
        # DuckDuckGo HTML has results in specific div structure
        
        # Find all result blocks
        result_pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
        snippet_pattern = r'<a[^>]*class="result__snippet"[^>]*>([^<]*(?:<[^>]*>[^<]*)*)</a>'
        
        # Alternative patterns for different DDG HTML versions
        alt_result_pattern = r'<a[^>]*rel="nofollow"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
        alt_snippet_pattern = r'class="result__snippet"[^>]*>([^<]+)'
        
        try:
            # Try primary pattern
            title_matches = re.findall(result_pattern, html, re.IGNORECASE)
            
            if not title_matches:
                # Try alternative pattern
                title_matches = re.findall(alt_result_pattern, html, re.IGNORECASE)
            
            # Get snippets
            snippet_matches = re.findall(snippet_pattern, html, re.IGNORECASE | re.DOTALL)
            
            if not snippet_matches:
                snippet_matches = re.findall(alt_snippet_pattern, html, re.IGNORECASE)
            
            # Clean HTML tags from snippets
            clean_snippets = []
            for snippet in snippet_matches:
                clean = re.sub(r'<[^>]+>', '', snippet)
                clean = clean.strip()
                if clean:
                    clean_snippets.append(clean)
            
            # Combine results
            for i, (url, title) in enumerate(title_matches[:num_results]):
                if not url or not title:
                    continue
                    
                # Skip DuckDuckGo redirect URLs, extract actual URL
                if 'uddg=' in url:
                    url_match = re.search(r'uddg=([^&]+)', url)
                    if url_match:
                        from urllib.parse import unquote
                        url = unquote(url_match.group(1))
                
                # Get snippet if available
                snippet = clean_snippets[i] if i < len(clean_snippets) else ""
                
                # Determine source name and credibility from URL
                source_name = self._extract_source_name(url)
                credibility = self._calculate_credibility(url)
                
                # Calculate relevance (based on position + credibility boost)
                base_relevance = 1.0 - (i * 0.1)  # First result = 1.0, decreases
                # Boost relevance for high-credibility sources
                relevance = base_relevance * (0.7 + 0.3 * credibility)
                
                results.append(WebSearchResult(
                    title=title.strip(),
                    url=url,
                    snippet=snippet[:500] if snippet else "No description available",
                    source_name=source_name,
                    timestamp=datetime.now().isoformat(),
                    relevance_score=max(0.3, relevance),
                    credibility_score=credibility
                ))
            
            # Sort by combined score (credibility + relevance) for best sources first
            results.sort(key=lambda x: (x.credibility_score * 0.6 + x.relevance_score * 0.4), reverse=True)
            
        except Exception as e:
            logger.logger.error(f"Error parsing DuckDuckGo HTML: {e}")
        
        return results
    
    def _calculate_credibility(self, url: str) -> float:
        """Calculate credibility score for a URL based on domain."""
        try:
            domain = url.split('://')[1] if '://' in url else url
            domain = domain.split('/')[0].lower()
            
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Check exact matches first
            for key, score in SOURCE_CREDIBILITY.items():
                if key in domain:
                    return score
            
            # Check TLD for .gov, .edu, .org
            if domain.endswith('.gov'):
                return SOURCE_CREDIBILITY.get('gov', 0.90)
            elif domain.endswith('.edu'):
                return SOURCE_CREDIBILITY.get('edu', 0.85)
            elif domain.endswith('.org'):
                return SOURCE_CREDIBILITY.get('org', 0.70)
            
            return SOURCE_CREDIBILITY.get('default', 0.40)
            
        except Exception:
            return 0.40
    
    def _extract_source_name(self, url: str) -> str:
        """Extract a readable source name from URL."""
        try:
            # Remove protocol
            domain = url.split('://')[1] if '://' in url else url
            domain = domain.split('/')[0]
            
            # Remove www.
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Known sources
            source_mappings = {
                'wikipedia.org': 'Wikipedia',
                'bbc.com': 'BBC News',
                'bbc.co.uk': 'BBC News',
                'cnn.com': 'CNN',
                'reuters.com': 'Reuters',
                'nytimes.com': 'NY Times',
                'theguardian.com': 'The Guardian',
                'medium.com': 'Medium',
                'github.com': 'GitHub',
                'stackoverflow.com': 'Stack Overflow',
                'arxiv.org': 'arXiv (Academic)',
                'nature.com': 'Nature (Academic)',
                'sciencedirect.com': 'ScienceDirect (Academic)',
                'ncbi.nlm.nih.gov': 'PubMed (Medical)',
                'ieee.org': 'IEEE (Academic)',
                'acm.org': 'ACM (Academic)',
                'britannica.com': 'Britannica',
            }
            
            for key, name in source_mappings.items():
                if key in domain.lower():
                    return name
            
            # Return domain name (capitalized)
            return domain.split('.')[0].capitalize()
            
            return domain.split('.')[0].capitalize()
            
        except Exception:
            return "Web Source"
    
    def enable(self):
        """Enable web search."""
        self.enabled = True
        logger.logger.info("Web search enabled")
    
    def disable(self):
        """Disable web search."""
        self.enabled = False
        logger.logger.info("Web search disabled")
    
    def clear_cache(self):
        """Clear the search cache."""
        self.cache.clear()
        logger.logger.info("Web search cache cleared")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of web search service."""
        provider_names = {
            'serper': 'Serper.dev (Google Results)',
            'tavily': 'Tavily AI Search',
            'duckduckgo': 'DuckDuckGo (Basic)'
        }
        return {
            "enabled": self.enabled,
            "provider": self.primary_provider,
            "provider_name": provider_names.get(self.primary_provider, 'Unknown'),
            "has_api_key": bool(self.serper_api_key or self.tavily_api_key),
            "max_results": self.max_results,
            "timeout": self.timeout,
            "cache_size": len(self.cache),
            "cache_ttl_seconds": self.cache_ttl
        }


# Global instance
web_search_service = WebSearchService()


# Convenience functions
async def search_web(query: str, num_results: int = 5) -> List[WebSearchResult]:
    """Perform a web search."""
    return await web_search_service.search(query, num_results)


def get_web_search_status() -> Dict[str, Any]:
    """Get web search service status."""
    return web_search_service.get_status()
