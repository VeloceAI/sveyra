# Supporting Repositories

These repositories may support SVEYRA development. Before commercial use, check license, model weights, datasets, patents, and hosted API terms.

| Area | Repository | Use | Priority | Notes |
| --- | --- | --- | --- | --- |
| Body / face / hands | https://github.com/google-ai-edge/mediapipe | Pose, face, hands, makeup, rings, accessories | 5 | Strong MVP candidate |
| Body / garment segmentation | https://github.com/facebookresearch/sam2 | Person, garment, shoe, accessory, hair segmentation | 5 | Check model terms |
| CV utilities | https://github.com/opencv/opencv | Image, video, color, calibration, preprocessing | 5 | Foundational |
| Pose estimation | https://github.com/open-mmlab/mmpose | Whole-body pose and 3D mesh research | 4 | Useful for advanced body work |
| ML runtime | https://github.com/pytorch/pytorch | Training and inference | 5 | Foundational |
| 3D human body | https://github.com/vchoutas/smplx | Parametric avatar body, face, hands | - | **BLOCKED - non-commercial.** Commercial sub-license runs through Meshcapade, acquired by Epic Games Feb 2026. Use SAM 3D Body + SOMA-X instead. |
| 3D rendering research | https://github.com/facebookresearch/pytorch3d | Meshes, rendering, body fitting | 4 | Research-heavy |
| 3D ML | https://github.com/NVIDIAGameWorks/kaolin | Meshes, point clouds, rendering | 3 | Later-stage |
| 3D geometry | https://github.com/isl-org/Open3D | Reconstruction and geometry processing | 4 | Good for pipelines |
| 3D reconstruction | https://github.com/colmap/colmap | Multi-view product reconstruction | 4 | Useful for product assets |
| 3D asset tooling | https://github.com/blender/blender | Modeling, rigging, simulation, rendering | 5 | Core asset workflow |
| Asset format | https://github.com/KhronosGroup/glTF | Runtime 3D asset format | 5 | Use GLB/glTF for web delivery |
| Browser 3D | https://github.com/mrdoob/three.js | Avatar and product rendering | 5 | Frontend 3D base |
| React 3D | https://github.com/pmndrs/react-three-fiber | React integration for Three.js | 5 | Preferred web 3D integration |
| React 3D helpers | https://github.com/pmndrs/drei | Cameras, controls, loaders, environments | 5 | Speeds MVP |
| 2D try-on | https://github.com/yisol/IDM-VTON | 2D virtual try-on research | - | **BLOCKED - CC BY-NC-SA 4.0, non-commercial.** Research reference only. |
| 2D try-on | https://github.com/rlawjdghek/StableVITON | Diffusion try-on research | - | **BLOCKED - CC BY-NC-SA 4.0, non-commercial.** Research reference only. |
| Backend | https://github.com/fastapi/fastapi | API layer | 5 | Default backend |

## Commercially Cleared Avatar Stack

Verified 2026-09-03. These replace the blocked entries above.

| Area | Repository | Use | Priority | License |
| --- | --- | --- | --- | --- |
| Garment segmentation | https://github.com/facebookresearch/sam3 | Cut-out and background removal for the digital closet | 5 | SAM License - commercial use allowed |
| 3D human body | https://github.com/facebookresearch/sam-3d-body | Full-body mesh from a single image, MHR rig | 5 | SAM License - commercial use allowed |
| Body model unification | https://github.com/NVlabs/SOMA-X | One topology and skeleton across SMPL / SMPL-X / MHR / Anny | 5 | Apache 2.0 |
| Parametric body | https://github.com/naver/anny | Interpretable shape parameters, WHO-calibrated | 4 | Permissive |
| Hosted 2D try-on | Vertex AI Virtual Try-On | Phase 1 avatar with no self-hosting | 4 | Commercial, paid per image |

SAM 3D Body outputs an MHR mesh and SOMA-X accepts MHR as an identity backend,
so the two compose without pulling in a SMPL license.

CatVTON is sometimes suggested alongside IDM-VTON and StableVITON. It is also
CC BY-NC-SA 4.0. Do not add it.
