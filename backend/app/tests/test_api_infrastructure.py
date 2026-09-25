from app.core.config import Settings
from app.schemas.scan import ExtractedLabelData
from app.services.ocr_service import ocr_text_to_label_data
from app.services.product_lookup import lookup_product
from app.services.providers.base import VisionStrategy
from app.services.vision_llm import MOCK_EXTRACTED_LABEL, VisionLLMService, VisionProviderBusyError
from app.services.web_verification import verify_manufacturer


def test_settings_helpers_detect_configured_keys(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "  ")
    settings = Settings()
    assert settings.is_gemini_configured() is True
    assert settings.is_openai_configured() is False
    assert settings.is_anthropic_configured() is False
    assert "gemini" in settings.configured_vision_providers()
    assert settings.provider_status()["gemini"] is True
    assert "test-gemini" not in str(settings.provider_status())


def test_ocr_text_maps_common_label_fields() -> None:
    text = "MRP Rs. 40\nNet Qty 200 g\nMfg 08/2026\n8901234567890"
    extracted = ocr_text_to_label_data(text)
    assert extracted.is_packaging_label is True
    assert extracted.mrp is not None and "40" in extracted.mrp
    assert extracted.net_quantity and "200" in extracted.net_quantity
    assert extracted.barcode == "8901234567890"


def test_vision_fallback_uses_next_provider(monkeypatch) -> None:
    from app.services import vision_llm as module

    class FailGemini(VisionStrategy):
        name = "gemini"

        def is_configured(self) -> bool:
            return True

        def extract(self, image_bytes: bytes, mime_type: str) -> ExtractedLabelData:
            raise TimeoutError("gemini timed out")

    class OkOpenAI(VisionStrategy):
        name = "openai"

        def is_configured(self) -> bool:
            return True

        def extract(self, image_bytes: bytes, mime_type: str) -> ExtractedLabelData:
            return MOCK_EXTRACTED_LABEL.model_copy()

    monkeypatch.setattr(module, "build_vision_strategies", lambda: [FailGemini(), OkOpenAI()])
    service = VisionLLMService()
    extracted, used_mock = service.extract(b"\xff\xd8\xffabc", mime_type="image/jpeg")
    assert used_mock is False
    assert service.last_provider == "openai"
    assert extracted.mrp == MOCK_EXTRACTED_LABEL.mrp


def test_vision_all_busy_raises(monkeypatch) -> None:
    from app.services import vision_llm as module

    class Busy(VisionStrategy):
        name = "gemini"

        def is_configured(self) -> bool:
            return True

        def extract(self, image_bytes: bytes, mime_type: str) -> ExtractedLabelData:
            raise VisionProviderBusyError()

    monkeypatch.setattr(module, "build_vision_strategies", lambda: [Busy()])
    service = VisionLLMService()
    try:
        service.extract(b"\xff\xd8\xffabc", mime_type="image/jpeg")
        raise AssertionError("expected VisionProviderBusyError")
    except VisionProviderBusyError:
        pass


def test_product_and_web_stubs_skip_when_unconfigured(monkeypatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "BARCODE_LOOKUP_API_KEY", None)
    monkeypatch.setattr(settings, "OPEN_FOOD_FACTS_URL", "")
    monkeypatch.setattr(settings, "TAVILY_API_KEY", None)
    monkeypatch.setattr(settings, "SERPAPI_KEY", None)
    assert lookup_product(barcode="8901234567890", product_name="Test") is None
    assert verify_manufacturer(manufacturer="Acme Foods", product_name="Test") is None
