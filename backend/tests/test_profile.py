from fastapi.testclient import TestClient

from app.main import create_app


def test_profile_summary() -> None:
    client = TestClient(create_app())
    response = client.get("/v1/profile/summary")
    assert response.status_code == 200
    assert response.json() == {
        "user_id": "demo",
        "style_words": ["minimal", "sharp", "comfortable"],
        "wardrobe_items": 0,
        "fit_profile_ready": False,
        "avatar_ready": False,
    }
