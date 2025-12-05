🐍 Wdrożenie Bota Discord (Python) na Fly.io
Uruchomienie bota Discord na Fly.io wymaga skonfigurowania kilku kluczowych plików w Twoim repozytorium oraz użycia narzędzia flyctl do wdrożenia.

1. Wymagane Pliki Repozytorium
Twoje główne katalogi muszą zawierać następujące pliki, aby umożliwić zbudowanie i uruchomienie kontenera przez Fly.io:

Plik	Cel	Opis
bot.py	Aplikacja bota	Główny skrypt zawierający logikę bota.
requirements.txt	Zależności Pythona	Lista wszystkich bibliotek (np. discord.py, pycord) do zainstalowania przez pip.
Dockerfile	Instrukcje budowania	Definicja środowiska Pythona i kolejność instalacji/uruchamiania.
fly.toml	Konfiguracja Fly.io	Ustawienia regionu, zasobów i sieci dla maszyny wirtualnej (generowany przez $ fly launch).

Eksportuj do Arkuszy

2. Przykładowa Konfiguracja Plików
A. Przykład: requirements.txt
Zawiera biblioteki wymagane przez bota.

Plaintext

discord.py
aiohttp
# Dodaj inne biblioteki, jeśli są potrzebne
B. Przykład: Dockerfile
Instrukcje dla Fly.io, jak zbudować środowisko robocze.

Dockerfile

# Użyj oficjalnego, lekkiego image'u Pythona
FROM python:3.11-slim

# Ustaw katalog roboczy wewnątrz kontenera
WORKDIR /app

# Skopiuj plik zależności
COPY requirements.txt .

# Zainstaluj zależności
RUN pip install --no-cache-dir -r requirements.txt

# Skopiuj resztę plików aplikacji (w tym bot.py)
COPY . .

# Polecenie do uruchomienia bota po starcie kontenera
CMD ["python", "bot.py"]
C. Przykład: Odczytywanie Tokenu w bot.py
W pliku bota token musi być odczytywany ze zmiennej środowiskowej, a nie zakodowany na stałe.

Python

import os
import discord
from discord.ext import commands

# Odczytanie tokenu z zmiennej środowiskowej DISCORD_BOT_TOKEN
TOKEN = os.environ.get('DISCORD_BOT_TOKEN')

# Sprawdzenie, czy token istnieje
if not TOKEN:
    print("BŁĄD: Zmienna środowiskowa DISCORD_BOT_TOKEN nie jest ustawiona.")
    exit()

intents = discord.Intents.default()
intents.message_content = True # Jeśli używasz contentu wiadomości
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user}')

# ... (reszta logiki bota) ...

bot.run(TOKEN)
3. Kroki Wdrożenia na Fly.io (przy użyciu flyctl)
Wykonaj poniższe kroki w terminalu, znajdując się w katalogu głównym Twojego projektu.

Krok 1: Inicjalizacja Aplikacji (Generowanie fly.toml)
Bash

$ fly launch
Podczas inicjalizacji podaj nazwę aplikacji i wybierz region serwera.

Komenda automatycznie wygeneruje plik fly.toml.

Krok 2: Ustawienie Tokenu Bota (Secrets)
Użyj Fly Secrets, aby bezpiecznie przechowywać Twój token bota Discord.

Bash

$ fly secrets set DISCORD_BOT_TOKEN="TWÓJ_TOKEN_BOTA_TUTAJ"
Token jest teraz dostępny dla Twojego bota przez os.environ.get().

Krok 3: Wdrożenie i Budowa Kontenera
Rozpocznij proces wdrożenia. Fly.io zbuduje kontener na podstawie Dockerfile i uruchomi go.

Bash

$ fly deploy
Spowoduje to zbudowanie (Build) image'u Docker i jego wdrożenie (Deploy).

Krok 4: Monitorowanie Logów
Sprawdź, czy bot uruchomił się poprawnie i zalogował do Discorda, używając logów w czasie rzeczywistym.

Bash

$ fly logs
Powinieneś zobaczyć komunikat Zalogowano jako [nazwa_bota] z Twojego skryptu Pythona.