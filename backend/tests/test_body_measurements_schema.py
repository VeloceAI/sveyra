from fastapi.testclient import TestClient

from tests.auth_helpers import register_and_auth


def test_named_measurements_round_trip(client: TestClient) -> None:
    user_id, headers = register_and_auth(client, "measure@example.com")
    response = client.post(
        f"/v1/profile/{user_id}/body",
        headers=headers,
        json={
            "measurements": {"height_cm": 178.5, "waist_cm": 82, "inseam_cm": 81},
            "fit_preferences": {"ease": "regular"},
        },
    )
    assert response.status_code == 200
    assert response.json()["measurements"] == {
        "height_cm": 178.5,
        "waist_cm": 82.0,
        "inseam_cm": 81.0,
    }


def test_unset_measurements_are_not_stored_as_nulls(client: TestClient) -> None:
    user_id, headers = register_and_auth(client, "sparse@example.com")
    response = client.post(
        f"/v1/profile/{user_id}/body",
        headers=headers,
        json={"measurements": {"height_cm": 165}, "fit_preferences": {}},
    )
    assert response.json()["measurements"] == {"height_cm": 165.0}


def test_free_form_measurement_keys_still_round_trip(client: TestClient) -> None:
    user_id, headers = register_and_auth(client, "notes@example.com")
    response = client.post(
        f"/v1/profile/{user_id}/body",
        headers=headers,
        json={"measurements": {"notes": "standing relaxed"}, "fit_preferences": {}},
    )
    assert response.json()["measurements"] == {"notes": "standing relaxed"}


def test_impossible_measurements_are_rejected(client: TestClient) -> None:
    user_id, headers = register_and_auth(client, "impossible@example.com")
    for bad in ({"height_cm": -5}, {"height_cm": 0}, {"weight_kg": 100000}):
        response = client.post(
            f"/v1/profile/{user_id}/body",
            headers=headers,
            json={"measurements": bad, "fit_preferences": {}},
        )
        assert response.status_code == 422, bad
