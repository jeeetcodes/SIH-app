from io import BytesIO

from app.services.vision_llm import MOCK_EXTRACTED_LABEL
from app.schemas.scan import ExtractedLabelData


def test_analyze_without_api_keys_returns_mock_scan(client, monkeypatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", None)

    image = BytesIO(b"\xff\xd8\xff fake-jpeg-bytes")
    response = client.post(
        "/api/v1/scans/analyze",
        files={"file": ("label.jpg", image, "image/jpeg")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["used_mock_vision"] is True
    assert payload["extracted_data"]["mrp"] == MOCK_EXTRACTED_LABEL.mrp
    assert payload["extracted_data"]["net_quantity"] == MOCK_EXTRACTED_LABEL.net_quantity
    assert payload["status"] == "COMPLIANT"
    assert payload["overall_score"] == 100


def test_analyze_rejects_empty_upload(client) -> None:
    response = client.post(
        "/api/v1/scans/analyze",
        files={"file": ("empty.jpg", BytesIO(b""), "image/jpeg")},
    )
    assert response.status_code == 400


def test_analyze_rejects_non_image_content_type(client) -> None:
    response = client.post(
        "/api/v1/scans/analyze",
        files={"file": ("notes.txt", BytesIO(b"not an image"), "text/plain")},
    )
    assert response.status_code == 400


def test_analyze_rejects_malformed_image_bytes(client) -> None:
    response = client.post(
        "/api/v1/scans/analyze",
        files={"file": ("broken.jpg", BytesIO(b"not-a-jpeg"), "image/jpeg")},
    )
    assert response.status_code == 400


def test_analyze_rejects_non_label_image_from_vision(client, monkeypatch) -> None:
    from app.api.v1.endpoints.scans import vision_service

    monkeypatch.setattr(
        vision_service,
        "extract",
        lambda *_args, **_kwargs: (
            ExtractedLabelData(
                is_packaging_label=False,
                image_assessment="The photo shows a pet, not a package label.",
            ),
            False,
        ),
    )
    response = client.post(
        "/api/v1/scans/analyze",
        files={"file": ("pet.jpg", BytesIO(b"\xff\xd8\xff photo"), "image/jpeg")},
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "Valid product label not detected" in (
        detail if isinstance(detail, str) else str(detail)
    )


def test_analyze_busy_vision_returns_503(client, monkeypatch) -> None:
    from app.api.v1.endpoints.scans import vision_service
    from app.services.vision_llm import VisionProviderBusyError

    def _busy(*_args, **_kwargs):
        raise VisionProviderBusyError()

    monkeypatch.setattr(vision_service, "extract", _busy)
    response = client.post(
        "/api/v1/scans/analyze",
        files={"file": ("label.jpg", BytesIO(b"\xff\xd8\xff photo"), "image/jpeg")},
    )
    assert response.status_code == 503
    assert "busy" in response.json()["detail"].lower()


def test_healthcheck(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
