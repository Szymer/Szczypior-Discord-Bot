FROM python:3.13-slim AS build

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON=python

WORKDIR /app

COPY services/db-service/pyproject.toml services/db-service/uv.lock ./db-service/
COPY libs ./libs

WORKDIR /app/db-service

RUN uv sync \
    --frozen \
    --no-install-project \
    --no-dev

COPY services/db-service /app/db-service

RUN uv sync \
    --frozen \
    --no-dev

FROM python:3.13-slim AS runtime

# Kopiowanie obrazu uv, jeśli chcesz uruchamiać przez "uv run" (opcjonalnie, ale bezpieczniej)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app/db-service

# Kopiowanie plików z etapu build
COPY --from=build /app /app

# Cloud Run dynamicznie przypisuje PORT, usunięto sztywne EXPOSE
ENV PORT=8080

# Uruchomienie bezpośrednio z pliku binarnego w środowisku wirtualnym
CMD ["/app/db-service/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]