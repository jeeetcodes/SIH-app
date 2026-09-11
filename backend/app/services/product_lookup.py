from __future__ import annotations

import logging
from typing import Optional

from app.core.config import settings
from app.schemas.scan import ProductLookupResult

logger = logging.getLogger(__name__)


def lookup_product(
    *,
    barcode: Optional[str] = None,
    product_name: Optional[str] = None,
) -> Optional[ProductLookupResult]:
    """Resolve a scanned barcode/name against barcode catalogs or Open Food Facts.

    Returns None when no product database is configured or the lookup is skipped.
    Failures are swallowed so label analysis is never blocked by this enrichment.
    """
    if not settings.is_product_database_configured():
        return None
    query_barcode = (barcode or "").strip() or None
    query_name = (product_name or "").strip() or None
    if not query_barcode:
        return None

    if settings.is_barcode_lookup_configured():
        result = _lookup_barcode_api(query_barcode)
        if result is not None:
            return result

    if settings.is_open_food_facts_configured():
        return _lookup_open_food_facts(barcode=query_barcode, product_name=query_name)
    return None


def _lookup_barcode_api(barcode: str) -> Optional[ProductLookupResult]:
    import httpx

    url = "https://api.barcodelookup.com/v3/products"
    try:
        with httpx.Client(timeout=httpx.Timeout(12.0, connect=5.0)) as client:
            response = client.get(
                url,
                params={"barcode": barcode, "key": settings.BARCODE_LOOKUP_API_KEY},
            )
            response.raise_for_status()
        payload = response.json()
        products = payload.get("products") or []
        first = products[0] if products else {}
        return ProductLookupResult(
            source="barcode_lookup",
            found=bool(first),
            barcode=barcode,
            product_name=first.get("title") or first.get("product_name"),
            brand=first.get("brand"),
            summary=(first.get("description") or "")[:400] or None,
        )
    except Exception as exc:
        logger.warning("Barcode Lookup API failed: %s", exc)
        return ProductLookupResult(
            source="barcode_lookup",
            found=False,
            barcode=barcode,
            summary="Barcode catalog lookup failed.",
        )


def _lookup_open_food_facts(
    *,
    barcode: Optional[str],
    product_name: Optional[str],
) -> Optional[ProductLookupResult]:
    import httpx

    base = (settings.OPEN_FOOD_FACTS_URL or "https://world.openfoodfacts.org").rstrip("/")
    try:
        with httpx.Client(timeout=httpx.Timeout(12.0, connect=5.0)) as client:
            if barcode:
                response = client.get(f"{base}/api/v2/product/{barcode}.json")
                response.raise_for_status()
                payload = response.json()
                product = payload.get("product") or {}
                found = str(payload.get("status")) in {"1", "found"} or bool(product)
                return ProductLookupResult(
                    source="open_food_facts",
                    found=found,
                    barcode=barcode,
                    product_name=product.get("product_name") or product.get("generic_name"),
                    brand=product.get("brands"),
                    summary=(product.get("ingredients_text") or "")[:400] or None,
                )
            response = client.get(
                f"{base}/cgi/search.pl",
                params={
                    "search_terms": product_name,
                    "search_simple": 1,
                    "json": 1,
                    "page_size": 1,
                },
            )
            response.raise_for_status()
            products = response.json().get("products") or []
            first = products[0] if products else {}
            return ProductLookupResult(
                source="open_food_facts",
                found=bool(first),
                product_name=first.get("product_name"),
                brand=first.get("brands"),
                barcode=first.get("code"),
                summary=(first.get("ingredients_text") or "")[:400] or None,
            )
    except Exception as exc:
        logger.warning("Open Food Facts lookup failed: %s", exc)
        return ProductLookupResult(
            source="open_food_facts",
            found=False,
            barcode=barcode,
            product_name=product_name,
            summary="Open Food Facts lookup failed.",
        )
