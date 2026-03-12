# Użyj oficjalnego, lekkiego image'u Pythona
FROM python:3.13-slim

# Ustaw katalog roboczy wewnątrz kontenera
WORKDIR /app

# Zmienne środowiskowe dla czystszego logowania
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Ścieżki WZGLĘDNE do kontekstu (infrastructure/docker/)
COPY services/discord-bot/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Skopiuj kod bota (z services/discord-bot/)
COPY services/discord-bot /app

COPY libs /app/libs

# Skopiuj skrypt startowy (jeśli jest w infrastructure/docker/)
COPY start.sh /app/start.sh
RUN sed -i 's/\r$//' /app/start.sh && chmod +x /app/start.sh

EXPOSE 8080

# Uruchom bota bezpośrednio (lub start.sh)
CMD ["python", "bot/main.py"]
