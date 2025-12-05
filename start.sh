#!/bin/sh

# Sprawdź zmienne środowiskowe Google
if [ -n "$GOOGLE_SERVICE_ACCOUNT" ]; then
    echo "✅ GOOGLE_SERVICE_ACCOUNT environment variable is set"
    echo "   Length: ${#GOOGLE_SERVICE_ACCOUNT} chars"
    echo "   First 200 chars: $(echo "$GOOGLE_SERVICE_ACCOUNT" | head -c 200)"
    echo "   Checking for BOM..."
    echo "$GOOGLE_SERVICE_ACCOUNT" | od -An -tx1 | head -c 50
else
    echo "⚠️  GOOGLE_SERVICE_ACCOUNT not set - Google Sheets will not work"
fi

if [ -n "$GOOGLE_SHEETS_SPREADSHEET_ID" ]; then
    echo "✅ GOOGLE_SHEETS_SPREADSHEET_ID: $GOOGLE_SHEETS_SPREADSHEET_ID"
else
    echo "⚠️  GOOGLE_SHEETS_SPREADSHEET_ID not set"
fi

# Uruchom bota
python -m bot.main
