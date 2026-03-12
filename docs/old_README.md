# Szczypior Discord Bot 🌿

Bot Discord napisany w Pythonie z wykorzystaniem biblioteki discord.py.

## 📋 Wymagania

- Python 3.9 lub nowszy
- Token Discord Bot (z [Discord Developer Portal](https://discord.com/developers/applications))

## 🚀 Instalacja

1. Sklonuj repozytorium:
```bash
git clone https://github.com/twoja-nazwa/Szczypior-Discord-Bot.git
cd Szczypior-Discord-Bot
```

2. Utwórz środowisko wirtualne:
```bash
python -m venv venv
```

3. Aktywuj środowisko wirtualne:
- Windows:
  ```bash
  venv\Scripts\activate
  ```
- Linux/Mac:
  ```bash
  source venv/bin/activate
  ```

4. Zainstaluj zależności:
```bash
pip install -r requirements.txt
```

5. Skopiuj `.env.example` na `.env` i uzupełnij swój token:
```bash
cp .env.example .env
```

6. Edytuj `.env` i wpisz swój token Discord:
```
DISCORD_TOKEN=twój_token_tutaj
```

## 🔐 Konfiguracja Uprawnień Bota

Bot wymaga następujących uprawnień Discord:

### **Wymagane uprawnienia:**
- ✅ **View Channels** - Wyświetlanie kanałów
- ✅ **Send Messages** - Wysyłanie wiadomości
- ✅ **Read Message History** - Odczyt historii wiadomości (do synchronizacji)
- ✅ **Add Reactions** - Dodawanie reakcji
- ✅ **Embed Links** - Osadzanie linków
- ✅ **Attach Files** - Załączanie plików

### **Link zaproszenia z uprawnieniami:**
```
https://discord.com/api/oauth2/authorize?client_id=TWOJE_CLIENT_ID&permissions=19520&scope=bot
```
Zastąp `TWOJE_CLIENT_ID` ID swojej aplikacji z Discord Developer Portal.

⚠️ **Jeśli bot wyświetla błąd "Missing Access"**, sprawdź przewodnik: [DISCORD_PERMISSIONS_FIX.md](DISCORD_PERMISSIONS_FIX.md)

## 🎮 Uruchomienie

```bash
python -m bot.main
```

## 🧪 Testowanie

Zainstaluj zależności deweloperskie:
```bash
pip install -r requirements-dev.txt
```

Uruchom testy:
```bash
pytest
```

Uruchom testy z pokryciem:
```bash
pytest --cov=bot --cov-report=html
```

## 🎨 Formatowanie kodu

Sprawdź formatowanie z Black:
```bash
black --check bot/ tests/
```

Automatyczne formatowanie:
```bash
black bot/ tests/
```

## 📝 Dostępne komendy

### Podstawowe
- `!ping` - Sprawdza czy bot odpowiada i pokazuje latencję
- `!hello` - Powitanie od bota
- `!pomoc` - Wyświetla listę wszystkich komend

### Zarządzanie aktywnościami
- `!typy_aktywnosci` - Wyświetla wszystkie dostępne typy aktywności
- `!dodaj_aktywnosc <typ> <wartość> [obciążenie] [przewyższenie]` - Dodaje nową aktywność
  - Przykład: `!dodaj_aktywnosc bieganie 5.2`
  - Przykład: `!dodaj_aktywnosc bieganie 10 5` (z 5kg obciążeniem)
  - Przykład: `!dodaj_aktywnosc bieganie 15 0 200` (z 200m przewyższeniem)
- `!moja_historia [limit]` - Wyświetla ostatnie aktywności użytkownika
- `!moje_punkty` - Sprawdza sumę punktów użytkownika

### Rankingi i statystyki
- `!ranking [limit]` - Ranking użytkowników według punktów
- `!stats` - Ogólne statystyki serwera
- `!stats_aktywnosci` - Statystyki według typu aktywności

### Typy aktywności
Bot wspiera następujące typy aktywności zgodnie z wytycznymi konkursu:

- 🏃 **bieganie_teren** - 1000 pkt/km (min. dystans: BRAK, bonusy: obciążenie, przewyższenie)
- 🏃‍♂️ **bieganie_bieznia** - 800 pkt/km (min. dystans: BRAK, bonusy: obciążenie)
- 🏊 **plywanie** - 4000 pkt/km (min. dystans: BRAK, bonusy: brak)
- 🚴 **rower** - 300 pkt/km (min. dystans: 6km, bonusy: przewyższenie)
- 🚶 **spacer** - 200 pkt/km (min. dystans: 3km, bonusy: obciążenie, przewyższenie)
- 🔫 **cardio** - 800 pkt/km (wioślarz, orbitrek, ASG - min. dystans: BRAK, bonusy: obciążenie, przewyższenie)

#### Bonusy punktowe:
- **Obciążenie**: 10% bazowej wartości za każde 5kg
- **Przewyższenie**: 5% bazowej wartości za każde 100m

## 🔧 Rozwój

Projekt wykorzystuje:
- **Black** - do formatowania kodu
- **pytest** - do testów jednostkowych
- **GitHub Actions** - do CI/CD

### Struktura projektu

```
Szczypior-Discord-Bot/
├── bot/                    # Kod źródłowy bota
│   ├── __init__.py
│   └── main.py            # Główny plik bota
├── tests/                 # Testy
│   ├── __init__.py
│   └── test_bot.py
├── .github/
│   └── workflows/
│       └── ci-cd.yml      # GitHub Actions CI/CD
├── .env.example           # Przykładowy plik konfiguracyjny
├── .gitignore
├── pyproject.toml         # Konfiguracja projektu
├── requirements.txt       # Zależności produkcyjne
├── requirements-dev.txt   # Zależności deweloperskie
└── README.md
```

## 🤝 Wkład w rozwój

1. Fork projektu
2. Stwórz branch z funkcjonalnością (`git checkout -b feature/AmazingFeature`)
3. Commit zmian (`git commit -m 'Add some AmazingFeature'`)
4. Push do brancha (`git push origin feature/AmazingFeature`)
5. Otwórz Pull Request

## 📜 Licencja

Ten projekt jest na licencji MIT - zobacz plik `LICENSE` po szczegóły.

## 👤 Autor

Twoje Imię - [@twój_twitter](https://twitter.com/twój_twitter)

Link do projektu: [https://github.com/twoja-nazwa/Szczypior-Discord-Bot](https://github.com/twoja-nazwa/Szczypior-Discord-Bot)
