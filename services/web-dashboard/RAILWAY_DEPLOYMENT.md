# Railway Deployment Guide

## Wymagania

1. Konto na [Railway.app](https://railway.app)
2. Railway CLI zainstalowane (opcjonalnie)

## Django Backend Deployment

### 1. Utwórz nowy projekt na Railway

```bash
# Z katalogu głównego repo
railway login
railway init
```

### 2. Dodaj zmienne środowiskowe w Railway Dashboard:

**Wymagane:**

- `DJANGO_SECRET_KEY` - Django secret key
- `DEBUG` - `False` dla produkcji
- `DB_NAME` - Nazwa bazy danych (Supabase)
- `DB_USER` - User bazy danych
- `DB_PASSWORD` - Hasło bazy danych
- `DB_HOST` - Host bazy danych (Supabase)
- `DB_PORT` - Port bazy danych (6543 dla Supabase pooler)
- `CORS_ALLOWED_ORIGINS` - Dozwolone originy (np. `https://twoja-domena.railway.app`)
- `SUPABASE_JWT_SECRET` - JWT secret z Supabase
- `DB_SERVICE_BASE_URL` - URL do db-service (`https://szczypior-db-service.fly.dev`)
- `DB_SERVICE_API_KEY` - API key dla db-service

### 3. Deploy backend:

```bash
cd services/web-dashboard
railway up
```

## React Frontend Deployment

### 1. Utwórz nowy serwis dla frontendu

W Railway Dashboard:

- Dodaj nowy serwis w tym samym projekcie
- Wybierz repo GitHub
- Ustaw `Root Directory` na `services/web-dashboard/react`
- Railway automatycznie wykryje `railway.json`

### 2. Dodaj zmienne środowiskowe dla buildu:

**Wymagane (build-time):**

- `VITE_DJANGO_API_URL` - URL do Django backend (np. `https://twoj-backend.railway.app`)
- `VITE_SUPABASE_URL` - URL Supabase
- `VITE_SUPABASE_PUBLISHABLE_DEFAULT_KEY` - Publishable key Supabase

**Zalecane (OAuth Discord):**

- `VITE_AUTH_REDIRECT_URL` - pełny URL powrotu po logowaniu (np. `https://twoj-frontend.railway.app/home`)

### 2.1. Wymagana konfiguracja w Supabase (Auth)

W Supabase Dashboard ustaw:

- `Authentication -> URL Configuration -> Site URL`:
   - `https://twoj-frontend.railway.app`
- `Authentication -> URL Configuration -> Redirect URLs`:
   - `https://twoj-frontend.railway.app/home`
   - (opcjonalnie lokalnie) `http://localhost:8080/home`

Jeżeli produkcyjny URL nie jest na liście Redirect URLs, Supabase może zignorować `redirectTo` i przekierować na stary adres (np. localhost).

### 3. Deploy frontend:

```bash
cd services/web-dashboard/react
railway up
```

## Alternatywne wdrożenie przez GitHub

1. Połącz Railway z GitHub repo
2. Utwórz 2 serwisy w Railway:
   - **Backend**: Root directory = `services/web-dashboard`
   - **Frontend**: Root directory = `services/web-dashboard/react`
3. Ustaw zmienne środowiskowe w Railway Dashboard
4. Railway automatycznie wdroży przy każdym push do GitHub

## Sprawdzenie deployment

### Backend:

```bash
curl https://twoj-backend.railway.app/api/v1/players/
```

### Frontend:

Otwórz w przeglądarce: `https://twoj-frontend.railway.app`

## Troubleshooting

### Backend nie startuje:

- Sprawdź logi: `railway logs`
- Upewnij się że wszystkie zmienne środowiskowe są ustawione
- Sprawdź czy migracje się wykonały

### Frontend nie łączy się z backendem:

- Sprawdź `VITE_DJANGO_API_URL`
- Sprawdź `CORS_ALLOWED_ORIGINS` w backendzie
- Sprawdź logi przeglądarki (F12)

## Automatyczne deployment

Railway automatycznie wdroży nową wersję po:

- Push do GitHub (jeśli połączone)
- `railway up` z CLI
