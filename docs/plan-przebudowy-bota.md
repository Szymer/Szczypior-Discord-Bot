# Plan przebudowy bota (Bot = transport, AI = logika, API Manager = baza)

## 1. Cel przebudowy

Docelowo bot ma byc cienka warstwa transportowa Discord:

- odbiera wiadomosci,
- filtruje tylko podstawowe warunki wejscia,
- przekazuje wiadomosc do modulu AI,
- odsyla odpowiedz do uzytkownika na podstawie danych zwrotnych z AI.

Logika domenowa, analiza aktywnosci, walidacje i operacje CRUD zostaja po stronie AI.
Komunikacja z baza zostaje po stronie API Managera (wywolywanego przez AI).

## 2. Stan obecny (na podstawie analizy)

Aktualnie warstwa bota zawiera zbyt duzo odpowiedzialnosci:

- obsluge wiadomosci,
- duza logike orchestratora (analiza, walidacje, punktacja, zapisy),
- startup sync backlogu,
- liczne komendy tekstowe i slash,
- elementy raportowania i podsumowan.

To utrudnia rozwoj i testowanie, bo warstwa transportowa jest mocno sprzezona z logika biznesowa.

## 3. Architektura docelowa

### 3.1 Podzial odpowiedzialnosci

Bot:

- odbiera eventy Discord,
- wykonuje minimalny filtr (bot/komenda/kanał/typ wiadomosci),
- przekazuje request do AI,
- mapuje wynik AI na odpowiedz Discord (embed/tekst/reakcje).

AI:

- rozpoznanie aktywnosci,
- deduplikacja,
- walidacje,
- punktacja,
- CRUD przez API Manager,
- przygotowanie danych odpowiedzi (status, payload, komunikat).

API Manager:

- tylko klient HTTP do db-service,
- brak logiki Discord i brak logiki promptow.

### 3.2 Kontrakt Bot <-> AI (proponowany)

Warstwa bota przekazuje do AI obiekt wejsciowy (np. ActivityRequest):

- message_id,
- author_id,
- author_display,
- channel_id,
- content,
- attachments,
- created_at.

AI zwraca obiekt wynikowy (np. ActivityResponse):

- status: ignored | duplicate | saved | rejected | error,
- reply_text lub reply_embed_data,
- reaction: np. "✅", "❓", "⚠️" lub null,
- debug/meta opcjonalnie (iid, points, reason).

## 4. Zakres refaktoryzacji

### 4.1 Co zostaje w bocie

- eventy: on_ready, on_message,
- inicjalizacja klienta Discord,
- inicjalizacja AI facade (bez logiki AI w pliku bota),
- jedna komenda: !ping,
- placeholder pod przyszle komendy (pusty rejestr/modul).

### 4.2 Co usuwamy z warstwy bota

- komendy: hello, moja_historia, moje_punkty, ranking, activity_fix, pomoc,
- slash command podsumowanie i autocomplete,
- generowanie podsumowan AI bezposrednio w main,
- logike biznesowa z orchestratora, ktora nie jest transportem Discord.

### 4.3 Co pozostaje bez zmian na teraz

- folder AI: services/discord-bot-szczypior/ai (bez zmian implementacyjnych teraz),
- API Manager jako klient komunikacji z baza.

## 5. Plan wdrozenia (iteracyjny)

### Etap 1: Wydzielenie cienkiej warstwy wejscia

1. Uproscic on_message:

- tylko filtry techniczne,
- przekazanie do jednego punktu wejscia AI (np. ai_handler.process_message).

2. Dodac adapter odpowiedzi AI -> Discord:

- jedna funkcja mapujaca statusy AI na odpowiedz i reakcje.

3. Zachowac !ping bez zmian.

### Etap 2: Ograniczenie powierzchni komend

1. Usunac wszystkie komendy poza !ping.
2. Zostawic placeholder (np. pusty modul commands_placeholder.py lub sekcja TODO).

### Etap 3: Wygaszenie logiki domenowej po stronie bota

1. Oznaczyc metody orchestratora do migracji lub usuniecia.
2. Zostawic tylko cienki interfejs wywolujacy AI.
3. Usunac dead code i zaleznosci nieuzywane przez bot transportowy.

### Etap 4: Testy i walidacja

1. Testy jednostkowe bota:

- filtracja wiadomosci,
- wywolanie AI dla poprawnych wiadomosci,
- mapowanie statusow AI na odpowiedz Discord.

2. Testy integracyjne:

- scenariusz duplicate,
- scenariusz saved,
- scenariusz rejected/error.

## 6. Zmiany plikow (planowane)

- services/discord-bot-szczypior/bot/main.py
  - mocne uproszczenie eventow i komend,
  - zostaje !ping,
  - integracja z jednym punktem wejscia AI.

- services/discord-bot-szczypior/bot/orchestrator.py
  - redukcja odpowiedzialnosci (docelowo adapter/bridge),
  - stopniowe usuwanie logiki domenowej z warstwy bota.

- services/discord-bot-szczypior/bot/(nowy plik opcjonalny) ai_bridge.py
  - cienki kontrakt wywolania AI i mapowania odpowiedzi.

## 7. Kryteria akceptacji

Przebudowa jest zakonczona, gdy:

- bot obsluguje tylko eventy wiadomosci i !ping,
- bot nie zawiera logiki biznesowej aktywnosci,
- AI odpowiada za logike i CRUD,
- API Manager jest wykorzystywany przez AI,
- usuniete sa stare komendy i slash,
- testy przeplywu wiadomosci przechodza.

## 8. Ryzyka i zabezpieczenia

Ryzyka:

- chwilowe regresje w embedach odpowiedzi,
- roznice w obsludze duplicate/silent-mode,
- zaleznosci ukryte w starym orchestratorze.

Zabezpieczenia:

- migracja etapami,
- feature flag dla nowej sciezki (opcjonalnie),
- testy statusow AI i snapshot odpowiedzi Discord.

## 9. Minimalny backlog wykonawczy

1. Ustalic finalny kontrakt response z AI.
2. Uproscic main.py do modelu event-driven + !ping.
3. Usunac stare komendy i slash.
4. Dodac adapter odpowiedzi AI -> Discord.
5. Dodac testy transportowej warstwy bota.
6. Posprzatac importy i dead code.
