"""Web search tool for Research & Action Agent - Updated with standard contract."""

from __future__ import annotations

import os
import json
import time
import uuid
from typing import List, Dict, Any, Optional
from langchain.tools import tool
from .base_tool import ToolResponse, tool_wrapper

# Try to use Tavily if available
TAVILY_AVAILABLE = False
try:
    from langchain_community.tools.tavily_search import TavilySearchResults
    TAVILY_AVAILABLE = True
except ImportError:
    pass

# Try Bing Search API
BING_AVAILABLE = False
try:
    from langchain_community.tools import BingSearchRun
    BING_AVAILABLE = True
except ImportError:
    pass

# Domain reputation scores (simplified)
DOMAIN_REPUTATION = {
    "wikipedia.org": 0.95,
    "github.com": 0.90,
    "stackoverflow.com": 0.90,
    "news.ycombinator.com": 0.85,
    "reddit.com": 0.70,
    "twitter.com": 0.65,
    "facebook.com": 0.60,
}

# Blacklist domains
BLACKLIST_DOMAINS = [
    "malware.com",
    "phishing.com",
    # Add more as needed
]


@tool
def search_web(query: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> str:
    """
    Search the web for current information using Tavily or Bing API.
    
    Args:
        query: The search query string
        top_k: Maximum number of results to return (default: 5)
        filters: Optional filters dict with date_from, domains, etc.
    
    Returns:
        JSON string with standard contract: {status, data, meta, error}
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        # Validate inputs
        if not query or not query.strip():
            return ToolResponse(
                status="error",
                tool_name="search_web",
                request_id=request_id,
                source="tavily",
                error={
                    "code": "invalid_input",
                    "message": "Query cannot be empty",
                    "details": {}
                }
            ).to_json()
        
        top_k = max(1, min(top_k, 20))  # Limit between 1 and 20
        
        results = []
        source_used = "tavily"
        
        # Try Tavily first (preferred)
        if TAVILY_AVAILABLE and os.getenv("TAVILY_API_KEY"):
            try:
                search = TavilySearchResults(max_results=top_k)
                tavily_results = search.invoke(query)
                
                for idx, result in enumerate(tavily_results[:top_k]):
                    url = result.get("url", "")
                    domain = url.split("/")[2] if "/" in url else ""
                    
                    # Check blacklist
                    if any(blacklisted in domain for blacklisted in BLACKLIST_DOMAINS):
                        continue
                    
                    # Calculate source score
                    source_score = DOMAIN_REPUTATION.get(domain, 0.75)
                    
                    # Truncate snippet
                    snippet = result.get("content", result.get("snippet", ""))
                    if len(snippet) > 1000:
                        snippet = snippet[:1000] + "..."
                    
                    results.append({
                        "title": result.get("title", f"Result {idx+1}"),
                        "url": url,
                        "snippet": snippet,
                        "published_at": result.get("published_date", ""),
                        "source_score": source_score
                    })
                
                if results:
                    # Deduplicate by URL
                    seen_urls = set()
                    unique_results = []
                    for r in results:
                        if r["url"] not in seen_urls:
                            seen_urls.add(r["url"])
                            unique_results.append(r)
                    results = unique_results[:top_k]
                    
            except Exception as e:
                # Try Bing as fallback
                if BING_AVAILABLE and os.getenv("BING_SEARCH_SUBSCRIPTION_KEY"):
                    try:
                        search = BingSearchRun()
                        bing_result = search.invoke(query)
                        
                        results.append({
                            "title": "Bing Search Result",
                            "url": "",
                            "snippet": str(bing_result)[:1000],
                            "published_at": "",
                            "source_score": 0.75
                        })
                        source_used = "bing"
                    except:
                        pass
        
        # If no results and no API configured
        if not results:
            return ToolResponse(
                status="ok",
                data={"results": []},
                tool_name="search_web",
                duration_ms=int((time.time() - start_time) * 1000),
                request_id=request_id,
                source=source_used if results else "none"
            ).to_json()
        
        return ToolResponse(
            status="ok",
            data={"results": results},
            tool_name="search_web",
            duration_ms=int((time.time() - start_time) * 1000),
            request_id=request_id,
            source=source_used
        ).to_json()
        
    except Exception as e:
        return ToolResponse(
            status="error",
            tool_name="search_web",
            request_id=request_id,
            source="unknown",
            error={
                "code": type(e).__name__,
                "message": str(e),
                "details": {}
            }
        ).to_json()
