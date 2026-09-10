from fastapi.testclient import TestClient

from tests.auth_helpers import register_and_auth


def test_platform_readiness_is_private(client: TestClient) -> None:
    response = client.get("/v1/platform/readiness")
    assert response.status_code == 401


def test_new_account_gets_one_coherent_next_action(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "readiness-new@example.com")
    response = client.get("/v1/platform/readiness", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["parity_phase"].startswith("P0")
    assert body["personal_model"] == {
        "style_ready": False,
        "appearance_ready": False,
        "body_ready": False,
        "body_measurement_count": 0,
        "wardrobe_items": 0,
        "enriched_items": 0,
        "core_completion_percent": 0,
        "next_action": {
            "label": "Set your style direction",
            "href": "/profile",
            "reason": (
                "A few preferences keep recommendations personal rather than generic."
            ),
        },
    }

    capabilities = {item["key"]: item for item in body["capabilities"]}
    assert capabilities["closet"]["status"] == "ready"
    assert capabilities["garment_vision"]["status"] == "demo"
    assert capabilities["stylist"]["status"] == "ready"
    assert capabilities["avatar"]["provider"] == "SVYERA Human Engine"
    assert capabilities["avatar"]["status"] == "ready"
    assert capabilities["visual_try_on"]["status"] == "setup_required"
    assert capabilities["metric_fit"]["status"] == "planned"


def test_readiness_progresses_from_style_to_closet_to_body(client: TestClient) -> None:
    user_id, headers = register_and_auth(client, "readiness-progress@example.com")

    style = client.post(
        "/v1/profile",
        headers=headers,
        json={
            "preferences": {"style": "minimal"},
            "dislikes": {},
            "budget": {"currency": "USD", "max": 200},
        },
    )
    assert style.status_code == 200, style.text
    after_style = client.get("/v1/platform/readiness", headers=headers).json()
    assert after_style["personal_model"]["core_completion_percent"] == 33
    assert after_style["personal_model"]["next_action"]["href"] == "/wardrobe/new"

    garment = client.post(
        "/v1/wardrobe",
        headers=headers,
        json={
            "category": "shirt",
            "color": "navy",
            "brand": "owned",
            "attributes": {},
        },
    )
    assert garment.status_code == 200, garment.text
    after_closet = client.get("/v1/platform/readiness", headers=headers).json()
    assert after_closet["personal_model"]["core_completion_percent"] == 67
    assert after_closet["personal_model"]["next_action"]["href"] == "/avatar"

    body_profile = client.post(
        f"/v1/profile/{user_id}/body",
        headers=headers,
        json={
            "measurements": {"height_cm": 178, "waist_cm": 78},
            "fit_preferences": {"ease": "regular"},
        },
    )
    assert body_profile.status_code == 200, body_profile.text
    ready = client.get("/v1/platform/readiness", headers=headers).json()
    assert ready["personal_model"]["core_completion_percent"] == 100
    assert ready["personal_model"]["body_measurement_count"] == 2
    assert ready["personal_model"]["next_action"]["href"] == "/appearance"
