from fastapi.testclient import TestClient

from tests.auth_helpers import register_and_auth


def test_second_user_cannot_claim_another_users_reference(client: TestClient) -> None:
    _alice, alice_headers = register_and_auth(client, "ref-alice@example.com")
    _bob, bob_headers = register_and_auth(client, "ref-bob@example.com")

    uploaded = client.post(
        "/v1/media/upload",
        headers=alice_headers,
        files={"file": ("a.png", b"alice-bytes", "image/png")},
    )
    assert uploaded.status_code == 200
    alice_reference = uploaded.json()["reference"]

    claimed = client.post(
        "/v1/media",
        headers=bob_headers,
        json={"reference": alice_reference},
    )
    assert claimed.status_code == 409
    assert claimed.json() == {
        "error": {
            "code": "media_reference_already_claimed",
            "message": "That media reference is already registered.",
        }
    }


def test_alice_keeps_her_bytes_after_bob_attempts_a_claim(client: TestClient) -> None:
    _alice, alice_headers = register_and_auth(client, "ref-keep-a@example.com")
    _bob, bob_headers = register_and_auth(client, "ref-keep-b@example.com")

    uploaded = client.post(
        "/v1/media/upload",
        headers=alice_headers,
        files={"file": ("a.png", b"alice-bytes", "image/png")},
    ).json()

    client.post("/v1/media", headers=bob_headers, json={"reference": uploaded["reference"]})

    access = client.get(f"/v1/media/{uploaded['id']}/access", headers=alice_headers)
    assert access.status_code == 200


def test_same_user_cannot_register_one_reference_twice(client: TestClient) -> None:
    _user, headers = register_and_auth(client, "ref-dup@example.com")

    first = client.post("/v1/media", headers=headers, json={"reference": "storage/object-1"})
    second = client.post("/v1/media", headers=headers, json={"reference": "storage/object-1"})

    assert first.status_code == 200
    assert second.status_code == 409
