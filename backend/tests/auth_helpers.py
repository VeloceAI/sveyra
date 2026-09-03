from fastapi.testclient import TestClient

TEST_PASSWORD = "password12"


def register_and_auth(client: TestClient, email: str) -> tuple[str, dict[str, str]]:
    registered = client.post(
        "/v1/auth/register",
        json={"email": email, "password": TEST_PASSWORD},
    )
    assert registered.status_code == 200, registered.text
    user_id = registered.json()["id"]
    login = client.post(
        "/v1/auth/login",
        json={"email": email, "password": TEST_PASSWORD},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    assert "password" not in login.json()
    return user_id, {"Authorization": f"Bearer {token}"}
