"""Hair segmentation, grouping, and volume reconstruction."""

import numpy as np
import pytest

from sveyra_human import BodyParameters, SveyraHumanEngine
from sveyra_human.body.cage import build_cage
from sveyra_human.hair import (
    GROUP_REGIONS,
    HairGroup,
    Hairstyle,
    build_hairstyle,
    groups_present,
    measure_thickness,
    segment_hair,
)
from sveyra_human.skeleton.model import build_skeleton

SKIN = (205, 155, 130)
HAIR = (45, 35, 30)
WALL = (210, 208, 202)


def head_part():
    params = BodyParameters(height=180.0)
    return build_cage(params, build_skeleton(params).positions).part("head")


def portrait(hair_rows: int = 26, height: int = 200, width: int = 100):
    """A crude portrait: hair on top of a skin-coloured head, on a wall."""
    image = np.full((height, width, 3), WALL, dtype=np.uint8)
    person = np.zeros((height, width), dtype=bool)
    person[10:190, 30:70] = True
    image[person] = SKIN
    image[10 : 10 + hair_rows, 30:70] = HAIR
    return image, person


# -- segmentation --------------------------------------------------------


def test_hair_is_separated_from_skin() -> None:
    image, person = portrait()
    result = segment_hair(image, person)
    assert result.mask.any()
    # Hair must land at the top of the head, not on the face.
    rows = np.nonzero(result.mask.any(axis=1))[0]
    assert rows.min() < 20
    assert result.confidence > 0.0


def test_a_bald_head_yields_no_hair() -> None:
    """Returning nothing is the honest answer; inventing hair is not."""
    image, person = portrait(hair_rows=0)
    assert not segment_hair(image, person).mask.any()


def test_an_empty_person_mask_yields_no_hair() -> None:
    image, _ = portrait()
    result = segment_hair(image, np.zeros(image.shape[:2], dtype=bool))
    assert not result.mask.any()
    assert result.confidence == 0.0


def test_hair_is_only_looked_for_on_the_head() -> None:
    """Dark trousers are not hair."""
    image, person = portrait(hair_rows=0)
    image[150:190, 30:70] = HAIR
    assert not segment_hair(image, person).mask.any()


def test_mismatched_resolutions_are_rejected() -> None:
    image, _ = portrait()
    with pytest.raises(ValueError):
        segment_hair(image, np.zeros((10, 10), dtype=bool))


# -- thickness -----------------------------------------------------------


def test_thickness_is_half_the_silhouette_growth() -> None:
    head = np.zeros((100, 100), dtype=bool)
    head[20:60, 40:60] = True
    hair = np.zeros((100, 100), dtype=bool)
    hair[20:60, 35:65] = True  # 5 px wider each side
    assert measure_thickness(hair, head, pixels_per_cm=2.0) == pytest.approx(2.5)


def test_thicker_hair_measures_thicker() -> None:
    head = np.zeros((100, 100), dtype=bool)
    head[20:60, 45:55] = True
    thin = np.zeros((100, 100), dtype=bool)
    thin[20:60, 43:57] = True
    thick = np.zeros((100, 100), dtype=bool)
    thick[20:60, 35:65] = True
    assert measure_thickness(thick, head, 2.0) > measure_thickness(thin, head, 2.0)


def test_thickness_never_collapses_to_zero() -> None:
    """A shell at zero offset z-fights with the scalp."""
    empty = np.zeros((50, 50), dtype=bool)
    assert measure_thickness(empty, empty, 2.0) > 0


def test_a_nonsense_scale_is_rejected() -> None:
    head = np.ones((10, 10), dtype=bool)
    with pytest.raises(ValueError):
        measure_thickness(head, head, pixels_per_cm=0.0)


# -- groups and volumes --------------------------------------------------


def test_every_group_is_built_over_a_normal_head() -> None:
    style = build_hairstyle(head_part(), thickness_cm=2.5)
    assert {v.group for v in style.volumes} == set(GROUP_REGIONS)


def test_hair_sits_outside_the_skull() -> None:
    head = head_part()
    style = build_hairstyle(head, thickness_cm=3.0)
    fringe = style.group(HairGroup.FRINGE)
    # The forward-facing arc must have moved outward in +Z.
    assert fringe.rings[:, :, 2].max() > head.rings[:, :, 2].max()


def test_thicker_hair_sits_further_out() -> None:
    head = head_part()
    thin = build_hairstyle(head, 1.0).group(HairGroup.FRINGE)
    thick = build_hairstyle(head, 4.0).group(HairGroup.FRINGE)
    assert thick.rings[:, :, 2].max() > thin.rings[:, :, 2].max()


def test_only_groups_the_photograph_supports_are_built() -> None:
    coverage = {HairGroup.FRINGE: 0.4, HairGroup.TOP: 0.5, HairGroup.BACK: 0.01}
    style = build_hairstyle(head_part(), 2.0, coverage=coverage)
    built = {v.group for v in style.volumes}
    assert HairGroup.FRINGE in built
    assert HairGroup.BACK not in built


def test_groups_present_filters_by_threshold() -> None:
    coverage = {HairGroup.TOP: 0.5, HairGroup.BACK: 0.02}
    assert groups_present(coverage) == [HairGroup.TOP]


def test_a_zero_thickness_style_is_rejected() -> None:
    with pytest.raises(ValueError):
        build_hairstyle(head_part(), thickness_cm=0.0)


def test_volumes_carry_control_chains_for_a_future_solver() -> None:
    style = build_hairstyle(head_part(), 2.5)
    fringe = style.group(HairGroup.FRINGE)
    assert fringe.chains
    chain = fringe.chains[0]
    assert chain.nodes.shape[1] == 3
    assert chain.length > 0


def test_a_hairstyle_serialises_for_the_metadata_sidecar() -> None:
    payload = build_hairstyle(head_part(), 2.5).to_dict()
    assert payload["source"] == "reconstructed"
    assert len(payload["groups"]) == len(GROUP_REGIONS)


def test_an_unknown_group_is_reported_not_guessed() -> None:
    with pytest.raises(KeyError):
        Hairstyle(volumes=[]).group(HairGroup.TOP)


# -- through the engine --------------------------------------------------


def test_the_engine_reconstructs_hair_from_a_photograph() -> None:
    params = BodyParameters(height=180.0)
    cage = build_cage(params, build_skeleton(params).positions)
    image, person = portrait()

    style = SveyraHumanEngine("draft").build_hair(cage, image, person, pixels_per_cm=2.0)
    assert style.volumes


def test_the_engine_returns_no_hair_rather_than_default_hair() -> None:
    params = BodyParameters(height=180.0)
    cage = build_cage(params, build_skeleton(params).positions)
    image, person = portrait(hair_rows=0)

    style = SveyraHumanEngine("draft").build_hair(cage, image, person, pixels_per_cm=2.0)
    assert style.volumes == []
    assert style.source == "none-detected"
