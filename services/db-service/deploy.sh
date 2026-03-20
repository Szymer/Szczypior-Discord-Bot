#!/bin/bash
# Skrypt wdrożenia db-service na Fly.io

set -e

echo "🚀 Wdrażanie szczypior-db-service na Fly.io..."

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
APP_NAME="szczypior-db-service"
if ! fly apps list | grep -q "$APP_NAME"; then
    echo "📱 Tworzenie nowej aplikacji: $APP_NAME"
    fly apps create "$APP_NAME" --org personal
fi

# Ustaw sekrety w Fly.io
echo "🔑 Ustawianie sekretów..."
fly secrets set \
    DB_SERVICE_API_KEY="$DB_SERVICE_API_KEY" \
    user="$user" \
    password="$password" \
    host="$host" \
    port="$port" \
    dbname="$dbname" \
    -a "$APP_NAME"

# Wdróż aplikację (z roota projektu - kontekst dla Dockerfile)
echo "🚢 Wdrażanie aplikacji..."
cd /workspaces/Szczypior-Discord-Bot

# Skopiuj fly.toml tymczasowo do roota
cp services/db-service/fly.toml ./fly.toml.tmp

# Zaktualizuj ścieżkę Dockerfile
sed -i 's|dockerfile = "../../infrastructure/docker/db-service.Dockerfile"|dockerfile = "infrastructure/docker/db-service.Dockerfile"|' ./fly.toml.tmp

# Deploy
fly deploy --ha=false -a "$APP_NAME" -c fly.toml.tmp

# Cleanup
rm -f fly.toml.tmp

echo ""
echo "✅ Wdrożenie zakończone!"
echo ""
echo "📊 Sprawdź status:"
echo "   fly status -a $APP_NAME"
echo ""
echo "📝 Logi:"
echo "   fly logs -a $APP_NAME"
echo ""
echo "🌐 URL aplikacji:"
fly apps list | grep "$APP_NAME"
echo ""
echo "🔗 Dashboard:"
echo "   https://fly.io/apps/$APP_NAME"
