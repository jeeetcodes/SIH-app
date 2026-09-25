from __future__ import annotations

import base64
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Optional, Union

from app.core.config import settings
from app.schemas.scan import ExtractedLabelData
from app.services.llm_service import get_llm_strategy
from app.services.ocr_service import get_ocr_strategy
from app.services.providers.base import VisionStrategy
from app.services.vision_errors import (
    BUSY_DETAIL,
    VisionProviderBusyError,
    is_provider_busy,
    is_retryable_failure,
)
from app.services.vision_prompts import SYSTEM_PROMPT, USER_PROMPT

logger = logging.getLogger(__name__)

# Safe fallback fixture when vision API keys are not present (never used for 429/503 failures).
MOCK_EXTRACTED_LABEL = ExtractedLabelData(
    product_name="BrandX Snacks",
    mrp="Rs. 99.00 incl. of all taxes",
    net_quantity="500 g",
    manufacturer_details="BrandX Snacks Pvt Ltd, Plot 12, MIDC, Pune, Maharashtra 411019, India",
    date_of_packing="08/2026",
    country_of_origin="India",
    consumer_care="care@brandx.example | 1800-123-4567",
    unit_sale_price="Rs. 0.20/g",
    is_packaging_label=True,
    image_assessment="Mock extraction: configure a Gemini/OpenAI vision API key for live AI label recognition.",
)


def build_vision_strategies() -> list[VisionStrategy]:
    """Configured providers in VISION_PROVIDER_ORDER (Gemini first by default)."""
    strategies: list[VisionStrategy] = []
    seen: set[str] = set()
    for provider_id in settings.vision_provider_order_list:
        if provider_id in seen:
            continue
        seen.add(provider_id)
        strategy = get_llm_strategy(provider_id) or get_ocr_strategy(provider_id)
        if strategy is None:
            logger.debug("Unknown vision provider id skipped: %s", provider_id)
            continue
        if strategy.is_configured():
            strategies.append(strategy)
    return strategies


def run_with_timeout(strategy: VisionStrategy, image_bytes: bytes, mime_type: str) -> ExtractedLabelData:
    timeout = max(5.0, float(settings.VISION_REQUEST_TIMEOUT_SECONDS))
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(strategy.extract, image_bytes, mime_type)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError as exc:
            future.cancel()
            raise TimeoutError(f"{strategy.name} timed out after {timeout}s") from exc


class VisionLLMService:
    """OCR + structured visual extraction with automatic multi-provider fallback."""

    def __init__(self) -> None:
        self.last_provider: Optional[str] = None

    def extract(
        self,
        image: Union[bytes, str],
        mime_type: str = "image/jpeg",
    ) -> tuple[ExtractedLabelData, bool]:
        """Extract label fields from raw bytes or base64. Returns (extracted_data, used_mock_vision)."""
        self.last_provider = None
        try:
            image_bytes = self._coerce_bytes(image)
        except Exception:
            logger.exception("Unable to decode uploaded image payload")
            self.last_provider = "mock"
            return ExtractedLabelData(), True

        if not image_bytes:
            self.last_provider = "mock"
            return ExtractedLabelData(), True

        strategies = build_vision_strategies()
        if not strategies:
            logger.warning("No vision API key configured; returning structured mock extraction")
            self.last_provider = "mock"
            return MOCK_EXTRACTED_LABEL.model_copy(), True

        last_error: Optional[BaseException] = None
        busy_only = True
        for strategy in strategies:
            try:
                extracted = run_with_timeout(strategy, image_bytes, mime_type)
                self.last_provider = strategy.name
                logger.info("Vision extraction succeeded via %s", strategy.name)
                return extracted, False
            except VisionProviderBusyError as exc:
                last_error = exc
                logger.warning("%s busy/rate-limited; trying next provider", strategy.name)
            except Exception as exc:
                last_error = exc
                if is_retryable_failure(exc):
                    logger.warning("%s failed (%s); trying next provider", strategy.name, exc)
                else:
                    busy_only = False
                    logger.exception("%s failed; trying next provider", strategy.name)

        if last_error is None:
            raise RuntimeError("Vision analysis failed")
        if busy_only:
            raise VisionProviderBusyError() from last_error
        logger.exception("All vision providers failed")
        raise last_error

    def _coerce_bytes(self, image: Union[bytes, str]) -> bytes:
        if isinstance(image, bytes):
            return image
        payload = image.strip()
        if not payload:
            return b""
        if payload.startswith("data:") and "," in payload:
            payload = payload.split(",", 1)[1]
        return base64.b64decode(payload, validate=False)


# Re-export names used by the scan endpoint and tests.
__all__ = [
    "BUSY_DETAIL",
    "MOCK_EXTRACTED_LABEL",
    "SYSTEM_PROMPT",
    "USER_PROMPT",
    "VisionLLMService",
    "VisionProviderBusyError",
    "build_vision_strategies",
    "is_provider_busy",
]
