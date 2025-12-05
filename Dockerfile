# Użyj oficjalnego, lekkiego image'u Pythona
FROM python:3.11-slim

# Ustaw katalog roboczy wewnątrz kontenera
WORKDIR /app

# Skopiuj plik zależności
COPY requirements.txt .

# Zainstaluj zależności
RUN pip install --no-cache-dir -r requirements.txt

# Skopiuj resztę plików aplikacji
COPY . .

# Skopiuj pliki konfiguracyjne (jeśli istnieją)
# Fly.io secrets będą używane dla wrażliwych danych

# Polecenie do uruchomienia bota po starcie kontenera
CMD ["python", "-m", "bot.main"]
