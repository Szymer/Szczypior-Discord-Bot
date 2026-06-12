FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/web-dashboard/.venv/bin:$PATH" \
    PORT=8001

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY services/web-dashboard/pyproject.toml services/web-dashboard/uv.lock ./web-dashboard/
COPY libs ./web-dashboard/libs

WORKDIR /app/web-dashboard

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --python /usr/local/bin/python --no-install-project

COPY services/web-dashboard /app/web-dashboard

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --python /usr/local/bin/python

EXPOSE 8001

CMD ["sh", "-c", "python manage.py runserver 0.0.0.0:${PORT}"]