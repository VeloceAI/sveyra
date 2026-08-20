from fastapi.testclient import TestClient

from tests.auth_helpers import register_and_auth

GAPS_URL = "/v1/recommendations/gaps"


def _add_item(
    client: TestClient,
    headers: dict[str, str],
    *,
    category: str,
    color: str = "black",
    brand: str = "unbranded",
) -> str:
    response = client.post(
        "/v1/wardrobe",
        headers=headers,
        json={"category": category, "color": color, "brand": brand, "attributes": {}},
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


# ---------------------------------------------------------------------------
# 1. Complete wardrobe (top + bottom + shoes) → no gaps
# ---------------------------------------------------------------------------


def test_complete_wardrobe_returns_no_gaps(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "gap-complete@example.com")
    _add_item(client, headers, category="shirt")
    _add_item(client, headers, category="trousers")
    _add_item(client, headers, category="shoes")

    response = client.post(GAPS_URL, headers=headers, json={})

    assert response.status_code == 200
    body = response.json()
    assert body["gaps"] == []


# ---------------------------------------------------------------------------
# 2. Missing top → top gap reported
# ---------------------------------------------------------------------------


def test_missing_top_returns_top_gap(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "gap-no-top@example.com")
    _add_item(client, headers, category="trousers")
    _add_item(client, headers, category="shoes")

    response = client.post(GAPS_URL, headers=headers, json={})

    assert response.status_code == 200
    gaps = response.json()["gaps"]
    categories = [g["category"] for g in gaps]
    assert categories == ["top"]
    assert gaps[0]["priority"] == "high"
    assert gaps[0]["reason"]


# ---------------------------------------------------------------------------
# 3. Missing bottom → bottom gap reported
# ---------------------------------------------------------------------------


def test_missing_bottom_returns_bottom_gap(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "gap-no-bottom@example.com")
    _add_item(client, headers, category="shirt")
    _add_item(client, headers, category="sneakers")

    response = client.post(GAPS_URL, headers=headers, json={})

    assert response.status_code == 200
    gaps = response.json()["gaps"]
    categories = [g["category"] for g in gaps]
    assert categories == ["bottom"]
    assert gaps[0]["priority"] == "high"
    assert gaps[0]["reason"]


# ---------------------------------------------------------------------------
# 4. Missing shoes → shoes gap reported
# ---------------------------------------------------------------------------


def test_missing_shoes_returns_shoes_gap(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "gap-no-shoes@example.com")
    _add_item(client, headers, category="blouse")
    _add_item(client, headers, category="jeans")

    response = client.post(GAPS_URL, headers=headers, json={})

    assert response.status_code == 200
    gaps = response.json()["gaps"]
    categories = [g["category"] for g in gaps]
    assert categories == ["shoes"]
    assert gaps[0]["priority"] == "high"
    assert gaps[0]["reason"]


# ---------------------------------------------------------------------------
# 5. Empty wardrobe → all three gaps, HTTP 200
# ---------------------------------------------------------------------------


def test_empty_wardrobe_returns_all_gaps_with_200(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "gap-empty@example.com")

    response = client.post(GAPS_URL, headers=headers, json={})

    assert response.status_code == 200
    gaps = response.json()["gaps"]
    categories = [g["category"] for g in gaps]
    assert set(categories) == {"top", "bottom", "shoes"}
    assert len(categories) == 3
    for gap in gaps:
        assert gap["priority"] == "high"
        assert gap["reason"]


# ---------------------------------------------------------------------------
# 6. User isolation: user A's wardrobe does not influence user B's result
# ---------------------------------------------------------------------------


def test_gap_analysis_is_isolated_per_user(client: TestClient) -> None:
    _user_a, headers_a = register_and_auth(client, "gap-user-a@example.com")
    _user_b, headers_b = register_and_auth(client, "gap-user-b@example.com")

    # User A has a full wardrobe.
    _add_item(client, headers_a, category="shirt")
    _add_item(client, headers_a, category="trousers")
    _add_item(client, headers_a, category="shoes")

    # User B has an empty wardrobe.
    response_b = client.post(GAPS_URL, headers=headers_b, json={})

    assert response_b.status_code == 200
    categories_b = [g["category"] for g in response_b.json()["gaps"]]
    assert set(categories_b) == {"top", "bottom", "shoes"}

    # User A should still have no gaps despite user B being present in the DB.
    response_a = client.post(GAPS_URL, headers=headers_a, json={})
    assert response_a.status_code == 200
    assert response_a.json()["gaps"] == []


# ---------------------------------------------------------------------------
# 7. Missing JWT → 401
# ---------------------------------------------------------------------------


def test_unauthenticated_gaps_returns_401(client: TestClient) -> None:
    response = client.post(GAPS_URL, json={})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


# ---------------------------------------------------------------------------
# 8. Error envelope is consistent (unexpected request field → 422)
# ---------------------------------------------------------------------------


def test_unexpected_gap_request_field_rejected(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "gap-strict@example.com")

    response = client.post(GAPS_URL, headers=headers, json={"user_id": "some-id"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
