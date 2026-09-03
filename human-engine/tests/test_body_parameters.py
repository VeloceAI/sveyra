import pytest

from sveyra_human.body.parameters import BodyParameters


def test_height_alone_produces_a_complete_parameter_set() -> None:
    params = BodyParameters(height=180.0)
    for name in ("shoulder_width", "chest_width", "waist_depth", "thigh_length", "head_width"):
        value = getattr(params, name)
        assert value is not None and value > 0, name


def test_supplied_measurements_are_not_overwritten() -> None:
    params = BodyParameters(height=180.0, waist_width=42.0)
    assert params.waist_width == 42.0


@pytest.mark.parametrize("height", [0.0, -5.0, 20.0, 400.0])
def test_impossible_heights_are_rejected(height: float) -> None:
    with pytest.raises(ValueError):
        BodyParameters(height=height)


def test_neutral_proportions_scale_linearly_with_height() -> None:
    small = BodyParameters(height=150.0)
    large = BodyParameters(height=300.0 / 2 + 75.0)  # 225
    ratio = float(large.shoulder_width) / float(small.shoulder_width)
    assert ratio == pytest.approx(225.0 / 150.0, rel=1e-6)


def test_round_trips_through_a_dict() -> None:
    original = BodyParameters(height=177.0, chest_width=40.0, hip_width=38.0)
    restored = BodyParameters.from_dict(original.to_dict())
    assert restored.to_dict() == original.to_dict()


def test_unknown_numeric_keys_survive_in_extra() -> None:
    data = BodyParameters(height=170.0).to_dict()
    data["glute_projection"] = 4.5
    restored = BodyParameters.from_dict(data)
    assert restored.extra["glute_projection"] == 4.5


def test_landmark_levels_are_ordered_from_floor_upward() -> None:
    params = BodyParameters(height=180.0)
    order = ["ankle", "knee", "hip", "waist", "chest", "shoulder", "neck"]
    levels = [params.level_cm(name) for name in order]
    assert levels == sorted(levels)


def test_waist_position_moves_the_waist() -> None:
    high = BodyParameters(height=180.0, waist_position=0.68)
    low = BodyParameters(height=180.0, waist_position=0.58)
    assert high.level_cm("waist") > low.level_cm("waist")
