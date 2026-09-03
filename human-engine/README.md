# SVEYRA Human Engine

Realistic, rigged 3D humans from a handful of photographs, without CUDA, SMPL,
diffusion models or a cloud round trip in the core reconstruction.

**AI understands the photographs. Mathematics constructs the human.**

A body here is a few dozen named measurements, not a neural network's opaque
output. That makes it inspectable, storable, editable, reproducible, and free of
research-only licences.

## Status

Phases 1 and 3 of 9. Parameters in, rigged topology and a GLB out, and silhouettes
in, body parameters out. All on CPU: ~19 ms to build, ~0.7 s to fit. Turning a
photograph into a silhouette (Phase 2) is not built and refuses rather than faking it.

See [docs/STATUS.md](docs/STATUS.md) for the exact line between the two.

## Quick start

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"

.venv/Scripts/python -m sveyra_human.cli build-parametric --height 184 --out avatar.glb
```

```python
from sveyra_human import BodyParameters, SveyraHumanEngine

engine = SveyraHumanEngine()
avatar = engine.build_parametric(BodyParameters(height=184, waist_width=32))
avatar.export("person.glb")

print(avatar.measurements)   # chest, waist and hip girths, inseam, arm length
```

Supply as few or as many measurements as you have; the rest come from neutral
proportions scaled by height.

## Viewing the result

```bash
cp avatar.glb viewer/threejs/
python -m http.server -d viewer/threejs 8080
```

Orbit, wireframe, vertex normals, ground grid, axes, live vertex and dimension
readout.

## Design

Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). The short version:

- The body is `BodyParameters`. Everything else is a pure function of it.
- The optimiser will move a few hundred cage points, never tens of thousands of
  vertices. That is what keeps this on a laptop CPU.
- An avatar is reproducible from its JSON alone. The photographs are never
  needed twice.
- Vertex AI is an optional try-on provider hanging off the side. A test fails the
  build if core code so much as mentions it.

## Licensing

Every dependency is recorded in [THIRD_PARTY.md](THIRD_PARTY.md) with its
commercial-use status. SMPL, SMPL-X, HMR2 and the CC BY-NC try-on models are
explicitly rejected and the reasons are written down. Nothing gets added without
a row in that table.

## Tests

```bash
.venv/Scripts/python -m pytest -q
```

89 passing, including the Phase 3 acceptance test:
synthetic silhouettes are generated from known parameters and the fitter must
recover them to within 5 percent.
