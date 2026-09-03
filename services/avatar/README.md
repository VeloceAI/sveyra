# Avatar Service

Owns personalized body, face, garment, and accessory visualization workflows.

## First Jobs

- Store avatar profile state
- Manage GLB/glTF avatar assets
- Connect body profile to 3D representation
- Prepare try-on inputs and outputs

## Build Order

Ship 2D before 3D. A hosted 2D try-on backend has no licence risk and needs no
GPUs, and it matches what comparable products actually ship today. Self-hosted
segmentation comes next, because per-image API pricing stops working at volume.
Real 3D is last, and it is the differentiator.

The `AvatarPort` in `backend/app/avatar/` is the seam: backends swap by
`AVATAR_BACKEND` the same way `STORAGE_BACKEND` works.

## Dependencies

| Purpose | Component | Licence |
| --- | --- | --- |
| Garment cut-out and background removal | SAM 3 / SAM 3.1 | SAM Licence — commercial use allowed |
| Body mesh from a single photo | SAM 3D Body | SAM Licence — commercial use allowed |
| Body model unification | SOMA-X (NVIDIA) | Apache 2.0 |
| Interpretable body parameters | Anny (Naver) | Permissive |
| Pose landmarks for measurement | MediaPipe | Apache 2.0 |
| Browser rendering | Three.js, React Three Fiber, Drei | MIT |
| Asset authoring | Blender | GPL — tooling only, not linked |

SAM 3D Body emits an MHR mesh and SOMA-X accepts MHR as an input backend, so
those two compose directly without a SMPL licence anywhere in the chain.

## Not Used

SMPL-X is **not** in this pipeline. Its model files are non-commercial, and a
commercial sub-licence runs through Meshcapade, which Epic Games acquired in
February 2026. See `docs/research/SUPPORTING_REPOS.md` for the full list of
components that are blocked for commercial use.

## Non-Goals

- Cloth physics simulation. Garments are fitted proxy meshes.
- Promising measurement accuracy figures before measuring our own.
