"""The style calendar: what was worn, what is planned, and what never gets used."""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.auth_helpers import register_and_auth

TODAY = date.today().isoformat()


def _item(client: TestClient, headers: dict[str, str], category: str = "shirt") -> str:
    return client.post(
        "/v1/wardrobe",
        headers=headers,
        json={"category": category, "color": "navy", "brand": "unbranded", "attributes": {}},
    ).json()["id"]


def test_a_day_can_be_logged(client: TestClient) -> None:
    user_id, headers = register_and_auth(client, "cal-log@example.com")
    item = _item(client, headers)

    response = client.post(
        "/v1/calendar",
        headers=headers,
        json={"worn_on": TODAY, "item_ids": [item], "occasion": "work"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["worn_on"] == TODAY
    assert body["item_ids"] == [item]
    assert body["planned"] is False
    assert body["user_id"] == user_id


def test_logging_the_same_day_twice_replaces_it(client: TestClient) -> None:
    """A calendar cell holds one outfit; changing your mind must not need a delete."""
    _user_id, headers = register_and_auth(client, "cal-replace@example.com")
    first, second = _item(client, headers), _item(client, headers, "jacket")

    client.post("/v1/calendar", headers=headers, json={"worn_on": TODAY, "item_ids": [first]})
    client.post("/v1/calendar", headers=headers, json={"worn_on": TODAY, "item_ids": [second]})

    listed = client.get("/v1/calendar", headers=headers).json()
    assert listed["total"] == 1
    assert listed["entries"][0]["item_ids"] == [second]


def test_a_future_day_can_be_planned(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "cal-plan@example.com")
    future = (date.today() + timedelta(days=3)).isoformat()

    response = client.post(
        "/v1/calendar", headers=headers, json={"worn_on": future, "planned": True}
    )
    assert response.status_code == 200
    assert response.json()["planned"] is True


def test_entries_are_listed_in_date_order(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "cal-order@example.com")
    for offset in (2, 0, 1):
        day = (date.today() + timedelta(days=offset)).isoformat()
        client.post("/v1/calendar", headers=headers, json={"worn_on": day})

    dates = [e["worn_on"] for e in client.get("/v1/calendar", headers=headers).json()["entries"]]
    assert dates == sorted(dates)


def test_the_range_can_be_narrowed(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "cal-range@example.com")
    inside = (date.today() + timedelta(days=1)).isoformat()
    outside = (date.today() + timedelta(days=20)).isoformat()
    for day in (inside, outside):
        client.post("/v1/calendar", headers=headers, json={"worn_on": day})

    listed = client.get(
        "/v1/calendar",
        headers=headers,
        params={"start": inside, "end": inside},
    ).json()
    assert listed["total"] == 1
    assert listed["entries"][0]["worn_on"] == inside


def test_an_entry_can_be_removed(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "cal-del@example.com")
    client.post("/v1/calendar", headers=headers, json={"worn_on": TODAY})

    assert client.delete(f"/v1/calendar/{TODAY}", headers=headers).status_code == 204
    assert client.get("/v1/calendar", headers=headers).json()["total"] == 0


def test_removing_a_day_that_was_never_logged_is_a_404(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "cal-missing@example.com")
    response = client.delete(f"/v1/calendar/{TODAY}", headers=headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "wear_log_not_found"


def test_logging_an_item_you_do_not_own_is_refused(client: TestClient) -> None:
    _a, headers_a = register_and_auth(client, "cal-own-a@example.com")
    _b, headers_b = register_and_auth(client, "cal-own-b@example.com")
    theirs = _item(client, headers_b)

    response = client.post(
        "/v1/calendar", headers=headers_a, json={"worn_on": TODAY, "item_ids": [theirs]}
    )
    assert response.status_code == 404


def test_logging_an_outfit_you_do_not_own_is_refused(client: TestClient) -> None:
    _a, headers_a = register_and_auth(client, "cal-outfit-a@example.com")
    _b, headers_b = register_and_auth(client, "cal-outfit-b@example.com")
    theirs = client.post(
        "/v1/outfits", headers=headers_b, json={"occasion": "work", "item_ids": []}
    ).json()["id"]

    response = client.post(
        "/v1/calendar", headers=headers_a, json={"worn_on": TODAY, "outfit_id": theirs}
    )
    assert response.status_code == 404


def test_one_calendar_does_not_leak_into_another(client: TestClient) -> None:
    _a, headers_a = register_and_auth(client, "cal-leak-a@example.com")
    _b, headers_b = register_and_auth(client, "cal-leak-b@example.com")
    client.post("/v1/calendar", headers=headers_a, json={"worn_on": TODAY})

    assert client.get("/v1/calendar", headers=headers_b).json()["total"] == 0


def test_the_calendar_requires_authentication(client: TestClient) -> None:
    assert client.get("/v1/calendar").status_code == 401
    assert client.post("/v1/calendar", json={"worn_on": TODAY}).status_code == 401


# -- usage ---------------------------------------------------------------


def test_usage_counts_what_gets_worn(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "cal-usage@example.com")
    favourite = _item(client, headers)
    for offset in range(3):
        day = (date.today() - timedelta(days=offset)).isoformat()
        client.post("/v1/calendar", headers=headers, json={"worn_on": day, "item_ids": [favourite]})

    usage = client.get("/v1/calendar/usage", headers=headers).json()
    assert usage["logged_days"] == 3
    assert usage["most_worn"][0] == {"item_id": favourite, "times_worn": 3}


def test_usage_surfaces_what_is_never_worn(client: TestClient) -> None:
    """A wardrobe's dead weight is invisible until something counts it."""
    _user_id, headers = register_and_auth(client, "cal-dead@example.com")
    worn = _item(client, headers)
    ignored = _item(client, headers, "jacket")
    client.post("/v1/calendar", headers=headers, json={"worn_on": TODAY, "item_ids": [worn]})

    usage = client.get("/v1/calendar/usage", headers=headers).json()
    assert usage["never_worn_item_ids"] == [ignored]


def test_usage_on_an_empty_calendar_is_not_an_error(client: TestClient) -> None:
    _user_id, headers = register_and_auth(client, "cal-empty@example.com")
    usage = client.get("/v1/calendar/usage", headers=headers).json()
    assert usage == {"most_worn": [], "never_worn_item_ids": [], "logged_days": 0}
