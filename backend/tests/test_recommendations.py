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


def test_style_this_item_keeps_required_piece_in_every_look(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "rec-lock@example.com")
    locked_shirt = _add_item(client, headers, category="shirt", color="red")
    _add_item(client, headers, category="shirt", color="navy")
    _add_item(client, headers, category="trousers", color="black")
    _add_item(client, headers, category="shoes", color="white")

    response = client.post(
        "/v1/recommendations",
        headers=headers,
        json={"occasion": "dinner", "required_item_ids": [locked_shirt]},
    )

    assert response.status_code == 200
    recommendations = response.json()["recommendations"]
    assert recommendations
    assert all(locked_shirt in candidate["item_ids"] for candidate in recommendations)
    assert all("selected piece" in candidate["rationale"].lower() for candidate in recommendations)


def test_excluded_item_never_appears(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "rec-exclude@example.com")
    excluded_shirt = _add_item(client, headers, category="shirt", color="red")
    kept_shirt = _add_item(client, headers, category="shirt", color="white")
    trousers = _add_item(client, headers, category="trousers", color="black")

    response = client.post(
        "/v1/recommendations",
        headers=headers,
        json={"occasion": "work", "excluded_item_ids": [excluded_shirt]},
    )

    assert response.status_code == 200
    recommendations = response.json()["recommendations"]
    assert recommendations
    assert all(excluded_shirt not in candidate["item_ids"] for candidate in recommendations)
    assert {kept_shirt, trousers}.issubset(set(recommendations[0]["item_ids"]))


def test_swap_replaces_same_slot_and_preserves_other_items(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "rec-swap@example.com")
    old_shirt = _add_item(client, headers, category="shirt", color="red")
    new_shirt = _add_item(client, headers, category="shirt", color="white")
    trousers = _add_item(client, headers, category="trousers", color="black")
    shoes = _add_item(client, headers, category="shoes", color="black")

    response = client.post(
        "/v1/recommendations",
        headers=headers,
        json={
            "occasion": "work",
            "required_item_ids": [trousers, shoes],
            "replacement_item_id": old_shirt,
        },
    )

    assert response.status_code == 200
    recommendations = response.json()["recommendations"]
    assert recommendations
    for candidate in recommendations:
        assert old_shirt not in candidate["item_ids"]
        assert new_shirt in candidate["item_ids"]
        assert trousers in candidate["item_ids"]
        assert shoes in candidate["item_ids"]
        assert "replaces the selected top slot" in candidate["rationale"].lower()


def test_foreign_constraint_uses_safe_not_found_response(client: TestClient) -> None:
    _user_a, headers_a = register_and_auth(client, "rec-constraint-a@example.com")
    _user_b, headers_b = register_and_auth(client, "rec-constraint-b@example.com")
    _add_item(client, headers_a, category="shirt")
    _add_item(client, headers_a, category="trousers")
    foreign = _add_item(client, headers_b, category="shirt")

    response = client.post(
        "/v1/recommendations",
        headers=headers_a,
        json={"occasion": "casual", "required_item_ids": [foreign]},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "wardrobe_item_not_found"


def test_incompatible_required_slots_return_no_false_look(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "rec-conflict@example.com")
    dress = _add_item(client, headers, category="dress")
    shirt = _add_item(client, headers, category="shirt")
    _add_item(client, headers, category="trousers")

    response = client.post(
        "/v1/recommendations",
        headers=headers,
        json={
            "occasion": "party",
            "required_item_ids": [dress, shirt],
        },
    )

    assert response.status_code == 200
    assert response.json()["recommendations"] == []


def test_overlapping_item_constraints_are_rejected(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "rec-invalid-constraint@example.com")
    item_id = _add_item(client, headers, category="shirt")

    response = client.post(
        "/v1/recommendations",
        headers=headers,
        json={
            "occasion": "casual",
            "required_item_ids": [item_id],
            "excluded_item_ids": [item_id],
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


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
