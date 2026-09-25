from __future__ import annotations

import base64
import json
import logging
import time
from typing import Union

from app.core.config import settings
from app.schemas.scan import ExtractedLabelData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Chain-of-Thought System Prompt (Stage 1 – structured visual audit)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are a Senior Legal Metrology Inspector in India enforcing the Legal Metrology (Packaged Commodities) Rules, 2011 "
    "and associated FSSAI labeling mandates.\n"
    "Perform a high-precision visual audit of this product label image.\n\n"
    "You MUST perform a micro-scan of the entire package surface, including fine print, ingredients lists, legal footers, barcode areas, side edges, crimp seals, top/bottom flaps, and back-of-pack text.\n\n"
    "STEP-BY-STEP AUDIT PROCEDURE:\n"
    "0. PRODUCT CATEGORIZATION: Classify the product into one of the following exact categories: "
    "'Food & Beverage', 'Cosmetics', 'Electronics', 'General Grocery', 'Medical/FMCG', or 'Other'.\n"
    "1. REGIONAL TEXT SCAN: Locate all text blocks containing product names, contact details, grievances, disclaimers, prices, dates, or addresses.\n"
    "   - Extract the product or brand name as product_name when visible.\n"
    "2. MAXIMUM RETAIL PRICE (MRP) (Rule 6(1)(e)):\n"
    "   - Extract numerical price digits and verify if 'incl. of all taxes' or 'inclusive of all taxes' is written.\n"
    "3. CUSTOMER CARE / GRIEVANCE REDRESSAL (Rule 6(1)(h)):\n"
    "   - Scan explicitly for terms like: 'Customer Care', 'Consumer Care', 'Grievance Officer', 'Write to us at', 'Care Executive', 'Feedback', 'Questions/Comments', 'Call us', 'Toll Free', 'Email:', 'Ph:', 'Tel:'.\n"
    "   - Do NOT mark consumer_care as null if ANY phone number, email address, or grievance contact string is present.\n"
    "4. NET QUANTITY (Rule 6(1)(c)):\n"
    "   - Extract exact numeric value and unit (e.g., '500 g', '1 L', '100 ml', '1 N', '2 units').\n"
    "5. DATES (Rule 6(1)(d)):\n"
    "   - Extract month and year of manufacture/packing/import into date_of_packing.\n"
    "   - Extract expiry date, best before date, or use-by date into expiry_date.\n"
    "6. MANUFACTURER / IMPORTER / PACKER (Rule 6(1)(a)):\n"
    "   - Extract complete legal name and postal address.\n"
    "7. FSSAI LICENSE NUMBER:\n"
    "   - If this is a Food & Beverage product, extract the 14-digit FSSAI license number (e.g. '10012011000123') into fssai_license.\n"
    "8. INGREDIENTS LIST:\n"
    "   - Extract list of ingredients or composition into ingredients if present.\n"
    "9. FORMATTING & LEGIBILITY:\n"
    "   - If font is too small, contrast is poor, or text is obscured, describe the issue in formatting_assessment. Otherwise 'Clear print'.\n"
    "10. COUNTRY OF ORIGIN (Rule 6(1)(aa)):\n"
    "   - Required for imported commodities.\n\n"
    "DO NOT guess or invent text. However, DO NOT leave fields null if the text is present in small font sizes.\n"
    "First decide whether this is a readable consumer-package label. If it is definitely NOT a package label or is completely unreadable, "
    "set is_packaging_label to false, explain why in image_assessment, and leave all declaration fields null."
)

USER_PROMPT = (
    "Extract mandatory Legal Metrology (Packaged Commodities) Rule 6 declarations, classify product category, and detect FSSAI / Expiry / Ingredients from this packaging label image.\n"
    "Perform a thorough micro-scan of ALL surfaces visible in the image.\n"
    "Return JSON matching the schema. Use null when a field is genuinely missing or completely unreadable."
)

# Safe fallback fixture when vision API keys are not present (never used for 429/503 failures).
MOCK_EXTRACTED_LABEL = ExtractedLabelData(
    product_name="BrandX Snacks",
    product_category="Food & Beverage",
    mrp="Rs. 99.00 incl. of all taxes",
    net_quantity="500 g",
    manufacturer_details="BrandX Snacks Pvt Ltd, Plot 12, MIDC, Pune, Maharashtra 411019, India",
    date_of_packing="08/2026",
    expiry_date="Best before 12 months from packing",
    country_of_origin="India",
    consumer_care="care@brandx.example | 1800-123-4567 | Plot 12, MIDC Pune",
    unit_sale_price="Rs. 0.20/g",
    fssai_license="10015022003891",
    ingredients="Potato, Edible Vegetable Oil, Salt, Spices & Condiments",
    formatting_assessment="Clear high-contrast print, compliant font height.",
    is_packaging_label=True,
    image_assessment="Mock extraction: configure a Gemini/OpenAI vision API key for live AI label recognition.",
)

BUSY_STATUS_CODES = {429, 503}
BUSY_DETAIL = (
    "The AI server is currently busy due to high demand. Please try again in a few moments."
)


CONNECTION_ERROR_DETAIL = (
    "Unable to connect to AI provider. Check backend internet connection/DNS."
)


class VisionProviderBusyError(Exception):
    """Raised when Gemini/OpenAI/OpenRouter is rate-limited or unavailable."""

    def __init__(self, message: str = BUSY_DETAIL) -> None:
        super().__init__(message)


class VisionProviderRateLimitError(Exception):
    """Raised when Gemini remains rate-limited after retrying."""

    def __init__(self) -> None:
        super().__init__(
            "AI Vision Provider is currently rate limited. Please try again in 15 seconds."
        )


class VisionProviderConnectionError(Exception):
    """Raised when DNS resolution or network connection to AI provider fails."""

    def __init__(self, message: str = CONNECTION_ERROR_DETAIL) -> None:
        super().__init__(message)


def is_provider_busy(exc: BaseException) -> bool:
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(exc, "code", None)
    if status is None:
        status = getattr(exc, "status", None)
    try:
        if int(status) in BUSY_STATUS_CODES:
            return True
    except (TypeError, ValueError):
        pass

    response = getattr(exc, "response", None)
    response_status = getattr(response, "status_code", None) if response is not None else None
    try:
        if int(response_status) in BUSY_STATUS_CODES:
            return True
    except (TypeError, ValueError):
        pass

    text = str(exc).upper()
    return any(
        token in text
        for token in (
            "429",
            "503",
            "UNAVAILABLE",
            "TOO MANY REQUESTS",
            "RESOURCE_EXHAUSTED",
            "RESOURCE EXHAUSTED",
        )
    )


def is_provider_connection_error(exc: BaseException) -> bool:
    text = str(exc).upper()
    type_name = type(exc).__name__.upper()
    tokens = (
        "GETADDRINFO FAILED",
        "CONNECTERROR",
        "CONNECTIONERROR",
        "GAIERROR",
        "NAME OR SERVICE NOT KNOWN",
        "COULD NOT RESOLVE HOST",
        "ENOTFOUND",
        "ERRNO 11001",
        "SOCKET.GAIERROR",
        "NAME RESOLUTION",
        "CONNECT TIMEOUT",
        "CONNECTION REFUSED",
        "TEMPORARY FAILURE IN NAME RESOLUTION",
    )
    return any(t in text or t in type_name for t in tokens)


class VisionLLMService:
    """OCR + structured visual extraction via Gemini, OpenAI, or OpenRouter."""

    def extract(
        self,
        image: Union[bytes, str],
        mime_type: str = "image/jpeg",
    ) -> tuple[ExtractedLabelData, bool]:
        """Extract label fields from raw bytes or base64. Returns (extracted_data, used_mock_vision)."""
        try:
            # Master try-except wrapper to guarantee zero process-level crashes.
            try:
                image_bytes = self._coerce_bytes(image)
            except Exception:
                logger.exception("Unable to decode uploaded image payload")
                return ExtractedLabelData(), True

            if not image_bytes:
                return ExtractedLabelData(), True

            if not settings.has_vision_provider:
                logger.warning("No vision API key configured; returning structured mock extraction")
                return MOCK_EXTRACTED_LABEL.model_copy(), True

            # Multi-provider cascade: Layer 1 (Gemini) → Layer 2 (OpenRouter) → Layer 3 (OpenAI)
            providers = []

            # Layer 1: Gemini (if keys configured)
            if settings.GEMINI_API_KEY or settings.GEMINI_API_KEYS:
                providers.append(("Gemini", self._extract_with_gemini))

            # Layer 2: OpenRouter (if key configured)
            if settings.OPENROUTER_API_KEY:
                providers.append(("OpenRouter", self._extract_with_openrouter))

            # Layer 3: OpenAI (if key configured)
            if settings.OPENAI_API_KEY:
                providers.append(("OpenAI", self._extract_with_openai))

            if not providers:
                logger.critical("No vision providers configured")
                return MOCK_EXTRACTED_LABEL.model_copy(), True

            # Try each provider in sequence until one succeeds.
            last_exception = None
            for provider_name, provider_func in providers:
                try:
                    logger.info("Attempting extraction with provider: %s", provider_name)
                    result = provider_func(image_bytes, mime_type)
                    logger.info("Successfully extracted with provider: %s", provider_name)
                    return result, False
                except Exception as exc:
                    logger.warning(
                        "Provider %s failed: %s. Cascading to next provider...",
                        provider_name,
                        str(exc)[:150],
                    )
                    last_exception = exc
                    continue

            # All providers exhausted without success.
            logger.error("All vision providers exhausted without success")
            if last_exception:
                raise last_exception
            raise RuntimeError("All vision providers failed")

        except Exception as exc:
            # Final safety net: log and re-raise as a known exception type.
            logger.exception("Critical failure in vision extraction service")
            # Wrap unknown exceptions to prevent raw 500 crashes.
            raise RuntimeError(f"Vision extraction failed: {exc}") from exc

    def _coerce_bytes(self, image: Union[bytes, str]) -> bytes:
        if isinstance(image, bytes):
            return image
        payload = image.strip()
        if not payload:
            return b""
        if payload.startswith("data:") and "," in payload:
            payload = payload.split(",", 1)[1]
        return base64.b64decode(payload, validate=False)

    def _extract_with_gemini(self, image_bytes: bytes, mime_type: str) -> ExtractedLabelData:
        from google import genai
        from google.genai import types

        # Safe key collection with zero startup crashes.
        api_keys = settings.gemini_api_keys_list
        if not api_keys:
            logger.warning("No valid Gemini API keys configured in GEMINI_API_KEYS or GEMINI_API_KEY")
            raise ValueError("No Gemini API keys configured")

        # Layer 1: Gemini models in priority order (verified active models).
        candidate_models = ["gemini-3.6-flash", "gemini-2.5-flash"]

        # Override with settings.GEMINI_MODEL if explicitly set and not empty.
        if settings.GEMINI_MODEL and settings.GEMINI_MODEL.strip():
            explicit_model = settings.GEMINI_MODEL.strip()
            if explicit_model not in candidate_models:
                candidate_models.insert(0, explicit_model)

        # Cascading loop: try every key × model combination with universal exception handling.
        for api_key in api_keys:
            client = genai.Client(api_key=api_key)
            key_suffix = api_key[-4:] if len(api_key) >= 4 else "****"

            for model in candidate_models:
                try:
                    request = {
                        "model": model,
                        "contents": [
                            types.Content(
                                role="user",
                                parts=[
                                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type or "image/jpeg"),
                                    types.Part.from_text(text=USER_PROMPT),
                                ],
                            )
                        ],
                        "config": types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.0,
                            top_p=1.0,
                            response_mime_type="application/json",
                            response_schema=ExtractedLabelData,
                        ),
                    }

                    response = client.models.generate_content(**request)

                    # Success — parse and return immediately.
                    raw_text = getattr(response, "text", None) or ""
                    logger.info("[Gemini:%s] Raw vision response:\n%s", model, raw_text)

                    parsed = getattr(response, "parsed", None)
                    if isinstance(parsed, ExtractedLabelData):
                        return parsed
                    try:
                        return ExtractedLabelData.model_validate_json(raw_text)
                    except Exception:
                        logger.warning("[Gemini:%s] JSON parsing failed, attempting sanitize: %s", model, raw_text)
                        cleaned = self._clean_json(raw_text)
                        return ExtractedLabelData.model_validate(json.loads(cleaned))

                except Exception as exc:
                    # Universal catch-all: ANY exception triggers fallback to next model/key.
                    # This includes 429, 503, 500, timeouts, connection errors, API errors, etc.
                    logger.warning(
                        "[Provider Warning] Model %s on Provider Gemini (key ending %s) failed with: %s. Trying next fallback...",
                        model,
                        key_suffix,
                        str(exc)[:150],
                    )
                    continue  # Try next model/key combination.

        # All Gemini keys and models failed — raise to trigger Layer 2 fallback.
        logger.warning("All Gemini keys and models exhausted without success")
        raise ValueError("All Gemini providers failed")

    def _extract_with_openai(self, image_bytes: bytes, mime_type: str) -> ExtractedLabelData:
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        encoded = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{mime_type or 'image/jpeg'};base64,{encoded}"
        completion = client.beta.chat.completions.parse(
            model=settings.OPENAI_VISION_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": USER_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url, "detail": "high"},
                        },
                    ],
                },
            ],
            response_format=ExtractedLabelData,
            temperature=0.0,
            top_p=1.0,
        )

        message = completion.choices[0].message
        logger.info("[OpenAI] Raw vision response:\n%s", message.content)

        if message.parsed is not None:
            return message.parsed
        if message.content:
            try:
                return ExtractedLabelData.model_validate_json(message.content)
            except Exception:
                cleaned = self._clean_json(message.content)
                return ExtractedLabelData.model_validate(json.loads(cleaned))
        return ExtractedLabelData()

    def _extract_with_openrouter(self, image_bytes: bytes, mime_type: str) -> ExtractedLabelData:
        """Layer 2: OpenRouter free vision models cascade with universal exception handling."""
        import httpx

        if not settings.OPENROUTER_API_KEY:
            raise ValueError("No OpenRouter API key configured")

        encoded = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{mime_type or 'image/jpeg'};base64,{encoded}"
        schema = ExtractedLabelData.model_json_schema()

        # OpenRouter free vision models in priority order.
        candidate_models = [
            "google/gemma-4-31b-it:free",
            "meta-llama/llama-3.2-11b-vision-instruct:free",
            "openrouter/free",  # Auto-router to any available free vision model.
        ]

        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        if settings.OPENROUTER_SITE_URL:
            headers["HTTP-Referer"] = settings.OPENROUTER_SITE_URL

        # Cascading loop: try each model with universal exception handling.
        for model in candidate_models:
            try:
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": USER_PROMPT},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": data_url, "detail": "high"},
                                },
                            ],
                        },
                    ],
                    "temperature": 0.0,
                    "top_p": 1.0,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "label_extraction",
                            "strict": True,
                            "schema": schema,
                        },
                    },
                }

                with httpx.Client(timeout=httpx.Timeout(45.0, connect=10.0)) as client:
                    response = client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()

                content = response.json()["choices"][0]["message"].get("content")
                logger.info("[OpenRouter:%s] Raw vision response:\n%s", model, content)

                if not isinstance(content, str) or not content.strip():
                    raise ValueError("OpenRouter returned no extraction content")
                cleaned = self._clean_json(content)
                return ExtractedLabelData.model_validate(json.loads(cleaned))

            except Exception as exc:
                # Universal catch-all: ANY exception triggers fallback to next model.
                logger.warning(
                    "[Provider Warning] Model %s on Provider OpenRouter failed with: %s. Trying next fallback...",
                    model,
                    str(exc)[:150],
                )
                continue  # Try next model.

        # All OpenRouter models failed.
        logger.warning("All OpenRouter models exhausted without success")
        raise ValueError("All OpenRouter providers failed")

    def _clean_json(self, raw: str) -> str:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return cleaned


def _is_rate_limit_error(exc: BaseException) -> bool:
    """Identify Gemini's 429/API RESOURCE_EXHAUSTED response shape."""
    for value in (
        getattr(exc, "status_code", None),
        getattr(exc, "code", None),
        getattr(exc, "status", None),
    ):
        try:
            if int(value) == 429:
                return True
        except (TypeError, ValueError):
            continue

    response = getattr(exc, "response", None)
    try:
        if int(getattr(response, "status_code", None)) == 429:
            return True
    except (TypeError, ValueError):
        pass

    text = str(exc).upper()
    return "429" in text or "RESOURCE_EXHAUSTED" in text or "RESOURCE EXHAUSTED" in text


def _retry_delay_seconds(exc: BaseException) -> float:
    """Read Gemini's retryDelay while keeping a practical fallback."""
    candidates = [getattr(exc, "details", None), getattr(exc, "response_json", None)]
    response = getattr(exc, "response", None)
    if response is not None:
        candidates.append(getattr(response, "json", None))

    for candidate in candidates:
        if callable(candidate):
            try:
                candidate = candidate()
            except Exception:
                continue
        if not isinstance(candidate, dict):
            continue
        retry_info = candidate.get("retryDelay") or candidate.get("retry_delay")
        if isinstance(retry_info, dict):
            retry_info = retry_info.get("seconds")
        try:
            return max(float(retry_info), 5.0)
        except (TypeError, ValueError):
            continue
    return 5.0
