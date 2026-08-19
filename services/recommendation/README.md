# Recommendation Service

Owns styling, ranking, and shopping intelligence.

## First Jobs

- Rank owned wardrobe items for an occasion
- Detect wardrobe gaps
- Recommend outfit combinations
- Explain tradeoffs around fit, weather, budget, and taste

## Current backend seam (M17 / M19)

The FastAPI API exposes `POST /v1/recommendations`. Ranking uses provider-neutral `StylistPort` with a deterministic default (`StubStylist` → metadata engine). Signals:

- Occasion
- Owned wardrobe `category` / `color` / `brand` / `attributes` (including M18 `attributes.cv`)
- Style profile `preferences`, `dislikes`, and `budget`
- Latest body `fit_preferences` when present

Image bytes and StoragePort are not used. Results are ephemeral. A future AI/LLM adapter can implement `StylistPort` without changing the HTTP contract.

## Signals (product roadmap)

- User style profile
- Body and fit profile
- Wardrobe attributes
- Occasion
- Budget
- Brand and size history
