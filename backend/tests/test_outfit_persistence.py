from uuid import uuid4

from fastapi.testclient import TestClient

from tests.auth_helpers import register_and_auth

RATIONALE = {"note": "navy shirt with trousers"}


def _create_item(client: TestClient, headers: dict[str, str], category: str = "shirt") -> str:
    return client.post(
        "/v1/wardrobe",
        headers=headers,
        json={
            "category": category,
            "color": "navy",
            "brand": "unbranded",
            "attributes": {},
        },
    ).json()["id"]


def _outfit_payload(
    item_ids: list[str],
    occasion: str = "casual",
    rationale: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "occasion": occasion,
        "item_ids": item_ids,
        "rationale": rationale if rationale is not None else RATIONALE,
    }


def test_post_outfit_creates_outfit_for_authenticated_user(client: TestClient) -> None:
    user_id, headers = register_and_auth(client, "outfit-user@example.com")
    shirt_id = _create_item(client, headers, "shirt")
    trousers_id = _create_item(client, headers, "trousers")
    response = client.post(
        "/v1/outfits",
        json=_outfit_payload([shirt_id, trousers_id]),
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == user_id
    assert body["occasion"] == "casual"
    assert body["item_ids"] == [shirt_id, trousers_id]
    assert body["rationale"] == RATIONALE
    assert body["id"]


def test_post_outfit_allows_empty_item_ids(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "outfit-user@example.com")
    response = client.post(
        "/v1/outfits", json=_outfit_payload([], rationale={}), headers=headers
    )
    assert response.status_code == 200
    assert response.json()["item_ids"] == []
    assert response.json()["rationale"] == {}


def test_post_outfit_rejects_missing_wardrobe_item(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "outfit-user@example.com")
    response = client.post(
        "/v1/outfits",
        json=_outfit_payload([str(uuid4())]),
        headers=headers,
    )
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "wardrobe_item_not_found",
            "message": "Wardrobe item was not found.",
        }
    }


def test_post_outfit_rejects_wardrobe_item_owned_by_another_user(client: TestClient) -> None:
    _user_a, headers_a = register_and_auth(client, "outfit-a@example.com")
    _user_b, headers_b = register_and_auth(client, "outfit-b@example.com")
    item_b = _create_item(client, headers_b)
    response = client.post("/v1/outfits", json=_outfit_payload([item_b]), headers=headers_a)
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "wardrobe_item_not_found",
            "message": "Wardrobe item was not found.",
        }
    }


def test_get_outfit_by_id(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "outfit-user@example.com")
    item_id = _create_item(client, headers)
    created = client.post(
        "/v1/outfits", json=_outfit_payload([item_id]), headers=headers
    ).json()
    response = client.get(f"/v1/outfits/{created['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json() == created


def test_cannot_get_another_users_outfit(client: TestClient) -> None:
    _user_a, headers_a = register_and_auth(client, "outfit-own@example.com")
    _user_b, headers_b = register_and_auth(client, "outfit-other@example.com")
    created = client.post(
        "/v1/outfits", json=_outfit_payload([]), headers=headers_a
    ).json()
    response = client.get(f"/v1/outfits/{created['id']}", headers=headers_b)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "outfit_not_found"


def test_get_missing_outfit_returns_error_envelope(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "outfit-user@example.com")
    response = client.get(f"/v1/outfits/{uuid4()}", headers=headers)
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "outfit_not_found", "message": "Outfit was not found."}
    }


def test_list_outfits_is_scoped_to_authenticated_user(client: TestClient) -> None:
    user_a, headers_a = register_and_auth(client, "outfit-list-a@example.com")
    _user_b, headers_b = register_and_auth(client, "outfit-list-b@example.com")
    item_a = _create_item(client, headers_a)
    item_b = _create_item(client, headers_b)
    first = client.post(
        "/v1/outfits",
        json=_outfit_payload([item_a], occasion="work"),
        headers=headers_a,
    ).json()
    second = client.post(
        "/v1/outfits",
        json=_outfit_payload([], occasion="casual", rationale={}),
        headers=headers_a,
    ).json()
    client.post(
        "/v1/outfits",
        json=_outfit_payload([item_b], occasion="formal"),
        headers=headers_b,
    )
    listed = client.get("/v1/outfits", headers=headers_a).json()
    assert listed["total"] == 2
    assert listed["limit"] == 50
    assert listed["offset"] == 0
    ids = {outfit["id"] for outfit in listed["outfits"]}
    assert ids == {first["id"], second["id"]}
    assert {outfit["occasion"] for outfit in listed["outfits"]} == {"work", "casual"}
    assert all(outfit["user_id"] == user_a for outfit in listed["outfits"])
