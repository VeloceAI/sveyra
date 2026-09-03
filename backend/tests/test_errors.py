from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import create_app


def test_missing_route_uses_error_envelope() -> None:
    app = create_app()
    assert app.state.settings is settings
    client = TestClient(app)
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "The requested resource was not found.",
        }
    }


def test_validation_error_uses_error_envelope(client: TestClient) -> None:
    response = client.post("/v1/auth/register", json={"email": "bad", "password": "x"})
    assert response.status_code == 422
    body = response.json()
    assert set(body.keys()) == {"error"}
    assert body["error"]["code"] == "validation_error"
    assert isinstance(body["error"]["message"], str)
    assert body["error"]["message"]
