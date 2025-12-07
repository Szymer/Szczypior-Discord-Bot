# Propozycja refaktoryzacji Szczypior Discord Bot

## Cele
- Ujednolicenie analizy wiadomości (tekst/obraz) dla trybu live i synchronizacji startowej.
- Upraszczanie klientów LLM do minimalnego, wielokrotnego użytku interfejsu.
- Centralizacja promptów: wyłącznie w `config.json` przez `config_manager`.
- Redukcja duplikatów, zbędnych zmiennych i rozproszonych warunków.
- Zwiększenie czytelności i łatwości utrzymania bez zmiany funkcjonalności końcowej.

## Obszary problemowe (stan obecny)
- `BotOrchestrator` ma rozdzieloną logikę analizy dla obrazów i tekstu, z powtórzeniami (np. budowa promptów, walidacje, reakcje). Synchronizacja czatu przy starcie wykorzystuje inną ścieżkę niż live analiza.
- Klienci LLM (`llm_clients/*`) mają rozbudowaną logikę z providerami i miejscami, gdzie prompt może pochodzić spoza `config.json`.
- W `main.py` i `orchestrator.py` są miejsca niekompletne/zbędne (komentarze `/* omitted */`, brak domknięć gałęzi lub zwrotów), które powodują niejednoznaczności i powtórzenia.
- Prompt building jest rozproszone: `_build_activity_analysis_prompt`, `_build_motivational_comment_prompt`, `_analyze_text_with_ai`, `_analyze_image_with_gemini` – część robi to samo, ale w różnych miejscach.

## Proponowane zmiany

### 1) Jedna ścieżka analizy wiadomości
- Wprowadzić jedną, publiczną metodę w `BotOrchestrator`: `analyze_message(message: discord.Message) -> Optional[Dict]`.
  - Wykrywa eligibility (tekst, obraz) i deleguje do wspólnej metody `analyze_content(text: Optional[str], image_url: Optional[str], user_history: Optional[List[Dict]]) -> Dict`.
  - Ta sama metoda używana w trybie live (`on_message`) oraz w synchronizacji (`sync_chat_history`).
- `analyze_content(...)`:
  - Pobiera wyłącznie prompt(y) przez `config_manager.get_llm_prompts(provider)`.
  - Jeśli `image_url` → używa `llm_client.analyze_image(image_url, user_prompt, system_instruction)`.
  - Jeśli tylko `text` → używa `llm_client.generate_text(user_prompt, system_instruction)`.
  - Normalizuje wynik do wspólnego schematu: `{ typ_aktywnosci, dystans, obciazenie?, przewyzszenie?, czas?, tempo?, puls_sredni?, kalorie?, komentarz? }`.
  - Waliduje wynik w jednym miejscu (brak typu lub dystansu → None).

Rationale:
- Jedna implementacja eliminuje powtórzenia i rozjazdy między live oraz sync.
- Wspólna normalizacja upraszcza dalsze kroki: liczenie punktów, embed, zapis do Sheets.
- Łatwiej testować (jedna funkcja wejściowa, dwa źródła danych).

Wpływ na funkcje:
- `on_message` i `sync_chat_history` zmienią wywołania na `analyze_message` / `analyze_content`; funkcjonalność końcowa zachowana.
- Reakcje emoji i odpowiedzi pozostają, ale ich wywołanie nastąpi po zwróceniu `analysis`.

### 2) Minimalny interfejs klientów LLM
- Zredukować klientów do:
  - `generate_text(prompt: str, system_instruction: Optional[str] = None) -> str`
  - `analyze_image(image_url: str, prompt: str, system_instruction: Optional[str] = None) -> Dict[str, Any]`
- Klienci nie znają `config.json`; wyłącznie wykonują zadanie na podstawie argumentów.
- Provider wybierany w `config_manager`, a instancja klienta tworzona przez `get_llm_client()` jako fabryka.

Rationale:
- Klient staje się prosty i łatwy do zamiany; cała konfiguracja (prompty, provider, system prompt) pochodzi z jednego miejsca.
- Mniejszy coupling między logiką bota a SDK dostawców.

Wpływ:
- `orchestrator` odczytuje prompty wyłącznie z `config_manager`; klienci nie wymagają modyfikacji poza uproszczeniem sygnatur.
- Pozostałe funkcje korzystające z LLM (motywacyjne komentarze, podsumowania okresów) będą używać tych samych metod.

### 3) Centralizacja promptów w `config.json`
- `config_manager.get_llm_prompts(provider)` zwraca wszystkie szablony:
  - `activity_analysis`, `text_analysis`, `motivational_comment`, `period_summary` itd.
- Wprowadzić walidację konfiguracji przy starcie:
  - Brak kluczowego szablonu → ostrzeżenie w logach i fallback do prostego, bezpiecznego tekstu.
- Usunąć lokalne stałe promptów i rozproszone budowanie stringów poza `orchestrator`.

Rationale:
- Jedno źródło prawdy ułatwia modyfikacje promptów bez dotykania kodu.
- Zmniejsza ryzyko niezgodności między trybami.

Wpływ:
- `main.py` i `orchestrator.py` nie będą konstruować promptów „ręcznie”; tylko wypełniać parametry `format(...)`.

### 4) Uporządkowanie punktacji i embedów
- `calculate_points(...)` zwraca krotkę `(points, error_msg)` — domknięcie gałęzi i spójny zwrot (teraz są miejsca z `return` bez wartości).
- `create_activity_embed(...)` i `_create_response_embed(...)` mogą zostać ujednolicone:
  - Jedna funkcja w `utils.py`, przyjmująca `activity_info`, `username/mention`, `analysis`, `points`, `saved`, ewentualne dodatkowe pola.

Rationale:
- Redukcja dublowania UI; mniejsza szansa na rozjazdy.

Wpływ:
- Miejsca tworzące odpowiedzi przechodzą na wspólną funkcję; efekt wizualny nie ulega zmianie.

### 5) Redukcja zbędnych zmiennych i warunków
- W `main.py`:
  - Zamykanie niedokończonych gałęzi (np. `points, error_msg =` → brak wartości).
  - Łączenie warunków inicjalizacji i logowania (mniej duplikatów `try/except`).
- W `orchestrator.py`:
  - Usunięcie powtórzonych sprawdzeń długości tekstu.
  - `_activity_already_exists` używa pomocnika `_create_unique_id` konsekwentnie.
  - `_detect_activity_type_from_text` zwraca pierwszy dopasowany typ; brak zbędnych `None` zwrotów po drodze.

Rationale:
- Czytelność i mniejsze ryzyko błędów przy utrzymaniu.

Wpływ:
- Brak wpływu na zewnętrzne API; poprawa stabilności.

## Plan migracji (bezpieczny)
1. Dodaj `analyze_content(...)` i przestaw `on_message` oraz `sync_chat_history` na jej użycie.
2. Uprość klientów LLM do dwóch metod i zaktualizuj `get_llm_client()`.
3. Wprowadź walidację promptów w `config_manager` i usuń lokalne szablony.
4. Ujednolić tworzenie embedów w `utils.py` i zaktualizować wywołania.
5. Domknąć gałęzie zwrotów w `calculate_points(...)` i brakujące `try/except` bloki.
6. Przejrzeć testy w `tests/` i dostosować mocki do wspólnego interfejsu.

## Wpływ na istniejące funkcje
- Komendy tekstowe (`!dodaj_aktywnosc`, `!typy_aktywnosci`, `!ranking`, `!stats`, `!stats_aktywnosci`, `/podsumowanie`) pozostają bez zmian logiki biznesowej.
- Inicjalizacja bota, synchronizacja i zapis do Sheets zachowują dotychczasowe efekty (IID, sprawdzenie duplikatów, `setup_headers`, `build_iid_cache`).
- Testy mogą wymagać aktualizacji do wspólnego interfejsu LLM i jednego punktu analizy.

## Ryzyka i mitigacje
- Ryzyko: Zmiana interfejsu klientów LLM może złamać istniejące wywołania.
  - Mitigacja: przejściowe wrappery kompatybilności lub etapowa zmiana z deprecjacją.
- Ryzyko: Fallback promptów może dawać mniej precyzyjne odpowiedzi.
  - Mitigacja: logowanie ostrzeżeń i szybka korekta w `config.json` bez releasu kodu.

## Następne kroki
- Zatwierdzić plan.
- Zaimplementować etap 1–2 w osobnej gałęzi i uruchomić testy.
- Po walidacji, wdrożyć etapy 3–5 i zaktualizować testy.
