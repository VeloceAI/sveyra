# Proportions

Unset measurements come from a swappable source. Three exist.

| Source | Needs | Use it when |
| --- | --- | --- |
| `AnthropometricProportions` | nothing | Default. Fractions of height, classical rules of thumb. |
| `ScaledProportions` | nothing | Fractions plus a BMI-derived build skew. Mass goes to the torso; limb lengths do not move. |
| `LearnedProportions` | a fitted model file | A regression over measured bodies. |

Swapping is one argument, and reverting is deleting it:

```python
BodyParameters(height=178, extra={"weight_kg": 82}, proportions=LearnedProportions(model_path=...))
```

## Fitting a model

The method follows `zengyh1900/3D-Human-Body-Shape` (MIT): one small regression
per target, each choosing its own predictors, rather than a single global
mapping. A waist is predicted by weight; an inseam is not.

```python
from sveyra_human.body import fit_from_table, evaluate

rows = [{"height_cm": 178, "weight_kg": 74, "waist_width": 31.2, ...}, ...]
model = fit_from_table(rows, targets=["waist_width", "chest_width", ...],
                       provenance="measured", notes="SPRING subset, 2026-09")
model.save("assets/proportions/spring.json")
print(evaluate(model, held_out))
```

**No dataset lives in this repository.** A model is a small coefficients file,
so the bodies used to fit it stay outside it along with their licence. That is
the whole reason this is a port: of twelve human-body repositories surveyed,
nine derive from SMPL and every one is non-commercial. Keeping data out means a
licence question never becomes a code change.

## Provenance is not decoration

`ProportionModel.provenance` is either `measured` or `synthetic`, and
`LearnedProportions.describe()` reports it. A model fitted on bodies the engine
generated proves the machinery works and says nothing about real anatomy, so it
must never be mistaken for measurement.

## The bundled proof of concept

`assets/proportions/synthetic_poc.json` is fitted on 400 engine-generated
bodies and marked `synthetic`. Held-out error is under 0.6 cm on every target,
which demonstrates the pipeline end to end: fit, save, load, drive a body,
build a mesh.

It is not evidence about people. Replace it with a model fitted on measured
bodies before any of this informs a real garment size.
