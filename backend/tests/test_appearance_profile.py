from fastapi.testclient import TestClient

from tests.auth_helpers import register_and_auth

APPEARANCE = {
    "skin": {
        "tone_hex": "#A86F55",
        "depth": "tan",
        "undertone": "warm",
        "sensitive": True,
    },
    "face": {"shape": "oval"},
    "eyes": {"color": "dark brown"},
    "hair": {
        "color": "black",
        "texture": "wavy",
        "chemically_treated": False,
    },
    "colour_analysis": {"contrast": "high"},
    "makeup": {
        "intensity": "polished",
        "finish": "satin",
        "focus": ["eyes"],
        "avoid": ["heavy fragrance"],
    },
    "evidence": {
        "source": "self_reported",
        "user_confirmed": True,
        "confidence": 1.0,
    },
}


def test_get_missing_appearance_returns_documented_404(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "appearance-missing@example.com")
    response = client.get("/v1/appearance", headers=headers)
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "appearance_profile_not_found",
            "message": "Appearance profile was not found.",
        }
    }


def test_put_and_get_appearance_with_palette(client: TestClient) -> None:
    user_id, headers = register_and_auth(client, "appearance@example.com")
    response = client.put("/v1/appearance", json=APPEARANCE, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == user_id
    assert body["skin"] == APPEARANCE["skin"]
    assert body["hair"] == APPEARANCE["hair"]
    assert body["evidence"] == APPEARANCE["evidence"]
    assert body["palette"]["title"] == "Warm tan palette"
    assert body["palette"]["metals"] == ["yellow gold", "bronze", "copper"]
    assert len(body["palette"]["best_colours"]) == 6
    assert len(body["palette"]["combinations"]) == 3
    assert "terracotta" in body["palette"]["makeup"]["cheeks"]
    assert body["created_at"]
    assert body["updated_at"]

    fetched = client.get("/v1/appearance", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]
    assert fetched.json()["palette"] == body["palette"]


def test_put_updates_the_single_profile_for_user(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "appearance-update@example.com")
    first = client.put("/v1/appearance", json=APPEARANCE, headers=headers).json()
    changed = {
        **APPEARANCE,
        "skin": {**APPEARANCE["skin"], "undertone": "cool"},
        "colour_analysis": {"contrast": "low"},
    }
    second = client.put("/v1/appearance", json=changed, headers=headers).json()
    assert second["id"] == first["id"]
    assert second["skin"]["undertone"] == "cool"
    assert second["palette"]["metals"] == ["silver", "white gold", "platinum"]
    assert "tonal combinations" in second["palette"]["combinations"][0]["guidance"]


def test_invalid_colour_and_unexpected_fields_are_rejected(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "appearance-invalid@example.com")
    invalid_colour = {
        **APPEARANCE,
        "skin": {**APPEARANCE["skin"], "tone_hex": "not-a-colour"},
    }
    response = client.put("/v1/appearance", json=invalid_colour, headers=headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"

    response = client.put(
        "/v1/appearance",
        json={**APPEARANCE, "identity_score": 0.99},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_appearance_is_private_to_authenticated_user(client: TestClient) -> None:
    _first_id, first_headers = register_and_auth(client, "appearance-a@example.com")
    _second_id, second_headers = register_and_auth(client, "appearance-b@example.com")
    created = client.put("/v1/appearance", json=APPEARANCE, headers=first_headers)
    assert created.status_code == 200
    response = client.get("/v1/appearance", headers=second_headers)
    assert response.status_code == 404
