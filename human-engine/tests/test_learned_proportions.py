"""A proportions mapping fitted to measured bodies."""

import numpy as np
import pytest

from sveyra_human import BodyParameters
from sveyra_human.body import LearnedProportions, ProportionModel, evaluate, fit_from_table
from sveyra_human.body.learned import PROVENANCE_SYNTHETIC
from sveyra_human.body.proportions import ScaledProportions

TARGETS = ["chest_width", "waist_width", "hip_width", "thigh_width"]


def bodies(count: int, seed: int = 3) -> list[dict[str, float]]:
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(count):
        height = float(rng.uniform(150, 200))
        weight = float(rng.uniform(17.5, 33.0)) * (height / 100) ** 2
        params = BodyParameters(
            height=height, extra={"weight_kg": weight}, proportions=ScaledProportions()
        )
        row = {"height_cm": height, "weight_kg": weight}
        for target in TARGETS:
            row[target] = float(getattr(params, target))
        rows.append(row)
    return rows


@pytest.fixture
def model() -> ProportionModel:
    return fit_from_table(bodies(300), TARGETS, provenance=PROVENANCE_SYNTHETIC)


def test_the_mapping_predicts_held_out_bodies(model: ProportionModel) -> None:
    errors = evaluate(model, bodies(80, seed=99))
    assert max(errors.values()) < 2.0, errors


def test_each_target_picks_its_own_predictors(model: ProportionModel) -> None:
    """The point of feature selection: a target uses what predicts it."""
    for target in TARGETS:
        chosen = [k for k in model.targets[target] if k != "_intercept"]
        assert 1 <= len(chosen) <= 2, target


def test_fitting_refuses_too_few_bodies() -> None:
    with pytest.raises(ValueError, match="at least four"):
        fit_from_table(bodies(3), TARGETS)


def test_fitting_refuses_rows_missing_a_predictor() -> None:
    rows = bodies(10)
    del rows[0]["weight_kg"]
    with pytest.raises(ValueError, match="predictor"):
        fit_from_table(rows, TARGETS)


def test_a_model_round_trips_through_a_file(model: ProportionModel, tmp_path) -> None:
    path = model.save(tmp_path / "m.json")
    loaded = ProportionModel.load(path)
    assert loaded.targets == model.targets
    assert loaded.provenance == PROVENANCE_SYNTHETIC


def test_provenance_travels_with_the_model(model: ProportionModel) -> None:
    """A model fitted on generated bodies must not pass as measurement."""
    assert "synthetic" in LearnedProportions(model=model).describe()


def test_the_source_drives_a_real_body(model: ProportionModel) -> None:
    source = LearnedProportions(model=model)
    light = BodyParameters(height=178.0, extra={"weight_kg": 62.0}, proportions=source)
    heavy = BodyParameters(height=178.0, extra={"weight_kg": 102.0}, proportions=source)
    assert float(heavy.waist_width) > float(light.waist_width)
    assert light.thigh_length == heavy.thigh_length


def test_a_body_without_a_weight_still_builds(model: ProportionModel) -> None:
    body = BodyParameters(height=178.0, proportions=LearnedProportions(model=model))
    assert float(body.waist_width) > 0


def test_the_source_refuses_without_a_model() -> None:
    with pytest.raises(ValueError, match="fitted model"):
        LearnedProportions()


def test_an_impossible_height_is_rejected(model: ProportionModel) -> None:
    with pytest.raises(ValueError):
        LearnedProportions(model=model).fractions(0.0)
