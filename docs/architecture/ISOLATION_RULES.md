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

## Database Rule

Postgres is the default database. Alembic owns schema migrations.

## AI And ML Rule

AI and ML code must remain behind explicit contracts. Product routes should not import raw experiments, notebooks, or external model repositories directly.

## File Size Rule

Project-authored source and docs should stay below 500 lines per file. A file may go slightly above only when there is a strong reason.

## Comment Rule

Avoid unused comments and empty docstrings. Comments should explain decisions, not repeat the code.
