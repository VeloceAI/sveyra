# Running and Testing SVEYRA

Everything here runs on a laptop with no cloud account. External services are
opt-in: each one is selected by an environment variable that defaults to a local
stub, so the default configuration needs no API key at all.

For *why* a given external service was chosen, and what it costs, see
`platform-blueprint/07_EXTERNAL_SERVICES.md`. This file is only about getting it
running and proving it works.

---

## What runs with no credentials

| Part | Default | Needs a key? |
| --- | --- | --- |
| Backend API | `VISION_BACKEND=stub`, `STYLIST_BACKEND=stub`, `STORAGE_BACKEND=memory` | no |
| Human engine | pure NumPy/SciPy, CPU only | no |
| Canonical viewer | static files plus three.js from a CDN | no |
| Frontend | Next.js against the local API | no |
| Photo reconstruction | two downloaded MediaPipe model files | no, but see below |

The only thing that needs a Google Cloud project is `VISION_BACKEND=vertex`.
Nothing else does.

---

## 1. Prerequisites

Python 3.12, Node.js 22+, Docker Desktop, Git.

```powershell
Copy-Item .env.example .env
docker compose -f infra/docker/docker-compose.yml up -d   # Postgres + Redis
```

---

## 2. Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt

cd ..\database
alembic upgrade head        # 0010_appearance_profiles is the current head

cd ..\backend
uvicorn app.main:app --reload
```

API at `http://localhost:8000`, OpenAPI at `/docs`.

`GET /v1/platform/readiness` reports which capabilities are configured and which
are still stubs. Read that before assuming a feature is live.

### Backend tests

```powershell
cd backend
.venv\Scripts\Activate.ps1
pytest -q
```

328 tests. They use SQLite and in-memory storage, so no Postgres, no Redis and
no network are required.

---

## 3. Human engine

A separate package with its own environment, because it must stay usable
without the backend.

```powershell
cd human-engine
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest -q
```

367 tests, CPU only, about ninety seconds.

### Where the engine stands

```powershell
python tools/digital_human_status.py
```

Builds each figure and prints every acceptance gate still failing. It is
deliberately pessimistic: where geometry does not exist the manifest says so
even when a bone suggests otherwise. Twenty-four gates remain.

---

## 4. Canonical viewer

The 13,380-vertex canonical human on its 163-bone rig, skinned on the GPU.

```powershell
cd human-engine
python tools/export_canonical_viewer.py     # writes viewer/threejs/canonical_data.json
python -m http.server 8810 --directory viewer/threejs
```

Open `http://localhost:8810/canonical.html`.

- **Figure** switches between man, woman and child. Each carries its own
  skeleton; a child is not a scaled adult.
- **Outfit check** poses are click-to-queue. Selecting several numbers them, and
  **Play sequence** runs them in that order.
- **Routines** are the prepared loops: fit check, fit stress, idle sway.
- Click the body to select the bone under the pointer, then drag to rotate it.

A pose that would drive a limb into the trunk is held back rather than drawn,
and the footer says by how much.

---

## 5. Photo reconstruction

Turns a photograph into a canonical body. Needs two MediaPipe model files, which
are downloaded rather than committed:

```powershell
mkdir models
curl -L -o models/pose_landmarker_full.task `
  https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task
curl -L -o models/selfie_multiclass.tflite `
  https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite

pip install "mediapipe==0.10.35"
python human-engine/tools/photo_server.py --port 8810 `
  --segmentation-model models/selfie_multiclass.tflite `
  --pose-model models/pose_landmarker_full.task
```

0.10.35 is the version this was verified against. The pin matters because
`mediapipe.solutions`, which the older `MediaPipeSegmenter` targets, is absent
from current wheels — `vision/mediapipe_tasks.py` uses the Tasks API instead,
and that is the adapter the server wires up.

Without the models the server still starts and serves the viewer, and says
plainly that reconstruction is unavailable rather than answering uploads with a
body nothing looked at.

### Known limitation

Girths come back too large. The arms are inside the silhouette, and a front-on
view of someone standing naturally cannot separate torso from arms — measured
on the samples, hips read about twice the joint-to-joint span.
`vision/torso_extraction.py` detects this and refuses rather than guessing, and
the response names which path produced the numbers. The fix is capture guidance
telling people to hold their arms clear, not better fitting.

---

## 6. Frontend

```powershell
cd frontend
npm install
npm run dev          # http://localhost:3000
```

```powershell
npm run lint
npm run typecheck
npm run build
```

Locally, `POST /v1/auth/dev-session` issues real tokens without a login so the
app can be driven without creating an account.

> **Before deploying anywhere real, set `APP_ENV`.** That route is gated on
> `APP_ENV` being local/dev/development/test, and `app_env` defaults to
> `"local"` in `backend/app/core/config.py`. A deployment that forgets to set it
> leaves an unauthenticated token-minting endpoint live.

---

## 7. External services

All optional. Each is off by default.

| Variable | Default | Turn on with | Credentials |
| --- | --- | --- | --- |
| `VISION_BACKEND` | `stub` | `vertex` | `GOOGLE_CLOUD_PROJECT` plus Application Default Credentials |
| `STORAGE_BACKEND` | `memory` | `gcs` | `GCS_BUCKET_NAME` plus ADC |
| `STYLIST_BACKEND` | `stub` | — | not yet implemented |
| `AVATAR_BACKEND` | `sveyra` | — | none; this is the local engine |

Vertex uses `google.auth.default()`, so authenticate with:

```powershell
gcloud auth application-default login
```

`VISION_BACKEND=vertex` refuses to start without `GOOGLE_CLOUD_PROJECT` rather
than silently falling back to the stub.

**`JWT_SECRET` must be changed outside local.** The config refuses to start with
the default value when `APP_ENV` is not local, but that check is skipped while
`APP_ENV` is local — which is also the default.

---

## 8. Everything CI runs

```powershell
cd human-engine ; pytest -q ; ruff check src/ tools/ tests/
cd ..\backend   ; pytest -q
cd ..\frontend  ; npm run lint ; npm run typecheck ; npm run build
cd ..\database  ; alembic heads      # must print exactly one head
```
