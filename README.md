# SVEYRA

SVEYRA is an AI-native personal fashion and lifestyle platform. It learns a user's wardrobe, body profile, measurements, fit preferences, skin, hair, grooming needs, lifestyle, occasions, budget, and evolving tastes.

The product goal is to become a persistent personal style intelligence layer that connects digital wardrobe, physical identity, fashion discovery, beauty, brands, commerce, 3D avatar, and virtual try-on.

## Repository Shape

```text
apps/
  web/                  Frontend app shell
  api/                  FastAPI backend
packages/
  database/             Postgres schema and Alembic migrations
  ai/                   LLM orchestration and prompts
  ml/                   Model interfaces and experiment contracts
  shared/               Shared contracts and constants
services/
  cv/                   Computer vision service boundary
  avatar/               3D avatar and try-on service boundary
  recommendation/       Styling and shopping intelligence
infra/
  docker/               Local development infrastructure
docs/
  architecture/         System design and flows
  product/              PRD and roadmap notes
  database/             Data model documentation
  research/             Supporting repos and license notes
scripts/                First-run and developer scripts
.claude/                Project agents and skills copied from Reprompt
```

## First Run

1. Install Python 3.12, Node.js 22+, Docker Desktop, and Git.
2. Copy `.env.example` to `.env`.
3. Start local infrastructure:

```powershell
docker compose -f infra/docker/docker-compose.yml up -d
```

4. Start the API:

```powershell
cd apps/api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

5. Start the frontend when its framework is selected:

```powershell
cd apps/web
npm install
npm run dev
```

## Architecture Principle

Each layer can evolve independently. The API owns request routing, handlers, services, repositories, and schemas. AI, ML, database, CV, avatar, and recommendation work live behind explicit contracts so experiments do not leak directly into product routes.

## Remote

GitHub remote:

```text
https://github.com/Veloce-AI/sveyra.git
```
