# SVEYRA Human Engine - Architecture

## The idea

Most photo-to-avatar systems hand the whole problem to a large neural network
and accept whatever body comes back. This engine splits the problem in two:

- **Lightweight vision answers "where are the human features?"** Landmarks,
  silhouettes, masks. Small models, CPU-friendly, replaceable.
- **Mathematics answers "what are this person's dimensions, and what shape is
  that?"** Cross sections, anatomical volumes, a deformation cage, an optimiser.

The consequence that matters commercially: the body is a few dozen numbers, not
a network's opaque output. Those numbers are inspectable, storable, editable,
reproducible, and carry no model licence.

## Layers

```
Capture -> Vision -> Camera -> Skeleton -> Measurements -> Body model
       -> Cage -> Surface -> Face -> Texture -> Hair -> Rig -> Physics -> GLB
```

Each layer is a module with an interface. Providers (Vertex and anything after
it) hang off the side, never in the middle.

## Rules that shape the code

**The body is parameters.** `BodyParameters` is the source of truth. The
skeleton, cage, mesh and measurements are all pure functions of it. Two builds
from the same parameters are byte-identical, which is asserted in the tests.

**The optimiser never touches vertices.** Fitting solves for a few dozen
parameters that produce a cage of a few hundred control points. It never solves
for the tens of thousands of surface vertices independently. This is what keeps
reconstruction on a laptop CPU instead of a GPU.

**Photographs are not needed twice.** Everything required to rebuild an avatar
is written to `body_parameters.json`. A test asserts that a body rebuilt from
that JSON alone is identical to the original.

**Vendor neutrality is structural, not aspirational.** A test walks the core
packages and fails if any of them mention `providers.vertex` or `google.cloud`.
Removing Vertex is deleting a directory, not a refactor.

**Unbuilt means unbuilt.** Stages that do not exist raise
`NotImplementedYetError`. `engine.build()` with four photographs refuses rather
than quietly returning a neutral body that ignored them.

## Key representations

### Cross sections

A body is a stack of horizontal slices. Each slice carries a width, a depth and
a shape exponent. Front photographs constrain width, side photographs constrain
depth, and the exponent lets a ribcage and a waist be different shapes rather
than both being forced into an ellipse.

The exponent is a superellipse power: `2.0` is an ellipse, higher is squarer.
Girth is integrated numerically from the outline, because a superellipse has no
closed-form perimeter. A test checks that the circular case matches `pi*d`.

### The cage

A few hundred control vertices arranged as rings per body part. This is what an
optimiser moves. The visible mesh is lofted from it and subdivided for export.

The cage exists so that fitting cost is independent of render resolution.
Subdivision raises triangle count without moving the surface, which a test
asserts by comparing bounds before and after.

### Camera

Orthographic for now, framed from the person's known height. Exact for a distant
camera, trivially invertible, and it lets the fitting maths be validated before
lens estimation is in the way. Perspective refinement is Phase 2.

## The Phase 3 acceptance test

`tests/test_synthetic_recovery.py` already generates ground-truth silhouettes
from known parameters. The recovery test that consumes them is written and
marked `xfail(strict=True)`: it fails today because no fitter exists, and it will
fail loudly if someone marks it passing without one.

This is deliberate. Phase 3 has a numeric target from its first commit rather
than being judged by eye.

## Where Vertex fits

```
photos ──┬──> Human Engine ──> 3D avatar (identity, fit, measurements, animation)
         └──> TryOnProvider ──> 2D photoreal preview
```

Vertex supplies immediate photorealism. The engine supplies persistent
interactive identity. Vertex output is never the authority on body geometry.

## Deliberately deferred

Cage deformation of a fixed canonical base mesh is the significant one. V1 lofts
the cage directly, so topology is deterministic but generated rather than
authored. Consistent cross-user topology is what garment transfer, morph targets
and shared UVs depend on, so it is the first thing Phase 3 should address.
`assets/base_mesh/` is reserved for it.
