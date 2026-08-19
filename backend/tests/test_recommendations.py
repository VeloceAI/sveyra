from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.services.recommendation_engine import WardrobeItemSignal, rank_outfits
from tests.auth_helpers import register_and_auth


def _add_item(
    client: TestClient,
    headers: dict[str, str],
    *,
    category: str,
    color: str = "navy",
    brand: str = "unbranded",
    attributes: dict[str, object] | None = None,
) -> str:
    response = client.post(
        "/v1/wardrobe",
        headers=headers,
        json={
            "category": category,
            "color": color,
            "brand": brand,
            "attributes": attributes or {},
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_authenticated_recommendation_succeeds(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "rec-user@example.com")
    shirt = _add_item(client, headers, category="shirt", color="navy")
    trousers = _add_item(client, headers, category="trousers", color="black")
    response = client.post(
        "/v1/recommendations",
        headers=headers,
        json={"occasion": "casual"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["occasion"] == "casual"
    assert body["recommendations"]
    first = body["recommendations"][0]
    assert set(first["item_ids"]) == {shirt, trousers} or set(first["item_ids"]).issubset(
        {shirt, trousers}
    )
    assert shirt in first["item_ids"]
    assert trousers in first["item_ids"]
    assert first["rationale"].strip()


def test_unauthenticated_recommendation_returns_401(client: TestClient) -> None:
    response = client.post("/v1/recommendations", json={"occasion": "casual"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_recommendations_only_use_caller_wardrobe(client: TestClient) -> None:
    _user_a, headers_a = register_and_auth(client, "rec-a@example.com")
    _user_b, headers_b = register_and_auth(client, "rec-b@example.com")
    item_a_shirt = _add_item(client, headers_a, category="shirt")
    item_a_trousers = _add_item(client, headers_a, category="trousers")
    item_b_shirt = _add_item(client, headers_b, category="shirt", color="red")
    item_b_trousers = _add_item(client, headers_b, category="trousers", color="green")

    response = client.post(
        "/v1/recommendations",
        headers=headers_a,
        json={"occasion": "work"},
    )
    assert response.status_code == 200
    owned = {item_a_shirt, item_a_trousers}
    foreign = {item_b_shirt, item_b_trousers}
    for candidate in response.json()["recommendations"]:
        ids = set(candidate["item_ids"])
        assert ids.issubset(owned)
        assert ids.isdisjoint(foreign)


def test_empty_wardrobe_returns_wardrobe_empty(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "rec-empty@example.com")
    response = client.post(
        "/v1/recommendations",
        headers=headers,
        json={"occasion": "casual"},
    )
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "wardrobe_empty",
            "message": "No wardrobe items are available for recommendations.",
        }
    }


def test_insufficient_wardrobe_returns_empty_recommendations(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "rec-one@example.com")
    _add_item(client, headers, category="shirt")
    response = client.post(
        "/v1/recommendations",
        headers=headers,
        json={"occasion": "casual"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["occasion"] == "casual"
    assert body["recommendations"] == []


def test_invalid_occasion_returns_422(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "rec-invalid@example.com")
    response = client.post(
        "/v1/recommendations",
        headers=headers,
        json={"occasion": ""},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_unexpected_recommendation_fields_rejected(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "rec-extra@example.com")
    response = client.post(
        "/v1/recommendations",
        headers=headers,
        json={"occasion": "casual", "user_id": str(uuid4())},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_ranked_item_ids_belong_to_user(client: TestClient) -> None:
    user_id, headers = register_and_auth(client, "rec-rank@example.com")
    ids = {
        _add_item(client, headers, category="shirt"),
        _add_item(client, headers, category="trousers"),
        _add_item(client, headers, category="shoes", color="white"),
    }
    body = client.post(
        "/v1/recommendations",
        headers=headers,
        json={"occasion": "casual"},
    ).json()
    assert body["recommendations"]
    for candidate in body["recommendations"]:
        assert candidate["rationale"]
        for item_id in candidate["item_ids"]:
            assert item_id in ids
            UUID(item_id)
    listed = client.get("/v1/wardrobe", headers=headers).json()["wardrobe_items"]
    assert all(item["user_id"] == user_id for item in listed)


def test_recommendation_engine_does_not_need_storage() -> None:
    items = [
        WardrobeItemSignal(
            id=uuid4(),
            category="shirt",
            color="navy",
            brand="a",
            attributes={},
        ),
        WardrobeItemSignal(
            id=uuid4(),
            category="trousers",
            color="black",
            brand="b",
            attributes={},
        ),
    ]
    ranked = rank_outfits(items, "casual")
    assert ranked
    assert all(entry.rationale for entry in ranked)
    assert {str(item_id) for entry in ranked for item_id in entry.item_ids}.issubset(
        {str(item.id) for item in items}
    )


def test_existing_outfit_endpoints_unchanged(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "rec-outfit@example.com")
    shirt = _add_item(client, headers, category="shirt")
    created = client.post(
        "/v1/outfits",
        headers=headers,
        json={"occasion": "casual", "item_ids": [shirt], "rationale": {"note": "saved"}},
    )
    assert created.status_code == 200
    outfit_id = created.json()["id"]
    fetched = client.get(f"/v1/outfits/{outfit_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["item_ids"] == [shirt]
