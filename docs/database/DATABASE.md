# Database

Default database: PostgreSQL with Alembic migrations.

## First Entities

```mermaid
erDiagram
  users ||--|| style_profiles : has
  users ||--o{ wardrobe_items : owns
  users ||--o{ outfits : saves
  users ||--o{ body_profiles : records
  wardrobe_items }o--o{ outfits : used_in

  users {
    uuid id
    text email
    timestamptz created_at
  }

  style_profiles {
    uuid id
    uuid user_id
    jsonb preferences
    jsonb dislikes
    jsonb budget
  }

  body_profiles {
    uuid id
    uuid user_id
    jsonb measurements
    jsonb fit_preferences
  }

  wardrobe_items {
    uuid id
    uuid user_id
    text category
    text color
    text brand
    jsonb attributes
  }

  outfits {
    uuid id
    uuid user_id
    text occasion
    jsonb item_ids
    jsonb rationale
  }
```

## Migration Workflow

```powershell
cd packages/database
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Rules

- Store structured unknowns in `jsonb` early, then promote stable fields.
- Keep measurements versioned because body and fit data changes over time.
- Keep AI outputs auditable with prompt version, model version, and rationale.
