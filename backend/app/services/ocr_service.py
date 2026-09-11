from __future__ import annotations

import base64
import logging
import re
from typing import Optional

from app.core.config import settings
from app.schemas.scan import ExtractedLabelData
from app.services.providers.base import VisionStrategy

logger = logging.getLogger(__name__)

MRP_RE = re.compile(r"(?:MRP|M\.R\.P\.|Rs\.?|INR|₹)\s*[:\-]?\s*([0-9]+(?:[.,][0-9]+)?)", re.I)
QTY_RE = re.compile(
    r"(\d+(?:[.,]\d+)?\s(?:mg|kg|g|ml|ltr|litres?|liters?|l|nos|pcs|units)\b|\d+\sN\b)",
    re.I,
)
DATE_RE = re.compile(r"(?:mfg|pkd|packing|packed|exp)[^\d]{0,12}(\d{1,2}[/-]\d{2,4}|\d{2}/\d{4})", re.I)
BARCODE_RE = re.compile(r"\b(\d{8}|\d{12,14})\b")


def ocr_text_to_label_data(text: str) -> ExtractedLabelData:
    cleaned = (text or "").strip()
    if not cleaned:
        return ExtractedLabelData(
            is_packaging_label=False,
            image_assessment="Dedicated OCR returned no readable text.",
        )
    mrp_match = MRP_RE.search(cleaned)
    qty_match = QTY_RE.search(cleaned)
    date_match = DATE_RE.search(cleaned)
    barcode_match = BARCODE_RE.search(cleaned)
    return ExtractedLabelData(
        mrp=f"Rs. {mrp_match.group(1)}" if mrp_match else None,
        net_quantity=qty_match.group(1) if qty_match else None,
        date_of_packing=date_match.group(1) if date_match else None,
        barcode=barcode_match.group(1) if barcode_match else None,
        manufacturer_details=cleaned[:500],
        is_packaging_label=True,
        image_assessment=f"Structured fields inferred from dedicated OCR text ({len(cleaned)} chars).",
    )


class AzureVisionStrategy(VisionStrategy):
    name = "azure"

    def is_configured(self) -> bool:
        return settings.is_azure_vision_configured()

    def extract(self, image_bytes: bytes, mime_type: str) -> ExtractedLabelData:
        import httpx

        from app.services.vision_errors import BUSY_STATUS_CODES, VisionProviderBusyError

        endpoint = (settings.AZURE_VISION_ENDPOINT or "").rstrip("/")
        url = (
            f"{endpoint}/computervision/imageanalysis:analyze"
            "?api-version=2024-02-01&features=read"
        )
        headers = {
            "Ocp-Apim-Subscription-Key": settings.AZURE_VISION_KEY,
            "Content-Type": mime_type or "application/octet-stream",
        }
        timeout = httpx.Timeout(settings.VISION_REQUEST_TIMEOUT_SECONDS, connect=10.0)
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, headers=headers, content=image_bytes)
            if response.status_code in BUSY_STATUS_CODES:
                raise VisionProviderBusyError()
            response.raise_for_status()
        text = _azure_read_text(response.json())
        logger.info("[Azure Vision] OCR characters=%s", len(text))
        return ocr_text_to_label_data(text)


class GoogleCloudVisionStrategy(VisionStrategy):
    name = "google"

    def is_configured(self) -> bool:
        return settings.is_google_cloud_vision_configured()

    def extract(self, image_bytes: bytes, mime_type: str) -> ExtractedLabelData:
        import httpx

        from app.services.vision_errors import BUSY_STATUS_CODES, VisionProviderBusyError

        url = "https://vision.googleapis.com/v1/images:annotate"
        payload = {
            "requests": [
                {
                    "image": {"content": base64.b64encode(image_bytes).decode("ascii")},
                    "features": [{"type": "TEXT_DETECTION"}],
                }
            ]
        }
        timeout = httpx.Timeout(settings.VISION_REQUEST_TIMEOUT_SECONDS, connect=10.0)
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                url,
                params={"key": settings.GOOGLE_CLOUD_VISION_KEY},
                json=payload,
            )
            if response.status_code in BUSY_STATUS_CODES:
                raise VisionProviderBusyError()
            response.raise_for_status()
        annotations = (response.json().get("responses") or [{}])[0]
        text = (annotations.get("fullTextAnnotation") or {}).get("text") or ""
        if not text:
            detections = annotations.get("textAnnotations") or []
            text = detections[0].get("description", "") if detections else ""
        logger.info("[Google Cloud Vision] OCR characters=%s", len(text))
        return ocr_text_to_label_data(text)


def _azure_read_text(payload: dict) -> str:
    read_result = payload.get("readResult") or {}
    blocks = read_result.get("blocks") or []
    lines: list[str] = []
    for block in blocks:
        for line in block.get("lines") or []:
            value = line.get("text")
            if value:
                lines.append(str(value))
    if lines:
        return "\n".join(lines)
    return str(payload.get("content") or "")


class OCRSpaceStrategy(VisionStrategy):
    name = "ocrspace"

    def is_configured(self) -> bool:
        return settings.is_ocrspace_configured()

    def extract(self, image_bytes: bytes, mime_type: str) -> ExtractedLabelData:
        import httpx

        from app.services.vision_errors import BUSY_STATUS_CODES, VisionProviderBusyError

        url = "https://api.ocr.space/parse/image"
        files = {"file": ("image.jpg", image_bytes, mime_type or "image/jpeg")}
        data = {
            "apikey": settings.OCRSPACE_API_KEY,
            "language": "eng",
            "isOverlayRequired": "false",
            "detectOrientation": "true",
            "scale": "true",
            "OCREngine": "2",  # Engine 2 is more accurate
        }
        timeout = httpx.Timeout(settings.VISION_REQUEST_TIMEOUT_SECONDS, connect=10.0)
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, files=files, data=data)
            if response.status_code in BUSY_STATUS_CODES:
                raise VisionProviderBusyError()
            response.raise_for_status()

        result = response.json()
        if not result.get("IsErroredOnProcessing"):
            parsed_results = result.get("ParsedResults") or []
            text = ""
            for parsed in parsed_results:
                text += (parsed.get("ParsedText") or "") + "\n"
            text = text.strip()
            logger.info("[OCR.space] OCR characters=%s", len(text))
            return ocr_text_to_label_data(text)

        error_msg = " ".join(result.get("ErrorMessage") or result.get("ErrorDetails") or ["OCR.space processing failed"])
        logger.warning("[OCR.space] Error: %s", error_msg)
        return ExtractedLabelData(
            is_packaging_label=False,
            image_assessment=f"OCR.space error: {error_msg}",
        )


def ocr_strategies() -> list[VisionStrategy]:
    return [OCRSpaceStrategy(), AzureVisionStrategy(), GoogleCloudVisionStrategy()]


def get_ocr_strategy(provider_id: str) -> Optional[VisionStrategy]:
    lookup = {strategy.name: strategy for strategy in ocr_strategies()}
    return lookup.get(provider_id)
