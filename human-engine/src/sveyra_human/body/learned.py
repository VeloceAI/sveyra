"""A proportions mapping fitted to measured bodies.

The method is the one from `zengyh1900/3D-Human-Body-Shape` (MIT): regress a
full set of body dimensions from a few known inputs, using per-target feature
selection rather than one global mapping. A waist is predicted well by weight
and poorly by inseam, and letting each target pick its own predictors is what
makes the fit better than a single global regression.

What is deliberately *not* here is any dataset. The model is a small file of
coefficients produced by `fit_from_table`, so whichever measured bodies are
used to fit it stay outside this repository along with their licence.

A model fitted on bodies the engine generated is a proof that the machinery
works, not evidence about real people, and `PROVENANCE_SYNTHETIC` says so in
the file itself.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

PROVENANCE_SYNTHETIC = "synthetic"
PROVENANCE_MEASURED = "measured"

# Inputs a user can actually give. Everything else is predicted from these.
PREDICTORS = ("height_cm", "weight_kg")

# How many predictors each target may use. Low on purpose: the whole point of
# feature selection is that a target uses what predicts it and ignores the rest.
MAX_FEATURES = 2


@dataclass
class ProportionModel:
    """Per-target linear coefficients over a shared predictor set."""

    targets: dict[str, dict[str, float]]
    predictors: tuple[str, ...]
    provenance: str
    sample_count: int
    notes: str = ""

    def predict(self, inputs: dict[str, float]) -> dict[str, float]:
        out: dict[str, float] = {}
        for target, coefficients in self.targets.items():
            value = coefficients.get("_intercept", 0.0)
            for name, weight in coefficients.items():
                if name == "_intercept":
                    continue
                value += weight * float(inputs.get(name, 0.0))
            out[target] = value
        return out

    def to_dict(self) -> dict[str, object]:
        return {
            "targets": self.targets,
            "predictors": list(self.predictors),
            "provenance": self.provenance,
            "sample_count": self.sample_count,
            "notes": self.notes,
        }

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: str | Path) -> ProportionModel:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            targets=data["targets"],
            predictors=tuple(data["predictors"]),
            provenance=data.get("provenance", PROVENANCE_MEASURED),
            sample_count=int(data.get("sample_count", 0)),
            notes=data.get("notes", ""),
        )


def fit_from_table(
    rows: list[dict[str, float]],
    targets: list[str],
    predictors: tuple[str, ...] = PREDICTORS,
    provenance: str = PROVENANCE_MEASURED,
    notes: str = "",
    max_features: int = MAX_FEATURES,
) -> ProportionModel:
    """Fit one small regression per target, each choosing its own predictors.

    `rows` are measured bodies: one dict per person, centimetres and kilograms.
    Nothing about the source is recorded except the provenance string, so the
    data never has to enter this repository.
    """
    if len(rows) < 4:
        raise ValueError("fitting needs at least four bodies")
    missing = [p for p in predictors if any(p not in row for row in rows)]
    if missing:
        raise ValueError(f"every row must carry every predictor; missing {missing}")

    design = np.array([[float(row[p]) for p in predictors] for row in rows])
    fitted: dict[str, dict[str, float]] = {}

    for target in targets:
        usable = [i for i, row in enumerate(rows) if target in row]
        if len(usable) < 4:
            continue
        x_all = design[usable]
        y = np.array([float(rows[i][target]) for i in usable])

        chosen = _select_features(x_all, y, max_features)
        x = np.column_stack([x_all[:, c] for c in chosen] + [np.ones(len(usable))])
        coefficients, *_ = np.linalg.lstsq(x, y, rcond=None)

        entry = {predictors[c]: float(coefficients[k]) for k, c in enumerate(chosen)}
        entry["_intercept"] = float(coefficients[-1])
        fitted[target] = entry

    return ProportionModel(
        targets=fitted,
        predictors=predictors,
        provenance=provenance,
        sample_count=len(rows),
        notes=notes,
    )


def _select_features(x: np.ndarray, y: np.ndarray, limit: int) -> list[int]:
    """Keep the predictors most correlated with this target.

    Simple on purpose. With two or three candidate predictors, anything more
    elaborate is ceremony that cannot change the answer.
    """
    scores: list[tuple[float, int]] = []
    for column in range(x.shape[1]):
        values = x[:, column]
        if float(np.std(values)) < 1e-9 or float(np.std(y)) < 1e-9:
            scores.append((0.0, column))
            continue
        scores.append((abs(float(np.corrcoef(values, y)[0, 1])), column))
    scores.sort(reverse=True)
    return sorted(column for _, column in scores[: max(1, limit)])


def evaluate(model: ProportionModel, rows: list[dict[str, float]]) -> dict[str, float]:
    """Mean absolute error per target, in centimetres, on held-out bodies."""
    errors: dict[str, list[float]] = {}
    for row in rows:
        predicted = model.predict(row)
        for target, value in predicted.items():
            if target in row:
                errors.setdefault(target, []).append(abs(value - float(row[target])))
    return {t: round(float(np.mean(e)), 3) for t, e in errors.items() if e}
