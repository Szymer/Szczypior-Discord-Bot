Zadania bota.
1. Szczypior ma odczytywać wiadomości innych użytkowników na konkretnym kanale
2. Bot analizuje wiadomość: jeżeli wiadomość zawiera grafikę/zdjęcie (wykluczamy gif) to przekazujemy to zdjęcie do LLM Gemini; jeżeli wiadomość zawiera informacje na temat obciążenia w kilogramach zapisuje je w cache'u klucz user-timestamp wiadomości.
3. Bot sprawdza czy dany user jest już zapisany w https://docs.google.com/spreadsheets/d/1dTQzfN9QnknQhGlcumyZ9nkvV4AMzJm6kNYouOmXcJo/edit?usp=sharing, jeżeli tak przekazuje dotychczasowe wyniki do prompta gemini
4. Gemini analizuje zdjęcie i jeżeli zawiera ono informacje na temat dyscypliny sportowej i/lub aktywności fizycznej zwraca je do bota, dodatkowo dodaje komentarz na temat postępów bazujący na dotychczasowych wynikach
5. Bot umieszcza informacje User, aktywność, dystans, ewentualne obciążenie w szablonie Google Docs https://docs.google.com/spreadsheets/d/1dTQzfN9QnknQhGlcumyZ9nkvV4AMzJm6kNYouOmXcJo/edit?usp=sharing
6. Bot odpowiada na wiadomość usera, podaje wynik punktowy aktywności wyliczony zgodnie z wytycznymi konkursu oraz przekazuje w wiadomości błyskotliwy komentarz Gemini

---

## 📊 ZASADY PUNKTACJI:

🏃 **Bieganie (Teren)**: 1000 pkt/km
- Min. dystans: BRAK
- Możliwe bonusy: obciążenie; przewyższenia

🏃‍♂️ **Bieganie (Bieżnia)**: 800 pkt/km
- Min. dystans: BRAK
- Możliwe bonusy: obciążenie

🏊 **Pływanie**: 4000 pkt/km
- Min. dystans: BRAK

🚴 **Rower/Rolki**: 300 pkt/km
- Min. dystans: 6km
- Możliwe bonusy: przewyższenia

🚶 **Spacer/Trekking**: 200 pkt/km
- Min. dystans: 3km
- Możliwe bonusy: obciążenie; przewyższenia

🔫 **Inne Cardio** - wioślarz, orbitrek (w tym ASG): 800 pkt/km
- Min. dystans: BRAK
- Możliwe bonusy: obciążenie; przewyższenia

💥 **MISJE SPECJALNE**: Raz w miesiącu wjeżdża zadanie dodatkowe za normalne + bonusowe punkty.

**Misja na GRUDZIEŃ**: "Rozruch Zimowy" ❄️
- Cel: Wykonaj dowolną aktywność ciągłą na dystansie min. 5 km
- Nagroda: +2000 pkt jednorazowego bonusu do rankingu
- Czas: Do końca roku

---

## ✅ STATUS IMPLEMENTACJI

### Zaimplementowane funkcjonalności (bez Gemini):
- ✅ Podstawowy system komend bota
- ✅ Komendy zarządzania aktywnościami (!dodaj_aktywnosc, !moja_historia, !moje_punkty)
- ✅ Prosty system punktacji (tymczasowy, uproszczony)
- ✅ Integracja z Google Sheets (odczyt/zapis)
- ✅ Komendy rankingowe (!ranking, !stats, !stats_aktywnosci)
- ✅ Komendy pomocnicze (!pomoc, !typy_aktywnosci)
- ✅ 8 typów aktywności (bieganie, rower, spacer, pływanie, siłownia, wspinaczka, narty, yoga)

### Do zaimplementowania:
- ⏳ Nasłuchiwanie wiadomości na konkretnym kanale
- ⏳ Analiza zdjęć przez Gemini
- ⏳ System cache'owania danych o obciążeniu
- ⏳ Zaawansowany system punktacji zgodny z wytycznymi konkursu
- ⏳ Integracja komentarzy Gemini w odpowiedziach
- ⏳ System misji specjalnych
- ⏳ Obsługa minimalnych dystansów
- ⏳ Bonusy za obciążenie i przewyższenie zgodne z regulaminem

### Notatki techniczne:
- Bot używa uproszczonej punktacji dla celów testowych
- Pełna integracja z Gemini zostanie dodana w kolejnym etapie
- Obecna wersja pozwala na testowanie funkcjonalności zapisu/odczytu danych 