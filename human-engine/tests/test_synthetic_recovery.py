"""The synthetic harness.

Known parameters generate silhouettes; a fitter must later recover those
parameters from the silhouettes alone. Building the harness before the fitter
means Phase 3 has a measurable target from its first commit instead of being
judged by eye.
"""

import numpy as np
import pytest

from sveyra_human import BodyParameters, SveyraHumanEngine
from sveyra_human.camera.projection import (
    OrthographicCamera,
    mask_iou,
    mask_width_profile,
    rasterise_silhouette,
)


def synthetic_views(
    params: BodyParameters, resolution: tuple[int, int] = (256, 384)
) -> dict[str, np.ndarray]:
    """Ground-truth silhouettes for a known body, as a fitter would see them."""
    width, height = resolution
    artifact = SveyraHumanEngine("draft").build_parametric(params)
    mesh = artifact._mesh
    return {
        view: rasterise_silhouette(
            mesh.vertices,
            mesh.faces,
            OrthographicCamera.fit_to_height(view, params.height, width, height),
        )
        for view in ("front", "side", "back")
    }


# -- camera --------------------------------------------------------------


def test_projection_puts_the_crown_near_the_top_and_feet_near_the_bottom() -> None:
    camera = OrthographicCamera.fit_to_height("front", 180.0, 256, 384)
    points = np.array([[0.0, 180.0, 0.0], [0.0, 0.0, 0.0]])
    crown, feet = camera.project(points)
    assert crown[1] < feet[1]  # image Y grows downward
    assert 0 < crown[1] < 384 and 0 < feet[1] < 384


def test_front_and_side_read_different_axes() -> None:
    point = np.array([[10.0, 90.0, 4.0]])
    front = OrthographicCamera.fit_to_height("front", 180.0, 256, 384).project(point)
    side = OrthographicCamera.fit_to_height("side", 180.0, 256, 384).project(point)
    assert front[0][0] != side[0][0]
    assert front[0][1] == pytest.approx(side[0][1])


def test_the_back_view_mirrors_the_front() -> None:
    point = np.array([[12.0, 90.0, 0.0]])
    front = OrthographicCamera.fit_to_height("front", 180.0, 256, 384).project(point)
    back = OrthographicCamera.fit_to_height("back", 180.0, 256, 384).project(point)
    assert front[0][0] == pytest.approx(256.0 - back[0][0], abs=1e-6)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"view": "diagonal", "width": 10, "height": 10, "pixels_per_cm": 1.0},
        {"view": "front", "width": 0, "height": 10, "pixels_per_cm": 1.0},
        {"view": "front", "width": 10, "height": 10, "pixels_per_cm": 0.0},
    ],
)
def test_bad_cameras_are_rejected(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        OrthographicCamera(**kwargs)


# -- silhouettes ---------------------------------------------------------


def test_a_body_rasterises_to_a_plausible_silhouette() -> None:
    mask = synthetic_views(BodyParameters(height=180.0))["front"]
    coverage = mask.mean()
    # A standing human in a framed portrait fills a modest slice of the frame.
    assert 0.05 < coverage < 0.45
    assert mask.any(axis=1).sum() > mask.shape[0] * 0.7  # spans most rows


def test_a_mask_matches_itself_exactly() -> None:
    mask = synthetic_views(BodyParameters(height=180.0))["front"]
    assert mask_iou(mask, mask) == 1.0


def test_two_empty_masks_agree() -> None:
    empty = np.zeros((8, 8), dtype=bool)
    assert mask_iou(empty, empty) == 1.0


def test_mismatched_mask_shapes_are_rejected() -> None:
    with pytest.raises(ValueError):
        mask_iou(np.zeros((4, 4), dtype=bool), np.zeros((5, 5), dtype=bool))


def test_a_wider_body_covers_more_of_the_frame() -> None:
    narrow = synthetic_views(BodyParameters(height=180.0, waist_width=26.0))["front"]
    wide = synthetic_views(BodyParameters(height=180.0, waist_width=46.0))["front"]
    assert wide.sum() > narrow.sum()
    assert mask_iou(narrow, wide) < 0.99


def test_depth_changes_show_in_the_side_view_but_not_the_front() -> None:
    """This is why both views are needed: each constrains a different axis."""
    base = BodyParameters(height=180.0)
    deeper = BodyParameters(height=180.0, chest_depth=32.0, waist_depth=28.0)
    front_iou = mask_iou(synthetic_views(base)["front"], synthetic_views(deeper)["front"])
    side_iou = mask_iou(synthetic_views(base)["side"], synthetic_views(deeper)["side"])
    assert front_iou > side_iou


def test_the_width_profile_is_widest_around_the_shoulders() -> None:
    mask = synthetic_views(BodyParameters(height=180.0))["front"]
    profile = mask_width_profile(mask)
    rows = np.nonzero(profile)[0]
    widest = int(np.argmax(profile))
    # Arms are out in the rest pose, so the widest row sits in the upper body.
    upper_third = rows.min() + (rows.max() - rows.min()) / 3.0
    assert widest <= upper_third


def test_the_harness_is_deterministic() -> None:
    a = synthetic_views(BodyParameters(height=176.0, hip_width=39.0))
    b = synthetic_views(BodyParameters(height=176.0, hip_width=39.0))
    for view in a:
        assert np.array_equal(a[view], b[view])


# -- the Phase 3 target --------------------------------------------------


@pytest.mark.xfail(
    reason="Phase 3 not implemented: no fitter exists to recover parameters yet.",
    strict=True,
)
def test_a_fitter_recovers_the_parameters_it_was_given() -> None:
    """The acceptance test for Phase 3.

    It fails on purpose today. When the optimiser lands, remove the xfail: this
    is the definition of the fitting working, and it must not be softened.
    """
    from sveyra_human.optimization.optimizer import fit_body_parameters  # type: ignore

    truth = BodyParameters(height=182.0, waist_width=34.0, hip_width=40.0, chest_width=39.0)
    views = synthetic_views(truth)

    recovered = fit_body_parameters(views, height_cm=truth.height)

    for field in ("waist_width", "hip_width", "chest_width"):
        assert getattr(recovered, field) == pytest.approx(getattr(truth, field), rel=0.05)
