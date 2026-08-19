# Isolation Rules

These rules keep SVEYRA modular as the product grows.

## Top-Level Folders

Each major layer lives at repo root:

- `frontend`
- `backend`
- `database`
- `ai`
- `ml`
- `shared`
- `services`
- `infra`
- `docs`
- `scripts`

## Backend Rule

Backend code follows route, handler, service, repository.

- Routes define URL and HTTP behavior.
- Handlers adapt request and response schemas.
- Services own business logic and orchestration.
- Repositories own database access.
- Authentication is a FastAPI dependency at the HTTP boundary (`get_current_user`). Repositories must not import JWT libraries. Services must not read FastAPI request objects.
- Request validation belongs at the schema/API boundary. Unexpected request fields are rejected. Provider/storage failures stay behind the storage and domain error envelope.

## Database Rule

Postgres is the default database. Alembic owns schema migrations.

Postgres stores structured product data and opaque media references. Image bytes live in object storage behind `StoragePort` (GCS in production; in-memory for tests/local). Signed access URLs are generated at request time and are not stored in PostgreSQL. Media deletion removes external objects through `StoragePort.delete()` and metadata through repositories; services orchestrate that sequence and retry the same path after a partial failure. Do not put media URLs or image bytes into `wardrobe_items.attributes`. See `docs/architecture/SYSTEM.md` (Media And Object Storage Boundary).

## AI And ML Rule

AI and ML code must remain behind explicit contracts. Product routes should not import raw experiments, notebooks, or external model repositories directly.

Vision/CV adapters live behind `VisionPort` (`backend/app/vision/`). Routes, handlers, repositories, authentication, and GCS adapters must not import provider-specific vision SDKs. Enrichment loads bytes only via `StoragePort.get` using a server-resolved opaque reference.

Stylist / recommendation ranking adapters live behind `StylistPort` (`backend/app/stylist/`). Default `StubStylist` is deterministic metadata ranking. Routes, handlers, repositories, authentication, and storage adapters must not import LLM provider SDKs.

## File Size Rule

Project-authored source and docs should stay below 500 lines per file. A file may go slightly above only when there is a strong reason.

## Comment Rule

Avoid unused comments and empty docstrings. Comments should explain decisions, not repeat the code.
