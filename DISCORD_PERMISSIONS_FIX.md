# 🔧 Jak Naprawić Uprawnienia Bota Discord

## Problem
```
❌ Bot nie ma wymaganych uprawnień w kanale 'cebulowe-bieganie-edycja-ciągła'!
   View Channel: False
   Read Message History: False
```

Bot potrzebuje uprawnień do odczytu kanału i historii wiadomości, aby móc synchronizować aktywności ze zdjęć.

---

## 🛠️ Rozwiązanie - 3 Metody

### **Metoda 1: Nadaj uprawnienia dla całego serwera (Najszybsze)**

1. Kliknij prawym przyciskiem na nazwę serwera Discord
2. Wybierz **"Ustawienia serwera"** (Server Settings)
3. Przejdź do **"Role"**
4. Znajdź rolę przypisaną do bota (np. "Szczypior Bot" lub podobna)
5. Włącz następujące uprawnienia:
   - ✅ **View Channels** (Wyświetlanie kanałów)
   - ✅ **Read Message History** (Odczyt historii wiadomości)
6. Kliknij **"Zapisz zmiany"**

---

### **Metoda 2: Nadaj uprawnienia dla konkretnego kanału**

1. Kliknij prawym przyciskiem na kanał **"cebulowe-bieganie-edycja-ciągła"**
2. Wybierz **"Edytuj kanał"** (Edit Channel)
3. Przejdź do zakładki **"Uprawnienia"** (Permissions)
4. Kliknij **"+"** i dodaj rolę bota lub wybierz ją z listy
5. Włącz następujące uprawnienia:
   - ✅ **View Channel** (Wyświetlanie kanału)
   - ✅ **Read Message History** (Odczyt historii wiadomości)
6. Kliknij **"Zapisz zmiany"**

---

### **Metoda 3: Ponowne zaproszenie bota z prawidłowymi uprawnieniami**

1. Wygeneruj nowy link zaproszenia z wymaganymi uprawnieniami:
   - Przejdź do [Discord Developer Portal](https://discord.com/developers/applications)
   - Wybierz swoją aplikację bota
   - Przejdź do **OAuth2 → URL Generator**
   
2. Zaznacz **SCOPES**:
   - ✅ `bot`
   - ✅ `applications.commands`

3. Zaznacz **BOT PERMISSIONS**:
   - ✅ `View Channels`
   - ✅ `Send Messages`
   - ✅ `Send Messages in Threads`
   - ✅ `Embed Links`
   - ✅ `Attach Files`
   - ✅ `Read Message History`
   - ✅ `Add Reactions`
   - ✅ `Use Slash Commands`

4. Skopiuj wygenerowany URL
5. Otwórz go w przeglądarce i zaproś bota ponownie na serwer

---

## 📋 Sprawdzenie Uprawnień

Po nadaniu uprawnień, uruchom bota ponownie:

```powershell
.\venv\Scripts\python.exe -m bot.main
```

Powinieneś zobaczyć:
```
✅ Google Sheets połączony i gotowy
✅ LLM Client połączony: gemini-1.5-flash

🔄 Rozpoczynam synchronizację historii czatu...
🔄 Rozpoczynam synchronizację historii czatu dla kanału: cebulowe-bieganie-edycja-ciągła
```

---

## ⚠️ Ważne Uwagi

1. **Privileged Gateway Intents**: Jeśli bot ma być użyty na większych serwerach (>100 członków), może potrzebujesz włączyć "Privileged Gateway Intents" w Developer Portal:
   - Przejdź do [Discord Developer Portal](https://discord.com/developers/applications)
   - Wybierz aplikację → **Bot**
   - Włącz **"Message Content Intent"** (jeśli jeszcze nie jest włączony)

2. **Weryfikacja dwuetapowa**: Niektóre serwery wymagają 2FA dla administratorów. Upewnij się, że masz włączoną weryfikację dwuetapową na swoim koncie Discord.

3. **Hierarchia ról**: Upewnij się, że rola bota znajduje się wyżej w hierarchii niż role użytkowników, których aktywności chcesz monitorować.

---

## 🆘 Nadal nie działa?

Jeśli po nadaniu uprawnień nadal występują problemy:

1. **Zrestartuj bota** całkowicie (zatrzymaj proces i uruchom ponownie)
2. **Sprawdź ID kanału** w pliku `.env`:
   ```
   MONITORED_CHANNEL_ID=1374393341789339708
   ```
3. **Sprawdź czy bot jest online** - powinien mieć zieloną kropkę na Discordzie
4. **Sprawdź logi bota** - szukaj szczegółowych komunikatów błędów

---

## ✅ Po Naprawieniu

Gdy uprawnienia zostaną poprawnie ustawione, bot będzie mógł:
- 📸 Automatycznie rozpoznawać aktywności ze zdjęć
- 📊 Synchronizować historię kanału z Google Sheets
- ✅ Dodawać reakcje do wiadomości (🤔, ✅, ❓)
- 💬 Wysyłać potwierdzenia i komentarze motywacyjne
