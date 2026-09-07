# SVEYRA Human Engine

Realistic, rigged 3D humans from a handful of photographs, without CUDA, SMPL,
diffusion models or a cloud round trip in the core reconstruction.

The current procedural body is a research foundation, not the final visual
target. The photoreal, measurable, animatable product contract and its staged
roadmap are defined in [`docs/product/DIGITAL_HUMAN.md`](../docs/product/DIGITAL_HUMAN.md).

**AI understands the photographs. Mathematics constructs the human.**

A body here is a few dozen named measurements, not a neural network's opaque
output. That makes it inspectable, storable, editable, reproducible, and free of
research-only licences.

## Status

The existing CPU pipeline fits a coarse procedural avatar. M1 of the photoreal
program is complete, and M2 now includes a reviewed watertight canonical body,
a 163-joint skin, portable rigged GLB export, and topology-preserving deformation
from 18 cross-sectional body parameters. It is not yet a perfect human clone:
photo identity fitting, full facial anatomy and controls, physical skin/eyes/hair,
and production rigging are active milestones.

See [docs/STATUS.md](docs/STATUS.md) for what works, what is shallow, and why.

## Quick start

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"

.venv/Scripts/python -m sveyra_human.cli build-parametric --height 184 --out avatar.glb

# View the fixed, detailed canonical topology and its 163-joint rest rig
.venv/Scripts/python -m sveyra_human.cli build-canonical-seed --height 184 --out canonical.glb
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

The canonical seed can also be loaded directly:

```python
from sveyra_human import BodyParameters, deform_canonical_human

body, rig, report = deform_canonical_human(
    BodyParameters(height=184, chest_width=42, waist_width=35, hip_width=40)
)
surface = body.to_surface_mesh(with_uv=True)
```

## Viewing the result

```bash
cp avatar.glb viewer/threejs/
python -m http.server -d viewer/threejs 8080
```

Orbit, wireframe, vertex normals, ground grid, axes, live vertex and dimension
readout.

## Pipeline

```
photographs -> segment -> fit body -> shape face -> texture -> hair -> rig -> GLB
```

Every stage is replaceable and every stage refuses rather than inventing. No
usable front view means no avatar; no visible hair means a bald head, not
default hair; no side view means depth is inferred and the quality report says
so.

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

The suite covers reconstruction invariants, export, the digital-human contract,
and the canonical mesh's licence-pinned topology and UV conversion.
