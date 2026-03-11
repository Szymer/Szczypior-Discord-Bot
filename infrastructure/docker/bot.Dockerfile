FROM python:3.13-slim

WORKDIR /bot

COPY services/discord-bot/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY services/discord-bot /bot