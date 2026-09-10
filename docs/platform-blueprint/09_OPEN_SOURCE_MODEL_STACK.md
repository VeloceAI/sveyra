# Deferred local and open-model research

Status: deferred; not in the active Alta-first build  
Evidence reviewed: 2026-09-08

Product decision (2026-09-08): do not implement or deploy the models below while
the Alta-class product loop is being built. They would add GPU infrastructure,
operations, and dependency/checkpoint licence review. Active developers must use
the managed-services plan in
[`07_EXTERNAL_SERVICES.md`](07_EXTERNAL_SERVICES.md). The material below is kept
only so earlier research is not lost; none of its checkpoints may be picked up
without a new architecture decision.

SVEYRA does not require Vertex AI to operate. The product shell, closet,
deterministic stylist, saved looks, personal appearance profile, canonical 3D
human, rig, motion constraints, and Three.js viewer already run locally. External
models accelerate image understanding and generated visual previews; they are
not the product's source of truth for identity, measurements, size, or fit.

"Open source", "open weights", and "source available" are not interchangeable.
Every code repository, checkpoint, base model, parser, and training dataset must
be reviewed independently before commercial deployment.

## Archived candidate research

| Capability | First local candidate | Licence/status | Decision |
| --- | --- | --- | --- |
| Single-garment cutout | Meta SAM 2 | code and checkpoints Apache-2.0 | approved for benchmark |
| Concept-prompted garment masks | Meta SAM 3 / 3.1 | custom SAM License; CUDA 12.6+ documented | benchmark after infrastructure and legal review |
| High-resolution flat-lay cutout | BiRefNet | repository MIT; each selected checkpoint still needs review | benchmark against SAM on difficult edges |
| Garment attributes and grounding | Qwen3-VL-2B-Instruct | official model card Apache-2.0 | approved for a schema-constrained benchmark |
| Exact color features | OpenCV plus Lab/OKLab implementation | Apache-2.0 for OpenCV | deterministic authority after calibration |
| Pose/capture landmarks | MediaPipe, then MMPose where needed | Apache-2.0 code; audit exact checkpoints | local capture-coaching candidates |
| Parametric human | SVEYRA Human Engine; evaluate Anny as a reference/adapter | SVEYRA math plus audited CC0 canonical assets; Anny code Apache-2.0 and listed assets CC0 | keep SVEYRA model authoritative |
| Photo-to-body initialization | evaluate SAM 3D Body and Multi-HMR 2/Anny | source available; model-specific licence and checkpoint audit required | optional seed only, never measurement truth |
| Photoreal 2D try-on | FASHN VTON v1.5 | repository Apache-2.0; inherited human-parser/base-model terms require review | first self-hosted benchmark |
| Browser rendering | Three.js | MIT | already in use |

Official references:

- [Meta SAM 2](https://github.com/facebookresearch/sam2)
- [Meta SAM 3](https://github.com/facebookresearch/sam3)
- [BiRefNet](https://github.com/ZhengPeng7/BiRefNet)
- [Qwen3-VL](https://github.com/QwenLM/Qwen3-VL)
- [Qwen3-VL-2B-Instruct model card](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct)
- [FASHN VTON v1.5](https://github.com/fashn-AI/fashn-vton-1.5)
- [FASHN Human Parser](https://github.com/fashn-AI/fashn-human-parser)
- [Anny](https://github.com/naver/anny)
- [SAM 3D Body](https://github.com/facebookresearch/sam-3d-body)
- [Multi-HMR 2](https://github.com/naver/multi-hmr2)

## Archived provider-off design

```text
private uploaded image
  -> quality and malware/decode checks
  -> local mask worker (SAM/BiRefNet)
  -> deterministic masked color and image features
  -> local Qwen vision worker proposes taxonomy-bound attributes
  -> Pydantic validation and confidence policy
  -> user confirmation/correction
  -> versioned closet record with per-field provenance
```

For visual try-on:

```text
consented person/avatar render + exact garment image
  -> TryOnPort job
  -> self-hosted FASHN adapter or optional hosted adapter
  -> identity/product preservation checks
  -> private generated asset
  -> UI label: AI visual preview - not a fit guarantee
```

The API process must not load these models. GPU inference runs in isolated
workers behind internal HTTP or queue contracts. This keeps the web/API service
small, allows CPU development, and makes provider changes reversible.

## Why the shortlist is split

Segmentation and understanding are different jobs. A mask model is better at
edges, transparency, occlusion, and separating the garment from its background.
A vision-language model is useful for open-vocabulary category, pattern,
material, season, and occasion proposals, but it must not invent authoritative
color, size, fabric composition, or product identity.

Generated try-on is another separate job. It produces plausible pixels; it does
not produce garment patterns, physical cloth, body measurements, pressure, ease,
or size guarantees. Metric fit stays in the SVEYRA body and garment simulation
track.

## Explicit exclusions and cautions

- Do not use CatVTON, IDM-VTON, or StableVITON in a commercial product under
  their current CC BY-NC-SA terms.
- Do not treat a repository-level licence as clearance for every checkpoint or
  training dataset.
- FASHN VTON v1.5 is promising, but its documented human parser inherits an
  NVIDIA source-code licence. Legal must review the exact dependency bundle and
  deployment/redistribution mode before release.
- SAM 3 and SAM 3D Body use Meta's custom SAM License, not Apache-2.0. Preserve
  the license and perform product/privacy review before deployment.
- Keep biometric/person images private, consent-scoped, region-controlled, and
  deletable regardless of whether inference is local or hosted.

## Deferred checkpoints (blocked by scope decision)

- [ ] `OSS-01` Expand `VisionPort` output with provider/model version, mask asset,
  per-field provenance, latency, and calibrated confidence.
- [ ] `OSS-02` Add an isolated `SegmentationPort` plus deterministic fixture
  adapter; never import PyTorch into FastAPI routes or handlers.
- [ ] `OSS-03` Build the rights-cleared garment benchmark: flat lay, hanger,
  worn, clutter, multiple items, lace, transparency, straps, fringe, sequins,
  reflections, dark-on-dark, and white-on-white.
- [ ] `OSS-04` Benchmark SAM 2 and BiRefNet for mask IoU, boundary score,
  correction time, latency, VRAM, and accepted-output cost.
- [ ] `OSS-05` Add a Qwen3-VL-2B worker adapter returning only the versioned
  garment schema; reject malformed or taxonomy-invalid output.
- [ ] `OSS-06` Compute color from the approved mask in a calibrated color
  pipeline; compare with expert labels using Delta E rather than VLM prose.
- [ ] `OSS-07` Define `TryOnPort`, job persistence, consent, idempotency,
  retention, and deterministic golden fixtures.
- [ ] `OSS-08` Benchmark FASHN VTON v1.5 for identity/product preservation,
  supported categories, artifacts, latency, VRAM, throughput, and licence risk.
- [ ] `OSS-09` Run the same private try-on evaluation through the optional Vertex
  adapter; select by quality, privacy, cost, reliability, and portability.
- [ ] `OSS-10` Evaluate Anny/SAM 3D Body/Multi-HMR 2 only as photo-to-parameter
  initialization against SVEYRA's metric multi-view acceptance suite.

No production adapter passes its checkpoint from a showcase image. It must pass
the private benchmark, commercial-rights review, privacy review, failure UI, and
provider-off degradation test.
