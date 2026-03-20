FROM python:3.13-slim

# Zainstaluj uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

RUN apt-get update && apt-get install -y \
    git \
    curl \
    docker-cli \
    docker-compose \
    netcat-traditional \
    iputils-ping \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Skopiuj projekty i libs (które używają uv)
COPY services/db-service/pyproject.toml services/db-service/uv.lock ./services/db-service/
COPY services/discord-bot-szczypior/pyproject.toml services/discord-bot-szczypior/uv.lock ./services/discord-bot-szczypior/
COPY services/web-dashboard/pyproject.toml services/web-dashboard/uv.lock ./services/web-dashboard/
COPY libs ./libs

# Zainstaluj zależności wszystkich serwisów używających uv
RUN cd services/db-service && uv sync --frozen --no-dev && \
    cd ../discord-bot-szczypior && uv sync --frozen --no-dev && \
    cd ../web-dashboard && uv sync --frozen --no-dev

# llm-service wciąż używa pip + requirements.txt
COPY services/llm-service/requirements.txt /tmp/req-llm.txt
RUN pip install --no-cache-dir -r /tmp/req-llm.txt

# Ustaw PATH dla wszystkich venv
ENV PATH="/workspace/services/db-service/.venv/bin:/workspace/services/discord-bot-szczypior/.venv/bin:/workspace/services/web-dashboard/.venv/bin:$PATH"
