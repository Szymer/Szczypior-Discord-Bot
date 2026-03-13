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
- `user`
- `password`
- `host`
- `port`
- `dbname`
- `DB_SERVICE_API_KEY` (wymagany klucz do autoryzacji wszystkich endpointów pod `/api/v1`)

Alternatywnie można podać pojedyncze `DATABASE_URL`, ale dla Supabase Session Pooler preferowany jest zestaw powyższych pól, z automatycznie dodawanym `sslmode=require`.

Opcjonalnie:
- `DB_SERVICE_API_KEY_HEADER` (domyślnie `X-API-Key`)

Każde żądanie do `/api/v1/*` musi zawierać nagłówek z kluczem API, np.:

```bash
curl -H "X-API-Key: <twoj-klucz>" http://127.0.0.1:8080/api/v1/health
```

## API (MVP)
Prefix: `/api/v1`
- `GET /health`
- `POST /users/upsert`
- `POST /activities`
- `GET /users/{discord_id}/history`
- `GET /rankings`
- `GET /missions/active`
- `POST /challenges` - tworzy challenge i zawsze zapisuje `activity_rules`; jeśli request ich nie poda, serwis tworzy domyślne reguły z `libs/shared/constants.py`
- `GET /challenges/{challenge_id}/activity-rules`
- `POST /challenges/{challenge_id}/activity-rules` - tworzy reguły tylko dla challenge, który jeszcze ich nie ma; pusty body oznacza reguły domyślne
- `PUT /challenges/{challenge_id}/activity-rules` - podmienia cały zestaw reguł challenge; pusty body oznacza domyślne reguły
- `PATCH /challenges/{challenge_id}/activity-rules` - aktualizuje wybrane pola istniejących reguł po `activity_type`
