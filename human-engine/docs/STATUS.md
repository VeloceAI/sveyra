# Status

What actually runs today, and what is only a designed interface. Nothing in the
"works" column is mocked; nothing in the "not built" column pretends to succeed.

Last verified 2026-09-04 against 144 passing tests.

## Works

| Capability | Where | Notes |
| --- | --- | --- |
| Body parameter model | `body/parameters.py` | Height alone fills a full set from neutral proportions. Round-trips through JSON. |
| SVEYRA skeleton | `skeleton/` | 21 joints, our own hierarchy, no SMPL. Bone lengths follow parameters. |
| Cross sections | `body/cross_sections.py` | Superellipse width/depth/exponent, interpolated onto any number of levels. |
| Girth measurement | `body/anatomy.py` | Numerically integrated. Validated against `pi*d` for the circular case. |
| Deformation cage | `body/cage.py` | 12 parts, ~700 control vertices. |
| Surface mesh | `body/mesh_deformer.py` | Lofted from the cage, midpoint subdivision per quality mode. |
| GLB export | `export/gltf.py` | Positions, normals, indices, material. Centimetres converted to metres. |
| JSON sidecars | `export/metadata.py` | Parameters, measurements, skeleton, quality, metadata. |
| Orthographic camera | `camera/projection.py` | Framed from known height. Front, side and back views. |
| Silhouette rasteriser | `camera/projection.py` | Barycentric fill, plus IoU and width profiles. |
| Synthetic harness | `tests/test_synthetic_recovery.py` | Ground-truth silhouettes from known parameters. |
| **Body fitting** | `optimization/` | Silhouettes to `BodyParameters`. Analytic init then least squares under priors. ~0.7 s. |
| Objective terms | `optimization/objective.py` | Proportion, anatomical and smoothness priors, separately weightable. |
| **Person segmentation** | `vision/segmentation.py` | Border-sampled background subtraction. No model, no GPU. IoU >0.95 on plain backgrounds. |
| Capture validation | `capture/validator.py` | Rejects cropped, tiny or unsegmentable views instead of fitting them. |
| Image loading | `capture/image_normalizer.py` | Paths, bytes or arrays. No cloud client. |
| **Photo to avatar** | `engine.build()` | Photographs in, fitted avatar out, end to end. |
| **Skin weights** | `rig/weights.py` | Distance-to-bone falloff, 4 influences per vertex, validated to sum to 1. |
| **Skinned GLB** | `export/skinned_gltf.py` | Joint hierarchy, inverse bind matrices, JOINTS_0/WEIGHTS_0. Poses in a viewer. |
| Dual quaternion skinning | `rig/dqs.py` | CPU posing for measurement. Sign-aligned blending, volume preserving. |
| Collision proxies | `physics/collision_body.py` | 10 capsules with signed distance. Cloth collides with these, not 6,000 triangles. |
| Garment contract | `garment/body_adapter.py` | `SveyraBody` satisfies the runtime-checkable protocol. |
| Provider seam | `providers/` | Protocol plus a deterministic mock. Core cannot import a provider; a test enforces it. |
| Garment interface | `garment/interfaces.py` | Collision body, measurements, skeleton, mesh, pose. |
| Collision primitives | `body/anatomy.py` | 14 capsules for cloth to collide against. |
| CLI | `cli.py` | `sveyra build-parametric --height 184 --out person.glb` |
| Debug viewer | `viewer/threejs/` | Orbit, wireframe, normals, grid, axes, live stats. |

### Measured

| | |
| --- | --- |
| Forward build, 184 cm, balanced | 3,528 vertices, 6,768 triangles, ~19 ms |
| Silhouette fit, 2 views | ~0.7 s, 13-15 objective evaluations, residual ~0.4 cm |
| Photograph to avatar, 2 views | ~0.9 s including segmentation |
| Skinning 3,528 vertices to 18 bones | ~20 ms |
| Rigged GLB | 255 KB, 18 joints |
| Segmentation quality | IoU 0.995 against ground truth on a lit, noisy wall |
| Fit accuracy, torso widths | within 10% across five body types; typically 1-4% |

Both on an ordinary laptop CPU with no GPU, inside the 5-20 s production target.

Verified properties:

- Crown sits at exactly the requested height (error 0.00 cm across 150-210 cm).
- The body stands on the floor, within 0.08 cm.
- Identical parameters produce byte-identical geometry.
- A body rebuilt from `body_parameters.json` alone is identical to the original.
- Waist, hip and chest parameters each move their own measurement.
- Known parameters are recovered from synthetic silhouettes to within 10%.
- Two different bodies do not fit to the same answer.
- Turning the silhouette off makes the fit worse, so the pixels are genuinely used.

## Not built

Every one of these raises `NotImplementedYetError` rather than returning
something plausible.

| Phase | Capability | Blocking note |
| --- | --- | --- |
| 2 | Pose landmarks | MediaPipe adapter written but untested here; fitting does not need pose. |
| 2 | Camera calibration from a photo | Orthographic assumes an upright, centred subject. |
| 3 | Fitting shoulder width and limb girths | Only the six torso width/depth parameters are solved; arms obscure the shoulder band. |
| 3 | Canonical base mesh + cage deformation | Topology is currently generated, not authored. Blocks garment transfer and morph targets. |
| 4 | Face fitting | |
| 5 | Projective texturing | Until this lands the avatar cannot resemble a specific person. |
| 6 | Hair volumes | |
| 7 | Corrective shapes and soft tissue | Skinning works; joints have no corrective morphs, so extreme bends will pinch. |
| 8 | Vertex try-on provider | Config reads env correctly; transport raises. |

## Honest limitations of what does work

- **A parametric body is a proportional model, not a person.** With no
  photographs it is a template at a given height. Every artifact says so in its
  quality warnings, and `source_views` is 0.
- **Neutral proportions are anthropometric rules of thumb**, not a fitted
  dataset. Good enough to be recognisably human, not a measurement claim.
- **Limbs are swept tapered capsules.** Truthful proportions, not truthful
  anatomy. Shoulders and hips have no deltoid or glute shaping yet.
- **Feet are wedges and hands do not exist.** The arm ends at the wrist.
- **Topology changes if cage resolution constants change.** Deterministic for a
  given build, but not yet the stable cross-user topology the design requires.
- **The mesh is not watertight** where limbs meet the torso; parts interpenetrate
  rather than being joined. Fine for viewing and silhouettes, not for physics.
- **Arms attach by overlap.** The shoulder joint is placed just inside the torso
  surface so the limb reads as connected in a silhouette. It is an intersection,
  not a welded seam, and a deltoid shape would be the proper fix.
- **Fitting solves six parameters, not the whole body.** Torso widths and depths
  only. A front view in the rest pose has arms across the shoulder band, so
  shoulder width is not recoverable from it; limb girths are not solved at all.
- **Fitting assumes the subject is bare or close-fitting.** Nothing separates
  clothing from body, so loose garments read as a larger waist.
- **Segmentation assumes a plain-ish background.** It estimates the wall from the
  frame border and keeps what differs. A busy room, a subject the colour of the
  wall, or someone standing against a doorway will defeat it. It reports low
  confidence rather than failing silently, and MediaPipe can be injected for
  harder images.
- **No pose is used.** The fit works from silhouettes alone, so a rotated or
  non-standing subject is not detected and will fit badly.
- **Skin weights are distance-based, not painted.** There is nothing to paint
  onto: the mesh is generated, so a painted map would not survive a change in
  cage resolution. Good for the rest pose and moderate articulation; shoulders
  and hips will pinch under extreme rotation because there are no corrective
  shapes yet.
- **Only the rest pose exists.** `get_pose()` reports `posed: false` rather than
  implying animation is supported.
- **Band sampling takes the widest row per band**, which slightly over-reads
  narrow regions. 64 bands keeps that under a centimetre; coarser banding
  over-estimated the waist by about 10%.

## Running it

```bash
python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"

.venv/Scripts/python -m pytest -q                 # 65 passed, 1 xfailed
.venv/Scripts/python -m sveyra_human.cli info
.venv/Scripts/python -m sveyra_human.cli build-parametric --height 184 --out avatar.glb

# View it
cp avatar.glb viewer/threejs/ && python -m http.server -d viewer/threejs 8080
```
