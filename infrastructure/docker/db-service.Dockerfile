# syntax=docker/dockerfile:1
FROM python:3.13-slim AS build

# Zainstaluj uv do obrazu budowlanego
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON=python

WORKDIR /app

# Skopiuj pliki zależności (dla cache buildu)
COPY services/db-service/pyproject.toml services/db-service/uv.lock ./db-service/

# Skopiuj libs (jeśli używane przez uv)
COPY libs ./libs

# Zmień workdir do katalogu projektu dla uv sync
WORKDIR /app/db-service

# Zainstaluj zależności do środowiska (bez projektu)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync \
        --frozen \
        --no-install-project \
        --no-dev

# Skopiuj kod serwisu
COPY services/db-service /app/db-service

# Zainstaluj sam projekt (jeśli ma main)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Opcjonalnie: zrób slim/runtime (bez uv)
FROM python:3.13-slim AS runtime

ENV PATH="/app/db-service/.venv/bin:$PATH"

WORKDIR /app/db-service

COPY --from=build /app /app

EXPOSE 80

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
