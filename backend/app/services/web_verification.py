from __future__ import annotations

import logging
from typing import Optional

from app.core.config import settings
from app.schemas.scan import WebVerificationResult

logger = logging.getLogger(__name__)


def verify_manufacturer(
    *,
    manufacturer: Optional[str] = None,
    product_name: Optional[str] = None,
) -> Optional[WebVerificationResult]:
    """Look up manufacturer / FSSAI details on the public web.

    Prefer Tavily, then SerpAPI. Returns None when no search key is configured.
    Errors never fail the parent scan.
    """
    if not settings.is_web_verification_configured():
        return None

    parts = [part.strip() for part in (manufacturer, product_name) if part and part.strip()]
    if not parts:
        return None
    query = f"{' '.join(parts)} FSSAI manufacturer India"

    if settings.is_tavily_configured():
        result = _search_tavily(query)
        if result is not None:
            return result
    if settings.is_serpapi_configured():
        return _search_serpapi(query)
    return None


def _search_tavily(query: str) -> Optional[WebVerificationResult]:
    import httpx

    try:
        with httpx.Client(timeout=httpx.Timeout(12.0, connect=5.0)) as client:
            response = client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.TAVILY_API_KEY,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 3,
                },
            )
            response.raise_for_status()
        results = response.json().get("results") or []
        snippets = [
            str(item.get("content") or item.get("title") or "").strip()
            for item in results
            if isinstance(item, dict)
        ]
        snippets = [item for item in snippets if item][:3]
        return WebVerificationResult(
            source="tavily",
            query=query,
            found=bool(snippets),
            snippets=snippets,
        )
    except Exception as exc:
        logger.warning("Tavily search failed: %s", exc)
        return None


def _search_serpapi(query: str) -> Optional[WebVerificationResult]:
    import httpx

    try:
        with httpx.Client(timeout=httpx.Timeout(12.0, connect=5.0)) as client:
            response = client.get(
                "https://serpapi.com/search.json",
                params={"q": query, "api_key": settings.SERPAPI_KEY, "engine": "google", "num": 3},
            )
            response.raise_for_status()
        organic = response.json().get("organic_results") or []
        snippets = [
            str(item.get("snippet") or item.get("title") or "").strip()
            for item in organic
            if isinstance(item, dict)
        ]
        snippets = [item for item in snippets if item][:3]
        return WebVerificationResult(
            source="serpapi",
            query=query,
            found=bool(snippets),
            snippets=snippets,
        )
    except Exception as exc:
        logger.warning("SerpAPI search failed: %s", exc)
        return WebVerificationResult(
            source="serpapi",
            query=query,
            found=False,
            snippets=[],
        )
