#!/bin/bash
# Skrypt wdrożenia discord-bot na Fly.io
# Uruchamiaj z roota repozytorium:
#   bash services/discord-bot-szczypior/deploy.sh

set -e

APP_NAME="szczypior-discord-bot"
ENV_FILE=".env"
FLY_TOML="services/discord-bot-szczypior/fly.toml"

echo "🚀 Wdrażanie $APP_NAME na Fly.io..."

# --- Sprawdź zależności ---
if ! command -v fly &> /dev/null; then
    echo "❌ fly CLI nie jest zainstalowane"
    echo "Zainstaluj ze: https://fly.io/docs/hands-on/install-flyctl/"
    exit 1
fi

if ! fly auth whoami &> /dev/null; then
    echo "🔐 Logowanie do Fly.io..."
    fly auth login
fi

# --- Załaduj .env ---
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Nie znaleziono pliku .env w: $ENV_FILE"
    echo "Skopiuj .env.example jako .env i uzupełnij wartości."
    exit 1
fi

set -a
source "$ENV_FILE"
set +a

# --- Sprawdź wymagane sekrety ---
REQUIRED_VARS=(DISCORD_TOKEN GEMINI_API_KEY OPENAI_API_KEY DB_SERVICE_BASE_URL DB_SERVICE_API_KEY)
MISSING=()
for VAR in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!VAR}" ]; then
        MISSING+=("$VAR")
    fi
done

if [ ${#MISSING[@]} -ne 0 ]; then
    echo "❌ Brakujące zmienne w .env: ${MISSING[*]}"
    exit 1
fi

# --- Utwórz aplikację jeśli nie istnieje ---
if ! fly apps list | grep -q "$APP_NAME"; then
    echo "📱 Tworzenie nowej aplikacji: $APP_NAME"
    fly apps create "$APP_NAME" --org personal
fi

# --- Ustaw sekrety ---
echo "🔑 Ustawianie sekretów..."
fly secrets set \
    DISCORD_TOKEN="$DISCORD_TOKEN" \
    GEMINI_API_KEY="$GEMINI_API_KEY" \
    OPENAI_API_KEY="$OPENAI_API_KEY" \
    DB_SERVICE_BASE_URL="$DB_SERVICE_BASE_URL" \
    DB_SERVICE_API_KEY="$DB_SERVICE_API_KEY" \
    -a "$APP_NAME"

# --- Wdróż (kontekst = root repozytorium) ---
echo "🚢 Wdrażanie..."
fly deploy \
    --ha=false \
    -a "$APP_NAME" \
    -c "$FLY_TOML" \
    --remote-only

echo "✅ Wdrożenie zakończone!"
echo "   Logi: fly logs -a $APP_NAME"
echo "   Status: fly status -a $APP_NAME"
