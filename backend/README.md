# SVEYRA API

FastAPI backend using route, handler, service, repository.

## Structure

```text
app/
  main.py
  routes/
  handlers/
  services/
  repositories/
  schemas/
  core/
```

## Local Run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Endpoint Naming

Implemented:

- `/health`
- `/v1/auth/register`
- `/v1/auth/login`
- `/v1/profile`
- `/v1/wardrobe`
- `PATCH /v1/wardrobe/{item_id}`
- `DELETE /v1/wardrobe/{item_id}`
- `POST /v1/wardrobe/{item_id}/enrich`
- `/v1/media`
- `/v1/media/upload`
- `/v1/media/{asset_id}/access`
- `DELETE /v1/media/{asset_id}`
- `/v1/outfits`
- `/v1/recommendations`
- `POST /v1/recommendations/gaps`
- `POST /v1/recommendations/shopping`

Named for later milestones (not implemented):


- `/v1/avatar`

## Recommendations

`POST /v1/recommendations` — authenticated. Body: `{ "occasion": "casual" }`. Returns ranked `recommendations` with `item_ids` and `rationale`. Uses owned wardrobe metadata (including optional `attributes.cv`), style preferences/dislikes/budget, and latest fit preferences when present. Does not read image bytes or call StoragePort. Ranking runs through `StylistPort` (default deterministic stub).

## Garment enrichment

`POST /v1/wardrobe/{item_id}/enrich` — authenticated. Loads the wardrobe item owned by the JWT user, resolves the linked media asset, reads bytes via `StoragePort.get(opaque reference)`, runs `VisionPort.analyze_garment`, and updates existing wardrobe fields (`category`, `color`, `attributes`). Clients never send storage references or image bytes. Default `VISION_BACKEND=stub` uses deterministic `StubVision` for local/tests; real CV providers are not integrated yet. Category/color columns update only when confidence is at least `0.75`; lower-confidence suggestions are stored under `attributes.cv` without overwriting user values. Missing linked media returns `404 wardrobe_media_missing`. Vision failures return `503 vision_unavailable`.

## Wardrobe lifecycle

`PATCH /v1/wardrobe/{item_id}` — authenticated partial update of `category`, `color`, `brand`, and/or `attributes`. Empty bodies and unknown fields return `422 validation_error`. Attributes must not contain URLs, storage references, or raw bytes.

`DELETE /v1/wardrobe/{item_id}` — authenticated. Cascades linked `media_assets` using M14 semantics (`StoragePort.delete` first, then metadata). Returns `204`. Storage failures return `503 storage_unavailable` and leave rows for retry. Saved outfits are not modified (historical `item_ids` may remain).

## Media storage configuration

Non-secret settings (see `.env.example`):

- `STORAGE_BACKEND` — `memory` (default) or `gcs`
- `GCS_BUCKET_NAME` — required when `STORAGE_BACKEND=gcs`
- `GCS_OBJECT_PREFIX` — optional object key prefix inside the bucket
- `MEDIA_ACCESS_URL_TTL_SECONDS` — short-lived access URL lifetime (default `900`, max `3600`)
- `JWT_SECRET` — HMAC secret for access tokens. Placeholder only in `.env.example`. Never commit a real secret.
- `JWT_ACCESS_TTL_SECONDS` — access token lifetime (default `900`, max `3600`)
- `VISION_BACKEND` — `stub` (default). Provider-neutral vision selection; only stub is implemented.
- `STYLIST_BACKEND` — `stub` (default). Provider-neutral stylist selection; only deterministic stub is implemented.

Protected product routes require `Authorization: Bearer <token>`. Identity is `users.id` from JWT `sub`. Do not send `user_id` to impersonate another user; unexpected request fields are rejected (`422 validation_error`).

List endpoints (`GET /v1/wardrobe`, `GET /v1/outfits`, `GET /v1/profile/{user_id}/body`) accept:

- `limit` — default `50`, minimum `1`, maximum `100`
- `offset` — default `0`, minimum `0`

Responses include `limit`, `offset`, and `total` plus the collection array.

`POST /v1/recommendations` returns ephemeral, ranked outfit candidates for an occasion using the authenticated user's wardrobe metadata (`category`, `color`, `brand`, `attributes` including M18 `cv` cues), style-profile preferences/dislikes/budget, and latest body fit preferences when available. Image bytes and StoragePort/GCS are not used. Recommendations are not persisted; clients may save an accepted look via `POST /v1/outfits`. Ranking is deterministic by default behind `StylistPort` so a future AI/LLM adapter can replace it without changing the HTTP contract. An empty wardrobe returns `404 wardrobe_empty`. Insufficient items return `200` with an empty `recommendations` list.

## Wardrobe gap analysis

`POST /v1/recommendations/gaps` — authenticated. Body: `{}` (no required fields). The API identifies missing primary wardrobe coverage buckets (`top`, `bottom`, `shoes`) from the authenticated user's existing wardrobe metadata. No image bytes, external APIs, LLMs, or CV are used. Identity comes exclusively from the JWT; no `user_id` may be supplied in the request. Returns `200` always, including when the wardrobe is empty (all three buckets reported as gaps). Response shape: `{ "gaps": [ { "category": "top", "priority": "high", "reason": "..." } ] }`. Unexpected request fields return `422 validation_error`. Missing JWT returns `401 unauthorized`.

## Shopping recommendations

`POST /v1/recommendations/shopping` — authenticated. Body: `{}` (no required fields). The API generates commerce recommendations linked to wardrobe gaps. It calls the `GapService` to determine the user's missing categories and fetches the user's style budget preferences (from `style_profiles`). It then queries a provider-neutral `ShoppingPort` (which uses a deterministic `StubShopping` default implementation) to return mock shoppable products matching those gaps and budget criteria. No database migrations, live catalogs, checkout, or external API integrations are used. Response shape: `{ "products": [ { "id": "...", "name": "...", "brand": "...", "price": 0.0, "url": "...", "category": "...", "image_url": "..." } ] }`. Unexpected request fields return `422 validation_error`.

GCS uses Application Default Credentials. Do not commit service-account JSON or private keys. For local GCS access, use `gcloud auth application-default login` or set `GOOGLE_APPLICATION_CREDENTIALS` to a local file outside the repository.


`GET /v1/media/{asset_id}/access` returns a temporary access URL (`{"url": "..."}`) generated server-side from the stored opaque reference. URLs are ephemeral and are not persisted in PostgreSQL.

`DELETE /v1/media/{asset_id}` removes the external object through `StoragePort.delete()` using the server-resolved opaque reference, then deletes the `media_assets` metadata row. Returns HTTP 204 on success. Storage and database deletion are not atomic; storage is deleted first. Retry the same `DELETE` after `storage_unavailable` or `media_deletion_incomplete`; deletion is idempotent when the object is already gone.
