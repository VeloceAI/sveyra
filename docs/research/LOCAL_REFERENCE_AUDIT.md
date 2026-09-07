# Local Digital-Human Reference Audit

Reviewed from the licence files under `C:\VeloceAI\tools` on 2026-09-05.
This is an engineering reuse policy, not legal advice. Any production import
still requires review of the exact file, its history, and bundled notices.

| Repository | Local licence finding | SVEYRA use |
| --- | --- | --- |
| `three-vrm` | MIT | May be used as a dependency with the copyright and licence notice preserved. Useful for humanoid runtime, expressions, gaze, and animation. |
| `makehuman.js` | Program code AGPL-3.0-or-later; bundled graphical assets generally described as CC0-1.0 | Do not copy program code. The checked-out `base/3dobjs/base.obj` has its own AGPLv3 header, so that exact copy was rejected. |
| `mpfb2` | Program code GPL-3.0-or-later; bundled graphical assets described as CC0-1.0 | Reference code only. Its HM08 base mesh explicitly states CC0 and the reviewed `body` group is the source of SVEYRA's provisional topology seed. |
| `mannequin.js` | GPL-3.0 | Reference behavior only. Do not copy or adapt its source into proprietary SVEYRA code. |
| `bodyapps-viz` | LGPL-3.0 | Reference its measurement and morph vocabulary. Direct use or modification requires a separate compliance decision. Do not copy code into the core by default. |

## Clean-room rule

For copyleft reference code:

1. Record the behavior or interface that SVEYRA needs without copying source.
2. Write SVEYRA tests from product requirements and mathematical definitions.
3. Implement independently in SVEYRA naming and architecture.
4. Record the reference as `kind="reference"`, `copied=false` in provenance.
5. Do not paste source, tuned constant tables, comments, or asset data.

For an asset described as CC0:

1. Identify the exact source file and repository commit.
2. Confirm that file falls within the repository's asset definition.
3. Check for a conflicting per-file notice or third-party origin.
4. Add it to `human-engine/THIRD_PARTY.md` before committing the asset.
5. Store an asset-level `ProvenanceRecord` with origin, licence, and source path.

## Imported HM08 body group

The selected source is MPFB commit
`437dd513888a92399d1d3200d2e80859fae55abc`, file
`src/mpfb/data/3dobjs/base.obj`, SHA-256
`bea00279464133e86b634220cd2774ebf3b470de280d11222a6b2269e4a8d950`.
Unlike the conflicting MakeHuman.js copy, this exact file says it was
explicitly released as CC0 in September 2020.

Only group `body` was retained. SVEYRA's original audit/extraction tool removed
helper and joint geometry and remapped indices. The result has 13,380 vertices,
13,378 quads, one connected component, complete UVs, no boundary or
non-manifold edges, consistent winding, and no degenerate faces. The preserved
notice and machine-readable provenance live under
`human-engine/src/sveyra_human/assets/canonical/`.

## Existing viewer audit

The current SVEYRA Three.js viewer describes several shapes, postures, and
constants as derived from or matching `mannequin.js`. Because `mannequin.js` is
GPL-3.0, this code must be reviewed before any proprietary distribution. The
safe resolution is to retain the SVEYRA engine interfaces and replace the
viewer geometry and posture implementation from anatomical requirements and
our own tests.

The development viewer is not the target renderer for the photoreal product.
No new work should deepen this dependency while the audit is open.
