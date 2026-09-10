# Privacy, Evaluation, and Operations

## Data classification

| Class | Examples | Baseline handling |
| --- | --- | --- |
| Account | email, auth/session, country | encrypted, least privilege, account retention |
| Preference | style, fit, beauty, budget | user-editable/exportable/deletable |
| Behaviour | views, saves, wears, returns | purpose-limited, pseudonymous analytics |
| Personal media | wardrobe and inspiration photos | private object storage, signed access |
| Biometric evidence | face/body images, video, landmarks, voice/lip-sync | restricted service identity, explicit consent, short raw retention |
| Biometric derivative | identity mesh, textures, embeddings, measurements | versioned, restricted, deletion cascade |
| Generated media | try-on, makeup and avatar renders | labelled, provenance, retention controls |
| Commerce | wishlists, clicks, purchases, returns | separate purpose and sponsor/affiliate audit |

Country-specific legal classification may be stricter. This document is an
engineering baseline, not legal advice.

## Consent model

Consent is versioned and purpose-specific:

- create and store Personal Model;
- analyze appearance photo;
- reconstruct and store biometric digital human;
- send a selected person/product image to an external try-on provider;
- connect calendar/location/email/receipts;
- use corrections or media for model improvement;
- share a look or generated image.

Each grant stores policy version, user, purpose, scope/assets, provider classes,
region, granted/revoked time and UI receipt. Revocation blocks new processing and
triggers the documented retention/deletion action; it cannot retroactively undo a
completed external disclosure, which the UI explains before consent.

Consent to use a feature is not consent to train a model.

## Asset lifecycle

```text
captured -> uploaded -> validated -> processing -> derived -> active
                                                -> quarantined/failed
active -> superseded -> retention expiry -> deletion queued -> deleted/verified
```

Every asset has:

- owner, purpose, data class and consent reference;
- storage provider/region and opaque key;
- parent/child derivation graph and model/version;
- created, last accessed, expiry and deletion timestamps;
- legal hold only when approved and auditable;
- checksum, MIME, size and malware/safety state;
- sharing/access policy.

Deletion walks the derivation graph, provider jobs/results, cache/CDN, embeddings,
search indexes, backups according to documented limits, and database rows. Record
verification without retaining deleted biometric content.

## Security controls

- short-lived JWT/session strategy with refresh/rotation before public launch;
- object storage private by default with short-lived signed URLs;
- workload identity and least-privilege service accounts; no browser cloud keys;
- secret manager and rotation; never committed `.env` secrets or key JSON;
- encryption in transit/at rest and key strategy for biometric derivatives;
- purpose-aware authorization in addition to row ownership;
- upload MIME/decode limits, malware scanning and image decompression protection;
- idempotency and replay protection for paid/provider jobs;
- egress allowlist, SSRF protection and server-resolved asset references;
- audit log for biometric access without raw media or face embeddings in logs;
- admin/support access approval, reason, time limit and user-visible history where
  appropriate;
- dependency/container/model provenance and vulnerability response;
- abuse reporting, impersonation/deepfake policy and generated-media disclosure.

## Threats to design for

- account takeover exposing body/face/wardrobe data;
- insecure direct object references across users;
- public or long-lived media URLs;
- malicious upload, parser exploit, zip/decompression bomb;
- prompt/image injection manipulating garment extraction or stylist tools;
- provider credential leakage or client-side external calls;
- replay causing duplicate paid generations;
- unauthorized digital-human export or impersonation;
- deletion that misses derived meshes, masks, embeddings or provider results;
- model output that changes identity/body/skin or logos deceptively;
- sponsor influence hidden inside organic recommendations;
- inference of sensitive demographic/health attributes.

Complete a formal privacy impact assessment, threat model, penetration test and
legal review before biometric beta.

## Evaluation governance

### Dataset record

Each evaluation dataset documents:

- intended purpose and metrics;
- collection/source, rights, consent and allowed derivatives;
- inclusion/exclusion and supported population/product range;
- annotation guide, annotator qualification, agreement and adjudication;
- train/validation/test identity and product separation;
- version, checksum, access control, retention and deletion obligations;
- known gaps and prohibited claims.

Never move user corrections or captures into training/evaluation automatically.

### Model/provider record

- adapter, model ID/version, configuration and prompt/schema version;
- dataset and code version;
- overall and sliced results with confidence intervals where appropriate;
- quality, safety, privacy, latency, reliability and cost;
- failure gallery and known limitations;
- approval owner/date, launch scope, rollback criteria and retirement plan.

## Provisional engineering gates

These are starting targets for planning, not permanent product promises. Domain
owners must sign final thresholds after baseline data exists.

### Wardrobe vision

- zero ownership leaks and no raw media in logs/garment attributes;
- category macro F1 and per-class minimum agreed from the rights-cleared set;
- segmentation IoU plus boundary score for difficult materials;
- calibrated colour error reported separately for calibrated/ordinary photos;
- OCR exact-field accuracy for brand, size and composition;
- low-confidence values do not exceed the target incorrect autofill rate;
- correction UI completion, provider failure, latency and accepted-item cost.

### Recommendations

- zero hard-constraint violations in fixtures and production audit sample;
- outfit completeness and diversity metrics;
- save/wear rate versus deterministic baseline;
- rejection reason and preference-reset correctness;
- organic rank unaffected by affiliate/sponsor value.

### Size

- top-1/top-2, calibration, coverage and `cannot_recommend` rate;
- keep/return and regional comfort versus chart-only baseline;
- error slices by brand, category, size system, body range and evidence quality;
- do not improve aggregate accuracy by refusing disproportionately for a cohort.

### Appearance and beauty

- repeated calibrated capture and colour difference by device/light/body region;
- user correction/confirmation and preference outcome;
- shade/product retrieval exact, acceptable and rejected match;
- preview mask leakage, skin/identity preservation and rendering under test lights;
- sensitivity/ingredient data source/date and zero medical diagnosis output.

### Digital human

- measurement and surface error against scan reference;
- novel-view identity and blinded human comparison;
- anatomy/manifest/rig/material/LOD conformance;
- joint-limit violation, self-penetration, foot slide, contact and temporal motion;
- skin/hair/eye appearance under standard lighting;
- runtime load/memory/frame budget by supported device tier;
- failure/recapture rate and regional confidence calibration.

### 2D visual try-on

- face/person/body/skin/hair preservation;
- exact garment variant colour, pattern/logo, length and construction preservation;
- hand/limb/occlusion/artifact and safety filter rates;
- generated disclosure/C2PA retention and deletion correctness;
- accepted-output latency, availability, attempts and total cost;
- results by intended skin/body/garment/device cohort.

### Metric 3D fit

- garment registration and simulation success;
- collision penetration and unstable/exploding simulation rate;
- pressure/strain/ease correlation with physical reference;
- hem/landmark and range-of-motion outcome;
- honest insufficient-evidence refusal.

## Human review

Quantitative metrics do not fully capture identity or fashion quality. Use
structured review, never vague `looks good` approval:

- participant self-rating for identity, body, skin/hair and comfort;
- independent expert garment/colour/3D review where appropriate;
- paired blinded comparison against baseline;
- exact failure taxonomy and severity;
- demographic and product slices with privacy-preserving reporting;
- reviewer well-being and restricted access for sensitive media.

## Experiment and rollout policy

1. Offline fixture and unit/integration tests.
2. Rights-cleared internal benchmark.
3. Dogfood with explicit consent and delete controls.
4. Small opt-in cohort behind feature flag.
5. Category/country/device-limited beta.
6. Gradual production rollout with automatic and manual kill switches.

Never A/B test biometric use, sponsor disclosure, or consent comprehension by
hiding material information. Experiments record assignment and support opt-out.

## Observability

### Structured events

- job requested/accepted/stage/completed/failed/cancelled/deleted;
- adapter/model/config version, feature flag, region and data class;
- duration, queue wait, retry, error class, output count and billed units;
- quality/safety result and user correction/acceptance;
- no raw prompt containing personal details, image bytes, signed URLs, exact face
  landmarks, embeddings or unredacted calendar text.

### Dashboards

- product outcomes and funnel;
- API/worker SLOs, queues, provider status and fallback;
- quality/calibration and cohort regressions;
- safety/moderation/artifact reports;
- storage/retention/deletion backlog;
- spend by feature/provider/model and accepted output;
- auth/access anomalies and support/admin access.

### Alerts and kill switches

Alert on ownership/auth failures, public bucket/policy change, deletion backlog,
provider cost spike, repeated 429/5xx, model-version drift, quality regression,
unsafe output, cohort disparity and logging redaction failure. A provider kill
switch must degrade to manual/deterministic owned-wardrobe features.

## SLO candidates

Set final values after baseline and architecture review. Track separately:

- synchronous product API availability and p50/p95/p99 latency;
- asynchronous job time-to-ready and completion rate;
- provider-dependent versus core owned-wardrobe availability;
- deletion request acknowledgement and verified completion window;
- recovery point/time objectives;
- cost per active user, processed garment, accepted try-on and completed human.

## Release checklist

- [ ] Product, design, accessibility and support sign-off.
- [ ] Security threat model, privacy impact and legal/terms review.
- [ ] Data/provider/model cards and benchmark report approved.
- [ ] Consent, export, deletion and provider-retention paths tested.
- [ ] Load, retry, idempotency, chaos/fallback and disaster recovery tested.
- [ ] Cost caps, rate limits, quotas, alerts and kill switches verified.
- [ ] Generated-media disclosure and reporting flow visible.
- [ ] Unsupported claims and known limitations reviewed in UI/help copy.
- [ ] Rollback and model retirement/migration rehearsed.
- [ ] Operations/support runbook and owner rotation active.

