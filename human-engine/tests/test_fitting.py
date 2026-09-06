"""Body fitting from silhouettes.

One recovered body proves nothing, so these sweep body types, check the
priors actually bite, and confirm the failure modes are honest.
"""

import numpy as np
import pytest

from sveyra_human import BodyParameters, SveyraHumanEngine
from sveyra_human.api.errors import ReconstructionError
from sveyra_human.camera.projection import OrthographicCamera, rasterise_silhouette
from sveyra_human.optimization import (
    AnatomicalPrior,
    ProportionPrior,
    SmoothnessTerm,
    fit_body_parameters,
)
from sveyra_human.optimization.silhouette_loss import (
    mask_to_band_profile,
    profile_residual,
    torso_band_slice,
)

RESOLUTION = (200, 320)
SOLVED = ("chest_width", "chest_depth", "waist_width", "waist_depth", "hip_width", "hip_depth")


def silhouettes(params: BodyParameters) -> dict[str, np.ndarray]:
    mesh = SveyraHumanEngine("draft").build_parametric(params)._mesh
    return {
        view: rasterise_silhouette(
            mesh.vertices,
            mesh.faces,
            OrthographicCamera.fit_to_height(view, params.height, *RESOLUTION),
        )
        for view in ("front", "side")
    }


def worst_error(truth: BodyParameters, fitted: BodyParameters, fields: tuple[str, ...]) -> float:
    return max(
        abs(float(getattr(fitted, f)) - float(getattr(truth, f))) / float(getattr(truth, f))
        for f in fields
    )


# -- recovery across body types ------------------------------------------


@pytest.mark.parametrize(
    ("label", "truth"),
    [
        ("neutral", BodyParameters(height=175.0)),
        ("slim", BodyParameters(height=190.0, waist_width=27.0, chest_width=34.0)),
        ("broad", BodyParameters(height=178.0, chest_width=46.0, waist_width=42.0)),
        ("wide hips", BodyParameters(height=165.0, hip_width=44.0, waist_width=30.0)),
        ("deep chest", BodyParameters(height=183.0, chest_depth=27.0)),
    ],
)
def test_widths_are_recovered_across_body_types(label: str, truth: BodyParameters) -> None:
    fitted = fit_body_parameters(silhouettes(truth), height_cm=truth.height)
    assert worst_error(truth, fitted, ("chest_width", "waist_width", "hip_width")) < 0.10, label


def test_depths_are_recovered_from_the_side_view() -> None:
    truth = BodyParameters(height=180.0, chest_depth=26.0, waist_depth=24.0, hip_depth=25.0)
    fitted = fit_body_parameters(silhouettes(truth), height_cm=truth.height)
    assert worst_error(truth, fitted, ("chest_depth", "waist_depth", "hip_depth")) < 0.15


def test_the_fit_reports_a_small_residual_and_converges() -> None:
    truth = BodyParameters(height=181.0, waist_width=33.0)
    result = fit_body_parameters(
        silhouettes(truth), height_cm=truth.height, return_details=True
    )
    assert result.converged
    assert result.residual_cm < 2.0
    assert set(result.per_view_residual_cm) == {"front", "side"}
    assert result.to_dict()["iterations"] > 0


def test_fitting_is_deterministic() -> None:
    truth = BodyParameters(height=177.0, hip_width=41.0)
    views = silhouettes(truth)
    a = fit_body_parameters(views, height_cm=truth.height)
    b = fit_body_parameters(views, height_cm=truth.height)
    assert a.to_dict() == b.to_dict()


def test_two_different_bodies_do_not_fit_to_the_same_answer() -> None:
    slim = BodyParameters(height=180.0, waist_width=27.0)
    heavy = BodyParameters(height=180.0, waist_width=44.0)
    a = fit_body_parameters(silhouettes(slim), height_cm=180.0)
    b = fit_body_parameters(silhouettes(heavy), height_cm=180.0)
    assert float(b.waist_width) > float(a.waist_width) * 1.25


def test_a_front_view_alone_still_recovers_width() -> None:
    truth = BodyParameters(height=176.0, waist_width=36.0, hip_width=41.0)
    front_only = {"front": silhouettes(truth)["front"]}
    fitted = fit_body_parameters(front_only, height_cm=truth.height)
    assert worst_error(truth, fitted, ("waist_width", "hip_width")) < 0.12


# -- honest failure ------------------------------------------------------


def test_fitting_without_a_front_view_is_refused() -> None:
    truth = BodyParameters(height=180.0)
    with pytest.raises(ReconstructionError):
        fit_body_parameters({"side": silhouettes(truth)["side"]}, height_cm=180.0)


@pytest.mark.parametrize("height", [0.0, -3.0])
def test_a_nonsense_height_is_rejected(height: float) -> None:
    with pytest.raises(ValueError):
        fit_body_parameters({"front": np.zeros((32, 32), dtype=bool)}, height_cm=height)


def test_an_empty_mask_does_not_crash_the_solver() -> None:
    """A failed segmentation must produce a body, not an exception."""
    fitted = fit_body_parameters({"front": np.zeros((320, 200), dtype=bool)}, height_cm=180.0)
    assert fitted.height == 180.0
    assert float(fitted.waist_width) > 0


# -- priors --------------------------------------------------------------


def test_the_proportion_prior_is_silent_on_a_neutral_body() -> None:
    assert np.allclose(ProportionPrior().residuals(BodyParameters(height=180.0)), 0.0)


def test_the_proportion_prior_pushes_back_on_extremes() -> None:
    extreme = BodyParameters(height=180.0, waist_width=90.0)
    assert np.abs(ProportionPrior().residuals(extreme)).max() > 0


def test_the_anatomical_prior_rejects_a_torso_deeper_than_it_is_wide() -> None:
    odd = BodyParameters(height=180.0, chest_width=25.0, chest_depth=40.0)
    assert AnatomicalPrior().residuals(odd)[0] > 0


def test_the_anatomical_prior_is_silent_on_an_ordinary_torso() -> None:
    assert np.allclose(AnatomicalPrior().residuals(BodyParameters(height=180.0)), 0.0)


def test_the_smoothness_term_penalises_a_stepped_torso() -> None:
    stepped = BodyParameters(height=180.0, waist_width=12.0)
    smooth = BodyParameters(height=180.0)
    assert np.abs(SmoothnessTerm().residuals(stepped)).sum() > np.abs(
        SmoothnessTerm().residuals(smooth)
    ).sum()


def test_priors_alone_cannot_explain_the_fit() -> None:
    """Turning the silhouette off must make the answer worse, or it was never used."""
    truth = BodyParameters(height=180.0, waist_width=44.0, hip_width=44.0)
    views = silhouettes(truth)
    with_pixels = fit_body_parameters(views, height_cm=truth.height)
    neutral = BodyParameters(height=truth.height)
    assert abs(float(with_pixels.waist_width) - 44.0) < abs(float(neutral.waist_width) - 44.0)


# -- profile helpers -----------------------------------------------------


def test_the_torso_band_slice_excludes_the_arms() -> None:
    band_slice = torso_band_slice(40)
    assert band_slice.start >= 16 and band_slice.stop <= 30


def test_a_band_profile_is_zero_for_an_empty_mask() -> None:
    camera = OrthographicCamera.fit_to_height("front", 180.0, 64, 96)
    assert not mask_to_band_profile(np.zeros((96, 64), dtype=bool), camera, 20).any()


def test_profile_residual_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError):
        profile_residual(np.zeros(10), np.zeros(12))
