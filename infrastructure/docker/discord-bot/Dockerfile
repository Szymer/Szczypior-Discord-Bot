FROM python:3.13-slim AS build

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY services/discord-bot-szczypior/pyproject.toml services/discord-bot-szczypior/uv.lock ./discord-bot/
COPY libs ./discord-bot/libs

WORKDIR /app/discord-bot

RUN uv sync --frozen --no-install-project --no-dev

COPY services/discord-bot-szczypior /app/discord-bot

RUN uv sync --frozen --no-dev


FROM python:3.13-slim

ENV PYTHONPATH="/app/discord-bot" \
    PATH="/app/discord-bot/.venv/bin:$PATH"

WORKDIR /app/discord-bot

COPY --from=build /app /app

EXPOSE 8080

CMD ["python", "run.py"]
