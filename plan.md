Szczypior - Specyfikacja Bota Trackera Aktywności Fizycznej
Kompleksowa dokumentacja systemu automatycznego śledzenia aktywności sportowych z integracją Gemini AI i Google Sheets dla serwera Discord.

📋 SPIS TREŚCI

Przegląd Systemu
Architektura
Przepływ Danych
Moduły Funkcjonalne
System Punktacji
Integracja z Gemini AI
Struktura Danych
Obsługa Błędów
Plan Implementacji


🎯 PRZEGLĄD SYSTEMU
Cel Projektu
Szczypior to bot Discord automatyzujący proces śledzenia aktywności fizycznych w ramach konkursu sportowego. System wykorzystuje sztuczną inteligencję (Google Gemini) do analizy zdjęć z aplikacji sportowych i automatycznego zapisywania wyników do wspólnej bazy danych.
Główne Funkcjonalności

Automatyczna Analiza Obrazów - Bot analizuje zdjęcia ekranów z aplikacji sportowych (Strava, Nike Run Club, Garmin, itp.)
Wydobywanie Danych - Automatyczne rozpoznawanie typu aktywności, dystansu, czasu i innych metryk
Inteligentne Komentarze - Gemini AI generuje spersonalizowane, motywujące komentarze na podstawie historii użytkownika
System Punktacji - Zaawansowany system naliczania punktów zgodny z regulaminem konkursu
Integracja z Google Sheets - Centralna baza danych dostępna dla wszystkich uczestników
Rankingi i Statystyki - Automatyczne generowanie rankingów i statystyk użytkowników

Kluczowe Technologie

Discord.py - Komunikacja z Discord API
Google Gemini 1.5 Flash - Analiza obrazów i generowanie komentarzy
Google Sheets API - Przechowywanie i zarządzanie danymi
Python 3.10+ - Język implementacji


🏗️ ARCHITEKTURA
Diagram Komponentów
┌─────────────────────────────────────────────────────────────┐
│                     DISCORD SERVER                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Kanał #treningi (Monitorowany)                    │    │
│  │  - User wysyła zdjęcie ekranu z aplikacji          │    │
│  │  - User opcjonalnie dodaje info o obciążeniu       │    │
│  └────────────────┬───────────────────────────────────┘    │
└───────────────────┼────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    BOT SZCZYPIOR                            │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Event Listener (on_message)                         │  │
│  │  - Filtruje kanały monitorowane                      │  │
│  │  - Ignoruje boty i GIFy                              │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                       │
│  ┌──────────────────▼───────────────────────────────────┐  │
│  │  Message Analyzer                                    │  │
│  │  - Wykrywa załączniki graficzne                      │  │
│  │  - Parsuje tekst (regex dla kg, km)                  │  │
│  │  - Wydobywa timestamp wiadomości                     │  │
│  └──────────────────┬───────────────────────────────────┘  │
└────────────────────┼────────────────────────────────────────┘
                     │
         ┌───────────┴────────────┐
         │                        │
         ▼                        ▼
┌──────────────────┐    ┌──────────────────────┐
│  Weight Cache    │    │  Image Processor     │
│  (In-Memory)     │    │  - Download image    │
│                  │    │  - Validate format   │
│  Key:            │    │  - Prepare for AI    │
│  user-timestamp  │    └──────────┬───────────┘
│                  │               │
│  TTL: 30min      │               │
└──────────────────┘               │
         │                         │
         │         ┌───────────────▼────────────────┐
         │         │  Google Sheets Manager         │
         │         │  - Fetch user history          │
         │         │  - Get past activities         │
         │         │  - Calculate statistics        │
         │         └───────────────┬────────────────┘
         │                         │
         │                         ▼
         │         ┌────────────────────────────────┐
         │         │  Gemini AI Analyzer            │
         │         │  1. Receive: image + history   │
         │         │  2. Analyze: extract metrics   │
         │         │  3. Generate: smart comment    │
         │         └───────────────┬────────────────┘
         │                         │
         │                         ▼
         │         ┌────────────────────────────────┐
         │         │  Data Aggregator               │
         └────────►│  - Combine AI results          │
                   │  - Add cached weight           │
                   │  - Merge all data points       │
                   └───────────────┬────────────────┘
                                   │
                                   ▼
                   ┌────────────────────────────────┐
                   │  Points Calculator             │
                   │  - Base points (distance×rate) │
                   │  - Weight bonus                │
                   │  - Elevation bonus             │
                   │  - Special mission check       │
                   └───────────────┬────────────────┘
                                   │
                   ┌───────────────▼────────────────┐
                   │  Google Sheets Writer          │
                   │  - Append new row              │
                   │  - Update totals               │
                   │  - Log mission completion      │
                   └───────────────┬────────────────┘
                                   │
                                   ▼
                   ┌────────────────────────────────┐
                   │  Response Generator            │
                   │  - Create Discord Embed        │
                   │  - Include AI comment          │
                   │  - Show points breakdown       │
                   │  - Reply to user               │
                   └────────────────────────────────┘
Warstwy Systemu
1. Warstwa Komunikacji (Discord Layer)

Nasłuchiwanie wiadomości na określonych kanałach
Filtrowanie eventów (ignorowanie botów, GIFów)
Wysyłanie odpowiedzi do użytkowników

2. Warstwa Przetwarzania (Processing Layer)

Analiza treści wiadomości (tekst + załączniki)
Ekstrakcja danych numerycznych (dystans, obciążenie)
Zarządzanie cache'em tymczasowym

3. Warstwa Analizy AI (AI Layer)

Komunikacja z Gemini API
Analiza wizualna obrazów
Generowanie kontekstowych komentarzy

4. Warstwa Logiki Biznesowej (Business Logic Layer)

Kalkulacja punktów według regulaminu
Walidacja minimalnych dystansów
Sprawdzanie misji specjalnych

5. Warstwa Persystencji (Data Layer)

Integracja z Google Sheets API
Zapis historii aktywności
Generowanie rankingów i statystyk


🔄 PRZEPŁYW DANYCH
Scenariusz 1: Użytkownik Wysyła Zdjęcie Ekranu
1. USER ACTION
   └─► Wysyła wiadomość na #treningi
       - Załącza screenshot z Strava
       - Opcjonalnie pisze: "20kg obciążenie"

2. BOT DETECTION
   └─► on_message event triggered
       - Sprawdza: czy kanał = #treningi? ✓
       - Sprawdza: czy author = bot? ✗
       - Sprawdza: czy są załączniki? ✓
       - Sprawdza: czy to GIF? ✗
       → Przekazuje do przetwarzania

3. TEXT PARSING
   └─► Regex analysis na tekście wiadomości
       - Pattern: (\d+)\s*kg
       - Wynik: weight = 20
       → Cache: "user123-1701619200" = {weight: 20, expires: +30min}

4. IMAGE DOWNLOAD
   └─► Pobiera załącznik z Discord CDN
       - URL: https://cdn.discordapp.com/attachments/...
       - Format: PNG/JPG
       → Przygotowuje do wysłania do Gemini

5. HISTORY FETCH
   └─► Google Sheets: SELECT * WHERE user_id = "user123"
       - Znajduje 47 poprzednich aktywności
       - Ostatnie 3:
         * Bieganie: 10km, 10000 pkt
         * Rower: 25km, 7500 pkt
         * Bieganie: 8km, 8400 pkt (z 5kg)
       → Przygotowuje summary dla AI

6. GEMINI ANALYSIS
   └─► Wysyła do Gemini:
       - Image: screenshot
       - Prompt: "Analyze this workout + user history"
       
       Gemini odpowiada:
       {
         "activity_type": "bieganie_teren",
         "distance_km": 12.5,
         "duration": "01:15:30",
         "elevation_m": 150,
         "confidence": 0.92,
         "motivational_comment": "Wow! 12.5km z 20kg plecakiem to hardcore! 
         Widzę że systematycznie pchasz swoje limity - 3 tygodnie temu 
         biegałeś z 5kg, teraz 20kg. Respect! 💪"
       }

7. DATA AGGREGATION
   └─► Łączy dane:
       - Gemini: activity_type, distance, elevation
       - Cache: weight = 20kg
       - Timestamp: message.created_at

8. POINTS CALCULATION
   └─► PointsCalculator.calculate()
       - Base: 12.5km × 1000 = 12,500 pkt
       - Weight bonus: 20kg × 50 × 12.5km = 12,500 pkt
       - Elevation bonus: 150m × 10 = 1,500 pkt
       - Total: 26,500 pkt
       
   └─► SpecialMissions.check()
       - Dystans 12.5km > 5km minimum ✓
       - Jest grudzień 2024 ✓
       - Misja "Rozruch Zimowy": +2,000 pkt bonusu

9. SHEETS WRITE
   └─► Append row:
       | 2024-12-03 14:30 | user123 | Jan | bieganie_teren | 
       | 12.5 | 01:15:30 | 20 | 150 | 12500 | 14000 | 26500 |
       | "Wow! 12.5km z 20kg..." | 2000 |

10. DISCORD RESPONSE
    └─► Tworzy Embed:
        ┌─────────────────────────────────────────┐
        │ 🏃 Aktywność Zapisana!                  │
        │                                          │
        │ Typ: Bieganie Teren                     │
        │ Dystans: 12.5 km                        │
        │ Czas: 01:15:30                          │
        │                                          │
        │ 🎯 Punkty: 26,500 pkt                   │
        │ • Bazowe: 12.5km × 1000 = 12,500 pkt   │
        │ • Obciążenie 20kg: +12,500 pkt          │
        │ • Przewyższenie 150m: +1,500 pkt        │
        │                                          │
        │ 🏆 Misje Ukończone!                     │
        │ 🎖️ Rozruch Zimowy: +2,000 pkt          │
        │                                          │
        │ 💬 Komentarz AI:                        │
        │ Wow! 12.5km z 20kg plecakiem to         │
        │ hardcore! Widzę że systematycznie       │
        │ pchasz swoje limity. Respect! 💪        │
        │                                          │
        │ Użytkownik: Jan                         │
        └─────────────────────────────────────────┘
    
    └─► Wysyła jako reply do wiadomości użytkownika
Scenariusz 2: Użytkownik Najpierw Pisze o Obciążeniu, Potem Wysyła Zdjęcie
1. MESSAGE 1 (14:28:00)
   User: "Dzisiaj bieganie z 15kg plecakiem"
   └─► Bot: Parsuje "15kg" → Cache["user123-1701619680"] = {weight: 15}

2. MESSAGE 2 (14:30:15) - 2 minuty później
   User: [załącza screenshot z Garmin]
   └─► Bot: 
       - Analizuje obrazek przez Gemini
       - Szuka weight w cache w oknie ±30min
       - Znajduje: weight = 15kg z message timestamp 14:28:00
       - Łączy dane i przetwarza normalnie

🧩 MODUŁY FUNKCJONALNE
Moduł 1: Event Listener & Filtering
Odpowiedzialność:

Nasłuchiwanie wszystkich wiadomości na serwerze Discord
Filtrowanie wiadomości według konfiguracji
Przekazywanie relevantnych wiadomości do processingu

Kryteria Filtrowania:

Kanał - Tylko wiadomości z kanałów w MONITORED_CHANNELS
Autor - Ignoruje wiadomości od botów (message.author.bot == False)
Załączniki - Sprawdza czy są załączniki graficzne
Format - Odrzuca GIFy, akceptuje PNG/JPG/WEBP

Konfiguracja:

Lista ID kanałów do monitorowania (zmienna środowiskowa)
Możliwość dynamicznego dodawania/usuwania kanałów przez komendę admina


Moduł 2: Message Analyzer & Data Extraction
Odpowiedzialność:

Analiza treści tekstowej wiadomości
Ekstrakcja danych numerycznych
Identyfikacja kontekstu (obciążenie, dystans, czas)

Parsowane Wzorce:
Obciążenie (Weight)

20kg, 20 kg, 20kilo, 20 kilogramów
obciążenie: 15kg, obciążenie 15 kg
z 25kg, z plecakiem 10kg
backpack 20kg, vest 15kg

Dystans (Distance)

5km, 5.5km, 5,5 km
dystans: 10km, dystans 10 km
przebiegłem 8km, przejechałem 25km

Czas (Time)

45min, 1h 30min, 1:30:00
czas: 01:15:30

Algorytm:

Normalizacja tekstu (lowercase, usunięcie znaków specjalnych)
Zastosowanie regex patterns w kolejności priorytetu
Walidacja wydobytych wartości (zakres 0-100kg dla obciążenia)
Zwrócenie struktury danych lub None jeśli nie znaleziono


Moduł 3: Weight Cache System
Odpowiedzialność:

Tymczasowe przechowywanie informacji o obciążeniu
Kojarzenie danych tekstowych ze zdjęciami
Automatyczne czyszczenie wygasłych wpisów

Struktura Cache:
Key: "{user_id}-{message_timestamp}"
Value: {
  weight: float,
  timestamp: datetime,
  expires_at: datetime (timestamp + 30min)
}
Mechanizm Działania:

User pisze "15kg" → wpis do cache z TTL 30min
User wysyła zdjęcie → bot sprawdza cache w oknie ±30min
Bot znajduje matching weight i używa w kalkulacji
Po 30min wpis automatycznie wygasa

Implementacja:

In-memory dictionary dla prostoty (Python dict)
Opcjonalnie Redis dla produkcji i multiple instances
Background task co 5min czyści expired entries


Moduł 4: Image Processor
Odpowiedzialność:

Pobieranie obrazów z Discord CDN
Walidacja formatów i rozmiaru
Przygotowanie obrazu dla Gemini API

Wspierane Formaty:

PNG
JPG/JPEG
WEBP

Proces:

Pobranie URL załącznika z Discord message
HTTP request do Discord CDN
Walidacja content-type i rozmiaru (max 20MB)
Konwersja do PIL Image object
Opcjonalna kompresja jeśli > 5MB
Przygotowanie base64 lub binary dla API


Moduł 5: Google Sheets Manager
Odpowiedzialność:

Komunikacja z Google Sheets API
CRUD operations na danych aktywności
Generowanie statystyk i rankingów

Główne Operacje:
get_user_history(user_id)
Pobiera wszystkie aktywności danego użytkownika z arkusza
Zwraca:
python[
  {
    'timestamp': '2024-12-01 10:30:00',
    'activity_type': 'bieganie_teren',
    'distance': 10.0,
    'duration': '00:50:00',
    'total_points': 10000,
    ...
  },
  ...
]
add_activity(activity_data)
Dodaje nowy wiersz z aktywnością do arkusza
Parametry:
python{
  'user_id': str,
  'username': str,
  'timestamp': datetime,
  'activity_type': str,
  'distance': float,
  'duration': str,
  'weight': float | None,
  'elevation': int | None,
  'points': int,
  'bonus_points': int,
  'comment': str,
  'mission_bonus': int
}
get_leaderboard(limit=10)
Zwraca ranking użytkowników według łącznej liczby punktów
Zwraca:
python[
  ('user123', {'username': 'Jan', 'total_points': 125000, 'activities': 47}),
  ('user456', {'username': 'Anna', 'total_points': 98000, 'activities': 32}),
  ...
]
get_activity_stats()
Zwraca statystyki globalne
Zwraca:
python{
  'total_activities': 523,
  'total_distance': 2547.5,
  'total_points': 1850000,
  'most_active_user': 'Jan',
  'most_popular_activity': 'bieganie_teren'
}
```

**Optymalizacja:**
- Cache dla często odpytywanych danych (leaderboard, stats)
- Batch operations dla multiple writes
- Rate limiting zgodnie z Google API limits

---

### Moduł 6: Gemini AI Analyzer

**Odpowiedzialność:**
- Analiza wizualna zdjęć z aplikacji sportowych
- Ekstrakcja metryk treningowych
- Generowanie spersonalizowanych komentarzy AI

#### Struktura Promptu dla Gemini

**Sekcja 1: Instrukcje Podstawowe**
```
Jesteś ekspertem od analizy aktywności sportowych. 
Przeanalizuj zdjęcie ekranu z aplikacji sportowej 
i wydobądź następujące informacje z maksymalną precyzją:

1. TYP AKTYWNOŚCI - Określ dokładny typ:
   - bieganie_teren (outdoor running, trail)
   - bieganie_bieznia (treadmill)
   - plywanie (swimming)
   - rower (cycling)
   - rolki (inline skating)
   - spacer (walking, nordic walking)
   - trekking (hiking)
   - inne_cardio (rowing machine, elliptical, airsoft)

2. METRYKI:
   - Dystans w kilometrach (dokładność do 0.1km)
   - Czas trwania (format HH:MM:SS)
   - Przewyższenie w metrach (jeśli widoczne)
   - Tempo średnie (jeśli widoczne)
   - Kalorie (jeśli widoczne)

3. CONFIDENCE LEVEL:
   - Oceń pewność rozpoznania (0.0 - 1.0)
   - 0.9+ = bardzo pewny
   - 0.7-0.9 = pewny
   - 0.5-0.7 = niepewny (wymaga konfirmacji)
   - <0.5 = bardzo niepewny (odrzuć)
```

**Sekcja 2: Kontekst Historii Użytkownika**
```
HISTORIA UŻYTKOWNIKA:
Użytkownik: {username}
Łączna liczba aktywności: {total_activities}
Całkowity dystans: {total_distance} km
Łączne punkty: {total_points}
Ulubiona aktywność: {favorite_activity}

Ostatnie 5 treningów:
1. {date}: {activity} - {distance}km, {points} pkt
2. {date}: {activity} - {distance}km, {points} pkt
3. {date}: {activity} - {distance}km, {points} pkt
4. {date}: {activity} - {distance}km, {points} pkt
5. {date}: {activity} - {distance}km, {points} pkt

Statystyki z ostatniego miesiąca:
- Średni dystans: {avg_distance} km
- Najdłuższy trening: {max_distance} km
- Częstotliwość: {frequency} treningów/tydzień
- Trend: {trend} (rosnący/stabilny/spadający)
```

**Sekcja 3: Instrukcje Komentarza**
```
Na podstawie analizy obrazu I historii użytkownika wygeneruj 
KRÓTKI (max 2 zdania) motywujący komentarz, który:

✓ Jest pozytywny i budujący
✓ Odnosi się do konkretnych danych (dystans, postęp)
✓ Porównuje z poprzednimi wynikami jeśli to relevant
✓ Brzmi naturalnie, jak komentarz trenera/kolegi
✓ Używa emoji (max 2) dla ekspresji

✗ NIE jest sarkatyczny
✗ NIE jest zbyt długi (max 2 zdania!)
✗ NIE zawiera ogólników typu "dobra robota"
✗ NIE powtarza tylko suchych danych

PRZYKŁADY DOBRYCH KOMENTARZY:
- "15km w godzinę to świetne tempo! Widzę że systematycznie 
   poprawiasz formę - miesiąc temu Twoja średnia to było 13km. 💪"
- "Wow, 20kg obciążenia na 10km! To już poziom ultramaratończyka. 
   Respect za konsekwencję! 🔥"
- "Kolejny dzień z rzędu na rowerze - widać że cel 1000km/miesiąc 
   jest w zasięgu! Jeszcze 150km i masz to! 🚴"

ODPOWIEDŹ W FORMACIE JSON:
{
  "activity_type": "string",
  "distance_km": float,
  "duration": "HH:MM:SS",
  "elevation_m": int | null,
  "pace": "MM:SS",
  "calories": int | null,
  "confidence": float,
  "motivational_comment": "string (MAX 2 ZDANIA!)",
  "detected_app": "string (Strava/Garmin/Nike/etc)"
}
Przykładowa Odpowiedź Gemini
json{
  "activity_type": "bieganie_teren",
  "distance_km": 12.8,
  "duration": "01:12:45",
  "elevation_m": 220,
  "pace": "05:41",
  "calories": 987,
  "confidence": 0.94,
  "motivational_comment": "Rekord dystansu pobity - 12.8km to Twój najlepszy wynik! Z takim tempem cel maratonu w przyszłym roku jest całkowicie realny. 🏃💨",
  "detected_app": "Strava"
}
```

#### Przetwarzanie Odpowiedzi

**Walidacja:**
1. Sprawdzenie czy confidence ≥ 0.6
2. Walidacja activity_type (czy jest na liście dozwolonych)
3. Sprawdzenie czy distance > 0
4. Walidacja długości komentarza (max 300 znaków)

**Fallback dla Niskiej Confidence:**
- Jeśli confidence < 0.6 → Bot prosi użytkownika o potwierdzenie
- Wyświetla wykryte dane i czeka na reakcję ✅/❌
- Po potwierdzeniu zapisuje normalnie

**Error Handling:**
- Timeout (30s) → Retry 1x → Fallback do manual entry
- Invalid JSON → Log error → Ask user to use manual command
- API Error → Informuje użytkownika + notify admin

---

## 📊 SYSTEM PUNKTACJI

### Tabela Podstawowych Stawek

| Typ Aktywności | Punkty/km | Min. Dystans | Bonusy Dostępne |
|----------------|-----------|--------------|-----------------|
| Bieganie (teren) | 1000 | - | obciążenie, przewyższenie |
| Bieganie (bieżnia) | 800 | - | obciążenie |
| Pływanie | 4000 | - | - |
| Rower | 300 | 6km | przewyższenie |
| Rolki | 300 | 6km | przewyższenie |
| Spacer | 200 | 3km | obciążenie, przewyższenie |
| Trekking | 200 | 3km | obciążenie, przewyższenie |
| Inne cardio | 800 | - | obciążenie, przewyższenie |

### Algorytm Kalkulacji

#### Krok 1: Walidacja Minimalnego Dystansu
```
IF activity.distance < MIN_DISTANCE[activity.type]:
    RETURN {
        points: 0,
        message: "Dystans poniżej minimum"
    }
```

#### Krok 2: Punkty Bazowe
```
base_points = distance_km × BASE_RATE[activity_type]
```

#### Krok 3: Bonus za Obciążenie
```
IF weight_kg AND activity_type IN allowed_weight_activities:
    weight_bonus = weight_kg × 50 × distance_km
    
Przykład:
- 10km bieg z 15kg plecakiem
- Bonus = 15kg × 50 × 10km = 7,500 pkt
```

#### Krok 4: Bonus za Przewyższenie
```
IF elevation_m AND activity_type IN allowed_elevation_activities:
    elevation_bonus = elevation_m × 10
    
Przykład:
- Bieg z 300m przewyższenia
- Bonus = 300m × 10 = 3,000 pkt
```

#### Krok 5: Misje Specjalne
```
FOR each active_mission:
    IF activity_meets_mission_criteria:
        mission_bonus += mission.bonus_points
        LOG mission_completion
```

#### Krok 6: Suma Końcowa
```
total_points = base_points + weight_bonus + elevation_bonus + mission_bonus
Przykłady Obliczeń