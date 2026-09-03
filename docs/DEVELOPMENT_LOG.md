# Development Log

A dated record of what changed and why. `PROJECT_PROGRESS.md` describes the
system as it stands today; this file explains how it got there.

Add a new entry at the top when you land work. Keep entries factual: what
changed, why it changed, and how it was verified. Link the PR.

---

## 2026-09-04 — Refresh-token sessions

PR [#3](https://github.com/VeloceAI/sveyra/pull/3)

Access tokens cap at one hour and there was no way to renew one, so every user
was signed out hourly and the web client sent them to the login screen on the
next request. That made the product hard to use and hard to dogfood.

Adds `POST /v1/auth/refresh` and `POST /v1/auth/logout`. Refresh tokens are
opaque random secrets rather than JWTs, because validity is a database lookup
and that is what makes revocation possible. Only a SHA-256 hash is stored, so a
leaked row cannot be replayed; the input is already 384 bits of entropy, so a
slow KDF would protect nothing.

Tokens rotate on every use. Presenting an already-rotated token revokes every
session for that user: rotation means the only way a revoked token reappears is
that someone kept a copy, and at that point neither holder can be trusted.
Logout is idempotent and says nothing about whether the token existed.

The web client now renews silently. A 401 triggers one refresh and replays the
original request before any redirect happens, and concurrent 401s share a single
in-flight refresh so a page with several requests in the air cannot spend its
single-use token more than once. Logging out revokes server-side instead of only
clearing browser storage.

### Verification

- Backend: `264 passed`, including rotation, reuse detection, expiry and logout
- Backend lint: `ruff check .` clean
- Alembic: single head at `0008_refresh_tokens`
- Frontend: lint, typecheck, `6 passed`, build succeeds

### Known gaps

- Tokens live in `sessionStorage`, which is reachable from XSS. An httpOnly
  cookie would be stronger, but cookies complicate the planned mobile clients,
  which is why rotation and revocation carry the risk for now.
- Nothing prunes expired rows from `refresh_tokens` yet.

---

## 2026-09-03 — Media ownership, auth rate limiting, avatar seam, CI

PR [#1](https://github.com/VeloceAI/sveyra/pull/1)

### Fixed: any user could delete another user's photos

`POST /v1/media` accepted a storage `reference` from the client and never
checked it against the caller. Ownership was verified on the asset row, but the
row pointed wherever the caller said. A second user could register a row aimed
at someone else's stored object, then mint an access URL for it or delete the
bytes behind it. On the GCS backend that was permanent loss of a user's upload.

`media_assets.reference` is now unique, so a storage object belongs to exactly
one asset row and a claim on an already-registered reference returns `409`.
Migration `0007_media_asset_reference_unique`.

### Fixed: no rate limiting on authentication

Register and login had no limiter, leaving credential stuffing unbounded and
making bcrypt a cheap CPU exhaustion vector. Added a sliding window keyed by
caller, configurable through `AUTH_RATE_LIMIT_MAX_REQUESTS` and
`AUTH_RATE_LIMIT_WINDOW_SECONDS`.

The counter is in-process, so the effective limit multiplies per worker. Move it
to Redis before running more than one API process.

### Fixed: common garment categories were silently dropped

`_bucket` matched three hardcoded frozensets, so `dress`, `jumpsuit`, `blazer`,
`cardigan`, `polo`, `vest`, `heels`, `flats`, `trainers` and the singular
`sneaker` all fell through to `None`. Those items were invisible to outfit
ranking and simultaneously counted as missing, so a wardrobe of dresses returned
no recommendations plus three false gap warnings.

Vocabulary moved to `app/services/category_taxonomy.py` and widened, with two
buckets the old three could not express: a one-piece covers both halves, and
outerwear is separate from tops so a blazer is never mistaken for the shirt
under it. Unrecognised categories still bucket as `None` but are offered as
layering extras rather than dropping out of the wardrobe.

### Added: avatar seam and corrected dependency licences

`AvatarPort` sits alongside the storage, vision and stylist ports so a hosted 2D
backend and a later 3D pipeline swap by `AVATAR_BACKEND`.

`SUPPORTING_REPOS.md` and the avatar README pointed at `smplx`, `IDM-VTON` and
`StableVITON`, all non-commercial. SMPL-X commercial licensing runs through
Meshcapade, acquired by Epic Games in February 2026. Those are marked blocked
and the cleared stack is recorded: SAM 3, SAM 3D Body, SOMA-X and Anny. SAM 3D
Body emits an MHR mesh and SOMA-X accepts MHR, so the two compose without a SMPL
licence.

Body measurements the avatar pipeline fits against are now typed. Extra keys are
still allowed so free-form data captured earlier keeps round-tripping.

### Added: CI

Nothing ran on pull requests, so the suite could only be verified by hand. The
workflow covers backend lint and tests, a single-migration-head check, and
frontend lint, typecheck, tests and build.

`ruff` selected no rules explicitly, so the rule set moved with whichever version
was installed and local runs disagreed with each other. The selection is pinned
to `E`, `F` and `I`, and bugbear is told that FastAPI resolves `Depends`,
`Query`, `File`, `Form` and `Body` per request rather than sharing one mutable
default.

That surfaced two real problems. The model relationships referenced names that
were never imported, now resolved through a `TYPE_CHECKING` block. And `tsc`
rejected the `.ts` import extension in the login redirect test, so frontend
typecheck was failing; `allowImportingTsExtensions` pairs with the existing
`noEmit` and keeps the file runnable under `node --test`. Those six tests had no
npm script at all and now run in CI.

### Verification

- Backend: `252 passed`
- Backend lint: `ruff check .` clean
- Alembic: single head at `0007_media_asset_reference_unique`
- Frontend: lint, typecheck, `6 passed`, build succeeds
- CI: Backend, Frontend and Migrations all green

### Known gaps left open

- Next.js `15.1.11` carries a critical advisory (SSRF through middleware
  redirects) plus high findings in `postcss` and `sharp`. The fix needs
  `15.5.25`, outside the stated range, so it belongs in its own PR.
- Access tokens cap at one hour with no refresh flow, so users are logged out
  hourly.
- The auth limiter counts per process.
- `ruff` is pinned to `E`, `F`, `I`. Ratchet toward `B` and `UP` once the
  existing `B904` exception chaining is cleaned up.
