# Third-Party Dependencies

Every dependency is recorded here with its commercial-use status before it is
introduced. SVEYRA is intended to become commercial software, so a permissive
licence is a requirement, not a preference.

## Core (required to build a parametric human)

| Name | Version | Licence | Source | Commercial use | Purpose |
| --- | --- | --- | --- | --- | --- |
| numpy | >=2.0 | BSD-3-Clause | https://github.com/numpy/numpy | Yes | Array maths, geometry |
| pygltflib | >=1.16 | MIT | https://gitlab.com/dodgyville/pygltflib | Yes | glTF/GLB serialisation |

## Planned, not yet introduced (Phase 2+)

| Name | Licence | Commercial use | Purpose |
| --- | --- | --- | --- |
| mediapipe | Apache-2.0 | Yes | Pose and face landmarks |
| opencv-python-headless | Apache-2.0 | Yes | Image processing |
| scipy | BSD-3-Clause | Yes | Optimisation (L-BFGS-B, least_squares) |

## Explicitly rejected

| Name | Licence | Reason |
| --- | --- | --- |
| SMPL / SMPL-X | Non-commercial research licence | Commercial route runs through Meshcapade, acquired by Epic Games Feb 2026. The SVEYRA skeleton and body model are our own precisely to avoid this. |
| HMR2 / 4D-Humans | Research, depends on SMPL | Heavy GPU model; carries the SMPL dependency. |
| IDM-VTON / StableVITON / CatVTON | CC BY-NC-SA 4.0 | Non-commercial. |

No base mesh, dataset or pretrained weight may be added without a row in this
table.
