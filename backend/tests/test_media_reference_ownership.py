from fastapi.testclient import TestClient

from tests.auth_helpers import register_and_auth


def test_second_user_cannot_claim_another_users_reference(
    client: TestClient,
) -> None:
    _alice, alice_headers = register_and_auth(
        client,
        "ref-alice@example.com",
    )
    _bob, bob_headers = register_and_auth(
        client,
        "ref-bob@example.com",
    )

    uploaded = client.post(
        "/v1/media/upload",
        headers=alice_headers,
        files={"file": ("a.png", b"alice-bytes", "image/png")},
    )

    assert uploaded.status_code == 200
    asset_id = uploaded.json()["id"]
    assert "reference" not in uploaded.json()

    # The old client-supplied-reference endpoint no longer exists.
    claimed = client.post(
        "/v1/media",
        headers=bob_headers,
        json={"reference": "client-supplied-reference"},
    )

    assert claimed.status_code == 404

    # Bob cannot access Alice's media.
    access = client.get(
        f"/v1/media/{asset_id}/access",
        headers=bob_headers,
    )
    assert access.status_code == 404


def test_alice_keeps_her_bytes_after_bob_attempts_a_claim(
    client: TestClient,
) -> None:
    _alice, alice_headers = register_and_auth(
        client,
        "ref-keep-a@example.com",
    )
    _bob, bob_headers = register_and_auth(
        client,
        "ref-keep-b@example.com",
    )

    uploaded = client.post(
        "/v1/media/upload",
        headers=alice_headers,
        files={"file": ("a.png", b"alice-bytes", "image/png")},
    )

    assert uploaded.status_code == 200
    asset_id = uploaded.json()["id"]

    # Bob cannot access Alice's media.
    bob_access = client.get(
        f"/v1/media/{asset_id}/access",
        headers=bob_headers,
    )
    assert bob_access.status_code == 404

    # Alice still has access to her own media.
    alice_access = client.get(
        f"/v1/media/{asset_id}/access",
        headers=alice_headers,
    )
    assert alice_access.status_code == 200


def test_upload_response_does_not_expose_storage_reference(
    client: TestClient,
) -> None:
    _user, headers = register_and_auth(
        client,
        "ref-response@example.com",
    )

    response = client.post(
        "/v1/media/upload",
        headers=headers,
        files={"file": ("a.png", b"test-bytes", "image/png")},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["id"]
    assert body["user_id"]
    assert "reference" not in body