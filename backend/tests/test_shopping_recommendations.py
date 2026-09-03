from fastapi.testclient import TestClient

from tests.auth_helpers import register_and_auth

SHOPPING_URL = "/v1/recommendations/shopping"


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
# 1. Complete wardrobe (no gaps) → empty shopping list
# ---------------------------------------------------------------------------


def test_complete_wardrobe_returns_empty_shopping(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "shop-complete@example.com")
    _add_item(client, headers, category="shirt")
    _add_item(client, headers, category="trousers")
    _add_item(client, headers, category="shoes")

    response = client.post(SHOPPING_URL, headers=headers, json={})

    assert response.status_code == 200
    body = response.json()
    assert body["products"] == []


# ---------------------------------------------------------------------------
# 2. Empty wardrobe (all gaps) → recommendations for all categories
# ---------------------------------------------------------------------------


def test_empty_wardrobe_returns_all_categories(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "shop-empty@example.com")

    response = client.post(SHOPPING_URL, headers=headers, json={})

    assert response.status_code == 200
    products = response.json()["products"]
    assert len(products) > 0

    categories = {p["category"] for p in products}
    assert categories == {"top", "bottom", "shoes"}


# ---------------------------------------------------------------------------
# 3. Partial wardrobe (missing shoes) → only shoe recommendations
# ---------------------------------------------------------------------------


def test_partial_wardrobe_returns_only_gap_categories(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "shop-partial@example.com")
    _add_item(client, headers, category="shirt")
    _add_item(client, headers, category="trousers")

    response = client.post(SHOPPING_URL, headers=headers, json={})

    assert response.status_code == 200
    products = response.json()["products"]
    assert len(products) > 0

    categories = {p["category"] for p in products}
    assert categories == {"shoes"}


# ---------------------------------------------------------------------------
# 4. Budget max constraint → only products <= max
# ---------------------------------------------------------------------------


def test_shopping_respects_budget_max_limit(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "shop-budget-max@example.com")

    # Set budget constraint max = 50.0
    client.post(
        "/v1/profile",
        headers=headers,
        json={
            "preferences": {},
            "dislikes": {},
            "budget": {"max": 50.0},
        },
    )

    response = client.post(SHOPPING_URL, headers=headers, json={})

    assert response.status_code == 200
    products = response.json()["products"]
    assert len(products) > 0

    for p in products:
        assert p["price"] <= 50.0


# ---------------------------------------------------------------------------
# 5. Budget brands constraint → only products matching brand
# ---------------------------------------------------------------------------


def test_shopping_respects_budget_brands(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "shop-budget-brand@example.com")

    # Set budget preferred brands
    client.post(
        "/v1/profile",
        headers=headers,
        json={
            "preferences": {},
            "dislikes": {},
            "budget": {"brands": ["Everlane", "Levi's"]},
        },
    )

    response = client.post(SHOPPING_URL, headers=headers, json={})

    assert response.status_code == 200
    products = response.json()["products"]
    assert len(products) > 0

    for p in products:
        assert p["brand"].lower() in {"everlane", "levi's"}


# ---------------------------------------------------------------------------
# 6. Unauthenticated requests → 401
# ---------------------------------------------------------------------------


def test_unauthenticated_shopping_returns_401(client: TestClient) -> None:
    response = client.post(SHOPPING_URL, json={})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


# ---------------------------------------------------------------------------
# 7. Request body validation (StrictRequestModel) → 422
# ---------------------------------------------------------------------------


def test_strict_shopping_request_rejects_extra_fields(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "shop-strict@example.com")

    response = client.post(SHOPPING_URL, headers=headers, json={"user_id": "hack"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
