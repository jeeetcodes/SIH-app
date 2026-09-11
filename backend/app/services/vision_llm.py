from __future__ import annotations

import base64
import json
import logging
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
            image_bytes = self._coerce_bytes(image)
        except Exception:
            logger.exception("Unable to decode uploaded image payload")
            return ExtractedLabelData(), True

        if not image_bytes:
            return ExtractedLabelData(), True

        if not settings.has_vision_provider:
            logger.warning("No vision API key configured; returning structured mock extraction")
            return MOCK_EXTRACTED_LABEL.model_copy(), True

        try:
            if settings.OPENROUTER_API_KEY:
                return self._extract_with_openrouter(image_bytes, mime_type), False
            if settings.GEMINI_API_KEY:
                return self._extract_with_gemini(image_bytes, mime_type), False
            return self._extract_with_openai(image_bytes, mime_type), False
        except (VisionProviderBusyError, VisionProviderConnectionError):
            raise
        except Exception as exc:
            if is_provider_busy(exc):
                logger.warning("Vision provider busy: %s", exc)
                raise VisionProviderBusyError() from exc
            if is_provider_connection_error(exc):
                logger.warning("Vision provider connection/DNS failed: %s", exc)
                raise VisionProviderConnectionError() from exc
            logger.exception("Vision provider failed")
            raise

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

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL or "gemini-2.5-flash",
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(data=image_bytes, mime_type=mime_type or "image/jpeg"),
                        types.Part.from_text(text=USER_PROMPT),
                    ],
                )
            ],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.0,
                top_p=1.0,
                response_mime_type="application/json",
                response_schema=ExtractedLabelData,
            ),
        )

        raw_text = getattr(response, "text", None) or ""
        logger.info("[Gemini] Raw vision response:\n%s", raw_text)

        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, ExtractedLabelData):
            return parsed
        try:
            return ExtractedLabelData.model_validate_json(raw_text)
        except Exception:
            logger.warning("[Gemini] JSON parsing failed, attempting sanitize: %s", raw_text)
            cleaned = self._clean_json(raw_text)
            return ExtractedLabelData.model_validate(json.loads(cleaned))

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
        import httpx

        encoded = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{mime_type or 'image/jpeg'};base64,{encoded}"
        schema = ExtractedLabelData.model_json_schema()
        payload = {
            "model": settings.OPENROUTER_MODEL,
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
        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        if settings.OPENROUTER_SITE_URL:
            headers["HTTP-Referer"] = settings.OPENROUTER_SITE_URL

        with httpx.Client(timeout=httpx.Timeout(45.0, connect=10.0)) as client:
            response = client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            if response.status_code in BUSY_STATUS_CODES:
                raise VisionProviderBusyError()
            response.raise_for_status()

        content = response.json()["choices"][0]["message"].get("content")
        logger.info("[OpenRouter] Raw vision response:\n%s", content)

        if not isinstance(content, str) or not content.strip():
            raise ValueError("OpenRouter returned no extraction content")
        cleaned = self._clean_json(content)
        return ExtractedLabelData.model_validate(json.loads(cleaned))

    def _clean_json(self, raw: str) -> str:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return cleaned
