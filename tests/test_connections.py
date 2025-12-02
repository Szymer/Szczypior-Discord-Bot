"""Test połączenia z Google Sheets i Discord."""

import os
from dotenv import load_dotenv

# Wczytaj zmienne środowiskowe
load_dotenv()

def test_google_sheets():
    """Test połączenia z Google Sheets."""
    print("\n" + "="*60)
    print("TEST POŁĄCZENIA Z GOOGLE SHEETS")
    print("="*60)
    
    try:
        from bot.sheets_manager import SheetsManager
        
        manager = SheetsManager()
        print(f"✅ Połączono z arkuszem: {manager.spreadsheet.title}")
        print(f"✅ Aktywna zakładka: {manager.worksheet.title}")
        
        # Sprawdź nagłówki
        headers = manager.worksheet.row_values(1)
        if headers:
            print(f"✅ Nagłówki arkusza: {headers}")
        else:
            print("⚠️  Brak nagłówków - tworzę...")
            manager.setup_headers()
        
        # Pobierz liczbę wierszy
        all_data = manager.worksheet.get_all_values()
        print(f"✅ Liczba wierszy w arkuszu: {len(all_data)}")
        
        print("\n✅ Test Google Sheets zakończony sukcesem!")
        return True
        
    except Exception as e:
        print(f"\n❌ Błąd połączenia z Google Sheets: {e}")
        print("\nSprawdź:")
        print("1. Czy arkusz jest publiczny (Anyone with the link - Editor)")
        print("2. Czy GOOGLE_API_KEY jest poprawny w .env")
        print("3. Czy Google Sheets API jest włączone w Cloud Console")
        return False


def test_discord():
    """Test połączenia z Discord (bez uruchamiania bota)."""
    print("\n" + "="*60)
    print("TEST KONFIGURACJI DISCORD")
    print("="*60)
    
    token = os.getenv("DISCORD_TOKEN")
    
    if not token:
        print("❌ Brak DISCORD_TOKEN w pliku .env")
        return False
    
    if token == "your_discord_token_here":
        print("❌ DISCORD_TOKEN nie został ustawiony (wciąż placeholder)")
        return False
    
    print(f"✅ Token Discord znaleziony (długość: {len(token)} znaków)")
    
    # Sprawdź format tokenu
    if "." in token:
        parts = token.split(".")
        print(f"✅ Format tokenu wygląda poprawnie ({len(parts)} części)")
    else:
        print("⚠️  Token może być nieprawidłowy (brak kropek)")
    
    print("\n✅ Konfiguracja Discord wygląda OK!")
    print("ℹ️  Aby sprawdzić rzeczywiste połączenie, uruchom bota: python -m bot.main")
    return True


if __name__ == "__main__":
    print("\n🔍 TESTY POŁĄCZEŃ SZCZYPIOR BOT")
    
    # Test Discord
    discord_ok = test_discord()
    
    # Test Google Sheets
    sheets_ok = test_google_sheets()
    
    # Podsumowanie
    print("\n" + "="*60)
    print("PODSUMOWANIE TESTÓW")
    print("="*60)
    print(f"Discord:       {'✅ OK' if discord_ok else '❌ BŁĄD'}")
    print(f"Google Sheets: {'✅ OK' if sheets_ok else '❌ BŁĄD'}")
    print("="*60)
    
    if discord_ok and sheets_ok:
        print("\n✅ Wszystko gotowe! Możesz uruchomić bota:")
        print("   python -m bot.main")
    else:
        print("\n⚠️  Popraw błędy przed uruchomieniem bota")
