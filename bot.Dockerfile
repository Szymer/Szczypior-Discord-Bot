FROM python:3.13-slim AS build

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY services/discord-bot-szczypior/pyproject.toml services/discord-bot-szczypior/uv.lock ./discord-bot/
COPY libs ./discord-bot/libs

# Zmień workdir do katalogu projektu dla uv sync
WORKDIR /app/discord-bot

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY services/discord-bot-szczypior /app/discord-bot

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Runtime
FROM python:3.13-slim

# Skopiuj uv do runtime
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV PYTHONPATH="/app/discord-bot"

WORKDIR /app/discord-bot

COPY --from=build /app /app

EXPOSE 8080

CMD ["uv", "run", "bot/main.py"]