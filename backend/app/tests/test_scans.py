from io import BytesIO

from app.services.vision_llm import MOCK_EXTRACTED_LABEL


def test_analyze_without_api_keys_returns_mock_scan(client) -> None:
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
    assert payload["status"] == "NON_COMPLIANT"
    assert 0 <= payload["overall_score"] <= 100
    assert any(item["field_name"] == "mrp" for item in payload["violations"])


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


def test_healthcheck(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
