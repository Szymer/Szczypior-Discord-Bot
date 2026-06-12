FROM python:3.13-slim AS build

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY services/web-dashboard/pyproject.toml services/web-dashboard/uv.lock ./web-dashboard/
COPY libs ./web-dashboard/libs

WORKDIR /app/web-dashboard

# Usunięto --mount=type=cache
RUN uv sync --frozen --python /usr/local/bin/python --no-install-project --no-dev

COPY services/web-dashboard /app/web-dashboard

# Usunięto --mount=type=cache
RUN uv sync --frozen --python /usr/local/bin/python --no-dev

RUN mkdir -p /app/staticfiles

FROM python:3.13-slim

ENV PATH="/app/web-dashboard/.venv/bin:$PATH" \
    PORT=8000

WORKDIR /app/web-dashboard

RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /app /app

EXPOSE 8000

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 3 webdashboard.wsgi:application"]