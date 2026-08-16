# API Conventions

## Route

Routes define URLs, HTTP methods, dependencies, and response models.

## Handler

Handlers adapt HTTP concerns to use cases. They should be easy to read and avoid deep business logic.

## Service

Services own product decisions and orchestration.

## Repository

Repositories own database access. They should not call external AI, ML, or HTTP services.

## Error Shape

Use a consistent shape:

```json
{
  "error": {
    "code": "profile_not_found",
    "message": "Profile was not found."
  }
}
```
