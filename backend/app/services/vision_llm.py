from __future__ import annotations

import base64
import json
import logging
from typing import Union

from app.core.config import settings
from app.schemas.scan import ExtractedLabelData

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an expert Legal Metrology Compliance Auditor in India. "
    "Extract mandatory packaging declarations verbatim from the image. "
    "Do not hallucinate or guess fields that are unreadable or missing; return null for unreadable fields. "
    "Capture MRP, net quantity, manufacturer name and complete address, date of packing "
    "(month and year), country of origin, consumer care (phone or email), and unit sale price when present."
    " First decide whether this is a readable consumer-package label. If it is not a package, "
    "or it has no readable packaging declarations, set is_packaging_label to false, explain why "
    "in image_assessment, and leave all declaration fields null."
)

USER_PROMPT = (
    "Extract the mandatory Legal Metrology (Packaged Commodities) Rule 6 declarations "
    "from this packaging label. Return JSON only. Use null when a field is missing or unreadable."
)

# Deterministic fixture used when GEMINI_API_KEY and OPENAI_API_KEY are absent.
MOCK_EXTRACTED_LABEL = ExtractedLabelData(
    mrp="Rs. 99.00",
    net_quantity="500 gms",
    manufacturer_details="BrandX Snacks",
    date_of_packing=None,
    country_of_origin=None,
    consumer_care=None,
    unit_sale_price=None,
    is_packaging_label=None,
    image_assessment="Mock extraction: configure a vision API key to verify whether this is a package label.",
)


class VisionLLMService:
    """OCR + structured extraction via Gemini 2.0 Flash or OpenAI, with a safe mock fallback."""

    def extract(
        self,
        image: Union[bytes, str],
        mime_type: str = "image/jpeg",
    ) -> tuple[ExtractedLabelData, bool]:
        """
        Extract label fields from raw bytes or base64.

        Returns (extracted_data, used_mock_vision).
        """
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
        except Exception:
            logger.exception("Vision provider failed; falling back to empty structured extraction")
            return ExtractedLabelData(), False

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
            model=settings.GEMINI_MODEL,
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
                temperature=0,
                response_mime_type="application/json",
                response_json_schema=ExtractedLabelData.model_json_schema(),
            ),
        )
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, ExtractedLabelData):
            return parsed
        text = getattr(response, "text", None) or ""
        return ExtractedLabelData.model_validate_json(text)

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
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            response_format=ExtractedLabelData,
            temperature=0,
        )
        message = completion.choices[0].message
        if message.parsed is not None:
            return message.parsed
        if message.content:
            return ExtractedLabelData.model_validate_json(message.content)
        return ExtractedLabelData()

    def _extract_with_openrouter(self, image_bytes: bytes, mime_type: str) -> ExtractedLabelData:
        """Send a local label image to a vision-capable OpenRouter model."""
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
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            "temperature": 0,
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
            response.raise_for_status()

        content = response.json()["choices"][0]["message"].get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("OpenRouter returned no extraction content")
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return ExtractedLabelData.model_validate(json.loads(cleaned))
