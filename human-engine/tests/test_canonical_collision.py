"""The body's rigid volumes.

These exist so a pose cannot drive a limb through the trunk. Joint limits alone
cannot catch that: every angle can sit inside its clinical range while the arm
ends up inside the ribs.
"""

from __future__ import annotations

import numpy as np
import pytest

from sveyra_human.body.figures import figure
from sveyra_human.body.parameters import BodyParameters
from sveyra_human.canonical.collision import (
    HAND_ROOTS,
    LIMB_PREFIXES,
    TRUNK_PREFIXES,
    Capsule,
    body_volumes,
    penetration_cm,
    segment_distance,
)
from sveyra_human.canonical.deformation import deform_canonical_human


@pytest.fixture(scope="module")
def volumes():
    body, rig, _ = deform_canonical_human(figure("man"))
    return body_volumes(body, rig)


def test_every_body_region_gets_a_volume(volumes):
    trunk = {c.bone for c in volumes["trunk"]}
    limb = {c.bone for c in volumes["limb"]}
    assert any(name.startswith("spine") for name in trunk)
    assert any(name.startswith("pelvis") for name in trunk)
    assert any(name.startswith("lowerarm") for name in limb)
    assert any(name.startswith("lowerleg") for name in limb)
    assert set(HAND_ROOTS) <= limb
    assert not trunk & limb


def test_only_the_distal_limb_is_tested_against_the_trunk(volumes):
    """A deltoid sits inside the torso's silhouette and a hip inside the pelvis.

    Including them means the body always collides with itself and even standing
    still gets held back, so the proximal segment of each limb is left out.
    """
    limb = {c.bone for c in volumes["limb"]}
    assert not any(name.startswith(("upperarm01", "upperleg01")) for name in limb)
    assert any(name.startswith("upperarm02") for name in limb)


def test_radii_are_a_body_and_not_a_stick(volumes):
    for capsule in volumes["trunk"] + volumes["limb"]:
        assert 0.5 < capsule.radius_cm < 30.0, capsule.bone
        assert capsule.length_cm > 0.0


def test_rest_overlap_is_real_and_must_be_calibrated_away(volumes):
    """Some capsules overlap at rest, and a consumer has to allow for it.

    A thigh abuts the lower spine at the hip, so it reads about seven
    centimetres inside. That is anatomy, not a fault, and it is why the rule
    cannot be "no overlap": a caller measures the rest state once and judges a
    pose by how much deeper than that it goes.
    """
    at_rest = {
        (limb.bone, trunk.bone): penetration_cm(limb, trunk)
        for limb in volumes["limb"]
        for trunk in volumes["trunk"]
    }
    overlapping = {k: v for k, v in at_rest.items() if v > 0.0}
    assert overlapping, "nothing overlaps at rest, so the baseline would be untested"
    assert max(overlapping.values()) < 15.0, "an overlap this deep is a bad capsule"

    # Every one of them is between a limb and something near it in the body,
    # never a hand inside a head.
    for (limb, trunk), depth in overlapping.items():
        assert limb.startswith(("upperleg", "lowerleg", "upperarm")), (limb, trunk, depth)


def test_penetration_is_measured_not_merely_detected():
    a = Capsule("a", np.array([0.0, 0.0, 0.0]), np.array([10.0, 0.0, 0.0]), 3.0)
    b = Capsule("b", np.array([5.0, 4.0, 0.0]), np.array([5.0, 14.0, 0.0]), 3.0)
    # Centres are 4 apart, radii sum to 6, so they overlap by 2.
    assert penetration_cm(a, b) == pytest.approx(2.0, abs=0.05)

    far = Capsule("c", np.array([5.0, 40.0, 0.0]), np.array([5.0, 50.0, 0.0]), 3.0)
    assert penetration_cm(a, far) == 0.0


def test_segment_distance_handles_parallel_and_crossing():
    origin = np.array([0.0, 0.0, 0.0])
    along_x = np.array([10.0, 0.0, 0.0])
    assert segment_distance(origin, along_x, origin + 5.0, along_x + 5.0) > 0.0

    # Two segments that cross at right angles touch exactly.
    a0, a1 = np.array([-5.0, 0.0, 0.0]), np.array([5.0, 0.0, 0.0])
    b0, b1 = np.array([0.0, -5.0, 0.0]), np.array([0.0, 5.0, 0.0])
    assert segment_distance(a0, a1, b0, b1) == pytest.approx(0.0, abs=1e-9)


def test_segment_distance_handles_point_capsules():
    point = np.array([0.0, 0.0, 0.0])
    line_start = np.array([2.0, -4.0, 0.0])
    line_end = np.array([2.0, 4.0, 0.0])
    assert segment_distance(point, point, line_start, line_end) == pytest.approx(2.0)
    assert segment_distance(line_start, line_end, point, point) == pytest.approx(2.0)


def test_volumes_follow_the_body_they_were_built_from():
    """A child's volumes are its own, not an adult's scaled down."""
    sizes = {}
    for kind in ("man", "child"):
        body, rig, _ = deform_canonical_human(figure(kind))
        capsules = body_volumes(body, rig)["trunk"]
        sizes[kind] = max(c.radius_cm for c in capsules)
    assert sizes["child"] < sizes["man"]


def test_trunk_boundary_adapts_to_photo_fitted_depth():
    shallow = BodyParameters(height=178.0, chest_depth=16.0, waist_depth=15.0)
    deep = BodyParameters(height=178.0, chest_depth=28.0, waist_depth=25.0)
    radii = []
    for params in (shallow, deep):
        body, rig, _ = deform_canonical_human(params)
        radii.append(max(c.radius_cm for c in body_volumes(body, rig)["trunk"]))
    assert radii[1] > radii[0]


def test_runtime_capsule_coordinates_are_bone_local(volumes):
    hand = next(c for c in volumes["limb"] if c.bone == "wrist.L")
    _body, rig, _report = deform_canonical_human(figure("man"))
    bone = next(b for b in rig.bones if b.name == hand.bone)
    payload = hand.to_bone_local_dict(np.asarray(bone.head_cm))

    assert payload["space"] == "bone-local"
    assert np.allclose(
        np.asarray(payload["head"]) + np.asarray(bone.head_cm),
        hand.head_cm,
        atol=1e-4,
    )
    # This catches the original viewer bug: model-space data was parented to
    # the bone and the bind translation was therefore applied twice.
    assert not np.allclose(payload["head"], hand.head_cm)


def test_the_prefix_lists_do_not_overlap():
    for limb in LIMB_PREFIXES:
        assert not limb.startswith(TRUNK_PREFIXES)
