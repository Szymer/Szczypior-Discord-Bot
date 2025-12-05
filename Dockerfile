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

# Skopiuj skrypt startowy i napraw końce linii (LF zamiast CRLF)
COPY start.sh /app/start.sh
RUN sed -i 's/\r$//' /app/start.sh && chmod +x /app/start.sh

# Fly.io secrets będą używane dla wrażliwych danych
# authorized_user.json będzie tworzony przy starcie z GOOGLE_CREDENTIALS

# Polecenie do uruchomienia bota po starcie kontenera
CMD ["/app/start.sh"]
