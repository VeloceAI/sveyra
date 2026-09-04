"""Changing a body without rebuilding the person."""

import numpy as np
import pytest

from sveyra_human import BodyParameters, SveyraHumanEngine
from sveyra_human.body import change_muscle, change_weight, interpolate, scale_measurement
from sveyra_human.body.anatomy import measurements

BASE = BodyParameters(height=178.0, waist_width=36.0, chest_width=40.0)


def waist_girth(params: BodyParameters) -> float:
    return measurements(params)["waist_girth_cm"]


# -- weight --------------------------------------------------------------


def test_losing_weight_narrows_the_waist() -> None:
    lighter, _ = change_weight(BASE, -10.0)
    assert waist_girth(lighter) < waist_girth(BASE)


def test_gaining_weight_widens_the_waist() -> None:
    heavier, _ = change_weight(BASE, 10.0)
    assert waist_girth(heavier) > waist_girth(BASE)


@pytest.mark.parametrize("kilograms", [-15.0, -5.0, 5.0, 15.0])
def test_the_response_matches_about_a_centimetre_of_girth_per_kilogram(
    kilograms: float,
) -> None:
    """The figure the model is calibrated against, so it must not drift."""
    changed, _ = change_weight(BASE, kilograms)
    per_kg = abs(waist_girth(changed) - waist_girth(BASE)) / abs(kilograms)
    assert 0.7 < per_kg < 1.4, per_kg


def test_weight_change_leaves_the_skeleton_alone() -> None:
    """Losing weight does not narrow a shoulder or shorten a leg."""
    lighter, _ = change_weight(BASE, -15.0)
    assert lighter.height == BASE.height
    assert lighter.shoulder_width == BASE.shoulder_width
    assert lighter.thigh_length == BASE.thigh_length
    assert lighter.ankle_width == BASE.ankle_width


def test_the_waist_moves_more_than_the_chest() -> None:
    """Weight is not uniform scaling; the abdomen carries most of it."""
    heavier, _ = change_weight(BASE, 12.0)
    waist_ratio = float(heavier.waist_width) / float(BASE.waist_width)
    chest_ratio = float(heavier.chest_width) / float(BASE.chest_width)
    assert waist_ratio > chest_ratio


def test_extreme_loss_cannot_shrink_a_body_to_nothing() -> None:
    """At some point a waist is bone and stops responding."""
    lighter, _ = change_weight(BASE, -200.0)
    assert float(lighter.waist_width) > float(BASE.waist_width) * 0.5


def test_a_large_change_is_flagged_as_a_sketch() -> None:
    _, report = change_weight(BASE, 45.0)
    assert any("rough sketch" in w for w in report.warnings)


def test_every_transform_admits_it_is_a_rule_of_thumb() -> None:
    for _, report in (change_weight(BASE, 5.0), change_muscle(BASE, 0.4)):
        assert any("rule of thumb" in w for w in report.warnings)


def test_the_report_names_what_changed() -> None:
    _, report = change_weight(BASE, 8.0)
    assert report.kind == "weight"
    assert "waist_width" in report.changed
    before, after = report.changed["waist_width"]
    assert after > before
    assert "changed" in report.to_dict()


# -- muscle --------------------------------------------------------------


def test_muscle_broadens_shoulders_and_arms() -> None:
    stronger, _ = change_muscle(BASE, 0.8)
    assert float(stronger.shoulder_width) > float(BASE.shoulder_width)
    assert float(stronger.upper_arm_radius) > float(BASE.upper_arm_radius)


def test_muscle_barely_touches_the_waist() -> None:
    stronger, _ = change_muscle(BASE, 0.8)
    shoulder_ratio = float(stronger.shoulder_width) / float(BASE.shoulder_width)
    waist_ratio = float(stronger.waist_width) / float(BASE.waist_width)
    assert shoulder_ratio > waist_ratio


def test_losing_muscle_narrows() -> None:
    weaker, _ = change_muscle(BASE, -0.6)
    assert float(weaker.upper_arm_radius) < float(BASE.upper_arm_radius)


def test_extrapolated_muscle_levels_are_flagged() -> None:
    _, report = change_muscle(BASE, 2.5)
    assert any("extrapolation" in w for w in report.warnings)


# -- direct scaling ------------------------------------------------------


def test_a_single_measurement_can_be_scaled() -> None:
    wider, report = scale_measurement(BASE, "hip_width", 1.2)
    assert float(wider.hip_width) == pytest.approx(float(BASE.hip_width) * 1.2)
    assert report.changed["hip_width"][1] > report.changed["hip_width"][0]


def test_scaling_leaves_everything_else_alone() -> None:
    wider, _ = scale_measurement(BASE, "hip_width", 1.2)
    assert wider.waist_width == BASE.waist_width
    assert wider.chest_width == BASE.chest_width


@pytest.mark.parametrize(("field", "factor"), [("hip_width", 0.0), ("hip_width", -1.0)])
def test_a_nonsense_factor_is_rejected(field: str, factor: float) -> None:
    with pytest.raises(ValueError):
        scale_measurement(BASE, field, factor)


def test_an_unknown_measurement_is_rejected() -> None:
    with pytest.raises(ValueError):
        scale_measurement(BASE, "wingspan", 1.1)


def test_an_extreme_factor_warns() -> None:
    _, report = scale_measurement(BASE, "hip_width", 3.0)
    assert report.warnings


# -- interpolation -------------------------------------------------------


def test_interpolation_ends_match_the_inputs() -> None:
    target, _ = change_weight(BASE, -12.0)
    assert interpolate(BASE, target, 0.0).to_dict() == BASE.to_dict()
    assert interpolate(BASE, target, 1.0).waist_width == pytest.approx(
        float(target.waist_width)
    )


def test_halfway_sits_between_the_two_bodies() -> None:
    target, _ = change_weight(BASE, -12.0)
    middle = interpolate(BASE, target, 0.5)
    assert waist_girth(target) < waist_girth(middle) < waist_girth(BASE)


@pytest.mark.parametrize("t", [-0.1, 1.1])
def test_interpolation_outside_the_range_is_rejected(t: float) -> None:
    target, _ = change_weight(BASE, -5.0)
    with pytest.raises(ValueError):
        interpolate(BASE, target, t)


def test_bodies_of_different_heights_cannot_be_blended() -> None:
    """Interpolating stature would produce a different person."""
    with pytest.raises(ValueError):
        interpolate(BASE, BodyParameters(height=190.0), 0.5)


# -- the point of all this -----------------------------------------------


def test_a_transformed_body_stays_morph_compatible() -> None:
    """Same topology, so a garment fitted to one fits the other."""
    engine = SveyraHumanEngine("draft")
    before = engine.build_parametric(BASE)._mesh
    after = engine.build_parametric(change_weight(BASE, -12.0)[0])._mesh

    assert after.vertex_count == before.vertex_count
    assert np.array_equal(after.faces, before.faces)
    assert not np.allclose(after.vertices, before.vertices)


def test_transforming_needs_no_photographs() -> None:
    """The whole point: an avatar is parameters, so change is arithmetic."""
    stored = BASE.to_dict()
    restored = BodyParameters.from_dict(stored)
    changed, _ = change_weight(restored, -8.0)
    assert waist_girth(changed) < waist_girth(restored)
