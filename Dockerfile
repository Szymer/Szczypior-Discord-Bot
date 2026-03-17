# Użyj oficjalnego, lekkiego obrazu Pythona jako bazowego
FROM python:3.11-slim

# Ustaw katalog roboczy wewnątrz kontenera
# Wszystkie polecenia będą wykonywane w tym katalogu
WORKDIR /app

# Skopiuj plik zależności do katalogu roboczego w kontenerze
# Dzięki temu możemy zainstalować zależności przed skopiowaniem całej aplikacji
COPY bot/requirements.txt /app/requirements.txt

# Zainstaluj zależności z pliku requirements.txt
# --no-cache-dir zapobiega przechowywaniu pamięci podręcznej, co zmniejsza rozmiar obrazu
RUN pip install --no-cache-dir -r requirements.txt

# Skopiuj resztę plików aplikacji do katalogu roboczego
# Dzięki temu cały kod aplikacji znajdzie się w kontenerze
COPY bot/ /app/

# Skopiuj skrypt startowy i upewnij się, że ma poprawne końce linii (LF zamiast CRLF)
# chmod +x nadaje skryptowi uprawnienia do wykonywania
COPY start.sh /app/start.sh
RUN sed -i 's/\r$//' /app/start.sh && chmod +x /app/start.sh

# Ustaw zmienną środowiskową PYTHONPATH
# Dzięki temu Python będzie wiedział, gdzie szukać modułów (w katalogu /app)
ENV PYTHONPATH="/app"

# Polecenie do uruchomienia aplikacji po starcie kontenera
# Skrypt start.sh uruchamia bota i sprawdza zmienne środowiskowe
CMD ["/app/start.sh"]
