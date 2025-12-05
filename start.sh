#!/bin/sh

# Utwórz plik authorized_user.json ze zmiennej środowiskowej
if [ -n "$GOOGLE_CREDENTIALS" ]; then
    printf '%s' "$GOOGLE_CREDENTIALS" > /app/authorized_user.json
    echo "✅ Created authorized_user.json from environment variable"
else
    echo "⚠️  GOOGLE_CREDENTIALS not set - Google Sheets will not work"
fi

# Uruchom bota
python -m bot.main
