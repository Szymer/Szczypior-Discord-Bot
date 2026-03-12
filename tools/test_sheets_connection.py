#!/usr/bin/env python3
"""Test Google Sheets connection with Service Account"""
import os
import json
import sys

def test_connection():
    print("🔍 Testowanie połączenia z Google Sheets...")
    
    # Check environment variables
    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT")
    spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
    
    print("\n📋 Sprawdzanie zmiennych środowiskowych:")
    print(f"   GOOGLE_SERVICE_ACCOUNT: {'✅ Ustawiona' if service_account_json else '❌ Brak'}")
    print(f"   GOOGLE_SHEETS_SPREADSHEET_ID: {spreadsheet_id if spreadsheet_id else '❌ Brak'}")
    
    if not service_account_json:
        print("❌ Brak zmiennej GOOGLE_SERVICE_ACCOUNT")
        return False
    
    if not spreadsheet_id:
        print("❌ Brak zmiennej GOOGLE_SHEETS_SPREADSHEET_ID")
        return False
    
    # Parse JSON
    print("\n🔑 Parsowanie Service Account JSON...")
    print(f"   Długość: {len(service_account_json)} znaków")
    print(f"   Pierwsze 50 znaków: {service_account_json[:50]}")
    
    try:
        creds_dict = json.loads(service_account_json)
        print("   ✅ JSON poprawny")
        print(f"   Type: {creds_dict.get('type')}")
        print(f"   Project ID: {creds_dict.get('project_id')}")
        print(f"   Client email: {creds_dict.get('client_email')}")
    except json.JSONDecodeError as e:
        print(f"   ❌ Błąd parsowania JSON: {e}")
        return False
    
    # Try to authenticate
    print("\n🔐 Testowanie autoryzacji Google...")
    try:
        from google.oauth2 import service_account
        
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        print("   ✅ Credentials utworzone poprawnie")
        print(f"   Service account email: {credentials.service_account_email}")
    except Exception as e:
        print(f"   ❌ Błąd tworzenia credentials: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Try to connect to Google Sheets
    print("\n📊 Próba połączenia z arkuszem...")
    try:
        import gspread
        
        gc = gspread.authorize(credentials)
        print("   ✅ Autoryzacja gspread OK")
        
        spreadsheet = gc.open_by_key(spreadsheet_id)
        print(f"   ✅ Arkusz otwarty: {spreadsheet.title}")
        
        worksheets = spreadsheet.worksheets()
        print(f"   ✅ Liczba zakładek: {len(worksheets)}")
        for ws in worksheets:
            print(f"      - {ws.title}")
        
        # Try to read first worksheet
        if worksheets:
            ws = worksheets[0]
            print(f"\n📖 Próba odczytu pierwszej zakładki '{ws.title}'...")
            try:
                all_values = ws.get_all_values()
                print(f"   ✅ Odczytano {len(all_values)} wierszy")
                if all_values:
                    print(f"   Pierwszy wiersz: {all_values[0][:5]}...")  # First 5 columns
            except Exception as e:
                print(f"   ❌ Błąd odczytu: {e}")
                
    except gspread.exceptions.APIError as e:
        print(f"   ❌ Błąd API Google Sheets: {e}")
        import traceback
        traceback.print_exc()
        return False
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"   ❌ Nie znaleziono arkusza o ID: {spreadsheet_id}")
        print(f"   💡 Sprawdź czy Service Account ({creds_dict.get('client_email')}) ma dostęp do arkusza")
        return False
    except Exception as e:
        print(f"   ❌ Nieoczekiwany błąd: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✅ Test zakończony sukcesem!")
    return True

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
