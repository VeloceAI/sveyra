# SVEYRA Platform Blueprint

This folder is the execution source of truth for building SVEYRA into a
personal style platform with a consent-based digital human. It converts the
product direction into checkpoints that another developer can pick up without
guessing about scope, dependencies, truth claims, or completion criteria.

## Product promise

SVEYRA helps a person understand what they own, decide what to wear, choose
colours and beauty products, predict likely size, and preview combinations on a
persistent representation of themselves.

The platform has three different kinds of output and must label them clearly:

1. **Recommendation** - a ranked styling or beauty suggestion.
2. **Visual preview** - an AI-generated or rendered approximation of appearance.
3. **Fit evidence** - a metric result supported by body, garment, material, and
   simulation data.

A visual preview is never presented as proof of fit. A photo estimate is never
silently promoted to a user-confirmed fact.

## Read in this order

1. [`01_PRODUCT_SYSTEM.md`](01_PRODUCT_SYSTEM.md) - first principles, product
   loops, domain map, and success measures.
2. [`02_EXECUTION_CHECKPOINTS.md`](02_EXECUTION_CHECKPOINTS.md) - ordered work
   packages, dependencies, acceptance criteria, and current status.
3. [`03_UI_UX_FLOWS.md`](03_UI_UX_FLOWS.md) - information architecture, screen
   flows, states, responsive behaviour, and design quality bar.
4. [`04_PERSONAL_MODEL_COLOR_BEAUTY.md`](04_PERSONAL_MODEL_COLOR_BEAUTY.md) -
   appearance evidence, calibrated colour, skin/hair/eye attributes, and makeup.
5. [`05_WARDROBE_VISION_STYLIST.md`](05_WARDROBE_VISION_STYLIST.md) - photo
   ingestion, garment identification, closet intelligence, and recommendations.
6. [`06_DIGITAL_HUMAN_SIZE_TRYON.md`](06_DIGITAL_HUMAN_SIZE_TRYON.md) - body
   truth, size prediction, identity reconstruction, animation, and 2D/3D try-on.
7. [`07_EXTERNAL_SERVICES.md`](07_EXTERNAL_SERVICES.md) - provider decisions,
   Google Cloud requirements, ports, costs, secrets, and procurement checklist.
8. [`08_PRIVACY_EVALUATION_OPERATIONS.md`](08_PRIVACY_EVALUATION_OPERATIONS.md)
   - biometric safety, consent, retention, evaluation, observability, and launch
   gates.
9. [`09_OPEN_SOURCE_MODEL_STACK.md`](09_OPEN_SOURCE_MODEL_STACK.md) - deferred
   local/open-model research retained for reference; not an active work queue.

## How developers use this blueprint

1. Pick the first unblocked task in `02_EXECUTION_CHECKPOINTS.md`.
2. Confirm every listed dependency is complete.
3. Write or update the provider-neutral contract before adding an SDK.
4. Implement route -> handler -> service -> repository for backend product APIs.
5. Add migration, tests, UI states, telemetry, and documentation in the same PR.
6. Demonstrate the acceptance criteria with a reproducible fixture or dataset.
7. Update the checkpoint status and link the PR or evidence report.

No task is complete when only the happy-path UI exists. Completion includes
authorization, ownership isolation, failure states, accessibility, privacy,
tests, and an honest user-facing confidence label.

## Current repository baseline

Status is accurate as of 2026-09-07 on branch
`feature/photoreal-digital-human`.

| Capability | Current state |
| --- | --- |
| Authentication | JWT register/login and local-only developer session exist |
| Personal profile | Style, body/fit, and appearance persistence exist |
| Color Studio | Editable appearance UI and deterministic starter palette exist |
| Wardrobe | CRUD, media boundary, upload, and stub enrichment exist |
| Styling | Deterministic recommendations, outfits, calendar, gaps, and stub shopping exist |
| Human engine | Canonical mesh, 163-joint skin, parameter deformation, developer viewer, and collision-aware pose work exist |
| Production garment vision | Not implemented; current `VisionPort` uses a stub |
| Calibrated photo appearance/body capture | Not implemented |
| Identity-quality photoreal human | Not implemented |
| External virtual try-on | Not integrated |
| Metric garment fit/cloth | Not implemented |

## Non-negotiable architecture rules

- The Personal Model is the only durable representation of the user.
- Every inferred field stores source, confidence, model/version, and timestamp.
- Users can inspect, correct, confirm, export, and delete inferred data.
- Provider SDKs remain behind ports in service or adapter layers.
- Raw biometric media uses private object storage and short retention by default.
- Shopping rank is separated from sponsored placement.
- Beauty guidance does not diagnose health or infer race/ethnicity.
- 2D generative try-on and metric 3D fit are separate products and APIs.
- Competitor implementation details are never assumed without public evidence.

## Decision records still required

- Photoroom garment-background-removal go/no-go after the managed pilot.
- Initial weather, calendar, catalog, affiliate, and price-tracking providers.
- Supported launch countries and applicable biometric/privacy regimes.
- Mobile client strategy and capture device support matrix.
- Commercially cleared face/body/hair training data and asset licenses.
- GPU runtime and reconstruction build-versus-buy decision after Alta parity.
- Google Virtual Try-On quality/category limits after SVEYRA's managed pilot.
