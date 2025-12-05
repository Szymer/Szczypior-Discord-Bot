#!/bin/sh

# Utwórz plik service_account.json ze zmiennej środowiskowej (opcjonalnie)
# Preferujemy używanie zmiennej GOOGLE_SERVICE_ACCOUNT bezpośrednio
if [ -n "$GOOGLE_SERVICE_ACCOUNT" ]; then
    echo "✅ GOOGLE_SERVICE_ACCOUNT environment variable is set"
else
    echo "⚠️  GOOGLE_SERVICE_ACCOUNT not set - Google Sheets will not work"
fi

# Uruchom bota
python -m bot.main
