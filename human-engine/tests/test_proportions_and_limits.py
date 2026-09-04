"""A swappable proportions source, and joints that behave like human ones."""

import math

import pytest

from sveyra_human import BodyParameters
from sveyra_human.body import (
    AnthropometricProportions,
    LearnedProportions,
    ProportionsSource,
    ScaledProportions,
)
from sveyra_human.skeleton import HINGES, LIMITS, clamp_pose, impossible_joints, limit_for

# -- the port ------------------------------------------------------------


def test_the_default_source_is_the_anthropometric_table() -> None:
    assert BodyParameters(height=178.0).waist_width == pytest.approx(178.0 * 0.160, rel=1e-6)


def test_a_source_can_be_swapped_in() -> None:
    heavy = BodyParameters(height=178.0, proportions=ScaledProportions(build=0.8))
    assert float(heavy.waist_width) > float(BodyParameters(height=178.0).waist_width)


def test_build_moves_soft_tissue_and_leaves_bone_alone() -> None:
    base = BodyParameters(height=178.0)
    heavy = BodyParameters(height=178.0, proportions=ScaledProportions(build=0.9))
    assert heavy.thigh_length == base.thigh_length
    assert heavy.upper_arm_length == base.upper_arm_length
    assert float(heavy.waist_width) > float(base.waist_width)


def test_build_can_be_derived_from_weight() -> None:
    slight = ScaledProportions().fractions(180.0, weight_kg=58.0)
    heavy = ScaledProportions().fractions(180.0, weight_kg=105.0)
    assert heavy["waist_width"] > slight["waist_width"]


def test_extreme_weights_are_clamped_to_something_human() -> None:
    absurd = ScaledProportions().fractions(180.0, weight_kg=400.0)
    assert absurd["waist_width"] < 0.160 * 1.4


def test_supplied_measurements_still_win_over_the_source() -> None:
    body = BodyParameters(height=178.0, waist_width=31.0, proportions=ScaledProportions(build=1.0))
    assert body.waist_width == 31.0


def test_the_source_is_behaviour_not_data() -> None:
    """A stored body must round-trip without carrying its generator."""
    body = BodyParameters(height=178.0, proportions=ScaledProportions(build=0.5))
    stored = body.to_dict()
    assert "proportions" not in stored
    assert BodyParameters.from_dict(stored).waist_width == body.waist_width


def test_the_learned_source_refuses_rather_than_inventing_one() -> None:
    with pytest.raises(NotImplementedError, match="SPRING"):
        LearnedProportions().fractions(178.0)


@pytest.mark.parametrize("source", [AnthropometricProportions(), ScaledProportions()])
def test_sources_satisfy_the_protocol(source) -> None:
    assert isinstance(source, ProportionsSource)
    assert source.fractions(178.0)["chest_width"] > 0


# -- joint limits --------------------------------------------------------


def test_an_elbow_does_not_extend_past_straight() -> None:
    """The failure that makes a rig look broken."""
    assert impossible_joints({"forearm_L": (0.9, 0.0, 0.0)}) == ["forearm_L"]
    assert clamp_pose({"forearm_L": (0.9, 0.0, 0.0)})["forearm_L"][0] == 0.0


def test_an_elbow_bends_the_way_it_should() -> None:
    bent = (-1.4, 0.0, 0.0)
    assert impossible_joints({"forearm_L": bent}) == []
    assert clamp_pose({"forearm_L": bent})["forearm_L"] == bent


def test_a_knee_bends_the_opposite_way_to_an_elbow() -> None:
    assert clamp_pose({"calf_L": (1.4, 0.0, 0.0)})["calf_L"][0] == pytest.approx(1.4)
    assert clamp_pose({"calf_L": (-1.0, 0.0, 0.0)})["calf_L"][0] == 0.0


@pytest.mark.parametrize("joint", sorted(HINGES))
def test_hinges_neither_twist_nor_splay(joint: str) -> None:
    limit = limit_for(joint)
    assert limit.twist == (0.0, 0.0)
    assert limit.abduct == (0.0, 0.0)


def test_a_shoulder_is_freer_than_an_elbow() -> None:
    shoulder = limit_for("upperarm_L")
    elbow = limit_for("forearm_L")
    span = lambda r: r[1] - r[0]  # noqa: E731
    assert span(shoulder.flex) > span(elbow.flex)
    assert span(shoulder.twist) > span(elbow.twist)


def test_limits_are_mirrored_left_to_right() -> None:
    for left, right in (("upperarm_L", "upperarm_R"), ("thigh_L", "thigh_R")):
        a, b = limit_for(left), limit_for(right)
        assert a.flex == b.flex
        assert a.abduct == (-b.abduct[1], -b.abduct[0])


def test_every_joint_range_is_ordered_and_plausible() -> None:
    for joint, limit in LIMITS.items():
        for name, span in (("flex", limit.flex), ("abduct", limit.abduct), ("twist", limit.twist)):
            assert span[0] <= span[1], f"{joint}.{name} is inverted"
            assert abs(span[0]) <= math.pi and abs(span[1]) <= math.pi, joint


def test_an_unknown_joint_passes_through_unconstrained() -> None:
    """Limits constrain a pose; they do not police the skeleton's contents."""
    pose = {"tail": (5.0, 5.0, 5.0)}
    assert clamp_pose(pose) == pose
    assert impossible_joints(pose) == []


def test_a_natural_standing_pose_breaks_nothing() -> None:
    pose = {
        "upperarm_L": (-0.3, 0.1, 0.4),
        "forearm_L": (-0.5, 0.0, 0.0),
        "thigh_R": (-0.2, 0.0, 0.1),
        "calf_R": (0.4, 0.0, 0.0),
        "head": (0.1, 0.2, 0.0),
    }
    assert impossible_joints(pose) == []
