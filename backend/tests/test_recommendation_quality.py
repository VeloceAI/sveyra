from uuid import uuid4

from fastapi.testclient import TestClient

from app.services.recommendation_engine import WardrobeItemSignal, rank_outfits
from app.storage.memory import InMemoryStorage
from tests.auth_helpers import register_and_auth


def _add_item(
    client: TestClient,
    headers: dict[str, str],
    *,
    category: str,
    color: str = "navy",
    brand: str = "unbranded",
    attributes: dict[str, object] | None = None,
) -> str:
    response = client.post(
        "/v1/wardrobe",
        headers=headers,
        json={
            "category": category,
            "color": color,
            "brand": brand,
            "attributes": attributes or {},
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_cv_occasion_tags_influence_ranking(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "m19-cv@example.com")
    formal_shirt = _add_item(
        client,
        headers,
        category="shirt",
        color="white",
        attributes={
            "cv": {
                "occasion_tags": ["formal"],
                "pattern": "solid",
                "material": "cotton",
                "silhouette": "regular",
            }
        },
    )
    casual_shirt = _add_item(
        client,
        headers,
        category="shirt",
        color="red",
        attributes={"cv": {"occasion_tags": ["casual"], "pattern": "graphic"}},
    )
    trousers = _add_item(client, headers, category="trousers", color="black")

    body = client.post(
        "/v1/recommendations",
        headers=headers,
        json={"occasion": "formal"},
    ).json()
    assert body["recommendations"]
    top = body["recommendations"][0]
    assert formal_shirt in top["item_ids"]
    assert casual_shirt not in top["item_ids"] or top["item_ids"].index(formal_shirt) == 0
    assert trousers in top["item_ids"]
    assert "formal" in top["rationale"].lower() or "cv" in top["rationale"].lower()
    assert top["rationale"].strip()


def test_style_preferences_influence_ranking(client: TestClient) -> None:
    user_id, headers = register_and_auth(client, "m19-style@example.com")
    client.post(
        "/v1/profile",
        headers=headers,
        json={
            "preferences": {"style": "minimal"},
            "dislikes": {},
            "budget": {},
        },
    )
    minimal_shirt = _add_item(
        client,
        headers,
        category="shirt",
        color="black",
        attributes={"style": "minimal", "cv": {"pattern": "solid"}},
    )
    loud_shirt = _add_item(
        client,
        headers,
        category="shirt",
        color="orange",
        attributes={"style": "bold"},
    )
    trousers = _add_item(client, headers, category="trousers", color="gray")

    body = client.post(
        "/v1/recommendations",
        headers=headers,
        json={"occasion": "work"},
    ).json()
    top_ids = set(body["recommendations"][0]["item_ids"])
    assert minimal_shirt in top_ids
    assert trousers in top_ids
    assert "minimal" in body["recommendations"][0]["rationale"].lower()
    assert loud_shirt not in top_ids or body["recommendations"][0]["item_ids"][0] == minimal_shirt


def test_dislikes_reduce_unsuitable_recommendations(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "m19-dislike@example.com")
    client.post(
        "/v1/profile",
        headers=headers,
        json={
            "preferences": {},
            "dislikes": {"prints": "loud"},
            "budget": {},
        },
    )
    clean_shirt = _add_item(
        client,
        headers,
        category="shirt",
        color="navy",
        attributes={"cv": {"pattern": "solid"}},
    )
    loud_shirt = _add_item(
        client,
        headers,
        category="shirt",
        color="yellow",
        attributes={"cv": {"pattern": "loud"}, "style": "loud"},
    )
    _add_item(client, headers, category="trousers", color="black")

    body = client.post(
        "/v1/recommendations",
        headers=headers,
        json={"occasion": "casual"},
    ).json()
    ranked = body["recommendations"]
    assert ranked
    first_ids = set(ranked[0]["item_ids"])
    assert clean_shirt in first_ids
    assert loud_shirt not in first_ids
    assert "dislike" in ranked[0]["rationale"].lower() or "avoid" in ranked[0]["rationale"].lower()


def test_fit_preferences_when_present_and_absent(client: TestClient) -> None:
    user_id, headers = register_and_auth(client, "m19-fit@example.com")
    shirt = _add_item(
        client,
        headers,
        category="shirt",
        attributes={"fit": "relaxed", "cv": {"silhouette": "relaxed"}},
    )
    trousers = _add_item(client, headers, category="trousers", color="black")

    without = client.post(
        "/v1/recommendations",
        headers=headers,
        json={"occasion": "casual"},
    )
    assert without.status_code == 200
    assert without.json()["recommendations"]
    assert without.json()["recommendations"][0]["rationale"].strip()

    client.post(
        f"/v1/profile/{user_id}/body",
        headers=headers,
        json={"measurements": {}, "fit_preferences": {"ease": "relaxed"}},
    )
    with_fit = client.post(
        "/v1/recommendations",
        headers=headers,
        json={"occasion": "casual"},
    )
    assert with_fit.status_code == 200
    rationale = with_fit.json()["recommendations"][0]["rationale"].lower()
    assert "fit" in rationale or "relaxed" in rationale
    assert shirt in with_fit.json()["recommendations"][0]["item_ids"]
    assert trousers in with_fit.json()["recommendations"][0]["item_ids"]


def test_ranking_is_deterministic() -> None:
    shirt_id = uuid4()
    trousers_id = uuid4()
    items = [
        WardrobeItemSignal(
            id=shirt_id,
            category="shirt",
            color="navy",
            brand="a",
            attributes={"cv": {"occasion_tags": ["casual"], "pattern": "solid"}},
        ),
        WardrobeItemSignal(
            id=trousers_id,
            category="trousers",
            color="black",
            brand="b",
            attributes={},
        ),
        WardrobeItemSignal(
            id=uuid4(),
            category="shirt",
            color="red",
            brand="c",
            attributes={"cv": {"occasion_tags": ["party"]}},
        ),
    ]
    first = rank_outfits(
        items,
        "casual",
        preferences={"style": "minimal"},
        dislikes={"prints": "loud"},
        budget={"max": 100},
        fit_preferences={"ease": "regular"},
    )
    second = rank_outfits(
        items,
        "casual",
        preferences={"style": "minimal"},
        dislikes={"prints": "loud"},
        budget={"max": 100},
        fit_preferences={"ease": "regular"},
    )
    assert [(r.item_ids, r.score, r.rationale) for r in first] == [
        (r.item_ids, r.score, r.rationale) for r in second
    ]
    assert all(entry.rationale.strip() for entry in first)


def test_rationale_is_signal_backed_and_safe() -> None:
    ranked = rank_outfits(
        [
            WardrobeItemSignal(
                id=uuid4(),
                category="shirt",
                color="navy",
                brand="house",
                attributes={
                    "cv": {
                        "occasion_tags": ["work"],
                        "pattern": "solid",
                        "material": "wool",
                    },
                    "style": "minimal",
                },
            ),
            WardrobeItemSignal(
                id=uuid4(),
                category="trousers",
                color="gray",
                brand="house",
                attributes={"fit": "regular"},
            ),
        ],
        "work",
        preferences={"style": "minimal"},
        fit_preferences={"ease": "regular"},
    )
    assert ranked
    text = ranked[0].rationale.lower()
    assert text
    assert "work" in text or "minimal" in text or "fit" in text or "balanced" in text
    assert "http://" not in text
    assert "gs://" not in text
    assert "memory://" not in text


def test_recommend_does_not_call_storage(client: TestClient) -> None:
    class SpyStorage(InMemoryStorage):
        def __init__(self) -> None:
            super().__init__()
            self.get_calls = 0
            self.put_calls = 0

        def get(self, reference: str) -> bytes:
            self.get_calls += 1
            return super().get(reference)

        def put(self, data: bytes) -> str:
            self.put_calls += 1
            return super().put(data)

    spy = SpyStorage()
    client.app.state.storage = spy
    _user_id, headers = register_and_auth(client, "m19-nostore@example.com")
    _add_item(client, headers, category="shirt")
    _add_item(client, headers, category="trousers")
    response = client.post(
        "/v1/recommendations",
        headers=headers,
        json={"occasion": "casual"},
    )
    assert response.status_code == 200
    assert spy.get_calls == 0
    assert spy.put_calls == 0
    assert "gs://" not in response.text.lower()
    assert "memory://" not in response.text.lower()
