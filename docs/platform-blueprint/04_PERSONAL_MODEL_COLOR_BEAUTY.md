# Personal Model, Colour, Skin, and Beauty

## Purpose

This domain represents what is known, estimated, and preferred about the
person's appearance. It powers colour combinations, outfit ranking, makeup and
hair suggestions, photoreal rendering, and product shade retrieval.

It must not become a classifier for race, ethnicity, health, attractiveness, or
other protected/sensitive conclusions.

## Evidence-aware field contract

Every inferred or measured field eventually uses a field-level envelope:

```json
{
  "value": "neutral",
  "source": "guided_photo_estimate",
  "confidence": 0.82,
  "user_confirmed": false,
  "observed_at": "2026-09-07T10:00:00Z",
  "model": "appearance-estimator",
  "model_version": "1.0.0",
  "protocol_version": "guided-face-v1",
  "evidence_ids": ["opaque-asset-id"],
  "uncertainty": {"kind": "categorical_distribution", "values": {}},
  "notes": null
}
```

Manual values omit model metadata. Instrument readings store device calibration,
geometry, illuminant, units, and measurement uncertainty. User confirmation
creates a new fact version; it does not modify the original observation.

## Appearance submodels

### Skin

- representative tone swatches in device-independent colour coordinates;
- body/face location, because skin colour is not uniform;
- depth/lightness as a descriptive styling feature, not demographic identity;
- warm/cool/neutral/olive undertone as an editable recommendation input;
- surface characteristics relevant to rendering: roughness, oiliness/dryness
  preference, freckles, moles, scars, tattoos, redness variation, facial hair;
- sensitivity and avoided ingredients as user preference, never medical status;
- temporary context such as tan, lighting, makeup already present, and date.

Do not store a single hex value as scientific skin truth. Hex/sRGB is a display
fallback. The current API field is a starter UI value and must evolve to a set of
versioned observations.

### Face

- identity geometry and landmarks belong to biometric reconstruction assets;
- editable styling descriptors may include face shape and feature emphasis;
- brow, lip, eye, lash, facial-hair, and hairstyle preferences are separate;
- face proportions must not be converted into attractiveness scores.

### Eyes and hair

- iris colour samples, limbal ring, sclera and eye material for rendering;
- hair base colour, highlights, colour treatment, root state, greying, density,
  strand width, texture/curl pattern, length, style, hairline, eyebrows, lashes,
  facial hair and body hair where the user chooses;
- colour and geometry evidence are separate so a hairstyle change does not
  invalidate permanent face/body identity.

### Preference and context

- desired contrast, colour families, metals, prints, finish, intensity, focus;
- makeup time, skill/complexity, product type, budget, ethical/ingredient filters;
- work/school/cultural dress codes and user-defined modesty boundaries;
- temporary event, lighting, camera, weather, and indoor/outdoor context.

## Calibrated colour capture pipeline

### Capture requirements

1. Disable beauty filters, portrait relighting, and colour effects when the
   device permits; record when this cannot be verified.
2. Use even, indirect neutral light and avoid mixed lighting.
3. Capture a neutral reference/colour chart in at least one calibration frame
   for high-confidence mode.
4. Retain camera metadata and embedded ICC profile when present.
5. Check clipping, blur, white balance stability, face coverage, and makeup.
6. Sample several skin regions and multiple frames; reject specular highlights,
   deep shadow, lips, eyes, hair, and occlusions.
7. Convert through the characterized/embedded colour profile into a defined
   connection space; record the pipeline and gamut mapping.
8. Aggregate robustly and return distribution/uncertainty, not one pixel.
9. Ask the user to confirm under a reasonably calibrated display and allow manual
   correction.

For ordinary uncalibrated photos, output only a low/medium-confidence styling
estimate. Exact foundation matching requires better evidence and product data.

### Colour representation

- Persist measurement-quality observations in CIE XYZ/Lab or the colour space
  required by the signed measurement protocol, including white point/illuminant.
- Use OKLab/OKLCH for perceptually arranged digital palettes and UI operations.
- Store display fallback in sRGB; retain Display-P3 values only when source and
  target profiles support them.
- Use a named colour vocabulary for search, never as the measurement authority.
- Record colour-difference formula and version when comparing samples.

Reference standards and resources are listed in `07_EXTERNAL_SERVICES.md`. CIE
256:2025 should guide the production skin-measurement protocol; implementation
requires qualified colour-science review and calibrated test devices.

## Colour analysis engine

### Inputs

- confirmed/calibrated skin distribution and undertone;
- eye and hair colours with confidence;
- personal contrast preference and observed feature contrast;
- garment/makeup product colour and material/finish;
- occasion, lighting, preference, cultural context, and user feedback.

### Outputs

- neutrals, accents, near-face colours, combinations, and metal suggestions;
- lightness/chroma/hue ranges rather than fixed seasonal labels only;
- contrast and proportion suggestions with reason codes;
- exceptions and experimental colours the user enjoys;
- confidence and missing evidence.

Traditional seasonal palettes may be offered as an optional, editable UX label,
not scientific ground truth. The engine should first rank candidates in a
continuous colour space, then explain them in familiar language.

### Starter deterministic strategy

The current appearance service uses explicit undertone/depth/contrast tables.
Keep this as a transparent baseline and test fixture while a calibrated engine is
developed. Future model-based ranking must outperform it on user-confirmed
outcomes and maintain deterministic hard constraints.

## Beauty product model

Model products at shade/variant level:

| Group | Required evidence |
| --- | --- |
| Identity | brand, line, variant, region, barcode/SKU, source, last verified |
| Colour | swatch/image source, Lab/XYZ when measured, display RGB, undertone |
| Optics | opacity/coverage, finish, gloss, sparkle, translucency, oxidation notes |
| Formula | product type, ingredients source/date, fragrance and user filters |
| Use | face region, application method, compatible layers, wear context |
| Commerce | price, currency, availability, retailer, affiliate/sponsor label |

Shade names such as `beige`, `tan`, or `medium` are not comparable across brands.
Catalog images are not assumed colour-accurate. A measured product sample should
carry method and batch/variant provenance.

## Makeup recommendation pipeline

1. Establish the requested occasion, intensity, finish, time, skill, owned
   products, budget, and sensitivity preferences.
2. Select a harmonious colour plan using confirmed appearance and outfit colours.
3. Retrieve products that satisfy region, formula, availability, evidence, and
   user filters.
4. Construct ordered layers and application amounts with editable alternatives.
5. Explain why each colour/finish was selected and mark uncertain shade matches.
6. Optionally generate a labelled visual preview.
7. Capture save, wear, comfort, match correction, oxidation, irritation report,
   and removal without turning reports into medical diagnoses.

### Look contract

```text
BeautyLook
  context and style intent
  complexion layers: primer/base/concealer/powder
  dimension: bronzer/contour/highlight
  cheeks: placement/colour/finish/intensity
  eyes: lid/crease/liner/mascara/lashes
  brows: shape/colour/hold
  lips: liner/base/topper/finish
  products or colour-only placeholders
  ordered application plan
  confidence, reasons, warnings, and preview provenance
```

The user can disable any region. Product suggestions remain useful even when no
face image or digital human exists.

## Makeup and hair visualization

### Fast preview

- use a consented face image with landmarks/segmentation and editable masks;
- composite physically motivated layers for colour/opacity/finish where possible;
- generative edits may improve realism but must not reshape identity silently;
- preserve original and provide opacity/intensity comparison;
- label generated/retouched output and store provider/model/version.

### Digital-human preview

- project makeup layers into stable facial UV/material regions;
- model diffuse colour separately from gloss, metallic, sparkle, roughness, and
  translucency;
- eyebrows, lashes, facial hair, and scalp hair need geometry-aware occlusion;
- validate under standardized daylight, indoor, warm evening, and camera flash
  environments;
- use the same appearance version in outfit, beauty, and try-on views.

## APIs to add

```text
GET/PUT  /v1/appearance
POST     /v1/appearance/captures
GET      /v1/appearance/captures/{id}
POST     /v1/appearance/analyses
GET      /v1/appearance/analyses/{id}
POST     /v1/colour/recommendations
POST     /v1/beauty/looks
GET/PATCH/DELETE /v1/beauty/looks/{id}
POST     /v1/beauty/previews
GET/DELETE /v1/beauty/previews/{id}
```

Long work returns `202` with a job resource. Routes never accept a caller-supplied
`user_id`; identity comes from the access token.

## Evaluation

- calibrated target and skin sample colour difference by device/light/protocol;
- repeatability across sessions and body regions;
- confidence calibration and user correction rate;
- palette preference and outfit/beauty save/wear rate versus baseline;
- shade retrieval exact/acceptable/rejected rates, including oxidation feedback;
- identity/skin-tone preservation and mask leakage for previews;
- performance slices across the intended skin, hair, age, device, and lighting
  range without treating demographic identity as a style rule;
- accessibility of swatches and non-colour explanations.

## Safety boundary

SVEYRA may recommend cosmetic appearance and warn about declared preferences or
manufacturer-listed ingredients. It does not diagnose acne, dermatitis,
pigmentation, allergies, skin cancer, or other medical conditions. Reports of
irritation direct the user to stop use and seek appropriate professional advice;
they do not generate a diagnosis.

