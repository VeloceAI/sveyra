# Alta-class product parity plan

Status: active execution overlay  
Research checked: 2026-09-08

Active scope decision (2026-09-08): finish the Alta-class daily styling product
before resuming metric 3D, photoreal digital-human, skin/beauty, and cloth
simulation work. The active implementation uses managed APIs; local/open-model
inference is deferred to avoid GPU operations and unresolved dependency licences.

This plan narrows SVEYRA's first product milestone. We will first deliver the
fast, useful personal-styling loop demonstrated by Alta, then add SVEYRA's deeper
differentiators: a metric 3D human, face and appearance fidelity, size evidence,
and garment physics.

"Parity" means comparable user outcomes and a complete daily workflow. It does
not mean copying Alta's brand, interface, proprietary data, or implementation.

## Observed product loop

The current public product and demos show this loop:

1. Answer a short style-goal onboarding.
2. Build a visual closet from photos, receipts/email, product lookup, or existing
   catalog items.
3. Remove image backgrounds and extract garment details so the closet looks
   editorial rather than like a camera roll.
4. Open a daily home feed of outfit ideas from owned items, weather, schedule,
   and learned taste.
5. Ask for a specific occasion or build around one chosen item.
6. Swap individual outfit slots, save or reject the look, and use that feedback
   to improve later suggestions.
7. Preview the look on a personalized visual avatar.
8. Save or wear the look, schedule it on a calendar, or add it to a lookbook.
9. Plan a multi-city trip from dates, activities, climates, and luggage size.
10. Discover closet gaps, shop alternatives, wishlist products, and monitor
    prices without losing the owned-wardrobe context.

Public evidence:

- [Alta product site](https://www.altadaily.com/)
- [Alta feature guide](https://www.altadaily.com/blog/alta-main-features)
- [Current Google Play listing](https://play.google.com/store/apps/details?id=com.alta)
- [GMA product demonstration](https://abcnews.com/video/132132956/)
- [Alta's account of the GMA flow](https://www.altadaily.com/blog/good-morning-america)
- [Meta engineering case study on Alta and Segment Anything](https://ai.meta.com/blog/alta-daily-fashion-app-segment-anything/)
- [Forbes founder/product video](https://www.forbes.com/video/f132c380-4b1e-485c-a64e-0a4bba3ce648/how-this-gen-z-founder-raised-11-million-to-build-the-aipowered-closet-from-clueless/)

The public Meta case study specifically identifies Segment Anything as a core
part of Alta's clothing/background segmentation pipeline. There is no public
evidence that Google Vertex is required for Alta's core product.

## SVEYRA baseline

| Product outcome | Current repository | Parity state |
|---|---|---|
| Account and local no-login development | JWT auth, refresh, dev session | foundation ready |
| Visual closet | CRUD, media upload, manual metadata | partial |
| Garment cleanup and identification | `VisionPort`; deterministic test adapter only | missing production adapter |
| Outfit ranking | deterministic owned-wardrobe ranker | partial |
| Build around one item / swap a slot | item locking and single-slot swap | implemented |
| Saved looks | outfit persistence | foundation ready |
| Daily home | no coherent home experience | missing |
| Weather and schedule context | calendar wear log only | missing |
| Outfit feedback and learning | style dislikes only | missing |
| Visual avatar try-on | local rigged 3D foundation; no dressed photoreal result | partial foundation |
| Calendar | plan/wear log and wardrobe usage | partial |
| Trips and packing | documented only | missing |
| Closet analytics | most/never worn only | partial |
| Wishlist, price tracking, product import | gap/shopping demo only | missing |
| Inspiration and shareable lookbooks | documented only | missing |

Appearance and color science already exceed the minimum Alta-style scope, but
they must enhance recommendations without delaying the core closet loop.

## Execution order

### P0 - One coherent product shell

- [x] `AP-P0-01` Make `Today` the signed-in landing page.
- [x] `AP-P0-02` Show setup progress, one next action, and honest engine/provider
  readiness in a single API response.
- [x] `AP-P0-03` Replace developer-oriented navigation names with user jobs;
  keep Human Engine under a clearly marked lab route.
- [x] `AP-P0-04` Complete a responsive mobile flow at 390 px without horizontal
  page overflow.

Exit gate: a new user can understand what SVEYRA does and reach the next useful
action in one tap.

### P1 - Fast visual closet ingestion

- [x] `AP-P1-01` Batch photo upload with per-item processing state.
- [ ] `AP-P1-02` Garment segmentation/background removal behind
  `SegmentationPort`; pilot Photoroom's managed Remove Background API and retain
  the original photo when no result passes product-identity checks.
- [ ] `AP-P1-03` Garment category, color, material, pattern, fit, season, and
  occasion extraction behind `VisionPort`.
- [ ] `AP-P1-04` Always show extracted fields for confirmation; preserve manual
  correction and provenance per field.
- [ ] `AP-P1-05` Visual closet grid, filters, sorting, duplicate review, and
  processing/error recovery.
- [ ] `AP-P1-06` Product URL/catalog import, followed by receipt/email import only
  after explicit consent and a retention policy.

Exit gate: a user can photograph ten garments, correct mistakes, and receive a
clean searchable closet without entering every field manually.

### P2 - The daily styling loop

- [ ] `AP-P2-01` Structured context: occasion, dress code, weather, activity,
  location granularity, comfort, and required/blocked items.
- [x] `AP-P2-02` Generate multiple complete looks from owned inventory.
- [x] `AP-P2-03` "Style this item" from every garment detail page.
- [x] `AP-P2-04` Swap a single outfit slot without regenerating everything.
- [ ] `AP-P2-05` Save, wear, schedule, like, dislike, and reject-with-reason.
- [ ] `AP-P2-06` Feed feedback into a versioned preference model.
- [ ] `AP-P2-07` Explain recommendations with garment and context evidence.

Exit gate: the home recommendation can be accepted, edited, or rejected, and a
second recommendation reflects durable feedback.

### P3 - Visual avatar parity

- [ ] `AP-P3-01` Repair the local canonical avatar path and persist avatar build
  state separately from ordinary media.
- [ ] `AP-P3-02` Create a consented look-alike visual-avatar onboarding flow.
- [ ] `AP-P3-03` Add provider-neutral `TryOnPort` for a person/avatar reference,
  ordered garment references, and a generated visual result.
- [ ] `AP-P3-04` Implement one benchmarked photoreal 2D try-on adapter, with job
  status, cost, deletion, retry, and safety controls.
- [ ] `AP-P3-05` Let users regenerate after swapping one outfit slot.
- [ ] `AP-P3-06` Label the output "visual preview"; do not claim size or physical
  fit from a generated image.

Exit gate: a saved outfit can produce a recognizable visual preview and a
changed garment can be regenerated reliably.

### P4 - Daily context, calendar, and trips

- [ ] `AP-P4-01` Permissioned, cached weather adapter.
- [ ] `AP-P4-02` Daily outfit cards based on current weather and planned events.
- [ ] `AP-P4-03` Multi-look day planning and drag/drop scheduling.
- [ ] `AP-P4-04` Multi-city trip wizard with dates, activities, dress codes,
  climate, laundry, rewear, and luggage constraints.
- [ ] `AP-P4-05` Packing list, trip lookbook, conflict detection, and private
  share link.
- [ ] `AP-P4-06` Cost-per-wear, most/least/never worn, and closet growth.

Exit gate: a trip produces wearable daily looks and a deduplicated packing list
that stays inside the luggage constraint.

### P5 - Search, inspiration, and commerce

- [ ] `AP-P5-01` Natural-language style search with closet-only and shopping
  modes.
- [ ] `AP-P5-02` Inspiration upload/feed and "recreate with my closet."
- [ ] `AP-P5-03` Wishlist, product URL import, offers, availability, and price
  history/alerts.
- [ ] `AP-P5-04` Rank shopping by real closet gaps, outfit yield, budget, palette,
  and known size evidence.
- [ ] `AP-P5-05` Shareable lookbooks with explicit privacy boundaries.

Exit gate: shopping recommendations demonstrably fill a wardrobe gap and show
several outfits using the candidate item.

## Provider strategy for parity

No single external API is the whole system.

| Need | First strategy | Portability rule |
|---|---|---|
| Background removal | pilot Photoroom Remove Background; preserve the original until its cutout passes identity checks | `SegmentationPort` |
| Garment tags | managed Gemini 3.1 Flash-Lite with schema validation and user confirmation | `VisionPort` |
| Outfit ranking | keep deterministic constraints; optionally rerank or phrase with a model | `StylistPort` |
| Photoreal 2D preview | Google `virtual-try-on-001`, generated only on explicit user request | `TryOnPort` |
| Weather | one cached provider using coarse location | `WeatherPort` |
| Catalog/offers | licensed catalog and affiliate adapters | `CatalogPort` / `OfferPort` |

The managed models accelerate image understanding and 2D visual try-on, but the
closet, deterministic stylist, calendar, and recommendation logic continue to
work when they are disabled. Metric size and fit remain separate from generated
imagery. The deferred local/open-model research is not an active work queue.

## Work after parity

After P0-P5 pass their gates, resume the differentiator track in
[`platform-blueprint`](../platform-blueprint/README.md): identity-fitted 3D,
anatomical motion, calibrated face/skin/hair/eyes, beauty science, brand sizing,
garment reconstruction, and cloth simulation.
