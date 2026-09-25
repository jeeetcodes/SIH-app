from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"


class StorageService:
    """Local filesystem storage for scan images (S3/Supabase can replace this later)."""

    def __init__(self, upload_dir: Optional[Path] = None) -> None:
        self.upload_dir = upload_dir or UPLOAD_DIR

    def save_image(self, image_bytes: bytes, filename: Optional[str] = None) -> Optional[str]:
        if not image_bytes:
            return None
        try:
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            suffix = Path(filename or "label.jpg").suffix or ".jpg"
            dest = self.upload_dir / f"{uuid4()}{suffix}"
            dest.write_bytes(image_bytes)
            return str(dest)
        except OSError:
            logger.exception("Failed to persist uploaded label image")
            return None

    @staticmethod
    def as_data_url(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"
