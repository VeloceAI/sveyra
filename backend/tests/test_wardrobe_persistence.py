from uuid import uuid4

from fastapi.testclient import TestClient

from tests.auth_helpers import register_and_auth


def _item_payload(category: str = "shirt") -> dict[str, object]:
    return {
        "category": category,
        "color": "navy",
        "brand": "unbranded",
        "attributes": {},
    }


def test_post_wardrobe_item_creates_item(client: TestClient) -> None:
    user_id, headers = register_and_auth(client, "wardrobe-user@example.com")
    response = client.post("/v1/wardrobe", json=_item_payload(), headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == user_id
    assert body["category"] == "shirt"
    assert body["color"] == "navy"
    assert body["brand"] == "unbranded"
    assert body["attributes"] == {}
    assert body["id"]


def test_get_wardrobe_item_returns_persisted_item(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "wardrobe-user@example.com")
    created = client.post("/v1/wardrobe", json=_item_payload(), headers=headers).json()
    response = client.get(f"/v1/wardrobe/{created['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["category"] == "shirt"


def test_list_wardrobe_items_is_scoped_to_authenticated_user(client: TestClient) -> None:
    _user_a, headers_a = register_and_auth(client, "wardrobe-a@example.com")
    _user_b, headers_b = register_and_auth(client, "wardrobe-b@example.com")
    first = client.post("/v1/wardrobe", json=_item_payload("shirt"), headers=headers_a).json()
    second = client.post(
        "/v1/wardrobe", json=_item_payload("trousers"), headers=headers_a
    ).json()
    client.post("/v1/wardrobe", json=_item_payload("jacket"), headers=headers_b)
    listed = client.get("/v1/wardrobe", headers=headers_a).json()
    assert listed["limit"] == 50
    assert listed["offset"] == 0
    assert listed["total"] == 2
    ids = {item["id"] for item in listed["wardrobe_items"]}
    assert ids == {first["id"], second["id"]}
    assert {item["category"] for item in listed["wardrobe_items"]} == {"shirt", "trousers"}


def test_cannot_get_another_users_wardrobe_item(client: TestClient) -> None:
    _user_a, headers_a = register_and_auth(client, "wardrobe-own@example.com")
    _user_b, headers_b = register_and_auth(client, "wardrobe-other@example.com")
    item_a = client.post("/v1/wardrobe", json=_item_payload(), headers=headers_a).json()
    response = client.get(f"/v1/wardrobe/{item_a['id']}", headers=headers_b)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "wardrobe_item_not_found"


def test_missing_wardrobe_item_returns_404(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "wardrobe-user@example.com")
    response = client.get(f"/v1/wardrobe/{uuid4()}", headers=headers)
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "wardrobe_item_not_found",
            "message": "Wardrobe item was not found.",
        }
    }
