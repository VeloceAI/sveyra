"""Segmentation, capture validation, and the whole photograph-to-avatar path."""

import numpy as np
import pytest

from sveyra_human import BodyParameters, SveyraHumanEngine
from sveyra_human.api.errors import ReconstructionError
from sveyra_human.camera.projection import OrthographicCamera, mask_iou, rasterise_silhouette
from sveyra_human.capture import load_image, validate_view
from sveyra_human.capture.validator import CaptureReport
from sveyra_human.vision import (
    BackgroundContrastSegmenter,
    SegmentationResult,
    clean_mask,
    crop_to_subject,
    is_full_body,
    silhouette_from_segmentation,
    vertical_extent,
)

WALL = (205, 200, 192)
SKIN = (62, 68, 86)


def true_silhouette(params: BodyParameters, view: str, res=(300, 480)) -> np.ndarray:
    mesh = SveyraHumanEngine("draft").build_parametric(params)._mesh
    return rasterise_silhouette(
        mesh.vertices, mesh.faces, OrthographicCamera.fit_to_height(view, params.height, *res)
    )


def photograph(
    params: BodyParameters,
    view: str,
    *,
    noise: float = 7.0,
    gradient: float = 12.0,
    subject=SKIN,
    seed: int = 3,
) -> tuple[np.ndarray, np.ndarray]:
    """A synthetic photo: subject on a noisy, unevenly lit wall."""
    rng = np.random.default_rng(seed)
    mask = true_silhouette(params, view)
    h, w = mask.shape
    wall = np.full((h, w, 3), WALL, dtype=float)
    wall += rng.normal(0, noise, (h, w, 3))
    wall += np.linspace(-gradient, gradient, w)[None, :, None]
    person = np.full((h, w, 3), subject, dtype=float) + rng.normal(0, 9, (h, w, 3))
    image = np.where(mask[:, :, None], person, wall)
    return np.clip(image, 0, 255).astype(np.uint8), mask


# -- segmentation --------------------------------------------------------


def test_a_person_is_separated_from_the_wall() -> None:
    image, truth = photograph(BodyParameters(height=180.0), "front")
    result = BackgroundContrastSegmenter().segment(image)
    assert mask_iou(silhouette_from_segmentation(result), truth) > 0.95
    assert result.confidence > 0.5


@pytest.mark.parametrize("noise", [2.0, 10.0, 18.0])
def test_segmentation_survives_a_noisy_wall(noise: float) -> None:
    image, truth = photograph(BodyParameters(height=180.0), "front", noise=noise)
    mask = silhouette_from_segmentation(BackgroundContrastSegmenter().segment(image))
    assert mask_iou(mask, truth) > 0.85, noise


def test_background_speckle_does_not_swallow_the_frame() -> None:
    """Filling holes before picking the subject once consumed the whole image."""
    image, _ = photograph(BodyParameters(height=180.0), "front", noise=20.0, gradient=25.0)
    mask = silhouette_from_segmentation(BackgroundContrastSegmenter().segment(image))
    assert mask.mean() < 0.5


def test_a_subject_matching_the_wall_reports_low_confidence() -> None:
    """Saying so is the requirement; getting it right is not always possible."""
    image, _ = photograph(BodyParameters(height=180.0), "front", subject=(200, 196, 188))
    assert BackgroundContrastSegmenter().segment(image).confidence < 0.6


def test_an_empty_image_yields_an_empty_mask() -> None:
    flat = np.full((200, 120, 3), WALL, dtype=np.uint8)
    result = BackgroundContrastSegmenter().segment(flat)
    assert result.confidence < 0.5


def test_greyscale_input_is_accepted() -> None:
    image, _ = photograph(BodyParameters(height=180.0), "front")
    grey = image.mean(axis=2).astype(np.uint8)
    assert BackgroundContrastSegmenter().segment(grey).mask.shape == grey.shape


def test_a_malformed_array_is_rejected() -> None:
    with pytest.raises(ValueError):
        BackgroundContrastSegmenter().segment(np.zeros((4, 4, 4, 4)))


# -- mask utilities ------------------------------------------------------


def test_clean_mask_drops_specks_but_keeps_the_subject() -> None:
    mask = np.zeros((100, 100), dtype=bool)
    mask[20:80, 40:60] = True
    mask[5, 5] = True
    cleaned = clean_mask(mask)
    assert cleaned[50, 50]
    assert not cleaned[5, 5]


def test_clean_mask_on_an_empty_mask_is_empty() -> None:
    assert not clean_mask(np.zeros((10, 10), dtype=bool)).any()


def test_vertical_extent_and_cropping() -> None:
    mask = np.zeros((100, 60), dtype=bool)
    mask[30:70, 20:40] = True
    assert vertical_extent(mask) == (30, 69)
    assert crop_to_subject(mask).shape[0] <= 44


def test_vertical_extent_rejects_an_empty_mask() -> None:
    with pytest.raises(ValueError):
        vertical_extent(np.zeros((5, 5), dtype=bool))


def test_a_cropped_subject_is_not_treated_as_full_body() -> None:
    mask = np.zeros((200, 100), dtype=bool)
    mask[150:190, 40:60] = True
    assert not is_full_body(mask)


def test_a_standing_subject_is_full_body() -> None:
    _, truth = photograph(BodyParameters(height=180.0), "front")
    assert is_full_body(truth)


# -- capture validation --------------------------------------------------


def test_a_tiny_image_is_fatal() -> None:
    issues = validate_view("front", np.zeros((20, 20, 3), np.uint8), np.ones((20, 20), bool), 1.0)
    assert any(i.fatal for i in issues)


def test_no_person_found_is_fatal() -> None:
    issues = validate_view(
        "front", np.zeros((300, 200, 3), np.uint8), np.zeros((300, 200), bool), 0.0
    )
    assert any(i.fatal for i in issues)


def test_poor_separation_warns_without_being_fatal() -> None:
    _, truth = photograph(BodyParameters(height=180.0), "front")
    issues = validate_view("front", np.zeros((480, 300, 3), np.uint8), truth, 0.1)
    assert issues and not any(i.fatal for i in issues)


def test_a_report_separates_warnings_from_errors() -> None:
    report = CaptureReport()
    report.issues.extend(
        validate_view("front", np.zeros((300, 200, 3), np.uint8), np.zeros((300, 200), bool), 0.0)
    )
    assert not report.usable
    assert report.errors()


# -- image loading -------------------------------------------------------


def test_arrays_load_unchanged() -> None:
    image, _ = photograph(BodyParameters(height=180.0), "front")
    assert load_image(image).shape == image.shape


def test_float_and_greyscale_arrays_normalise_to_rgb_bytes() -> None:
    loaded = load_image(np.ones((10, 10), dtype=np.float32) * 0.5)
    assert loaded.shape == (10, 10, 3)
    assert loaded.dtype == np.uint8


def test_an_unsupported_source_is_rejected() -> None:
    with pytest.raises(TypeError):
        load_image(object())


# -- end to end ----------------------------------------------------------


def test_photographs_produce_a_body_close_to_the_truth() -> None:
    truth = BodyParameters(height=181.0, waist_width=35.0, chest_width=41.0, hip_width=39.0)
    front, _ = photograph(truth, "front")
    side, _ = photograph(truth, "side")

    artifact = SveyraHumanEngine("balanced").build(
        front=front, side=side, height_cm=truth.height
    )

    assert artifact.source_views == 2
    for field in ("chest_width", "waist_width", "hip_width"):
        fitted = float(getattr(artifact.body_parameters, field))
        expected = float(getattr(truth, field))
        assert abs(fitted - expected) / expected < 0.10, field


def test_a_photo_build_reports_per_view_confidence_and_warnings() -> None:
    truth = BodyParameters(height=178.0)
    front, _ = photograph(truth, "front")
    artifact = SveyraHumanEngine("draft").build(front=front, height_cm=178.0)
    assert set(artifact.quality.views) == {"front"}
    assert any("side view" in w for w in artifact.quality.warnings)
    assert artifact.profiling_ms["vision_ms"] > 0
    assert artifact.profiling_ms["fitting_ms"] > 0


def test_building_without_a_usable_front_view_is_refused() -> None:
    blank = np.full((400, 250, 3), WALL, dtype=np.uint8)
    with pytest.raises(ReconstructionError):
        SveyraHumanEngine("draft").build(front=blank, height_cm=180.0)


def test_building_without_a_height_is_refused() -> None:
    front, _ = photograph(BodyParameters(height=180.0), "front")
    with pytest.raises(ValueError):
        SveyraHumanEngine("draft").build(front=front)


def test_a_custom_segmenter_is_used_instead_of_the_default() -> None:
    """The vision layer must be swappable without touching the body engine."""

    class AlwaysHalf:
        def segment(self, image):
            mask = np.zeros(image.shape[:2], dtype=bool)
            mask[:, image.shape[1] // 3 : 2 * image.shape[1] // 3] = True
            return SegmentationResult(mask=mask, confidence=0.9)

    front, _ = photograph(BodyParameters(height=180.0), "front")
    artifact = SveyraHumanEngine("draft", segmenter=AlwaysHalf()).build(
        front=front, height_cm=180.0
    )
    assert artifact.source_views == 1
