# Running SVEYRA locally

Three processes: the engine (a library), the API, and the web client.

## One-time setup

```bash
# Python: a fresh virtualenv, then the API and the engine
python -m venv .venv
.venv/Scripts/pip install -r backend/requirements-dev.txt   # installs the engine too

# Node
npm install
```

`backend/requirements.txt` installs the human engine from `../human-engine` as an
editable dependency, so a change to the engine is picked up without reinstalling.

## Create the database

SQLite is enough to try the product. Postgres is what production uses.

```bash
cd backend
DATABASE_URL="sqlite:///./dev.db" ../.venv/Scripts/python -c "
from app.db.base import Base
from app.db.session import get_engine
from app.models import *
Base.metadata.create_all(get_engine())
"
```

## Run it

Two terminals.

**API**

```bash
cd backend
APP_ENV=local \
STORAGE_BACKEND=memory \
AVATAR_BACKEND=sveyra \
DATABASE_URL="sqlite:///./dev.db" \
../.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

`AVATAR_BACKEND=sveyra` is the switch that turns on real 3D reconstruction.
Leave it unset and the avatar endpoint returns `503 avatar_unavailable` rather
than a fake body.

**Web**

```bash
npm --workspace @sveyra/web run dev
```

Then open <http://localhost:3000>. The web client proxies `/v1` to the API, so
there is no CORS setup and no second URL to configure.

## Trying the avatar

1. Register an account, then open **Avatar** in the nav.
2. Enter your height in centimetres. This is what sets the scale: without it
   there is no way to turn pixels into measurements.
3. Upload a **front** photo, standing, head to toe, against a plain wall. A
   **side** photo is optional but is what makes depth measured rather than
   inferred.
4. Build. Roughly three seconds later you get a rigged, textured GLB you can
   orbit, plus the measurements it derived and how confident it is.

### If it refuses

That is deliberate. The engine will not return a body it cannot honestly
reconstruct:

| Message | Cause |
| --- | --- |
| `no usable front view` | The subject was not found, or does not span enough of the frame to scale by height. Step back and use a plainer background. |
| `avatar_unavailable` | `AVATAR_BACKEND` is not set to `sveyra`, or the engine is not installed. |
| `the subject fills most of the frame` | A warning, not a failure. Step back for a better fit. |

## Without photographs

The engine also builds from measurements alone, which needs no server:

```bash
cd human-engine
../.venv/Scripts/python -m sveyra_human.cli build-parametric --height 184 --out avatar.glb
../.venv/Scripts/python -m sveyra_human.cli build-from-photos --front f.jpg --side s.jpg --height 184
```

## Tests

```bash
cd backend && ../.venv/Scripts/python -m pytest -q        # API
cd human-engine && ../.venv/Scripts/python -m pytest -q   # engine
npm --workspace @sveyra/web run test                      # web
```
