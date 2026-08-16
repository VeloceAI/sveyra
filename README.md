<div align="center">
<img src="docs/logo.svg?v=3" width="126" height="50" alt="SVEYRA logo" /><br/>

# SVEYRA

---

**SVEYRA is an AI-native personal style platform for intelligent styling, wardrobe management, fit, virtual try-on, beauty, and personalized shopping.**

*developed by [VeloceAI](https://veloceai.in/)*

<kbd>status: in development</kbd> <kbd>license: proprietary</kbd> <kbd>python: 3.12</kbd> <kbd>backend: FastAPI</kbd> <kbd>database: Postgres</kbd> <kbd>frontend: React + Three.js</kbd>

SVEYRA learns a user's wardrobe, body profile, measurements, fit preferences,
skin, hair, grooming needs, lifestyle, occasions, budget, and evolving tastes.
Over time, it becomes a persistent personal style intelligence layer connecting
digital wardrobe, physical identity, fashion discovery, beauty, brands,
commerce, 3D avatar, and virtual try-on.

</div>

---

## Repository Shape

```text
frontend/               Frontend app shell
backend/                FastAPI backend
database/               Postgres schema and Alembic migrations
ai/                     LLM orchestration and prompts
ml/                     Model interfaces and experiment contracts
shared/                 Shared contracts and constants
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

## What Each Folder Does

| Folder | Purpose |
| --- | --- |
| `frontend/` | User-facing app for wardrobe, outfits, profile, avatar, try-on, shopping, and stylist chat. |
| `backend/` | FastAPI product API using route, handler, service, repository structure. |
| `database/` | Postgres schema, Alembic migrations, and database documentation. |
| `ai/` | LLM prompts, AI orchestration contracts, stylist reasoning, and prompt versioning. |
| `ml/` | Model adapters, CV/fit/size interfaces, experiments, metrics, and evaluation contracts. |
| `shared/` | Shared domain vocabulary, constants, schemas, and cross-layer contracts. |
| `services/` | Independent service boundaries for CV, avatar, and recommendation intelligence. |
| `infra/` | Docker, deployment, environment, and infrastructure configuration. |
| `docs/` | Product, architecture, database, workflow, research, and decision documents. |
| `scripts/` | Developer setup, first-run, maintenance, and automation scripts. |

## Isolation Rules

The repo uses top-level independent folders:

```text
frontend/, backend/, database/, ai/, ml/, shared/, services/, infra/, docs/, scripts/
```

Detailed isolation rules are here:

```text
docs/architecture/ISOLATION_RULES.md
```

Short version:

- Keep each layer independently understandable and replaceable.
- Backend follows route, handler, service, repository.
- Postgres and Alembic are the default database path.
- AI and ML experiments stay behind stable contracts.
- Avoid files above 500 lines unless there is a strong reason.
- Avoid unused comments and empty docstrings.

## Coding Practice

- Prefer simple modules with clear ownership.
- Keep routes thin and move product logic into services.
- Keep repositories focused on database access only.
- Add migrations for schema changes instead of editing database state manually.
- Document new architecture decisions before implementation spreads.
- Treat third-party model and research repos as references until license review is complete.
- Keep tests close to behavior and scale coverage with risk.
- Use explicit names for fashion, body, fit, beauty, and commerce concepts.
- Do not mix frontend UI concerns into backend, AI, ML, or database folders.
- Do not import raw notebooks, experiments, or external repos directly into product routes.

## Reference Repositories

Reference repositories are tracked here:

```text
docs/research/SUPPORTING_REPOS.md
```

Use this file to evaluate third-party repos, priority, fit for SVEYRA, and license risk before adding them to product code.

## First Run

1. Install Python 3.12, Node.js 22+, Docker Desktop, and Git.
2. Copy `.env.example` to `.env`.
3. Start local infrastructure:

```powershell
docker compose -f infra/docker/docker-compose.yml up -d
```

4. Start the API:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

5. Start the frontend when its framework is selected:

```powershell
cd frontend
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
