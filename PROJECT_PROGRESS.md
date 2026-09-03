# SVEYRA Project Progress

This document summarizes the current product foundation for technical review. It describes what is implemented in the repository today, how the architecture is organized, and what remains intentionally deferred.

## Purpose of the architecture

SVEYRA is being built as an API-first personal style platform. The backend exposes stable HTTP contracts so the same product capabilities can power:

- the current Next.js web client
- future Android and iOS clients

Provider-specific systems (object storage backends, computer vision providers, shopping/commerce catalogs, and future LLM stylists) stay behind ports. Product routes, repositories, and authentication do not depend on a particular vendor SDK.

## Development flow implemented so far

### 1. FastAPI clean architecture

The API follows a consistent layering model:

`route → handler → service → repository`

Routes stay thin. Handlers adapt HTTP concerns. Services own product decisions. Repositories own database access.

### 2. Authentication and JWT identity

Users can register and log in. Protected product APIs use Bearer access tokens. Identity comes from the authenticated user (`JWT` subject), not from client-supplied ownership fields. Passwords are stored as hashes only.

### 3. PostgreSQL and Alembic schema

Product data is persisted in PostgreSQL. Schema evolution is owned by Alembic. Current revisions run through `0007_media_asset_reference_unique` and cover users, style profiles, body profiles, wardrobe items, media assets, outfits, password hashes, and a uniqueness constraint on media references.

### 4. Strict API contracts and validation

Request bodies reject unexpected fields. Collection endpoints support pagination. Failures return a consistent error envelope with a stable `code` and user-safe `message`. Internal exception details are not exposed to clients.

### 5. Object and media storage abstraction

Image bytes are stored outside PostgreSQL. The API uses a provider-neutral `StoragePort` with:

- an in-memory adapter for local/tests
- a Google Cloud Storage adapter for production-style object storage

Supported media flows include upload, metadata retrieval, short-lived access URL generation, and deletion with storage-first retry-friendly semantics. Opaque storage references are persisted; signed URLs and raw bytes are not stored as product data. A storage reference maps to exactly one asset row, so a caller cannot register a reference another user already owns.

### 6. Profile, body, and fit data

Authenticated users can persist and load:

- style preferences, dislikes, and budget
- body measurements and fit preferences

### 7. Wardrobe APIs and ownership

Authenticated users can create, list, and fetch wardrobe items they own. Cross-user access is denied. Wardrobe metadata remains structured product data (`category`, `color`, `brand`, `attributes`) without embedding media URLs or image bytes.

### 8. Garment enrichment through VisionPort

`POST /v1/wardrobe/{item_id}/enrich` loads owned wardrobe media through `StoragePort`, analyzes garment bytes through a provider-neutral `VisionPort`, and writes safe results into existing wardrobe fields. The default implementation is a deterministic stub suitable for local development and tests. Real CV providers are not integrated yet.

### 9. Outfit recommendations through StylistPort

`POST /v1/recommendations` ranks owned wardrobe items for an occasion using wardrobe metadata, style signals, and fit preferences when available. Ranking runs through a provider-neutral `StylistPort` with a deterministic default. Results are ephemeral; clients may persist an accepted look through the outfits API. Image bytes are not loaded during recommendation.

### 10. Wardrobe gap analysis

`POST /v1/recommendations/gaps` is authenticated. Identity comes from the JWT subject. The service inspects only the caller's wardrobe metadata and reports missing primary coverage buckets (`top`, `bottom`, `shoes`). Category vocabulary lives in `app/services/category_taxonomy.py`; a one-piece garment such as a dress covers both halves, and outerwear is tracked apart from tops. Results are ephemeral. An empty wardrobe still returns HTTP 200 with all three buckets as gaps. Image bytes, computer vision, and LLM ranking are not used.

### 11. Shopping recommendations through ShoppingPort

`POST /v1/recommendations/shopping` is authenticated. Identity comes from the JWT subject. The service uses wardrobe-gap results plus the caller's style-profile budget when present, then asks a provider-neutral `ShoppingPort` for matching products. The default implementation is deterministic `StubShopping`, which returns mock products only (demo `example.com` URLs). It can filter those mock products by budget maximum and preferred brands. There is no live catalog, checkout, cart, or external commerce API. Results are ephemeral. This work did not add database tables or migrations.

### 12. Wardrobe update and delete lifecycle

Authenticated users can partially update wardrobe metadata and delete owned items. Deletion cascades linked media using the existing storage-first deletion behavior. Saved outfits are not rewritten and may retain historical item references.

### 13. Next.js web client

A thin authenticated Next.js + React + TypeScript client consumes the same backend APIs for:

- register / login / logout
- style and body profile
- wardrobe create / list / detail / update / delete
- media upload and access-url preview (HTTPS when available; clear handling when local memory URLs are not browser-loadable)
- garment enrichment
- recommendations and saved outfits

The web client does not currently expose dedicated wardrobe-gap or shopping screens. The web client uses Next.js rewrites to reach the API and stores the access token in session storage for this stage of development. There is no refresh-token flow yet.

### 14. Future mobile clients

Android and iOS are not implemented in this repository yet. The current API contracts are intentionally client-agnostic so mobile apps can reuse the same authentication, wardrobe, media, enrichment, recommendation, gap, shopping, and outfit endpoints.

## Major capabilities present now

- JWT authentication and ownership enforcement
- PostgreSQL persistence with Alembic migrations through `0007_media_asset_reference_unique`
- Strict request validation and safe error envelopes
- Wardrobe CRUD with ownership checks
- Media upload, access URL, and delete flows
- `StoragePort` with memory and GCS implementations
- Garment enrichment behind `VisionPort` (stub default)
- Deterministic recommendations behind `StylistPort` (stub default)
- Wardrobe gap analysis at `POST /v1/recommendations/gaps`
- Shopping recommendations at `POST /v1/recommendations/shopping` behind `ShoppingPort` (`StubShopping` mock catalog)
- Style profile and body/fit persistence
- Next.js authenticated web client for the core product flow (no dedicated gap or shopping UI yet)
- Rate limiting on register and login, configurable through `AUTH_RATE_LIMIT_*`
- `AvatarPort` seam for avatar rendering (stub default, selected by `AVATAR_BACKEND`)
- Shared garment category taxonomy behind recommendations and gap analysis
- Automated backend test suite covering the implemented API behavior
- GitHub Actions CI running backend lint and tests, a migration-head check, and frontend lint, typecheck, tests and build

## Current status

The repository contains a working end-to-end foundation for the core product path:

authenticate → manage profile and wardrobe → upload media → enrich garments → recommend outfits → identify wardrobe gaps → receive stub shopping recommendations → save looks → manage wardrobe lifecycle → use the same core APIs from the web client.

Verification confirmed from the repository at the time of this report:

- Backend: `252 passed` from `python -m pytest -q` in `backend/`
- Backend lint: `ruff check .` clean against the pinned `E`, `F`, `I` rule selection
- Alembic head: `0007_media_asset_reference_unique`
- Frontend: lint, typecheck, `6 passed` from `npm run test`, and a successful build
- Frontend: the existing Next.js client was not extended with wardrobe-gap or shopping screens in this work

Production CV providers, LLM stylists, live commerce providers, checkout/cart, Redis-backed workers, avatar/try-on, dedicated gap/shopping web screens, and native mobile apps are not claimed as complete.

## Next direction

The foundation and core API product flow are in place. Future work can expand without rewriting the HTTP surface, for example:

- production-grade computer vision providers behind `VisionPort`
- AI stylist / LLM providers behind `StylistPort`
- live commerce adapters behind `ShoppingPort` (replacing the mock stub)
- dedicated wardrobe-gap and shopping screens in the web client
- virtual try-on, avatar, and 3D experiences
- Android and iOS clients against the same API contracts
- background workers only when a concrete product need requires them

## Key references

- `docs/architecture/SYSTEM.md`
- `docs/architecture/ISOLATION_RULES.md`
- `docs/database/DATABASE.md`
- `backend/README.md`
- `frontend/README.md`
- `database/alembic/versions/`
- `.env.example` and `frontend/.env.example` (non-secret configuration only)
- `docs/DEVELOPMENT_LOG.md` (dated record of what changed and why)
- `.github/workflows/ci.yml`
