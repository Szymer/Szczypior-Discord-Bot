#!/bin/bash
# Skrypt wdrożenia discord-bot-szczypior na Fly.io

set -e

echo "🚀 Wdrażanie szczypior-discord-bot-1.0 na Fly.io..."

# Sprawdź czy fly CLI jest zainstalowane
if ! command -v fly &> /dev/null; then
    echo "❌ fly CLI nie jest zainstalowane"
    echo "Zainstaluj ze: https://fly.io/docs/hands-on/install-flyctl/"
    exit 1
fi

# Sprawdź czy jesteś zalogowany
if ! fly auth whoami &> /dev/null; then
    echo "🔐 Logowanie do Fly.io..."
    fly auth login
fi

# Załaduj zmienne z .env
ENV_FILE="../../.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Nie znaleziono pliku .env w lokalizacji: $ENV_FILE"
    exit 1
fi

echo "📦 Ładowanie sekretów z .env..."
source "$ENV_FILE"

# Sprawdź czy aplikacja istnieje
APP_NAME="szczypior-discord-bot-1-0"
if ! fly apps list | grep -q "$APP_NAME"; then
    echo "📱 Tworzenie nowej aplikacji: $APP_NAME"
    fly apps create "$APP_NAME" --org personal
fi

# Ustaw sekrety w Fly.io
echo "🔑 Ustawianie sekretów..."

# Przygotuj zmienne opcjonalne
SECRETS_CMD="fly secrets set"
SECRETS_CMD="$SECRETS_CMD DISCORD_TOKEN=\"$DISCORD_TOKEN\""
SECRETS_CMD="$SECRETS_CMD DB_SERVICE_API_KEY=\"$DB_SERVICE_API_KEY\""

# Dodaj opcjonalne sekrety jeśli istnieją
if [ ! -z "$GEMINI_API_KEY" ]; then
    SECRETS_CMD="$SECRETS_CMD GEMINI_API_KEY=\"$GEMINI_API_KEY\""
fi

if [ ! -z "$GOOGLE_API_KEY" ]; then
    SECRETS_CMD="$SECRETS_CMD GOOGLE_API_KEY=\"$GOOGLE_API_KEY\""
fi

SECRETS_CMD="$SECRETS_CMD -a $APP_NAME"

# Wykonaj komendę sekretów
eval $SECRETS_CMD

# Wdróż aplikację (z roota projektu - kontekst dla Dockerfile)
echo "🚢 Wdrażanie aplikacji..."
cd /workspaces/Szczypior-Discord-Bot

# Skopiuj fly.toml tymczasowo do roota
cp services/discord-bot-szczypior/fly.toml ./fly.toml.bot.tmp

# Zaktualizuj ścieżkę Dockerfile
sed -i 's|dockerfile = "../../infrastructure/docker/discord-bot.Dockerfile"|dockerfile = "infrastructure/docker/discord-bot.Dockerfile"|' ./fly.toml.bot.tmp

# Deploy
fly deploy --ha=false -a "$APP_NAME" -c fly.toml.bot.tmp

# Cleanup
rm -f fly.toml.bot.tmp

echo ""
echo "✅ Wdrożenie zakończone!"
echo ""
echo "📊 Sprawdź status:"
echo "   fly status -a $APP_NAME"
echo ""
echo "📝 Logi:"
echo "   fly logs -a $APP_NAME"
echo ""
echo "🔗 Dashboard:"
echo "   https://fly.io/apps/$APP_NAME"
echo ""
echo "🔧 Endpoint DB Service: https://szczypior-db-service.fly.dev"
