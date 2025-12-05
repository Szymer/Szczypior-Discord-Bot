#!/bin/sh

# Sprawdź zmienne środowiskowe Google
if [ -n "$GOOGLE_SERVICE_ACCOUNT" ]; then
    echo "✅ GOOGLE_SERVICE_ACCOUNT environment variable is set (length: ${#GOOGLE_SERVICE_ACCOUNT})"
    echo "🔍 First 100 chars: $(echo "$GOOGLE_SERVICE_ACCOUNT" | head -c 100)"
else
    echo "⚠️  GOOGLE_SERVICE_ACCOUNT not set - Google Sheets will not work"
fi

if [ -n "$GOOGLE_SHEETS_SPREADSHEET_ID" ]; then
    echo "✅ GOOGLE_SHEETS_SPREADSHEET_ID is set"
else
    echo "⚠️  GOOGLE_SHEETS_SPREADSHEET_ID not set"
fi

# Uruchom bota
python -m bot.main
