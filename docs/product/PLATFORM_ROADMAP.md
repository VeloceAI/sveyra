# SVEYRA Platform Roadmap

The active delivery order is the
[Alta-class parity plan](./ALTA_PARITY_PLAN.md). This roadmap remains the broader
system and post-parity direction.

The detailed, developer-executable plan lives in
[`../platform-blueprint/README.md`](../platform-blueprint/README.md). That folder
owns checkpoint IDs, UI flows, external-provider requirements, and acceptance
gates; this document remains the concise product sequence.

## Product outcome

SVEYRA is a personal style operating system built around a consent-based digital
human. It should answer four questions with increasing levels of evidence:

1. What do I already own?
2. What should I wear for this context?
3. Which colours, shapes, sizes, hair, and makeup choices suit me?
4. What will this specific garment look and fit like on my body?

The daily product should be as immediate as a strong digital-closet app. The
technical differentiator is that sizing, appearance, and try-on share one
versioned Personal Model instead of generating an unrelated avatar per request.

## First principles

### Facts, estimates, and preferences are different data

- **Facts** are user-confirmed measurements, owned garments, wear history, and
  calibrated observations.
- **Estimates** are photo-derived body dimensions, skin/eye/hair colour, face
  landmarks, garment attributes, and model confidence.
- **Preferences** are style goals, comfort, modesty, fit ease, makeup intensity,
  disliked colours, brands, and budget.

Every inferred attribute must retain its source and confidence and remain
editable. A generated image is evidence of appearance only; it is not proof of
physical garment fit.

### The Personal Model is the shared source of truth

```text
Personal Model
  identity and consent
  body and brand-size history
  face, skin, eyes, hair, and colour profile
  style and fit preferences
  digital wardrobe and garment evidence
  calendar, context, reactions, and wear history
  versioned digital-human assets
```

The stylist, size engine, beauty engine, wardrobe, shopping system, and try-on
system read this model. They do not maintain competing copies of the person.

### Fit truth and visual truth are separate

- **Fit truth** requires a metric body, garment measurements or patterns,
  material behaviour, ease rules, collision, and pressure/strain evaluation.
- **Visual truth** requires identity shape, lighting-neutral skin, face, eyes,
  hair, physically based materials, and a validated renderer.
- A 2D generative try-on provider can give a fast visual preview, but cannot
  certify size or pressure. The product must label that distinction.

## Product loops

### Onboarding loop

1. Choose style goals and fit preferences.
2. Complete guided body and face capture with explicit consent.
3. Confirm measurements and appearance estimates.
4. Add five wardrobe pieces to unlock the first outfit; continue toward a
   useful closet containing tops, bottoms, one-pieces, layers, shoes, bags, and
   accessories.

### Daily loop

1. Read weather, calendar, occasion, dress code, and travel context.
2. Generate a small number of complete outfits from owned items.
3. Explain colour, proportion, comfort, and fit reasoning.
4. Preview on the digital human when evidence permits.
5. Save, schedule, wear, like/dislike, or request a variation.
6. Feed the outcome back into preference and wardrobe-usage signals.

### Shopping loop

1. Detect a wardrobe gap from real usage and upcoming contexts.
2. Search products that complete multiple owned outfits.
3. Predict brand size from metric body, garment chart, preferred ease, and
   past keep/return outcomes.
4. Preview combinations and expose uncertainty before purchase.

## Capability architecture

| Capability | Source of truth | Required output |
| --- | --- | --- |
| Body and size | Body profile + digital-human manifest | measurements, confidence, brand-size prediction |
| Appearance | confirmed skin/face/eye/hair profile | colour palette, combinations, makeup guidance |
| Wardrobe | garment records + media evidence | clean item image, taxonomy, colour, fabric, fit, usage |
| Stylist | Personal Model + context | ranked outfits with reason codes |
| Beauty | appearance + preferences + occasion | editable makeup/hair plan and colours |
| Try-on | digital human + garment contract | labelled visual preview and, later, fit/pressure report |
| Feedback | saves, skips, wears, edits, returns | durable preference and confidence updates |

## Delivery order

### Phase 1 - Personal Model and useful daily product

- Structured appearance profile with evidence and user confirmation.
- Personal colour palette, outfit combinations, metal and makeup guidance.
- Friendly body/fit and style forms; remove JSON editing from the product UI.
- Daily home that combines closet readiness, suggested action, outfit, weather,
  calendar, and Personal Model completion.
- Fast wardrobe ingestion with background removal, garment taxonomy, colour,
  fabric, season, dress-code, and user correction.
- Outfit reactions and constraint-based restyling.

### Phase 2 - Size intelligence

- Normalize body measurements and uncertainty from the human engine.
- Garment measurement and brand-size-chart contracts.
- Size recommendation based on body, garment, preferred ease, and category.
- Keep/return feedback and per-brand calibration.
- Never claim certainty when garment measurements are unavailable.

### Phase 3 - Identity-quality digital human

- Guided calibrated full-body and close-face capture.
- Multi-view shape fitting and regional evidence confidence.
- Complete eyes, mouth, teeth, tongue, hands, feet, face controls, skin, and hair.
- Novel-view identity, measurement, animation, and demographic evaluation.
- Runtime LODs and secure biometric-asset lifecycle.

### Phase 4 - Try-on

- Garment geometry/pattern, material, construction, and size contracts.
- Collision-safe dressing and cloth simulation on the metric body.
- Fit, ease, pressure, strain, hem, and range-of-motion reports.
- Optional fast 2D generated preview, explicitly labelled as visual only.
- Accessories, shoes, bags, jewellery, makeup, and hair combinations.

### Phase 5 - Complete style platform

- Trips, multi-city weather, packing lists, and shareable lookbooks.
- Wishlist, price tracking, closet-gap shopping, and product alternatives.
- Community inspiration mapped back to owned and shoppable items.
- Mobile capture and daily-use clients.
- Privacy controls, export, deletion, consent renewal, and audit history.

## Current implementation slice

The first active slice is the appearance layer of the Personal Model:

- persist user-confirmed skin, undertone, contrast, face, eye, hair, and makeup
  preferences;
- keep evidence source and confidence with those attributes;
- return deterministic starter colour and makeup guidance;
- expose an editable Color Studio in the web client;
- later replace or supplement manual input with calibrated photo estimates.

This slice is useful without pretending that uncalibrated photos can provide a
perfect skin colour or face analysis, and it gives wardrobe recommendations and
future try-on one stable contract to consume.
