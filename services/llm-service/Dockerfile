FROM python:3.13-slim
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml .
RUN uv pip install --system --no-cache fastapi uvicorn pydantic

COPY . .
CMD ["python", "-m", "app.main"]
