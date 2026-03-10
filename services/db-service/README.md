# DB Service

Osobny serwis API do dostępu do bazy PostgreSQL (Supabase), wspólny dla Bota i Django.

## Stack
- FastAPI
- SQLAlchemy 2.x
- Pydantic 2.x
- PostgreSQL (psycopg2)

## Run local
```bash
pip install -r services/db-service/requirements.txt
uvicorn app.main:app --app-dir services/db-service --reload --port 8080
```

## Env
Wymagane zmienne:
- `DATABASE_URL`

## API (MVP)
Prefix: `/api/v1`
- `GET /health`
- `POST /users/upsert`
- `POST /activities`
- `GET /users/{discord_id}/history`
- `GET /rankings`
- `GET /missions/active`
