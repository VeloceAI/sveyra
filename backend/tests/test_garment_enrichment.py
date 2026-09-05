from uuid import uuid4

from fastapi.testclient import TestClient

from app.storage.memory import InMemoryStorage
from app.vision.deps import get_vision
from app.vision.errors import VisionUnavailableError
from app.vision.port import GarmentAnalysis, VisionPort
from app.vision.stub import StubVision
from tests.auth_helpers import register_and_auth

UPLOAD_BYTES = b"garment-image-bytes-for-enrichment"


class SpyStorage:
    def __init__(self, inner: InMemoryStorage) -> None:
        self.inner = inner
        self.get_calls: list[str] = []

    def put(self, data: bytes) -> str:
        return self.inner.put(data)

    def get(self, reference: str) -> bytes:
        self.get_calls.append(reference)
        return self.inner.get(reference)

    def delete(self, reference: str) -> None:
        self.inner.delete(reference)

    def create_access_url(self, reference: str, expires_seconds: int) -> str:
        return self.inner.create_access_url(reference, expires_seconds)


class FailingVision(VisionPort):
    def analyze_garment(self, image: bytes) -> GarmentAnalysis:
        raise VisionUnavailableError


def _create_item(
    client: TestClient,
    headers: dict[str, str],
    *,
    category: str = "shirt",
    color: str = "navy",
    attributes: dict | None = None,
) -> str:
    return client.post(
        "/v1/wardrobe",
        headers=headers,
        json={
            "category": category,
            "color": color,
            "brand": "unbranded",
            "attributes": attributes or {},
        },
    ).json()["id"]


def _upload_linked(
    client: TestClient,
    headers: dict[str, str],
    item_id: str,
    payload: bytes = UPLOAD_BYTES,
) -> dict:
    response = client.post(
        "/v1/media/upload",
        headers=headers,
        data={"wardrobe_item_id": item_id},
        files={"file": ("garment.jpg", payload, "image/jpeg")},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_enrich_success_updates_metadata(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "enrich-ok@example.com")
    item_id = _create_item(client, headers, category="other", color="unknown")
    _upload_linked(client, headers, item_id)

    analysis = GarmentAnalysis(
        category="jacket",
        color="black",
        pattern="solid",
        material="wool",
        silhouette="regular",
        occasion_tags=["formal"],
        category_confidence=0.91,
        color_confidence=0.88,
    )
    client.app.state.vision = StubVision(analysis=analysis)

    response = client.post(f"/v1/wardrobe/{item_id}/enrich", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "jacket"
    assert body["color"] == "black"
    assert body["attributes"]["cv"]["applied_category"] is True
    assert body["attributes"]["cv"]["applied_color"] is True
    assert body["attributes"]["cv"]["pattern"] == "solid"
    assert body["attributes"]["cv"]["material"] == "wool"
    assert "http" not in str(body["attributes"]).lower()
    assert "memory://" not in str(body["attributes"]).lower()
    assert UPLOAD_BYTES.decode("latin-1") not in str(body["attributes"])


def test_enrich_requires_jwt(client: TestClient) -> None:
    response = client.post(f"/v1/wardrobe/{uuid4()}/enrich")
    assert response.status_code == 401
    assert response.json()["error"]["code"] in {"unauthorized", "invalid_token"}


def test_enrich_rejects_cross_user_wardrobe(client: TestClient) -> None:
    _user_a, headers_a = register_and_auth(client, "enrich-a@example.com")
    _user_b, headers_b = register_and_auth(client, "enrich-b@example.com")
    item_b = _create_item(client, headers_b)
    _upload_linked(client, headers_b, item_b)

    response = client.post(f"/v1/wardrobe/{item_b}/enrich", headers=headers_a)
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "wardrobe_item_not_found",
            "message": "Wardrobe item was not found.",
        }
    }


def test_enrich_missing_media_returns_404(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "enrich-nomedia@example.com")
    item_id = _create_item(client, headers)

    response = client.post(f"/v1/wardrobe/{item_id}/enrich", headers=headers)
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "wardrobe_media_missing",
            "message": "No media asset is linked to this wardrobe item.",
        }
    }


def test_enrich_uses_storage_port_get(client: TestClient) -> None:
    spy = SpyStorage(client.app.state.storage)
    client.app.state.storage = spy
    _user_id, headers = register_and_auth(client, "enrich-spy@example.com")
    item_id = _create_item(client, headers)
    before_refs = set(spy.inner._objects.keys())
    _upload_linked(client, headers, item_id)

    response = client.post(f"/v1/wardrobe/{item_id}/enrich", headers=headers)
    assert response.status_code == 200
    uploaded_reference = (set(spy.inner._objects.keys()) - before_refs).pop()
    assert spy.get_calls == [uploaded_reference]


def test_enrich_low_confidence_does_not_overwrite_category_color(
    client: TestClient,
) -> None:
    _user_id, headers = register_and_auth(client, "enrich-low@example.com")
    item_id = _create_item(
        client, headers, category="shirt", color="navy", attributes={"fit": "slim"}
    )
    _upload_linked(client, headers, item_id)

    client.app.state.vision = StubVision(
        analysis=GarmentAnalysis(
            category="dress",
            color="red",
            pattern="striped",
            category_confidence=0.4,
            color_confidence=0.5,
        )
    )

    response = client.post(f"/v1/wardrobe/{item_id}/enrich", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "shirt"
    assert body["color"] == "navy"
    assert body["attributes"]["fit"] == "slim"
    assert body["attributes"]["cv"]["applied_category"] is False
    assert body["attributes"]["cv"]["applied_color"] is False
    assert body["attributes"]["cv"]["suggested_category"] == "dress"
    assert body["attributes"]["cv"]["suggested_color"] == "red"
    assert body["attributes"]["cv"]["pattern"] == "striped"


def test_enrich_vision_failure_safe_envelope(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "enrich-fail@example.com")
    item_id = _create_item(client, headers)
    _upload_linked(client, headers, item_id)
    client.app.dependency_overrides[get_vision] = lambda: FailingVision()

    response = client.post(f"/v1/wardrobe/{item_id}/enrich", headers=headers)
    client.app.dependency_overrides.pop(get_vision, None)

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "vision_unavailable",
            "message": "Garment vision analysis is temporarily unavailable.",
        }
    }
    assert "Traceback" not in response.text
    assert "VisionUnavailable" not in response.text


def test_enrich_does_not_persist_urls_or_bytes_in_attributes(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "enrich-safe@example.com")
    item_id = _create_item(client, headers, category="shirt", color="navy")
    _upload_linked(client, headers, item_id)

    client.app.state.vision = StubVision(
        analysis=GarmentAnalysis(
            category="https://evil.example/x",
            color="gs://bucket/object",
            pattern="memory://local/key",
            material="ok-cotton",
            category_confidence=0.99,
            color_confidence=0.99,
        )
    )

    response = client.post(f"/v1/wardrobe/{item_id}/enrich", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "shirt"
    assert body["color"] == "navy"
    serialized = str(body["attributes"]).lower()
    assert "http://" not in serialized
    assert "https://" not in serialized
    assert "gs://" not in serialized
    assert "memory://" not in serialized
    assert body["attributes"]["cv"]["material"] == "ok-cotton"
