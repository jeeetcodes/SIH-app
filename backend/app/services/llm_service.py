from __future__ import annotations

import base64
import json
import logging
import re
from typing import Any, Optional

from app.core.config import settings
from app.schemas.scan import ExtractedLabelData
from app.services.providers.base import VisionStrategy
from app.services.vision_prompts import SYSTEM_PROMPT, USER_PROMPT

logger = logging.getLogger(__name__)

JSON_INSTRUCTION = (
    "\nReturn ONLY valid JSON with these keys: product_name, mrp, net_quantity, "
    "manufacturer_details, date_of_packing, country_of_origin, consumer_care, "
    "unit_sale_price, barcode, is_packaging_label, image_assessment. Use null for missing fields."
)


def parse_label_json(raw_text: str) -> ExtractedLabelData:
    cleaned = (raw_text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    if not cleaned:
        return ExtractedLabelData()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        payload = json.loads(match.group(0))
    return ExtractedLabelData.model_validate(payload)


class GeminiVisionStrategy(VisionStrategy):
    name = "gemini"

    def is_configured(self) -> bool:
        return settings.is_gemini_configured()

    def extract(self, image_bytes: bytes, mime_type: str) -> ExtractedLabelData:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL or "gemini-2.0-flash",
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
        return ExtractedLabelData.model_validate_json(raw_text)


class OpenAIVisionStrategy(VisionStrategy):
    name = "openai"

    def is_configured(self) -> bool:
        return settings.is_openai_configured()

    def extract(self, image_bytes: bytes, mime_type: str) -> ExtractedLabelData:
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=settings.VISION_REQUEST_TIMEOUT_SECONDS)
        encoded = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{mime_type or 'image/jpeg'};base64,{encoded}"
        completion = client.beta.chat.completions.parse(
            model=settings.OPENAI_VISION_MODEL or "gpt-4o",
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
            return parse_label_json(message.content)
        return ExtractedLabelData()


class AnthropicVisionStrategy(VisionStrategy):
    name = "anthropic"

    def is_configured(self) -> bool:
        return settings.is_anthropic_configured()

    def extract(self, image_bytes: bytes, mime_type: str) -> ExtractedLabelData:
        import httpx

        media_type = mime_type or "image/jpeg"
        if media_type not in {"image/jpeg", "image/png", "image/gif", "image/webp"}:
            media_type = "image/jpeg"
        payload = {
            "model": settings.ANTHROPIC_MODEL or "claude-3-5-sonnet-20241022",
            "max_tokens": 2000,
            "temperature": 0,
            "system": SYSTEM_PROMPT,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64.b64encode(image_bytes).decode("ascii"),
                            },
                        },
                        {"type": "text", "text": USER_PROMPT + JSON_INSTRUCTION},
                    ],
                }
            ],
        }
        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        timeout = httpx.Timeout(settings.VISION_REQUEST_TIMEOUT_SECONDS, connect=10.0)
        with httpx.Client(timeout=timeout) as client:
            response = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            self._raise_for_busy(response)
            response.raise_for_status()
        content_blocks = response.json().get("content") or []
        text = ""
        for block in content_blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                text += str(block.get("text") or "")
        logger.info("[Anthropic] Raw vision response:\n%s", text)
        return parse_label_json(text)

    @staticmethod
    def _raise_for_busy(response: Any) -> None:
        from app.services.vision_errors import BUSY_STATUS_CODES, VisionProviderBusyError

        if getattr(response, "status_code", None) in BUSY_STATUS_CODES:
            raise VisionProviderBusyError()


class OpenRouterVisionStrategy(VisionStrategy):
    name = "openrouter"

    def is_configured(self) -> bool:
        return settings.is_openrouter_configured()

    def extract(self, image_bytes: bytes, mime_type: str) -> ExtractedLabelData:
        import httpx

        from app.services.vision_errors import BUSY_STATUS_CODES, VisionProviderBusyError

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

        timeout = httpx.Timeout(settings.VISION_REQUEST_TIMEOUT_SECONDS, connect=10.0)
        with httpx.Client(timeout=timeout) as client:
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
        return parse_label_json(content)


def llm_strategies() -> list[VisionStrategy]:
    return [
        GeminiVisionStrategy(),
        OpenAIVisionStrategy(),
        AnthropicVisionStrategy(),
        OpenRouterVisionStrategy(),
    ]


def get_llm_strategy(provider_id: str) -> Optional[VisionStrategy]:
    lookup = {strategy.name: strategy for strategy in llm_strategies()}
    return lookup.get(provider_id)
