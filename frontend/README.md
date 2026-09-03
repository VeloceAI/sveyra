# SVEYRA Web

Thin authenticated Next.js client for the SVEYRA backend MVP (M21).

## Prerequisites

- Node.js 22+ (repo root recommends Node 22+)
- Running SVEYRA FastAPI backend (default `http://127.0.0.1:8000`)
- Postgres + migrations applied for the API

## Install

From the repository root (npm workspaces):

```powershell
npm install --workspace @sveyra/web
```

Or from `frontend/`:

```powershell
cd frontend
npm install
```

## Configure

Copy `.env.example` to `.env.local`:

```powershell
copy .env.example .env.local
```

Non-secret settings:

- `BACKEND_URL` — FastAPI origin used by Next.js **rewrites** (`/v1/*` → backend). Default `http://127.0.0.1:8000`.
- `NEXT_PUBLIC_API_BASE_URL` — leave **empty** to call same-origin `/v1` through rewrites (recommended; avoids browser CORS). Set only if the browser should call the API host directly.

Never put JWT secrets, GCS credentials, or service-account JSON in frontend env files.

## Development

```powershell
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Unauthenticated users are sent to `/login`.

## Scripts

- `npm run dev` — local development server
- `npm run build` — production build
- `npm run typecheck` — TypeScript check
- `npm run lint` — ESLint via `next lint`

## Authentication behavior

- `POST /v1/auth/login` returns a Bearer access token.
- The token and JWT `sub` (user id) are stored in **sessionStorage** for this MVP.
- Protected requests send `Authorization: Bearer <token>`.
- Logout clears the session.
- HTTP 401 clears the session and redirects to `/login`.
- There is no refresh-token flow; re-login when the access token expires.

## Implemented routes

- `/login`, `/register`
- `/profile` — style profile + body/fit profiles
- `/wardrobe`, `/wardrobe/new`, `/wardrobe/[id]` — CRUD, upload, enrich
- `/recommend` — occasion recommendations + save outfit
- `/outfits`, `/outfits/[id]` — list/detail

## Media / image previews

1. Upload with `POST /v1/media/upload` linked to a wardrobe item.
2. Request `GET /v1/media/{asset_id}/access`.
3. If the URL starts with `http://` or `https://`, it is shown in an `<img>`.
4. If the API returns `memory://…` (default `STORAGE_BACKEND=memory`), the UI shows a clear placeholder — browsers cannot load `memory://` URLs.

### Real image previews with GCS

Run the backend with GCS configured (see backend `.env.example`):

- `STORAGE_BACKEND=gcs`
- `GCS_BUCKET_NAME=…`
- Application Default Credentials for signing

Then access URLs are short-lived HTTPS signed URLs and previews work in the browser.

## Out of scope (M21)

Avatar / virtual try-on, Three.js/R3F UI, shopping / wardrobe-gap APIs, Ollama/Qwen, conversational stylist.
