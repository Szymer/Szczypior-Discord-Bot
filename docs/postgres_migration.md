# Migracja do PostgreSQL (Supabase)

## 1. Połączenie z bazą danych

Użyj connection stringa z Supabase Session Pooler (IPv4):
```
DATABASE_URL=postgresql://postgres.[project-ref]:[db-password]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```

Skąd go wziąć:
1. Zaloguj się do Supabase Dashboard.
2. Przejdź do Settings → Database.
3. W sekcji Connection string wybierz Session pooler.
4. Skopiuj wariant z hostem `aws-0-...pooler.supabase.com` i portem `6543`.

Dodaj do `.env`:
```bash
# PostgreSQL Database
DATABASE_URL=postgresql://postgres.[project-ref]:[db-password]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```

## 2. Wykonanie migracji

Jeśli baza została założona na starszym schemacie i `db-service` rzuca błędy typu `column "rules" of relation "challenges" does not exist`, najpierw uruchom migrację wyrównującą:

```bash
psql "$DATABASE_URL" -f infrastructure/postgres/migrations/001_sync_challenges_schema.sql
```

### Opcja A: Przez Supabase Dashboard
1. Zaloguj się do [Supabase Dashboard](https://app.supabase.com)
2. Wybierz swój projekt
3. Przejdź do **SQL Editor**
4. Wklej całą zawartość pliku `infrastructure/postgres/init.sql`
5. Kliknij **Run**

### Opcja B: Przez psql (terminal)
```bash
psql postgresql://postgres.[project-ref]:[db-password]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres < infrastructure/postgres/init.sql
```

### Opcja C: Przez Python script
```python
import psycopg2
import os

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cursor = conn.cursor()

with open("infrastructure/postgres/init.sql", "r") as f:
    cursor.execute(f.read())

conn.commit()
cursor.close()
conn.close()
print("✅ Migration complete!")
```

## 3. Weryfikacja schematu

### Sprawdź tabele
```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;
```

Powinno zwrócić:
- `activities`
- `special_missions`
- `users`

### Sprawdź views
```sql
SELECT table_name 
FROM information_schema.views 
WHERE table_schema = 'public';
```

Powinno zwrócić:
- `activity_type_stats`
- `mission_completions`
- `user_rankings`

### Sprawdź seed data
```sql
SELECT * FROM special_missions;
```

Powinna być misja "Rozruch Zimowy ❄️" na grudzień 2025.

## 4. Struktura tabel

### `users`
- Przechowuje użytkowników Discord
- Klucz: `discord_id` (unique)
- Bot będzie tworzył użytkownika przy pierwszej aktywności

### `activities`
- Przechowuje aktywności sportowe
- Link do `users` przez `user_id` (FK)
- Link do misji specjalnych przez `special_mission_id` (FK, nullable)
- Pełny breakdown punktów: base + weight_bonus + elevation_bonus + mission_bonus = total

### `special_missions`
- Definicje misji miesięcznych
- Warunki: min_distance_km, min_time_minutes, activity_type_filter
- Zakres dat: valid_from → valid_until
- Bot automatycznie przypisuje misję jeśli aktywność spełnia warunki

## 5. Przykładowe queries

### Dodaj użytkownika (lub zaktualizuj jeśli istnieje)
```sql
INSERT INTO users (discord_id, display_name, username) 
VALUES ('123456789012345678', 'JanKowalski', 'jan.kowalski')
ON CONFLICT (discord_id) 
DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    username = EXCLUDED.username,
    updated_at = CURRENT_TIMESTAMP
RETURNING *;
```

### Dodaj aktywność z auto-detekcją misji
```sql
WITH user_lookup AS (
    SELECT id FROM users WHERE discord_id = '123456789012345678'
),
mission AS (
    SELECT id, bonus_points
    FROM special_missions
    WHERE is_active = TRUE
      AND CURRENT_TIMESTAMP BETWEEN valid_from AND valid_until
      AND (activity_type_filter IS NULL OR activity_type_filter = 'bieganie_teren')
      AND 10.0 >= COALESCE(min_distance_km, 0)
    LIMIT 1
)
INSERT INTO activities (
    user_id, iid, activity_type, distance_km, weight_kg, elevation_m,
    base_points, weight_bonus_points, elevation_bonus_points,
    special_mission_id, mission_bonus_points, total_points,
    created_at, message_id, message_timestamp
)
SELECT 
    (SELECT id FROM user_lookup),
    '1234567890_9876543210',
    'bieganie_teren',
    10.0,
    15.0,
    200,
    10000,  -- base: 10km * 1000
    3000,   -- weight bonus: (15/5) * (10*1000*0.1) = 3000
    1000,   -- elevation bonus: (200/100) * (10*1000*0.05) = 1000
    mission.id,
    COALESCE(mission.bonus_points, 0),
    10000 + 3000 + 1000 + COALESCE(mission.bonus_points, 0)  -- total
FROM mission
RETURNING *;
```

### Pobierz ranking
```sql
SELECT 
    display_name,
    total_activities,
    total_distance_km,
    total_points,
    mission_bonus_points
FROM user_rankings
ORDER BY total_points DESC
LIMIT 10;
```

### Pobierz historię użytkownika
```sql
SELECT 
    a.created_at,
    a.activity_type,
    a.distance_km,
    a.total_points,
    a.base_points,
    a.weight_bonus_points,
    a.elevation_bonus_points,
    a.mission_bonus_points,
    sm.name AS mission_name
FROM activities a
JOIN users u ON a.user_id = u.id
LEFT JOIN special_missions sm ON a.special_mission_id = sm.id
WHERE u.discord_id = '123456789012345678'
ORDER BY a.created_at DESC
LIMIT 20;
```

## 6. Migracja danych z Google Sheets (opcjonalnie)

Jeśli chcesz przenieść dane z Google Sheets do PostgreSQL:

```python
import asyncio
from bot.sheets_manager import SheetsManager
import psycopg2
import os

async def migrate_from_sheets():
    # Połącz z Google Sheets
    sheets = SheetsManager()
    
    # Połącz z PostgreSQL
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor = conn.cursor()
    
    # Pobierz wszystkie aktywności
    activities = await sheets.get_all_activities_with_timestamps()
    
    print(f"Migrating {len(activities)} activities...")
    
    for activity in activities:
        nick = activity.get("Nick", "")
        
        # Utwórz użytkownika jeśli nie istnieje
        cursor.execute("""
            INSERT INTO users (discord_id, display_name)
            VALUES (%s, %s)
            ON CONFLICT (discord_id) DO UPDATE SET display_name = EXCLUDED.display_name
            RETURNING id
        """, (f"sheet_{nick}", nick))
        
        user_id = cursor.fetchone()[0]
        
        # Dodaj aktywność
        iid = activity.get("IID", f"migrated_{activity.get('Data', '')}")
        cursor.execute("""
            INSERT INTO activities (
                user_id, iid, activity_type, distance_km, 
                base_points, total_points, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (iid) DO NOTHING
        """, (
            user_id,
            iid,
            activity.get("Rodzaj Aktywności", ""),
            activity.get("Dystans (km)", 0),
            activity.get("PUNKTY", 0),
            activity.get("PUNKTY", 0),
            activity.get("Data", "2025-01-01 00:00:00")
        ))
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate_from_sheets())
```

## 7. Następne kroki

1. ✅ Wykonaj migrację schematu do Supabase
2. ⏳ Zaktualizuj `bot/sheets_manager.py` → `bot/db_manager.py` (użyj psycopg2 lub asyncpg)
3. ⏳ Dodaj obsługę misji specjalnych w `bot/orchestrator.py`
4. ⏳ Zaktualizuj komendy (!ranking, !moja_historia) do korzystania z PostgreSQL
5. ⏳ Dodaj komendę !misje do wyświetlania aktywnych misji

## 8. Dependencies

Dodaj do `services/discord-bot/requirements.txt`:
```
psycopg2-binary>=2.9.0
# lub dla async:
asyncpg>=0.29.0
```
