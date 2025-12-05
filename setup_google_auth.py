"""Skrypt do jednorazowej autoryzacji Google Sheets przez OAuth."""

import os
import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Zakres uprawnień dla Google Sheets i Google Drive
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

def setup_google_auth():
    """Autoryzacja OAuth i zapisanie tokenu."""
    creds = None
    
    # Sprawdź czy istnieje zapisany token
    if os.path.exists('authorized_user.json'):
        try:
            creds = Credentials.from_authorized_user_file('authorized_user.json', SCOPES)
        except Exception as e:
            print(f"Błąd wczytywania tokenu: {e}")
            creds = None
    
    # Jeśli brak ważnych credentials, uruchom proces autoryzacji
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Odświeżanie tokenu...")
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("❌ Brak pliku credentials.json!")
                print("Pobierz go z Google Cloud Console:")
                print("1. Przejdź do: https://console.cloud.google.com/")
                print("2. Włącz Google Sheets API i Google Drive API")
                print("3. Utwórz OAuth 2.0 Client ID (Desktop app)")
                print("4. Pobierz JSON i zapisz jako credentials.json")
                return False
            
            print("🔐 Uruchamianie procesu autoryzacji OAuth...")
            print("Za chwilę otworzy się przeglądarka - zaloguj się kontem Google")
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Zapisz token dla przyszłych użyć
        with open('authorized_user.json', 'w') as token:
            token.write(creds.to_json())
        print("✅ Token zapisany w authorized_user.json")
    
    # Test połączenia
    try:
        client = gspread.authorize(creds)
        print("\n✅ Autoryzacja zakończona pomyślnie!")
        print("Bot może teraz korzystać z Google Sheets")
        
        # Test otwarcia arkusza
        spreadsheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID', 
                                   '1g1ZE5-4pHMBEAPOlKiGkKCI7Lbg3F2HfFKq_tRdAPkE')
        try:
            sheet = client.open_by_key(spreadsheet_id)
            print(f"✅ Dostęp do arkusza: {sheet.title}")
            worksheet = sheet.get_worksheet(0)
            print(f"✅ Pierwsza zakładka: {worksheet.title}")
        except Exception as e:
            print(f"⚠️  Nie można otworzyć arkusza: {e}")
            print("Upewnij się, że arkusz jest udostępniony dla Twojego konta Google")
        
        return True
    except Exception as e:
        print(f"❌ Błąd autoryzacji: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("KONFIGURACJA GOOGLE SHEETS OAUTH")
    print("=" * 60)
    setup_google_auth()
