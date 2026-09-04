"""The avatar endpoint: photographs in, a stored GLB out."""

import io
import struct

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from tests.auth_helpers import register_and_auth

pytest.importorskip("sveyra_human", reason="the human engine is not installed")


def photo_bytes(view: str = "front", height_cm: float = 178.0) -> bytes:
    """A synthetic photograph the engine can actually segment and fit."""
    from sveyra_human import BodyParameters, SveyraHumanEngine
    from sveyra_human.camera.projection import OrthographicCamera, rasterise_silhouette

    mesh = SveyraHumanEngine("draft").build_parametric(
        BodyParameters(height=height_cm, waist_width=34.0)
    )._mesh
    camera = OrthographicCamera.fit_to_height(view, height_cm, 220, 350)
    mask = rasterise_silhouette(mesh.vertices, mesh.faces, camera)

    rng = np.random.default_rng(4)
    image = np.clip(
        np.full((*mask.shape, 3), (208, 204, 197), dtype=float)
        + rng.normal(0, 5, (*mask.shape, 3)),
        0,
        255,
    )
    subject = np.clip(
        np.full((*mask.shape, 3), (62, 66, 84), dtype=float) + rng.normal(0, 7, (*mask.shape, 3)),
        0,
        255,
    )
    buffer = io.BytesIO()
    Image.fromarray(np.where(mask[:, :, None], subject, image).astype(np.uint8)).save(
        buffer, format="PNG"
    )
    return buffer.getvalue()


@pytest.fixture
def engine_client(sqlite_engine):
    """A client with the real 3D avatar backend rather than the stub."""
    from collections.abc import Generator

    from sqlalchemy.orm import Session, sessionmaker

    from app.avatar.sveyra_engine import SveyraEngineAvatar
    from app.db.session import get_db
    from app.main import create_app
    from app.storage.memory import InMemoryStorage

    factory = sessionmaker(bind=sqlite_engine, expire_on_commit=False)

    def override_get_db() -> Generator[Session, None, None]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    storage = InMemoryStorage()
    app = create_app(storage=storage, avatar=SveyraEngineAvatar(storage, "draft"))
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client


def test_photographs_produce_a_downloadable_glb(engine_client: TestClient) -> None:
    _user_id, headers = register_and_auth(engine_client, "avatar@example.com")

    response = engine_client.post(
        "/v1/avatar/build",
        headers=headers,
        data={"height_cm": "178"},
        files={
            "front": ("front.png", photo_bytes("front"), "image/png"),
            "side": ("side.png", photo_bytes("side"), "image/png"),
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["backend"] == "sveyra-3d"
    assert body["source_views"] == 2
    assert body["measurements"]["height_cm"] == 178.0
    assert body["confidence"]["overall"] > 0

    # The avatar is retrievable through the ordinary media route.
    access = engine_client.get(f"/v1/media/{body['asset_id']}/access", headers=headers)
    assert access.status_code == 200


def test_the_stored_avatar_is_a_real_glb(engine_client: TestClient) -> None:
    _user_id, headers = register_and_auth(engine_client, "glb@example.com")
    built = engine_client.post(
        "/v1/avatar/build",
        headers=headers,
        data={"height_cm": "180"},
        files={"front": ("front.png", photo_bytes("front", 180.0), "image/png")},
    ).json()

    storage = engine_client.app.state.storage
    reference = next(iter(storage._objects))
    payload = storage.get(reference)
    magic, version, length = struct.unpack("<III", payload[:12])
    assert magic == 0x46546C67 and version == 2
    assert length == len(payload)
    assert built["asset_id"]


def test_a_front_view_is_required(engine_client: TestClient) -> None:
    _user_id, headers = register_and_auth(engine_client, "noview@example.com")
    response = engine_client.post(
        "/v1/avatar/build", headers=headers, data={"height_cm": "180"}
    )
    assert response.status_code == 422


def test_an_unsegmentable_photograph_is_refused(engine_client: TestClient) -> None:
    """A flat frame contains no person and must not yield a default body."""
    _user_id, headers = register_and_auth(engine_client, "flat@example.com")
    buffer = io.BytesIO()
    Image.fromarray(np.full((350, 220, 3), 200, dtype=np.uint8)).save(buffer, format="PNG")

    response = engine_client.post(
        "/v1/avatar/build",
        headers=headers,
        data={"height_cm": "180"},
        files={"front": ("flat.png", buffer.getvalue(), "image/png")},
    )
    assert response.status_code in (422, 503)


def test_building_an_avatar_requires_authentication(engine_client: TestClient) -> None:
    response = engine_client.post(
        "/v1/avatar/build",
        data={"height_cm": "180"},
        files={"front": ("front.png", photo_bytes(), "image/png")},
    )
    assert response.status_code == 401


def test_the_stub_backend_admits_it_cannot_do_this(client: TestClient) -> None:
    """The default backend must say so rather than returning a fake avatar."""
    _user_id, headers = register_and_auth(client, "stub@example.com")
    response = client.post(
        "/v1/avatar/build",
        headers=headers,
        data={"height_cm": "180"},
        files={"front": ("front.png", photo_bytes(), "image/png")},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "avatar_unavailable"
