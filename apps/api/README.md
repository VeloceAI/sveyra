# SVEYRA API

FastAPI backend using route, handler, service, repository.

## Structure

```text
app/
  main.py
  routes/
  handlers/
  services/
  repositories/
  schemas/
  core/
```

## Local Run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Endpoint Naming

- `/health`
- `/v1/profile`
- `/v1/wardrobe`
- `/v1/outfits`
- `/v1/recommendations`
- `/v1/avatar`
