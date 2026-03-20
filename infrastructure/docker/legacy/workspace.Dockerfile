FROM python:3.13-slim

RUN apt-get update && apt-get install -y \
    git \
    curl \
    docker-cli \
    docker-compose \
    netcat-traditional \
    iputils-ping \
    dnsutils

WORKDIR /workspace

# Instalacja zależności Python wszystkich serwisów
COPY services/db-service/requirements.txt /tmp/req-db.txt
COPY services/discord-bot-szczypior/requirements.txt /tmp/req-bot.txt
COPY services/llm-service/requirements.txt /tmp/req-llm.txt
COPY services/web-dashboard/requirements.txt /tmp/req-web.txt
RUN pip install --no-cache-dir \
    -r /tmp/req-db.txt \
    -r /tmp/req-bot.txt \
    -r /tmp/req-llm.txt \
    -r /tmp/req-web.txt
