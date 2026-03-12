# 📖 Przykłady użycia Szczypior Bot

## Podstawowe użycie

### Sprawdzanie statusu bota
```
!ping
```
Bot odpowie z latencją połączenia.

### Wyświetlanie pomocy
```
!pomoc
```
Wyświetli pełną listę dostępnych komend.

---

## Zarządzanie aktywnościami

### Wyświetlanie dostępnych aktywności
```
!typy_aktywnosci
```
Pokaże wszystkie typy aktywności, które możesz zapisać wraz z punktacją.

### Dodawanie prostej aktywności
```
!dodaj_aktywnosc bieganie 5.2
```
Zapisuje przebieg 5.2 km. Otrzymasz: 5.2 × 10 = **52 punkty**

```
!dodaj_aktywnosc rower 20
```
Zapisuje przejazd rowerem 20 km. Otrzymasz: 20 × 5 = **100 punktów**

```
!dodaj_aktywnosc silownia 45
```
Zapisuje trening siłowy 45 minut. Otrzymasz: 45 × 8 = **360 punktów**

### Dodawanie aktywności z obciążeniem
```
!dodaj_aktywnosc bieganie 10 5
```
Bieganie 10 km z plecakiem 5 kg:
- Podstawa: 10 × 10 = 100 punktów
- Bonus za obciążenie: 5 × 2 = 10 punktów
- **Razem: 110 punktów**

### Dodawanie aktywności z przewyższeniem
```
!dodaj_aktywnosc bieganie 15 0 200
```
Bieganie górskie 15 km z przewyższeniem 200 m:
- Podstawa: 15 × 10 = 150 punktów
- Bonus za przewyższenie: 200 / 10 = 20 punktów
- **Razem: 170 punktów**

### Dodawanie aktywności z obciążeniem i przewyższeniem
```
!dodaj_aktywnosc bieganie 12 8 150
```
Bieganie 12 km, plecak 8 kg, przewyższenie 150 m:
- Podstawa: 12 × 10 = 120 punktów
- Bonus za obciążenie: 8 × 2 = 16 punktów
- Bonus za przewyższenie: 150 / 10 = 15 punktów
- **Razem: 151 punktów**

---

## Sprawdzanie historii i punktów

### Wyświetlanie swojej historii
```
!moja_historia
```
Pokazuje ostatnie 5 aktywności (domyślnie).

```
!moja_historia 10
```
Pokazuje ostatnie 10 aktywności.

### Sprawdzanie punktów
```
!moje_punkty
```
Wyświetla sumę wszystkich Twoich punktów i liczbę aktywności.

---

## Rankingi i statystyki

### Ranking użytkowników
```
!ranking
```
Pokazuje TOP 10 użytkowników według punktów (domyślnie).

```
!ranking 5
```
Pokazuje TOP 5 użytkowników.

### Statystyki serwera
```
!stats
```
Wyświetla:
- Liczbę aktywnych użytkowników
- Całkowitą liczbę aktywności
- Sumę wszystkich punktów
- Sumę dystansu
- Najpopularniejszą aktywność

### Statystyki aktywności
```
!stats_aktywnosci
```
Pokazuje szczegółowe statystyki dla każdego typu aktywności:
- Ile razy wykonana
- Suma dystansu/czasu
- Suma punktów

---

## Przykładowe scenariusze

### Scenariusz 1: Codzienny biegacz
```
# Poniedziałek - lekki bieg
!dodaj_aktywnosc bieganie 5

# Środa - interwały
!dodaj_aktywnosc bieganie 8

# Piątek - długi bieg z plecakiem
!dodaj_aktywnosc bieganie 15 3

# Niedziela - bieg górski
!dodaj_aktywnosc bieganie 12 0 300

# Sprawdzenie postępów
!moje_punkty
!moja_historia
```

### Scenariusz 2: Miłośnik rowerów
```
# Wycieczka rowerowa
!dodaj_aktywnosc rower 45

# Szybki przejazd do pracy
!dodaj_aktywnosc rower 12

# Górska wyprawa rowerowa
!dodaj_aktywnosc rower 60 0 800

# Zobacz swoją historię
!moja_historia
```

### Scenariusz 3: Wszechstronny sportowiec
```
# Poniedziałek - siłownia
!dodaj_aktywnosc silownia 60

# Wtorek - bieganie
!dodaj_aktywnosc bieganie 8

# Środa - pływanie
!dodaj_aktywnosc plywanie 2

# Czwartek - yoga
!dodaj_aktywnosc yoga 45

# Piątek - wspinaczka
!dodaj_aktywnosc wspinaczka 90

# Sobota - rower
!dodaj_aktywnosc rower 30

# Niedziela - spacer
!dodaj_aktywnosc spacer 10

# Podsumowanie tygodnia
!moje_punkty
!moja_historia 10
```

### Scenariusz 4: Sprawdzanie rankingu
```
# Zobacz jak wypadasz na tle innych
!ranking

# Sprawdź statystyki serwera
!stats

# Zobacz które aktywności są najpopularniejsze
!stats_aktywnosci
```

---

## Wskazówki

1. **Regularne zapisywanie**: Zapisuj aktywności zaraz po ich wykonaniu, żeby nic nie umknęło!

2. **Dokładność**: Możesz używać wartości dziesiętnych, np. `5.2`, `8.75`

3. **Bonusy**: Nie zapomnij o bonusach za obciążenie i przewyższenie - mogą znacząco zwiększyć Twoje punkty!

4. **Historia**: Regularnie sprawdzaj swoją historię, aby śledzić postępy

5. **Ranking**: Rywalizuj z innymi użytkownikami na serwerze!

---

## Często zadawane pytania

**Q: Jak uzyskać więcej punktów?**
A: Wybieraj aktywności z wyższą punktacją bazową (np. pływanie 15 pkt/km) i dodawaj bonusy (obciążenie, przewyższenie).

**Q: Czy mogę edytować zapisaną aktywność?**
A: Obecnie nie ma takiej funkcji. Uważnie sprawdzaj dane przed zapisaniem.

**Q: Dlaczego nie widzę swoich danych?**
A: Upewnij się, że Google Sheets jest poprawnie skonfigurowany. Sprawdź w konsoli bota czy są błędy.

**Q: Czy mogę dodać własny typ aktywności?**
A: Obecnie nie, ale możesz zgłosić prośbę o dodanie nowego typu aktywności.

**Q: Jak działa system punktacji?**
A: Każda aktywność ma bazową stawkę punktów, która jest mnożona przez wartość (km/min). Dodatkowo otrzymujesz bonusy za obciążenie (+2 pkt/kg) i przewyższenie (+1 pkt/10m).
