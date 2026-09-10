# Third-Party Dependencies

Every dependency is recorded here with its commercial-use status before it is
introduced. SVEYRA is intended to become commercial software, so a permissive
licence is a requirement, not a preference.

## Core (required to build a parametric human)

| Name | Version | Licence | Source | Commercial use | Purpose |
| --- | --- | --- | --- | --- | --- |
| numpy | >=2.0 | BSD-3-Clause | https://github.com/numpy/numpy | Yes | Array maths, geometry |
| pygltflib | >=1.16 | MIT | https://gitlab.com/dodgyville/pygltflib | Yes | glTF/GLB serialisation |
| scipy | >=1.14 | BSD-3-Clause | https://github.com/scipy/scipy | Yes | Least-squares fitting, morphology |
| pillow | >=10.0 | MIT-CMU | https://github.com/python-pillow/Pillow | Yes | Decoding photograph files |

## Planned, not yet introduced (Phase 2+)

| Name | Licence | Commercial use | Purpose |
| --- | --- | --- | --- |
| mediapipe | Apache-2.0 | Yes | Pose and face landmarks |
| opencv-python-headless | Apache-2.0 | Yes | Image processing |

## Explicitly rejected

| Name | Licence | Reason |
| --- | --- | --- |
| SMPL / SMPL-X | Non-commercial research licence | Commercial route runs through Meshcapade, acquired by Epic Games Feb 2026. The SVEYRA skeleton and body model are our own precisely to avoid this. |
| HMR2 / 4D-Humans | Research, depends on SMPL | Heavy GPU model; carries the SMPL dependency. |
| IDM-VTON / StableVITON / CatVTON | CC BY-NC-SA 4.0 | Non-commercial. |

No base mesh, dataset or pretrained weight may be added without a row in this
table.

## Imported assets

| Name | Version / source revision | Licence | Exact source | Purpose |
| --- | --- | --- | --- | --- |
| MakeHuman HM08 body mesh (via MPFB) | MPFB `437dd513888a92399d1d3200d2e80859fae55abc` | CC0-1.0 | `src/mpfb/data/3dobjs/base.obj`, group `body`, SHA-256 `bea00279464133e86b634220cd2774ebf3b470de280d11222a6b2269e4a8d950` | Provisional fixed canonical body topology |
| MakeHuman standard rig and weights (via MPFB) | MPFB `437dd513888a92399d1d3200d2e80859fae55abc` | CC0-1.0 | `rig.default.json` SHA-256 `3dd01e5e547439f54adbb4317173cb6c36cb917ff01f0dea9f985abebb8100f2`; `weights.default.json` SHA-256 `e2623c088b05eb0677d04ff4ae701c98264634ade7b8a6393f437d50f84e04c2` | Converted 163-joint canonical rest rig and skin weights |

The derived file, transformation, topology audit, and derived hash are in
`src/sveyra_human/assets/canonical/PROVENANCE.json`. The upstream CC0 notice is
preserved next to the asset. No MPFB program code is copied or used at runtime.

## Evaluated local references (not dependencies)

These projects exist under `C:\VeloceAI\tools`. Presence on disk is not
permission to copy program code into SVEYRA.

| Name | Licence observed locally | Decision |
| --- | --- | --- |
| three-vrm | MIT | Candidate runtime dependency; preserve its notice. |
| makehuman.js | AGPL code; generally CC0 graphical assets | Code is reference-only. Its local `base/3dobjs/base.obj` has a conflicting AGPLv3 file header and was rejected. |
| MPFB | GPL code; CC0 graphical assets | Code is reference-only. The explicitly CC0 HM08 `body` group was reviewed and imported as the asset recorded above. |
| mannequin.js | GPL-3.0 | Reference-only; do not copy or adapt source into the proprietary core. |
| bodyapps-viz | LGPL-3.0 | Reference-only by default; direct linking or modification needs a compliance decision. |

See `docs/research/LOCAL_REFERENCE_AUDIT.md` for the clean-room procedure and
the open audit of the existing development viewer.
