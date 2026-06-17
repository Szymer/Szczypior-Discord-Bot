# deploy.ps1 – wdrożenie discord-bot na Fly.io
# Uruchamiaj z roota repozytorium:
#   .\services\discord-bot-szczypior\deploy.ps1

$ErrorActionPreference = "Stop"

$APP_NAME   = "szczypior-discord-bot"
$ENV_FILE   = ".env"
$FLY_TOML   = "services\discord-bot-szczypior\fly.toml"

Write-Host "Wdrazanie $APP_NAME na Fly.io..." -ForegroundColor Cyan

# --- Sprawdz fly CLI ---
if (-not (Get-Command fly -ErrorAction SilentlyContinue)) {
    Write-Error "fly CLI nie jest zainstalowane. Pobierz ze: https://fly.io/docs/hands-on/install-flyctl/"
}

# --- Logowanie ---
$loggedIn = $false
$hasNativeErrPref = $null -ne (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue)
if ($hasNativeErrPref) {
    $previousNativeErrPref = $PSNativeCommandUseErrorActionPreference
    $PSNativeCommandUseErrorActionPreference = $false
}

try {
    fly auth whoami *> $null
    $loggedIn = ($LASTEXITCODE -eq 0)
}
finally {
    if ($hasNativeErrPref) {
        $PSNativeCommandUseErrorActionPreference = $previousNativeErrPref
    }
}

if (-not $loggedIn) {
    Write-Host "Logowanie do Fly.io..." -ForegroundColor Yellow
    fly auth login
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Nie udalo sie zalogowac do Fly.io"
    }
}

# --- Zaladuj .env ---
if (-not (Test-Path $ENV_FILE)) {
    Write-Error "Nie znaleziono pliku .env w: $ENV_FILE`nSkopiuj .env.example jako .env i uzupelnij wartosci."
}

$envVars = @{}
Get-Content $ENV_FILE | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith('#') -and $line -match '^([^=]+)=(.*)$') {
        $envVars[$Matches[1].Trim()] = $Matches[2].Trim()
    }
}

# --- Sprawdz wymagane sekrety ---
$required = @("DISCORD_TOKEN", "GEMINI_API_KEY", "OPENAI_API_KEY", "DB_SERVICE_BASE_URL", "DB_SERVICE_API_KEY")
$missing  = $required | Where-Object { -not $envVars[$_] }
if ($missing) {
    Write-Error "Brakujace zmienne w .env: $($missing -join ', ')"
}

# --- Utworz aplikacje jesli nie istnieje ---
$appList = fly apps list 2>&1
if ($appList -notmatch $APP_NAME) {
    Write-Host "Tworzenie nowej aplikacji: $APP_NAME" -ForegroundColor Yellow
    fly apps create $APP_NAME --org personal
}

# --- Ustaw sekrety ---
Write-Host "Ustawianie sekretow..." -ForegroundColor Yellow
fly secrets set `
    "DISCORD_TOKEN=$($envVars['DISCORD_TOKEN'])" `
    "GEMINI_API_KEY=$($envVars['GEMINI_API_KEY'])" `
    "OPENAI_API_KEY=$($envVars['OPENAI_API_KEY'])" `
    "DB_SERVICE_BASE_URL=$($envVars['DB_SERVICE_BASE_URL'])" `
    "DB_SERVICE_API_KEY=$($envVars['DB_SERVICE_API_KEY'])" `
    -a $APP_NAME

# --- Deploy ---
Write-Host "Wdrazanie..." -ForegroundColor Yellow
fly deploy `
    --ha=false `
    -a $APP_NAME `
    -c $FLY_TOML `
    --remote-only

Write-Host "Wdrozenie zakonczone!" -ForegroundColor Green
Write-Host "  Logi:   fly logs -a $APP_NAME"
Write-Host "  Status: fly status -a $APP_NAME"
