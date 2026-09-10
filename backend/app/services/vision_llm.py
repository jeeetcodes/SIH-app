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
    "You are a Senior Legal Metrology Inspector in India enforcing the Legal Metrology (Packaged Commodities) Rules, 2011.\n"
    "Perform a high-precision visual audit of this product label image.\n\n"
    "You MUST perform a micro-scan of the entire package surface, including fine print, ingredients lists, legal footers, barcode areas, side edges, crimp seals, top/bottom flaps, and back-of-pack text.\n\n"
    "STEP-BY-STEP AUDIT PROCEDURE:\n"
    "1. REGIONAL TEXT SCAN: Locate all text blocks containing product names, contact details, grievances, disclaimers, prices, dates, or addresses.\n"
    "   - Extract the product or brand name as product_name when it is clearly visible.\n"
    "2. CUSTOMER CARE / GRIEVANCE REDRESSAL (Rule 6(1)(h)):\n"
    "   - Scan explicitly for terms like: 'Customer Care', 'Consumer Care', 'Grievance Officer', 'Write to us at', 'Care Executive', 'Feedback', 'Questions/Comments', 'Call us', 'Toll Free', 'Email:', 'Ph:', 'Tel:', 'PO Box'.\n"
    "   - Do NOT mark consumer_care as null if ANY phone number, email address, or grievance contact string is present anywhere on the package.\n"
    "3. MAXIMUM RETAIL PRICE (MRP) (Rule 6(1)(e)):\n"
    "   - Extract numerical price digits and verify if 'incl. of all taxes' or 'inclusive of all taxes' is written.\n"
    "4. NET QUANTITY (Rule 6(1)(c)):\n"
    "   - Extract exact numeric value and unit (e.g., '500 g', '1 L', '100 ml', '1 N', '2 units').\n"
    "5. DATE OF MFG/PACKING (Rule 6(1)(d)):\n"
    "   - Extract month and year of manufacture/packing/import.\n"
    "6. MANUFACTURER / IMPORTER / PACKER (Rule 6(1)(a)):\n"
    "   - Extract complete legal name and postal address.\n"
    "7. COUNTRY OF ORIGIN (Rule 6(1)(aa)):\n"
    "   - Required for imported commodities.\n\n"
    "DO NOT guess or invent text. However, DO NOT leave fields null if the text is present in small font sizes.\n"
    "First decide whether this is a readable consumer-package label. If it is definitely NOT a package label or is completely unreadable, "
    "set is_packaging_label to false, explain why in image_assessment, and leave all declaration fields null."
)

USER_PROMPT = (
    "Extract mandatory Legal Metrology (Packaged Commodities) Rule 6 declarations from this packaging label image.\n"
    "Perform a thorough micro-scan of ALL surfaces visible in the image.\n"
    "Return JSON matching the schema. Use null when a field is genuinely missing or completely unreadable."
)

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

BUSY_STATUS_CODES = {429, 503}
BUSY_DETAIL = (
    "The AI server is currently busy due to high demand. Please try again in a few moments."
)


class VisionProviderBusyError(Exception):
    """Raised when Gemini/OpenAI/OpenRouter is rate-limited or unavailable."""

    def __init__(self, message: str = BUSY_DETAIL) -> None:
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
        except VisionProviderBusyError:
            raise
        except Exception as exc:
            if is_provider_busy(exc):
                logger.warning("Vision provider busy: %s", exc)
                raise VisionProviderBusyError() from exc
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
            model=settings.GEMINI_MODEL or "gemini-3.6-flash",
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
        print(f"\n[Gemini] Raw vision response TEXT:\n{raw_text}\n")

        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, ExtractedLabelData):
            return parsed
        return ExtractedLabelData.model_validate_json(raw_text)

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
            return ExtractedLabelData.model_validate_json(message.content)
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
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return ExtractedLabelData.model_validate(json.loads(cleaned))
