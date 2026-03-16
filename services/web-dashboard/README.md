# Web Dashboard

Ten katalog zawiera backend Django oraz frontend React dla dashboardu.

## Uruchomienie w devcontainerze

### 1. Django w kontenerze

Z katalogu głównego repo uruchom usługę `web-dashboard` przez Docker Compose:

```sh
cd /workspaces/Szczypior-Discord-Bot
docker compose -f .devcontainer/docker-compose.dev.yml --profile dashboard up --build web-dashboard
```

Backend będzie dostępny pod adresem `http://localhost:8001`.

### 2. React z Discord OAuth

Właściwy frontend z logowaniem przez Discord znajduje się w katalogu głównym repo, a nie w `services/web-dashboard/temp-react`.
Uruchom go osobno wewnątrz aktualnego workspace/devcontainera:

```sh
cd /workspaces/Szczypior-Discord-Bot
npm ci
export VITE_DJANGO_API_URL=http://localhost:8001
npm run dev -- --host 0.0.0.0 --port 8080
```

`export` działa tylko w bieżącym terminalu, więc komendę `npm run dev` uruchom w tej samej sesji.

Przy kolejnych uruchomieniach możesz pominąć `npm ci`, jeśli zależności już są zainstalowane, i odpalić frontend krócej:

```sh
cd /workspaces/Szczypior-Discord-Bot
VITE_DJANGO_API_URL=http://localhost:8001 npm run dev -- --host 0.0.0.0 --port 8080
```

Frontend będzie dostępny pod adresem `http://localhost:8080`.

Adres logowania z Discord OAuth: `http://localhost:8080/`

## Szybki workflow

Uruchom najpierw Django:

```sh
cd /workspaces/Szczypior-Discord-Bot
docker compose -f .devcontainer/docker-compose.dev.yml --profile dashboard up --build web-dashboard
```

W drugim terminalu uruchom React:

```sh
cd /workspaces/Szczypior-Discord-Bot
npm ci
export VITE_DJANGO_API_URL=http://localhost:8001
npm run dev -- --host 0.0.0.0 --port 8080
```

Jeśli `npm ci` było już wykonane wcześniej:

```sh
cd /workspaces/Szczypior-Discord-Bot
VITE_DJANGO_API_URL=http://localhost:8001 npm run dev -- --host 0.0.0.0 --port 8080
```

## Uwagi

- Compose dla tego repo ma gotową usługę dla Django, ale nie ma osobnej usługi Compose dla Reacta.
- Django ładuje zmienne z pliku `.env` w katalogu repo.
- Katalog `services/web-dashboard/temp-react` zawiera starszą wersję frontendu bez Discord OAuth i nie powinien być używany do testowania obecnego logowania.
- Porty używane lokalnie: Django `8001`, React `8080`.
