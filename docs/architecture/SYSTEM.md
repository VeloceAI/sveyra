# System Architecture

## Layers

```mermaid
flowchart LR
  Web[Frontend App] --> API[FastAPI Backend]
  API --> DB[(Postgres)]
  API --> AI[AI Package]
  API --> Reco[Recommendation Service]
  API --> CV[Computer Vision Service]
  API --> Avatar[Avatar Service]
  CV --> ML[ML Package]
  Avatar --> ML
  Reco --> ML
```

## Backend Pattern

SVEYRA backend follows route, handler, service, repository.

```mermaid
sequenceDiagram
  participant Client
  participant Route
  participant Handler
  participant Service
  participant Repository
  participant DB
  Client->>Route: HTTP request
  Route->>Handler: Validate schema
  Handler->>Service: Run use case
  Service->>Repository: Load or persist data
  Repository->>DB: SQLAlchemy query
  DB-->>Repository: Rows
  Repository-->>Service: Domain data
  Service-->>Handler: Result
  Handler-->>Client: Response
```

## Independent Boundaries

- `apps/api` exposes product APIs.
- `packages/database` owns schema migrations.
- `packages/ai` owns prompt and model orchestration contracts.
- `packages/ml` owns model adapter contracts.
- `services/cv` owns perception workflows.
- `services/avatar` owns 3D identity and try-on workflows.
- `services/recommendation` owns ranking and styling decisions.

## Request Rule

Routes should stay thin. Handlers coordinate schemas and status codes. Services hold business logic. Repositories are the only layer that talks directly to the database.
