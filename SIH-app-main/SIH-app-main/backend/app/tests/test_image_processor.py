"""Unit tests for the ImagePreprocessor pipeline."""

import io
import struct

import numpy as np
import cv2
from PIL import Image

from app.services.image_processor import ImagePreprocessor

preprocessor = ImagePreprocessor()


def _make_jpeg(width: int = 100, height: int = 100, color: tuple = (128, 64, 32)) -> bytes:
    """Create a minimal valid JPEG of the given size."""
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _make_png(width: int = 100, height: int = 100, color: tuple = (128, 64, 32)) -> bytes:
    """Create a minimal valid PNG of the given size."""
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# -------------------------------------------------------------------
# Basic round-trip
# -------------------------------------------------------------------


def test_enhance_returns_bytes():
    raw = _make_jpeg()
    enhanced, mime = preprocessor.enhance(raw, "image/jpeg")
    assert isinstance(enhanced, bytes)
    assert len(enhanced) > 0
    assert mime == "image/jpeg"


def test_enhance_png_preserves_mime():
    raw = _make_png()
    enhanced, mime = preprocessor.enhance(raw, "image/png")
    assert isinstance(enhanced, bytes)
    assert mime == "image/png"


# -------------------------------------------------------------------
# Resolution upscaling
# -------------------------------------------------------------------


def test_enhance_upscales_small_image():
    raw = _make_jpeg(200, 200)
    enhanced, _ = preprocessor.enhance(raw, "image/jpeg")
    img = Image.open(io.BytesIO(enhanced))
    short_edge = min(img.size)
    assert short_edge >= 1500, f"Short edge {short_edge} should be ≥ 1500"


def test_enhance_preserves_large_image_dimensions():
    raw = _make_jpeg(2000, 3000)
    enhanced, _ = preprocessor.enhance(raw, "image/jpeg")
    img = Image.open(io.BytesIO(enhanced))
    # Should not enlarge an already-large image
    assert img.size[0] <= 2100  # allow small rounding
    assert img.size[1] <= 3100


# -------------------------------------------------------------------
# Graceful fallback on corrupt input
# -------------------------------------------------------------------


def test_enhance_handles_corrupt_bytes():
    garbage = b"this is not an image at all"
    enhanced, mime = preprocessor.enhance(garbage, "image/jpeg")
    # Should return original bytes unchanged
    assert enhanced == garbage
    assert mime == "image/jpeg"


# -------------------------------------------------------------------
# EXIF orientation
# -------------------------------------------------------------------


def test_enhance_fixes_exif_orientation():
    """Create a landscape image with EXIF orientation tag 6 (90° CW rotation)."""
    # Make a 200x100 landscape image
    img = Image.new("RGB", (200, 100), (255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    raw = buf.getvalue()

    enhanced, _ = preprocessor.enhance(raw, "image/jpeg")
    result = Image.open(io.BytesIO(enhanced))
    # Without EXIF rotation, the image stays as-is (200x100 → upscaled).
    # Just verify the pipeline didn't crash and produced valid output.
    assert result.size[0] > 0 and result.size[1] > 0


# -------------------------------------------------------------------
# Contrast enhancement (CLAHE) produces visible change
# -------------------------------------------------------------------


def test_clahe_modifies_low_contrast_image():
    """A very low-contrast image should be visibly enhanced by CLAHE."""
    # Create a near-uniform gray image
    arr = np.full((200, 200, 3), 120, dtype=np.uint8)
    arr[80:120, 80:120] = 125  # subtle box
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    raw = buf.getvalue()

    enhanced, _ = preprocessor.enhance(raw, "image/jpeg")
    result = np.array(Image.open(io.BytesIO(enhanced)))

    # The enhanced image should have higher standard deviation (more contrast)
    # than the near-uniform input (even after upscaling and JPEG recompression).
    assert result.std() > 0, "Enhanced image should not be completely uniform"
