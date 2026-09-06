"""Collision proxies and the garment contract."""

import numpy as np
import pytest

from sveyra_human import BodyParameters, SveyraHumanEngine
from sveyra_human.garment import GarmentBodyInterface, SveyraBody
from sveyra_human.physics import Capsule, build_collision_body
from sveyra_human.skeleton.model import build_skeleton


@pytest.fixture
def body():
    params = BodyParameters(height=180.0)
    return params, build_skeleton(params)


def test_a_capsule_reports_inside_and_outside() -> None:
    capsule = Capsule("test", np.array([0.0, 0.0, 0.0]), np.array([0.0, 10.0, 0.0]), 2.0)
    assert capsule.contains(np.array([0.0, 5.0, 0.0]))
    assert capsule.contains(np.array([1.5, 5.0, 0.0]))
    assert not capsule.contains(np.array([5.0, 5.0, 0.0]))


def test_capsule_distance_is_signed() -> None:
    capsule = Capsule("test", np.array([0.0, 0.0, 0.0]), np.array([0.0, 10.0, 0.0]), 2.0)
    assert capsule.distance_to(np.array([0.0, 5.0, 0.0])) < 0
    assert capsule.distance_to(np.array([6.0, 5.0, 0.0])) == pytest.approx(4.0)


def test_a_degenerate_capsule_behaves_like_a_sphere() -> None:
    point = np.array([0.0, 0.0, 0.0])
    capsule = Capsule("dot", point, point.copy(), 3.0)
    assert capsule.contains(np.array([2.0, 0.0, 0.0]))
    assert not capsule.contains(np.array([4.0, 0.0, 0.0]))


def test_the_collision_body_stays_cheap(body) -> None:
    """Clothing must collide with a few dozen primitives, not 6,000 triangles."""
    params, skeleton = body
    collision = build_collision_body(params, skeleton)
    assert 5 <= len(collision) <= 100


def test_the_collision_body_contains_the_torso_and_not_open_space(body) -> None:
    params, skeleton = body
    collision = build_collision_body(params, skeleton)
    assert collision.contains(np.array([0.0, params.level_cm("chest"), 0.0]))
    assert not collision.contains(np.array([300.0, 100.0, 0.0]))


def test_collision_distance_grows_with_separation(body) -> None:
    params, skeleton = body
    collision = build_collision_body(params, skeleton)
    near = collision.distance_to(np.array([40.0, 100.0, 0.0]))
    far = collision.distance_to(np.array([200.0, 100.0, 0.0]))
    assert far > near > 0


def test_an_empty_collision_body_is_rejected() -> None:
    from sveyra_human.physics import CollisionBody

    with pytest.raises(ValueError):
        CollisionBody(capsules=[]).distance_to(np.array([0.0, 0.0, 0.0]))


def test_the_collision_body_serialises(body) -> None:
    params, skeleton = body
    payload = build_collision_body(params, skeleton).to_dict()
    assert payload and all(p["kind"] == "capsule" for p in payload)
    assert all({"name", "start", "end", "radius"} <= set(p) for p in payload)


# -- garment contract ----------------------------------------------------


def test_an_avatar_satisfies_the_garment_contract() -> None:
    artifact = SveyraHumanEngine("draft").build_parametric(BodyParameters(height=176.0))
    garment_body = artifact.as_garment_body()

    assert isinstance(garment_body, SveyraBody)
    assert isinstance(garment_body, GarmentBodyInterface)

    assert garment_body.get_collision_body()
    assert "chest_girth_cm" in garment_body.get_measurements()
    assert "joints" in garment_body.get_skeleton()
    assert garment_body.get_surface_mesh().vertex_count > 0


def test_the_garment_contract_admits_it_is_unposed() -> None:
    artifact = SveyraHumanEngine("draft").build_parametric(BodyParameters(height=176.0))
    pose = artifact.as_garment_body().get_pose()
    assert pose["posed"] is False


def test_the_collision_body_tracks_the_person(body) -> None:
    slim = BodyParameters(height=180.0, thigh_width=12.0)
    broad = BodyParameters(height=180.0, thigh_width=24.0)
    radius = {}
    for label, params in (("slim", slim), ("broad", broad)):
        collision = build_collision_body(params, build_skeleton(params))
        radius[label] = next(c.radius for c in collision.capsules if c.name == "thigh_L")
    assert radius["broad"] > radius["slim"]
