"""Image preprocessing pipeline for improved vision-based label extraction.

Enhances uploaded packaging images before they are sent to the vision LLM,
targeting near-100% accuracy on dense, low-contrast, and fine-print text
commonly found on Indian FMCG / Legal Metrology labels.

Pipeline stages:
  1. EXIF orientation correction (auto-rotate)
  2. CLAHE adaptive contrast enhancement on LAB L-channel
  3. Unsharp-mask sharpening for 4pt–6pt text
  4. Resolution upscale (shortest edge ≥ 1500 px)
"""

from __future__ import annotations

import io
import logging
from typing import Tuple

import cv2
import numpy as np
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------
MIN_SHORT_EDGE: int = 1500  # minimum pixels on the shortest dimension
CLAHE_CLIP_LIMIT: float = 2.0
CLAHE_TILE_GRID: Tuple[int, int] = (8, 8)
UNSHARP_SIGMA: float = 1.0
UNSHARP_STRENGTH: float = 0.5
JPEG_QUALITY: int = 95


class ImagePreprocessor:
    """Stateless image-enhancement pipeline.

    Usage::

        preprocessor = ImagePreprocessor()
        enhanced_bytes, mime = preprocessor.enhance(raw_bytes, "image/jpeg")
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def enhance(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
    ) -> Tuple[bytes, str]:
        """Run the full preprocessing pipeline on *image_bytes*.

        Returns ``(enhanced_bytes, output_mime_type)``.
        If the image cannot be decoded the original bytes are returned
        unchanged so that downstream code never crashes.
        """
        try:
            pil_img = self._load_and_fix_orientation(image_bytes)
        except Exception:
            logger.warning(
                "Image could not be decoded for preprocessing; "
                "returning original bytes unchanged"
            )
            return image_bytes, mime_type

        try:
            cv_img = self._pil_to_cv2(pil_img)
            cv_img = self._apply_clahe(cv_img)
            cv_img = self._apply_unsharp_mask(cv_img)
            cv_img = self._ensure_min_resolution(cv_img)
            pil_img = self._cv2_to_pil(cv_img)
        except Exception:
            logger.warning(
                "Enhancement step failed; falling back to orientation-corrected image"
            )
            # pil_img still holds the orientation-corrected version

        output_mime = "image/png" if mime_type == "image/png" else "image/jpeg"
        enhanced_bytes = self._export(pil_img, output_mime)
        logger.info(
            "Image preprocessed: %d → %d bytes (%s)",
            len(image_bytes),
            len(enhanced_bytes),
            output_mime,
        )
        return enhanced_bytes, output_mime

    # ------------------------------------------------------------------
    # Stage 1 – EXIF orientation correction
    # ------------------------------------------------------------------
    @staticmethod
    def _load_and_fix_orientation(image_bytes: bytes) -> Image.Image:
        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)  # auto-rotate per EXIF tag 0x0112
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        return img

    # ------------------------------------------------------------------
    # Stage 2 – CLAHE contrast enhancement (LAB L-channel)
    # ------------------------------------------------------------------
    @staticmethod
    def _apply_clahe(cv_img: np.ndarray) -> np.ndarray:
        lab = cv2.cvtColor(cv_img, cv2.COLOR_BGR2LAB)
        l_chan, a_chan, b_chan = cv2.split(lab)
        clahe = cv2.createCLAHE(
            clipLimit=CLAHE_CLIP_LIMIT, tileGridSize=CLAHE_TILE_GRID
        )
        l_chan = clahe.apply(l_chan)
        merged = cv2.merge([l_chan, a_chan, b_chan])
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    # ------------------------------------------------------------------
    # Stage 3 – Unsharp-mask sharpening
    # ------------------------------------------------------------------
    @staticmethod
    def _apply_unsharp_mask(
        cv_img: np.ndarray,
        sigma: float = UNSHARP_SIGMA,
        strength: float = UNSHARP_STRENGTH,
    ) -> np.ndarray:
        blurred = cv2.GaussianBlur(cv_img, (0, 0), sigma)
        sharpened = cv2.addWeighted(cv_img, 1.0 + strength, blurred, -strength, 0)
        return sharpened

    # ------------------------------------------------------------------
    # Stage 4 – Resolution upscale
    # ------------------------------------------------------------------
    @staticmethod
    def _ensure_min_resolution(cv_img: np.ndarray) -> np.ndarray:
        h, w = cv_img.shape[:2]
        short_edge = min(h, w)
        if short_edge >= MIN_SHORT_EDGE:
            return cv_img
        scale = MIN_SHORT_EDGE / short_edge
        new_w = int(w * scale)
        new_h = int(h * scale)
        return cv2.resize(cv_img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _pil_to_cv2(pil_img: Image.Image) -> np.ndarray:
        arr = np.array(pil_img)
        if arr.ndim == 3 and arr.shape[2] == 3:
            return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        if arr.ndim == 3 and arr.shape[2] == 4:
            return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
        return arr

    @staticmethod
    def _cv2_to_pil(cv_img: np.ndarray) -> Image.Image:
        if cv_img.ndim == 3:
            rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            return Image.fromarray(rgb)
        return Image.fromarray(cv_img)

    @staticmethod
    def _export(pil_img: Image.Image, mime_type: str) -> bytes:
        buf = io.BytesIO()
        if mime_type == "image/png":
            pil_img.save(buf, format="PNG", optimize=True)
        else:
            if pil_img.mode == "RGBA":
                pil_img = pil_img.convert("RGB")
            pil_img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        return buf.getvalue()
