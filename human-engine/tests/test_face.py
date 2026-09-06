"""Face parameters, landmark fitting, and head shaping."""

import numpy as np
import pytest

from sveyra_human import BodyParameters
from sveyra_human.api.errors import ReconstructionError
from sveyra_human.body.cage import build_cage
from sveyra_human.face import (
    FaceParameters,
    apply_face_shape,
    fit_face_parameters,
    landmarks_from_parameters,
    width_profile,
)
from sveyra_human.skeleton.model import build_skeleton
from sveyra_human.vision.port import Landmark, PoseLandmarks


def worst_error(truth: FaceParameters, fitted: FaceParameters) -> float:
    return max(
        abs(float(getattr(fitted, f)) - float(getattr(truth, f))) / float(getattr(truth, f))
        for f in truth.solved_fields()
    )


def head_cage():
    params = BodyParameters(height=180.0)
    cage = build_cage(params, build_skeleton(params).positions)
    chin = params.level_cm("neck") + float(params.neck_length)
    return params, cage, cage.part("head"), chin


# -- parameters ----------------------------------------------------------


def test_face_length_alone_fills_a_whole_face() -> None:
    face = FaceParameters(face_length=18.0)
    for name in ("jaw_width", "eye_spacing", "nose_length", "mouth_width"):
        assert float(getattr(face, name)) > 0, name


@pytest.mark.parametrize("length", [0.0, -2.0, 4.0, 60.0])
def test_an_impossible_face_length_is_rejected(length: float) -> None:
    with pytest.raises(ValueError):
        FaceParameters(face_length=length)


def test_a_face_is_sized_from_the_head_it_sits_on() -> None:
    assert FaceParameters.for_head(26.0).face_length > FaceParameters.for_head(20.0).face_length


def test_a_face_round_trips_through_a_dict() -> None:
    original = FaceParameters(face_length=19.0, jaw_width=12.0)
    assert FaceParameters.from_dict(original.to_dict()).to_dict() == original.to_dict()


def test_projections_are_not_claimed_to_be_solvable() -> None:
    """A single front view says nothing about depth, so it must not be listed."""
    solved = FaceParameters(face_length=18.0).solved_fields()
    assert "nose_projection" not in solved
    assert "chin_projection" not in solved


# -- fitting -------------------------------------------------------------


def test_a_face_is_recovered_exactly_from_clean_landmarks() -> None:
    truth = FaceParameters(face_length=18.5, jaw_width=11.5, cheekbone_width=13.8)
    fitted = fit_face_parameters(
        landmarks_from_parameters(truth), face_length_cm=truth.face_length
    )
    assert worst_error(truth, fitted) < 0.01


def test_fitting_degrades_gracefully_with_a_noisy_detector() -> None:
    truth = FaceParameters(face_length=18.5, mouth_width=5.4)
    landmarks = landmarks_from_parameters(truth, jitter=0.004, seed=2)
    fitted = fit_face_parameters(landmarks, face_length_cm=truth.face_length)
    assert worst_error(truth, fitted) < 0.12


@pytest.mark.parametrize("length", [15.0, 18.0, 22.0])
def test_faces_of_different_sizes_are_all_recovered(length: float) -> None:
    truth = FaceParameters(face_length=length)
    fitted = fit_face_parameters(landmarks_from_parameters(truth), face_length_cm=length)
    assert worst_error(truth, fitted) < 0.02


def test_two_different_faces_do_not_fit_to_the_same_answer() -> None:
    narrow = FaceParameters(face_length=18.0, jaw_width=9.0)
    wide = FaceParameters(face_length=18.0, jaw_width=14.0)
    a = fit_face_parameters(landmarks_from_parameters(narrow), face_length_cm=18.0)
    b = fit_face_parameters(landmarks_from_parameters(wide), face_length_cm=18.0)
    assert float(b.jaw_width) > float(a.jaw_width) * 1.3


def test_a_wandering_landmark_cannot_distort_the_whole_face() -> None:
    """One bad point must be clamped, not believed."""
    truth = FaceParameters(face_length=18.0)
    broken = dict(landmarks_from_parameters(truth).points)
    broken["jaw_left"] = Landmark(name="jaw_left", x=-5.0, y=0.5)
    fitted = fit_face_parameters(PoseLandmarks(points=broken), face_length_cm=18.0)
    assert float(fitted.jaw_width) < float(truth.jaw_width) * 2.0


def test_missing_anchor_landmarks_are_refused() -> None:
    with pytest.raises(ReconstructionError):
        fit_face_parameters(PoseLandmarks(points={}), face_length_cm=18.0)


def test_coincident_anchors_are_refused() -> None:
    points = {
        "chin": Landmark(name="chin", x=0.5, y=0.5),
        "hairline": Landmark(name="hairline", x=0.5, y=0.5),
    }
    with pytest.raises(ReconstructionError):
        fit_face_parameters(PoseLandmarks(points=points), face_length_cm=18.0)


def test_fitting_without_any_scale_is_refused() -> None:
    """A face in an image has no absolute size; guessing one would be a lie."""
    landmarks = landmarks_from_parameters(FaceParameters(face_length=18.0))
    with pytest.raises(ValueError):
        fit_face_parameters(landmarks)


def test_invisible_landmarks_are_ignored() -> None:
    truth = FaceParameters(face_length=18.0)
    hidden = dict(landmarks_from_parameters(truth).points)
    hidden["mouth_left"] = Landmark(name="mouth_left", x=0.1, y=0.9, visibility=0.0)
    fitted = fit_face_parameters(PoseLandmarks(points=hidden), face_length_cm=18.0)
    # Falls back to the neutral proportion rather than trusting a hidden point.
    assert float(fitted.mouth_width) == pytest.approx(
        float(FaceParameters(face_length=18.0).mouth_width)
    )


# -- shaping -------------------------------------------------------------


def test_the_width_profile_runs_chin_to_forehead() -> None:
    profile = width_profile(FaceParameters(face_length=18.0), samples=12)
    assert profile.shape == (12,)
    assert profile[0] < profile[len(profile) // 2]  # chin narrower than cheekbones


def test_shaping_widens_the_head_when_the_face_is_wide() -> None:
    params, _, head, chin = head_cage()
    narrow = apply_face_shape(
        head, FaceParameters(face_length=16.0, cheekbone_width=11.0), chin, params.height
    )
    wide = apply_face_shape(
        head, FaceParameters(face_length=16.0, cheekbone_width=17.0), chin, params.height
    )
    assert np.ptp(wide.rings[:, :, 0]) > np.ptp(narrow.rings[:, :, 0])


def test_shaping_leaves_depth_alone() -> None:
    """Nothing in a front view constrains projection, so it must not change."""
    params, _, head, chin = head_cage()
    shaped = apply_face_shape(head, FaceParameters(face_length=16.0), chin, params.height)
    assert np.allclose(shaped.rings[:, :, 2], head.rings[:, :, 2])


def test_shaping_preserves_topology() -> None:
    params, _, head, chin = head_cage()
    shaped = apply_face_shape(head, FaceParameters(face_length=16.0), chin, params.height)
    assert shaped.rings.shape == head.rings.shape
    assert shaped.closed_top == head.closed_top


def test_an_inverted_head_span_is_rejected() -> None:
    _, _, head, _ = head_cage()
    with pytest.raises(ValueError):
        apply_face_shape(head, FaceParameters(face_length=16.0), 150.0, 100.0)


def test_the_engine_applies_a_face_without_disturbing_the_body() -> None:
    from sveyra_human import SveyraHumanEngine

    engine = SveyraHumanEngine("draft")
    params, cage, _, _ = head_cage()
    face = engine.fit_face(
        landmarks_from_parameters(FaceParameters(face_length=17.0, cheekbone_width=15.0)),
        face_length_cm=17.0,
    )
    shaped = engine.shape_head(cage, params, face)

    assert len(shaped.parts) == len(cage.parts)
    assert np.allclose(shaped.part("torso").rings, cage.part("torso").rings)
    assert not np.allclose(shaped.part("head").rings, cage.part("head").rings)
