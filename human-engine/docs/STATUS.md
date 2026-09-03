# Status

What actually runs today, and what is only a designed interface. Nothing in the
"works" column is mocked; nothing in the "not built" column pretends to succeed.

Last verified 2026-09-04 against 65 passing tests and 1 expected failure.

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
| Provider seam | `providers/` | Protocol plus a deterministic mock. Core cannot import a provider; a test enforces it. |
| Garment interface | `garment/interfaces.py` | Collision body, measurements, skeleton, mesh, pose. |
| Collision primitives | `body/anatomy.py` | 14 capsules for cloth to collide against. |
| CLI | `cli.py` | `sveyra build-parametric --height 184 --out person.glb` |
| Debug viewer | `viewer/threejs/` | Orbit, wireframe, normals, grid, axes, live stats. |

### Measured

A 184 cm body at balanced quality: **3,528 vertices, 6,768 triangles, ~19 ms**
on an ordinary laptop CPU, no GPU. The 5-20 s production target has a lot of
headroom, because fitting is not in this number yet.

Verified properties:

- Crown sits at exactly the requested height (error 0.00 cm across 150-210 cm).
- The body stands on the floor, within 0.08 cm.
- Identical parameters produce byte-identical geometry.
- A body rebuilt from `body_parameters.json` alone is identical to the original.
- Waist, hip and chest parameters each move their own measurement.

## Not built

Every one of these raises `NotImplementedYetError` rather than returning
something plausible.

| Phase | Capability | Blocking note |
| --- | --- | --- |
| 2 | Pose, segmentation, face landmarks | Interfaces defined; MediaPipe is an optional extra, not yet wired. |
| 2 | Camera calibration from a photo | Orthographic assumes an upright, centred subject. |
| 3 | **Body fitting from silhouettes** | The core research milestone. Acceptance test already written and failing. |
| 3 | Canonical base mesh + cage deformation | Topology is currently generated, not authored. Blocks garment transfer and morph targets. |
| 4 | Face fitting | |
| 5 | Projective texturing | Until this lands the avatar cannot resemble a specific person. |
| 6 | Hair volumes | |
| 7 | Skinning, corrective shapes, soft tissue | Skeleton and mesh exist but are not bound. |
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

## Running it

```bash
python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"

.venv/Scripts/python -m pytest -q                 # 65 passed, 1 xfailed
.venv/Scripts/python -m sveyra_human.cli info
.venv/Scripts/python -m sveyra_human.cli build-parametric --height 184 --out avatar.glb

# View it
cp avatar.glb viewer/threejs/ && python -m http.server -d viewer/threejs 8080
```
