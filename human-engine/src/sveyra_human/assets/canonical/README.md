# Canonical body asset

`hm08_body_cc0.obj` is the provisional fixed-topology seed for SVEYRA's M2
reconstruction work. It is a deterministic body-only derivative of MPFB's
bundled HM08 base mesh. The upstream asset explicitly states that it was
released under CC0; the complete notice is preserved in `CC0-1.0.md` and exact
source and derived hashes are recorded in `PROVENANCE.json`.

This asset establishes stable, watertight body connectivity and UVs. It does
not by itself meet SVEYRA's photoreal digital-human gate.

`hm08_rig_v0.1.json` is the matching converted rest rig and four-influence skin.
It retains 163 body, finger, toe, eye, jaw, tongue, and facial bones. All 13,380
canonical vertices have normalized weights. The converter removes weights for
the source OBJ's helper geometry and records every conversion statistic in
`PROVENANCE.json`.

Production work still needs separate eyes, mouth cavity, teeth, tongue meshes,
identity deformation, PBR appearance, hair, local bone-axis normalization,
corrective shapes, facial blendshapes, animation clips, and validated LODs.

The OBJ is in its source coordinate convention: Y-up, +Z-forward, and ten OBJ
units per metre. Engine ingestion converts it to centimetres. Export code must
apply the runtime convention declared by the digital-human manifest.

Reproduce the derivative from the reviewed local checkout:

```powershell
.\.venv\Scripts\python.exe human-engine\tools\audit_canonical_mesh.py `
  C:\VeloceAI\tools\mpfb2\src\mpfb\data\3dobjs\base.obj `
  --group body `
  --extract human-engine\src\sveyra_human\assets\canonical\hm08_body_cc0.obj
```

Reproduce the rig conversion:

```powershell
.\.venv\Scripts\python.exe human-engine\tools\import_canonical_rig.py `
  --body C:\VeloceAI\tools\mpfb2\src\mpfb\data\3dobjs\base.obj `
  --rig C:\VeloceAI\tools\mpfb2\src\mpfb\data\rigs\standard\rig.default.json `
  --weights C:\VeloceAI\tools\mpfb2\src\mpfb\data\rigs\standard\weights.default.json `
  --group body `
  --out human-engine\src\sveyra_human\assets\canonical\hm08_rig_v0.1.json
```
