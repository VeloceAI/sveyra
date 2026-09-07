# Digital Human Baseline

Measured against the `DigitalHumanManifest` 1.0 acceptance gate on 2026-09-05.
This document prevents the existing procedural avatar from being mistaken for
the photoreal product target.

## What the current engine contributes

- metric height and named body parameters
- deterministic topology across generated bodies
- torso measurement fitting from silhouettes
- a body skeleton, skin weights, pose solving, and anatomical joint limits
- projective colour texture from supplied photographs
- GLB export and provider-neutral product integration
- capture validation and confidence warnings

These components remain useful inputs and evaluation tools.

## Why it does not pass

| Gate | Current state | Required direction |
| --- | --- | --- |
| Capture | A front photo is sufficient; extra views are optional | Guided multi-view body and close face capture |
| Geometry | Generated parts overlap and are not watertight | One canonical watertight surface with stable LODs |
| Anatomy | Hands are proportional viewer geometry; feet and face are coarse | Full hands, feet, eyes, mouth cavity, teeth, and tongue |
| Face | Front-landmark widths; no complete depth identity | Multi-view high-resolution head and face reconstruction |
| Rig | Body joints only; no production finger or facial controls | Fingers, gaze, eyelids, jaw, tongue, and 52+ blendshapes |
| Deformation | Distance-based skinning without correctives | Joint correctives and soft-tissue behavior |
| Skin | Projected colour retains scene illumination | Lighting-neutral albedo, normal, roughness, and subsurface maps |
| Hair | Seven coarse shells | Reconstructed cards, strands, or validated neural hair |
| Evidence | Overall warnings, limited region accounting | Per-region observed/measured/inferred confidence |

## M2 topology seed

The first M2 import is now present at
`src/sveyra_human/assets/canonical/hm08_body_cc0.obj`. It is a body-only derivative of the
explicitly CC0 HM08 asset in MPFB. An original SVEYRA parser and audit tool
proved:

- 13,380 vertices and 13,378 quads;
- one connected, watertight component;
- complete UV coverage;
- zero boundary, non-manifold, inconsistent-winding, or degenerate faces;
- exact upstream commit, source hash, derived hash, and preserved CC0 notice.

The asset is hash-pinned and can now be loaded in centimetres, scaled to exact
standing height without changing topology, converted across OBJ UV seams, and
exported as a skinned GLB with `sveyra build-canonical-seed`.

The matching MPFB standard rig is now converted and hash-pinned. It has 163
bones covering the body, fingers, toes, eyes, jaw, tongue, and facial regions.
The original SVEYRA converter removed 17,473 helper-only weight entries, capped
portable glTF skinning to the strongest four influences, renormalized every
body vertex, and retained exact source and derived hashes. The exported GLB can
be posed and the browser viewer exposes a skeleton overlay and arm-motion test.

This is a rest-rig milestone, not the M5 animation gate: source roll data is
retained, but canonical local bone axes, corrective shapes, facial blendshapes,
motion retargeting, and animation evaluation remain outstanding.

The first canonical measurement fitter now deforms that body and rest rig
together. It uses the existing skin weights to blend semantic torso, head, arm,
and leg deformation fields while keeping all 13,380 vertex indices, faces, UVs,
and skin influences fixed. Eighteen cross-sectional dimensions are supported;
unsafe ratios are bounded and reported. Limb/torso lengths, calibrated photo
landmarks, and surface identity are still future evidence-gated stages, so this
does not yet claim likeness.
