from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.scan import ExtractedLabelData


class VisionStrategy(ABC):
    """Strategy contract for a vision/OCR provider."""

    name: str = "unknown"

    @abstractmethod
    def is_configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def extract(self, image_bytes: bytes, mime_type: str) -> ExtractedLabelData:
        raise NotImplementedError
