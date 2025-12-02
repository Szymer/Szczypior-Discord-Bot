# 🚀 Szybki start - Szczypior Bot

## Uruchomienie bota (bez Google Sheets)

Jeśli chcesz tylko przetestować bota bez zapisywania danych:

1. Upewnij się, że masz skonfigurowany `.env` z tokenem Discord:
```bash
DISCORD_TOKEN=twój_token_discord
```

2. Uruchom bota:
```bash
.\venv\Scripts\python.exe -m bot.main
```

Bot będzie działał, ale **dane nie będą zapisywane** do Google Sheets.

---

## Uruchomienie bota (z Google Sheets)

### Krok 1: Konfiguracja Google Sheets

Dodaj do `.env`:
```bash
DISCORD_TOKEN=twój_token_discord
GOOGLE_SHEETS_SPREADSHEET_ID=1dTQzfN9QnknQhGlcumyZ9nkvV4AMzJm6kNYouOmXcJo
```

### Krok 2: Autoryzacja Google

**Opcja A: OAuth (zalecane)**
```bash
python setup_google_auth.py
```
Postępuj zgodnie z instrukcjami w przeglądarce.

**Opcja B: API Key (arkusz musi być publiczny)**
```bash
GOOGLE_API_KEY=twój_api_key
```

### Krok 3: Uruchom bota
```bash
.\venv\Scripts\python.exe -m bot.main
```

---

## Pierwsze kroki na Discord

1. **Sprawdź czy bot działa:**
```
!ping
```

2. **Wyświetl pomoc:**
```
!pomoc
```

3. **Zobacz dostępne aktywności:**
```
!typy_aktywnosci
```

4. **Dodaj swoją pierwszą aktywność:**
```
!dodaj_aktywnosc bieganie 5
```

5. **Sprawdź swoje punkty:**
```
!moje_punkty
```

6. **Zobacz ranking:**
```
!ranking
```

---

## Testowanie funkcji

### Test kalkulacji punktów
```bash
.\venv\Scripts\python.exe tests\test_calculations.py
```

### Test połączenia z Google Sheets
```bash
python test_connections.py
```

---

## Najważniejsze komendy

| Komenda | Opis | Przykład |
|---------|------|----------|
| `!pomoc` | Wyświetla wszystkie komendy | `!pomoc` |
| `!typy_aktywnosci` | Lista aktywności | `!typy_aktywnosci` |
| `!dodaj_aktywnosc` | Dodaj aktywność | `!dodaj_aktywnosc bieganie 10` |
| `!moja_historia` | Twoja historia | `!moja_historia` |
| `!moje_punkty` | Twoje punkty | `!moje_punkty` |
| `!ranking` | Ranking użytkowników | `!ranking` |
| `!stats` | Statystyki serwera | `!stats` |

---

## Rozwiązywanie problemów

### Bot nie odpowiada
- Sprawdź czy MESSAGE CONTENT INTENT jest włączony w Discord Developer Portal
- Sprawdź czy bot ma uprawnienia do czytania i pisania wiadomości

### Google Sheets nie działa
- Sprawdź czy plik `authorized_user.json` istnieje (OAuth)
- Sprawdź czy GOOGLE_SHEETS_SPREADSHEET_ID jest poprawny
- Bot będzie działał bez Google Sheets (dane nie będą zapisywane)

### Błąd importu modułów
- Upewnij się, że środowisko wirtualne jest aktywne
- Zainstaluj ponownie zależności: `pip install -r requirements.txt`

---

## Przykładowe sesje

### Sesja 1: Pierwszy użytkownik
```
!ping                          # Sprawdź bota
!typy_aktywnosci              # Zobacz co możesz dodać
!dodaj_aktywnosc bieganie 5   # Dodaj swój pierwszy bieg
!moje_punkty                  # Sprawdź ile masz punktów
```

### Sesja 2: Aktywny tydzień
```
!dodaj_aktywnosc bieganie 8
!dodaj_aktywnosc rower 20
!dodaj_aktywnosc silownia 45
!dodaj_aktywnosc bieganie 10 5 # Z plecakiem 5kg
!moja_historia                # Zobacz co zrobiłeś
!moje_punkty                  # Sprawdź postęp
```

### Sesja 3: Rywalizacja
```
!ranking                      # Sprawdź kto jest na topie
!stats                        # Zobacz statystyki serwera
!stats_aktywnosci            # Co ludzie najczęściej robią
```

---

## Dalsze kroki

- [ ] Zaproś znajomych na serwer Discord
- [ ] Regularnie dodawaj swoje aktywności
- [ ] Śledź postępy w rankingu
- [ ] Rywalizuj z innymi o najwyższe miejsce!

**Powodzenia! 🌿🏃‍♂️**
