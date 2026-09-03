from fastapi.testclient import TestClient

from tests.auth_helpers import register_and_auth


def _add(client: TestClient, headers: dict[str, str], category: str) -> None:
    response = client.post(
        "/v1/wardrobe",
        headers=headers,
        json={"category": category, "color": "black", "brand": "unbranded", "attributes": {}},
    )
    assert response.status_code == 200, response.text


def _gap_categories(client: TestClient, headers: dict[str, str]) -> set[str]:
    response = client.post("/v1/recommendations/gaps", headers=headers, json={})
    assert response.status_code == 200, response.text
    return {gap["category"] for gap in response.json()["gaps"]}


def test_a_dress_wardrobe_is_not_reported_as_missing_tops_and_bottoms(
    client: TestClient,
) -> None:
    _user_id, headers = register_and_auth(client, "dress-only@example.com")
    _add(client, headers, "dress")
    _add(client, headers, "heels")

    assert _gap_categories(client, headers) == set()


def test_previously_unrecognised_categories_now_close_gaps(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "modern@example.com")
    _add(client, headers, "polo")
    _add(client, headers, "leggings")
    _add(client, headers, "trainers")

    assert _gap_categories(client, headers) == set()


def test_outerwear_alone_does_not_satisfy_the_top_gap(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "coat-only@example.com")
    _add(client, headers, "blazer")
    _add(client, headers, "jeans")
    _add(client, headers, "boots")

    assert _gap_categories(client, headers) == {"top"}


def test_a_dress_still_reports_a_missing_shoe_gap(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "dress-noshoes@example.com")
    _add(client, headers, "jumpsuit")

    assert _gap_categories(client, headers) == {"shoes"}


def test_a_dress_produces_recommendations(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "dress-recs@example.com")
    _add(client, headers, "dress")
    _add(client, headers, "heels")

    response = client.post(
        "/v1/recommendations", headers=headers, json={"occasion": "dinner"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["recommendations"]
