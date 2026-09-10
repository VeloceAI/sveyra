# External Services and Infrastructure

Verified against linked official documentation on 2026-09-08. Provider models,
regions, prices, quotas, terms, and retirement dates can change; re-verify them at
implementation and launch.

## Decision summary

| Capability | Decision | Why |
| --- | --- | --- |
| Private media | Google Cloud Storage through existing `StoragePort` | already designed; opaque references and signed access |
| 2D visual try-on | integrate Google `virtual-try-on-001` behind `TryOnPort` | managed GA API avoids a self-hosted GPU stack; output remains a visual preview |
| Garment attributes | integrate managed Gemini 3.1 Flash-Lite behind `VisionPort` | inexpensive multimodal schema proposals; user confirmation remains mandatory |
| Garment segmentation | pilot Photoroom Remove Background behind `SegmentationPort` | dedicated managed alpha/RGBA output at a published $0.02 per successful call; preserve originals |
| Catalog visual match | Cloud Vision Product Search is a candidate only for indexed catalogs | apparel matching, not full garment understanding |
| Capture coaching | MediaPipe Pose/Face candidate on device | landmarks/face controls useful for quality, not metric truth |
| Colour science | implement standards-based pipeline; no external API is the authority | calibration and protocol determine accuracy |
| Metric human/cloth | SVEYRA human engine plus evaluated compute/models | Vertex VTO does not create metric 3D or fit reports |
| Weather/calendar | select behind ports after country/privacy requirements | avoid early vendor coupling |
| Commerce/catalog | select retailer/affiliate feeds per launch market | inventory, variants, charts and rights differ by provider |

No public evidence has been found that proves which private AI provider Alta uses.
Do not base SVEYRA architecture or claims on that assumption.

## Alta-first managed-services decision

The active build does not deploy self-hosted vision or try-on models. The local
and open-model shortlist is retained only as deferred research. Alta's public
Meta case study confirms Segment Anything in Alta's segmentation workflow; it
does not establish that Alta uses Google Vertex. Google is SVEYRA's managed
implementation choice because it minimizes infrastructure work.

Current planning prices in USD:

| Operation | Published/assumed unit | Planning cost |
| --- | --- | --- |
| Virtual try-on | Google published price per output image | $0.06 |
| 1,000 requested previews, one output each | 1,000 x $0.06 | $60 |
| 1,000 previews, four alternatives each | 4,000 x $0.06 | $240 |
| 10,000 requested previews, one output each | 10,000 x $0.06 | $600 |
| Photoroom background removal | published Basic price per successful image | $0.02 |
| 10,000 closet cutouts | 10,000 x $0.02 | $200 |
| Garment tagging with Gemini 3.1 Flash-Lite, global endpoint | $0.25/M input tokens + $1.50/M text output tokens | usage based |
| 10,000 garment tags on global | assumed 1,000-2,000 input and 200-400 output tokens each | about $5.50-$11.00 |

The garment-tagging row is an estimate, not a Google per-image price. Record the
actual token count and accepted-output rate during the pilot. Storage, network,
retry, moderation, and background-removal charges are additional. Google
currently prices the non-global Gemini 3.1 Flash-Lite endpoint 10% above
global ($0.275/M input and $1.65/M text output), so use the correct endpoint in
the live calculator. Do not call Virtual Try-On while scrolling or automatically
generating daily outfits; call it after the user taps Preview, default to one
output, cache by person/garment input hash, and require another explicit action
to generate alternatives.

## Google Vertex AI Virtual Try-On

### Current capability

The official model is `virtual-try-on-001`. Google documents an input person
image plus product image and generated try-on image output. The published model
card lists:

- GA status;
- PNG/JPEG inputs;
- maximum two input images per prompt;
- maximum 7 MB per file for inline/console upload;
- one to four output images;
- output aspect ratio/resolution matching the input;
- C2PA content credentials support;
- Pay-as-you-go and provisioned-throughput options in listed regions;
- a currently published retirement date of 2027-01-20.

The official pricing page currently lists Virtual Try-On at USD 0.06 per output
image. Treat this as a planning value only and build a live cost calculator before
launch. The model card currently lists a 2027-01-20 retirement date, so the model
ID must stay configurable and the adapter requires a migration test.

Official references:

- [Virtual Try-On model card](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/vto/virtual-try-on-001)
- [Generate Virtual Try-On images](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/generate-virtual-try-on-images)
- [Vertex AI release notes](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/release-notes)
- [Generative AI pricing](https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing)
- [Prediction REST method](https://cloud.google.com/vertex-ai/generative-ai/docs/reference/rest/v1/projects.locations.endpoints/predict)

### Correct product role

Use Vertex for `generated_visual_preview` only. It does not return:

- 3D body geometry or a persistent avatar;
- body or garment measurements;
- pattern/material parameters;
- pressure, strain, ease or range-of-motion evidence;
- a guaranteed size or physical fit.

The UI disclosure is: `AI visual preview - not a fit guarantee`.

### Required cloud setup

- Google Cloud organization/project with billing and a chosen supported region;
- Vertex AI API enabled and publisher model access confirmed;
- service-to-service Application Default Credentials or workload identity;
- least-privilege service account for prediction and only the required buckets;
- private input/output buckets with uniform access, encryption policy, lifecycle,
  retention/deletion, audit logs and region alignment;
- budget alerts, quota/concurrency controls and per-feature kill switch;
- DPA/terms/privacy review for biometric/person images and supported countries;
- zero-data-retention review and any required abuse-monitoring exception process;
- provider incident, model retirement and migration runbook.

Google states that managed Vertex data is not used to train/fine-tune models
without permission, but its zero-data-retention documentation describes limited
retention scenarios and actions customers must take. Legal/security must validate
the exact account configuration rather than relying on a marketing summary.

- [Vertex AI and zero data retention](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/vertex-ai-zero-data-retention)

### Server configuration contract

Names only; never commit values or service-account JSON:

```text
TRYON_BACKEND=stub|vertex
GOOGLE_CLOUD_PROJECT=
GOOGLE_CLOUD_LOCATION=
VERTEX_TRYON_MODEL_ID=virtual-try-on-001
VERTEX_TRYON_OUTPUT_BUCKET=
VERTEX_TRYON_TIMEOUT_SECONDS=
VERTEX_TRYON_MAX_OUTPUTS=
VERTEX_TRYON_DAILY_BUDGET_USD=
VERTEX_TRYON_ENABLED=false
```

Use workload identity in deployed environments. Local developers use ADC. The
browser calls SVEYRA APIs, never Vertex directly.

### Integration spike

1. Create `TryOnPort` and deterministic stub with golden fixtures.
2. Create server-side Vertex adapter using opaque SVEYRA asset IDs.
3. Re-encode/validate supported MIME, size, aspect and exact product variant.
4. Check active consent before resolving bytes.
5. Write provider request/output to private storage and audit metadata to DB.
6. Preserve C2PA/content credentials and add visible AI disclosure.
7. Run safety and quality post-checks before returning an asset.
8. Delete intermediate/request assets according to consent and lifecycle.
9. Benchmark cost, latency, failure, identity and product preservation.
10. Decide `go`, `limited categories`, or `no-go`; document alternative.

## Garment image understanding

### Gemini managed adapter

Gemini models can process images and text. Use Gemini 3.1 Flash-Lite first,
behind `VisionPort`, to propose schema-validated garment attributes or interpret
OCR/context. It is GA and Google currently lists retirement no earlier than
2027-05-07. It does not replace segmentation, exact variant matching, calibrated
colour measurement, or a rights-cleared benchmark.

- [Gemini API in Vertex AI quickstart and image understanding](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/start/quickstart)

Benchmark model candidates on the exact garment JSON schema with deterministic
temperature/settings where supported. Reject malformed or taxonomy-invalid output.
Never store free-form model text directly into authoritative attributes.

Proposed configuration:

```text
VISION_BACKEND=stub|vertex
VERTEX_VISION_MODEL_ID=gemini-3.1-flash-lite
VISION_TIMEOUT_SECONDS=
VISION_MAX_RETRIES=
VISION_MIN_AUTOFILL_PRECISION=
VISION_ENABLED=false
```

### Cloud Vision Product Search candidate

Google Cloud Vision Product Search can compare an input image with reference
images in a retailer-managed product set and supports an apparel category. Use it
only when SVEYRA or a partner has an authorized indexed catalog. It is a visual
retrieval tool; it does not provide SVEYRA's complete taxonomy, material, size,
care, segmentation, or fit evidence.

- [Vision API Product Search](https://docs.cloud.google.com/vision/product-search/docs)
- [Searching for products](https://docs.cloud.google.com/vision/product-search/docs/searching)

### Segmentation/background removal

Pilot Photoroom's managed Remove Background API first. Its official API supports
uploaded image bytes and PNG/JPEG/WebP output, including RGBA or alpha channels;
its published Basic price is USD 0.02 per successful image. Keep it behind
`SegmentationPort`, record successful-call cost, and validate privacy/deletion
terms before production.

- [Photoroom Remove Background API](https://www.photoroom.com/api/remove-background)
- [Photoroom API pricing](https://www.photoroom.com/api/pricing)
- [Photoroom API reference](https://docs.photoroom.com/api-reference-openapi)

Until the adapter passes SVEYRA's garment benchmark, retain the original image
and let the user crop/reframe; do not silently replace it. A general image
generation/editing model is not accepted merely because it creates a visually
clean background: it may change garment details.

Evaluation must cover lace, mesh, transparency, straps, fringe, sequins,
reflections, white-on-white, black-on-black, worn garments, hands/hair overlap and
multiple garments. Review data use, geographic processing, latency, unit cost,
commercial rights, training-data terms and deletion API.

## Capture coaching and landmark services

MediaPipe is a candidate for on-device or private processing of pose and face
landmarks, capture coverage, live coaching, expression controls and rough camera
quality. Its outputs are observations, not metric body/face reconstruction.

- [MediaPipe Pose Landmarker](https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/PoseLandmarker)
- [MediaPipe Face Landmarker result](https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/FaceLandmarkerResult)

Before shipping, verify model/license redistribution, supported devices, latency,
thermal use, demographic error and landmark stability under intended capture.

## Colour and skin measurement standards

No generic cloud API can make an uncalibrated phone photo into exact skin colour.
The production protocol should be reviewed against:

- [CIE 256:2025 Measurement of Human Skin Colour](https://www.cie.co.at/publications/measurement-human-skin-colour-0),
  including method, illumination geometry, body location, diversity and uncertainty;
- [ICC current specifications](https://www.color.org/specifications/) for device
  profiles and colour-management interchange;
- [W3C CSS Color 4](https://www.w3.org/TR/css-color-4/) for web colour spaces,
  Lab/OKLab/OKLCH, gamut mapping and colour-difference implementation guidance.

External needs for a high-confidence lab/calibration track:

- qualified colour scientist/consultant;
- supported colour target with batch/reference data;
- controlled illuminant/geometry and characterized camera workflow;
- spectrophotometer/spectrocolorimeter access for reference collection;
- characterized test displays and device matrix;
- rights-cleared diverse validation samples.

The manual starter palette remains available without these resources and is
labelled user-confirmed/styling guidance.

## Beauty product data

Provider not selected. Required before product/shade recommendations:

- authorized product and shade/variant catalog;
- source/date for ingredients, finish, coverage and swatches;
- region-specific availability, price and retailer identifiers;
- measured colour/optics for a validated subset;
- recall/discontinuation and stale-data handling;
- manufacturer link and non-medical ingredient warning boundary.

FDA information describes cosmetic allergen/contact-reaction considerations and
professional patch testing, but SVEYRA must not convert this into medical claims.

- [FDA: Allergens in Cosmetics](https://www.fda.gov/cosmetics/cosmetic-ingredients/allergens-cosmetics)

## Weather, calendar, and notification providers

Select only after launch markets and privacy requirements are fixed.

### Port contracts

```text
WeatherPort.forecast(coarse_location, interval, units)
CalendarPort.list_calendars(grant)
CalendarPort.list_selected_events(grant, range, field_policy)
NotificationPort.send(user, template, channel, schedule)
```

Requirements:

- minimum OAuth scopes and per-calendar selection;
- coarse location and caching by default;
- timezone, units, severe-weather source and forecast staleness;
- disconnect and deletion semantics;
- rate limits, webhook security and token rotation;
- no event title/description ingestion unless the user explicitly enables it.

## Commerce, catalog, affiliate, and price providers

Provider selection is market-specific. Required contracts:

- canonical product, variant, colourway, size system and GTIN/SKU;
- images and permitted derivative/try-on use rights;
- fresh offers, currency/tax/shipping, inventory and size availability;
- size charts and garment measurements with source dates;
- affiliate attribution and sponsored-result disclosure;
- webhook/polling updates, deduplication and stale offer expiry;
- purchase/return feedback integration only with explicit consent.

Do not scrape sites in violation of terms or treat a product image as permission
to create persistent 3D assets.

## Internal cloud components

The active Alta-first production stack needs provider-neutral equivalents of:

- Postgres for structured product state;
- private object storage for original/derived media and human/garment assets;
- queue/task service with dead-letter handling;
- stateless API and worker services;
- managed inference jobs for garment understanding and requested try-on;
- secrets manager, KMS/encryption, audit logging and IAM;
- metrics/traces/logs with PII/biometric redaction;
- CDN only for authorized derived/public assets, never raw biometric capture;
- feature flags, budgets, rate limits and abuse controls.

GPU reconstruction, metric body, and cloth infrastructure is deferred until the
Alta-class gates pass. Infrastructure names are decided in an ADR before
implementation. Product code continues to depend on ports.

## Provider scorecard

Every provider decision records:

| Dimension | Evidence |
| --- | --- |
| Product quality | SVEYRA private benchmark and failure examples |
| Coverage/fairness | slices across intended people, garments, devices, regions |
| Truth boundary | exact outputs and claims the provider does/does not support |
| Privacy/security | data use, retention, subprocessors, region, deletion, audit |
| Legal/rights | commercial use, biometric/person images, catalog derivatives |
| Reliability | latency percentiles, quotas, 429/5xx behaviour, SLA and fallback |
| Cost | per accepted output plus retries, storage, egress and moderation |
| Lifecycle | GA/preview, version pinning, deprecation/retirement and migration |
| Integration | SDK/runtime, REST contract, auth, observability and testability |
| Exit | data export/deletion, alternate provider and no-provider degradation |

No provider is approved solely from a demo image.
