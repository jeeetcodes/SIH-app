from __future__ import annotations

import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.scan import Scan
from app.models.violation import Violation as ViolationRow
from app.schemas.scan import ScanResponse
from app.services.image_processor import ImagePreprocessor
from app.services.rules_engine import RulesEngine
from app.services.storage import StorageService
from app.services.vision_llm import VisionLLMService, VisionProviderBusyError, is_provider_busy

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/bmp",
    "image/heic",
    "image/heif",
}

image_preprocessor = ImagePreprocessor()
vision_service = VisionLLMService()
rules_engine = RulesEngine()
storage_service = StorageService()


def _safe_content_type(upload: UploadFile) -> str:
    declared = (upload.content_type or "").split(";")[0].strip().lower()
    if declared in ALLOWED_CONTENT_TYPES:
        return "image/jpeg" if declared == "image/jpg" else declared
    filename = (upload.filename or "").lower()
    if filename.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if filename.endswith(".png"):
        return "image/png"
    if filename.endswith(".webp"):
        return "image/webp"
    if filename.endswith(".gif"):
        return "image/gif"
    if filename.endswith(".bmp"):
        return "image/bmp"
    if filename.endswith((".heic", ".heif")):
        return "image/heic"
    return "image/jpeg"


def _looks_like_image(image_bytes: bytes, mime_type: str) -> bool:
    """Lightweight signature validation before sending data to a vision provider.

    This deliberately avoids image decoding dependencies in the request path while
    rejecting clearly malformed uploads. The vision provider remains responsible
    for fully decoding supported image formats.
    """
    signatures = {
        "image/jpeg": (b"\xff\xd8\xff",),
        "image/png": (b"\x89PNG\r\n\x1a\n",),
        "image/gif": (b"GIF87a", b"GIF89a"),
        "image/webp": (b"RIFF",),
        "image/bmp": (b"BM",),
    }
    if mime_type == "image/webp":
        return image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP"
    if mime_type in {"image/heic", "image/heif"}:
        return len(image_bytes) >= 12 and image_bytes[4:8] == b"ftyp"
    return any(image_bytes.startswith(signature) for signature in signatures.get(mime_type, ()))


@router.post("/analyze", response_model=ScanResponse)
async def analyze_scan(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ScanResponse:
    if file is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image file is required")

    try:
        image_bytes = await file.read()
    except Exception:
        logger.exception("Failed to read uploaded image")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to read the uploaded image",
        )

    if not image_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded image is empty")

    if len(image_bytes) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image exceeds the 10 MB upload limit",
        )

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type and not content_type.startswith("image/") and content_type != "application/octet-stream":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload must be an image file",
        )

    mime_type = _safe_content_type(file)
    if not _looks_like_image(image_bytes, mime_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a readable image of the declared type",
        )

    # --- Image preprocessing for improved OCR accuracy ---
    image_bytes, mime_type = image_preprocessor.enhance(image_bytes, mime_type)

    try:
        extracted, used_mock = vision_service.extract(image_bytes, mime_type=mime_type)
    except VisionProviderBusyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI server is currently busy due to high demand. Please try again in a few moments.",
        )
    except HTTPException:
        raise
    except Exception as e:
        if is_provider_busy(e):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The AI server is currently busy due to high demand. Please try again in a few moments.",
            )
        logger.exception("Vision extraction crashed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Vision analysis failed. Please try again with a clearer photo.",
        )

    if extracted.is_packaging_label is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid product label not detected. Please upload a clear photo of a packaging label.",
        )

    try:
        status_label, overall_score, violations = rules_engine.evaluate(extracted)
    except Exception:
        logger.exception("Rules evaluation crashed")
        from app.schemas.scan import Violation

        status_label = "NON_COMPLIANT"
        overall_score = 0
        violations = [
            Violation(
                rule_id="LM-ENGINE-ERROR",
                field_name="extracted_data",
                severity="WARNING",
                message="Compliance evaluation failed. Review the extracted fields manually.",
                citation="Internal rules engine safeguard",
            )
        ]

    scan_id = str(uuid4())
    image_uri = storage_service.save_image(image_bytes, file.filename)

    _persist_scan(
        db,
        scan_id=scan_id,
        status_label=status_label,
        overall_score=overall_score,
        extracted_json=extracted.model_dump_json(),
        image_uri=image_uri,
        violations=violations,
    )

    return ScanResponse(
        scan_id=scan_id,
        status=status_label,  # type: ignore[arg-type]
        overall_score=overall_score,
        extracted_data=extracted,
        violations=violations,
        used_mock_vision=used_mock,
        is_packaging_label=extracted.is_packaging_label,
        image_assessment=extracted.image_assessment,
    )


def _persist_scan(
    db: Session,
    *,
    scan_id: str,
    status_label: str,
    overall_score: int,
    extracted_json: str,
    image_uri: Optional[str],
    violations: list,
) -> None:
    try:
        scan = Scan(
            id=scan_id,
            status=status_label,
            overall_score=overall_score,
            extracted_json=extracted_json,
            image_uri=image_uri,
        )
        db.add(scan)
        for item in violations:
            db.add(
                ViolationRow(
                    scan_id=scan_id,
                    rule_id=item.rule_id,
                    field_name=item.field_name,
                    severity=item.severity,
                    message=item.message,
                    citation=item.citation,
                )
            )
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Scan audit persistence failed; returning in-memory result")
