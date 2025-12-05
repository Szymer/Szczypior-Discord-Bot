# 🚀 Instrukcja wdrożenia Szczypior Bot na Fly.io

## Przygotowane pliki

✅ `Dockerfile` - Definicja obrazu Docker z Pythonem 3.11
✅ `fly.toml` - Konfiguracja aplikacji Fly.io
✅ `.dockerignore` - Pliki wykluczane z obrazu Docker

## Kroki wdrożenia

### 1. Instalacja Fly CLI

**Windows (PowerShell):**
```powershell
iwr https://fly.io/install.ps1 -useb | iex
```

**macOS/Linux:**
```bash
curl -L https://fly.io/install.sh | sh
```

### 2. Logowanie do Fly.io

```bash
fly auth login
```

### 3. Tworzenie aplikacji (opcjonalne - jeśli chcesz zmienić nazwę)

Możesz użyć wygenerowanego `fly.toml` lub utworzyć nową aplikację:

```bash
fly launch
```

### 4. Ustawienie sekretów (zmienne środowiskowe)

**WYMAGANE:**

```bash
# Token Discord
fly secrets set DISCORD_TOKEN="TWÓJ_TOKEN_DISCORD"

# Klucz API LLM (wybierz jeden)
fly secrets set ANTHROPIC_API_KEY="TWÓJ_KLUCZ_ANTHROPIC"
# lub
fly secrets set GOOGLE_GEMINI_API_KEY="TWÓJ_KLUCZ_GEMINI"
# lub
fly secrets set OPENAI_API_KEY="TWÓJ_KLUCZ_OPENAI"

# Preferred LLM provider
fly secrets set PREFERRED_LLM="anthropic"  # lub "gemini" lub "openai"
```

**OPCJONALNE (dla Google Sheets):**

```bash
# Sprawdź zawartość credentials.json i przekonwertuj na JSON string
fly secrets set GOOGLE_CREDENTIALS='{"type":"service_account","project_id":"...","private_key":"...","client_email":"..."}'

# ID arkusza Google Sheets
fly secrets set GOOGLE_SHEET_ID="TWÓJ_ID_ARKUSZA"
```

### 5. Wdrożenie aplikacji

```bash
fly deploy
```

### 6. Sprawdzenie logów

```bash
fly logs
```

Powinieneś zobaczyć komunikat podobny do:
```
Zalogowano jako Szczypior Bot
Google Sheets connected and ready
LLM Client connected
Slash commands synchronized
```

### 7. Monitorowanie

```bash
# Status aplikacji
fly status

# Logi na żywo
fly logs -f

# Informacje o maszynie
fly vm status
```

## Zarządzanie aplikacją

### Zatrzymanie bota
```bash
fly scale count 0
```

### Uruchomienie bota
```bash
fly scale count 1
```

### Restart bota
```bash
fly apps restart szczypior-discord-bot
```

### Aktualizacja sekretów
```bash
fly secrets set NAZWA_ZMIENNEJ="nowa_wartość"
```

### Wyświetlenie sekretów (tylko nazwy)
```bash
fly secrets list
```

## Konfiguracja w fly.toml

Możesz edytować `fly.toml` aby:

- **Zmienić region:** `primary_region = "waw"` (Warsaw) lub inny: `fra` (Frankfurt), `ams` (Amsterdam)
- **Zwiększyć pamięć:** `memory_mb = 512` (jeśli bot potrzebuje więcej)
- **Skalować CPU:** `cpus = 2` (jeśli bot wymaga więcej mocy)

## Rozwiązywanie problemów

### Bot się nie uruchamia

1. Sprawdź logi: `fly logs`
2. Zweryfikuj sekrety: `fly secrets list`
3. Sprawdź status: `fly status`

### Brak połączenia z Discord

- Upewnij się, że `DISCORD_TOKEN` jest poprawnie ustawiony
- Sprawdź czy bot ma odpowiednie uprawnienia w Discord Developer Portal

### Brak połączenia z Google Sheets

- Upewnij się, że `GOOGLE_CREDENTIALS` jest poprawnie sformatowany jako JSON
- Zweryfikuj `GOOGLE_SHEET_ID`
- Sprawdź czy service account ma dostęp do arkusza

### LLM Client nie działa

- Sprawdź czy ustawiony jest odpowiedni klucz API (`ANTHROPIC_API_KEY`, `GOOGLE_GEMINI_API_KEY` lub `OPENAI_API_KEY`)
- Zweryfikuj wartość `PREFERRED_LLM`

## Koszty

Fly.io oferuje darmowy tier:
- 3 shared-cpu VMs z 256MB RAM każda
- 3GB persistent storage

Szczypior Bot z konfiguracją:
- 1 VM × 256MB RAM
- ~100MB storage
- **= 0 USD/miesiąc** (w ramach free tier)

## Aktualizacja bota

Po zmianach w kodzie:

```bash
fly deploy
```

## Usunięcie aplikacji

```bash
fly apps destroy szczypior-discord-bot
```

---

**Wsparcie:** https://fly.io/docs/
**Discord Bot Tutorial:** https://discord.com/developers/docs/intro
