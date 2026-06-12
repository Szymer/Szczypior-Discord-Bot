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

ENV PATH="/app/db-service/.venv/bin:$PATH"

WORKDIR /app/db-service

COPY --from=build /app /app

EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]