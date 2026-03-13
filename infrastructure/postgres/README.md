# PostgreSQL Schema Documentation

## Overview

Szczypior Discord Bot używa PostgreSQL (Supabase) do przechowywania danych o użytkownikach, aktywnościach sportowych i misjach specjalnych.

## Architecture

### ER Diagram
```
┌─────────────────┐       ┌──────────────────────┐       ┌──────────────────────┐
│     users       │       │     activities       │       │  special_missions    │
├─────────────────┤       ├──────────────────────┤       ├──────────────────────┤
│ id (PK)         │◄─────┤│ user_id (FK)         │       │ id (PK)              │
│ discord_id      │       │ id (PK)              │       │ name                 │
│ display_name    │       │ iid (UNIQUE)         │┌─────►│ description          │
│ username        │       │ activity_type        ││      │ emoji                │
│ avatar_url      │       │ distance_km          ││      │ bonus_points         │
│ created_at      │       │ weight_kg            ││      │ min_distance_km      │
│ updated_at      │       │ elevation_m          ││      │ min_time_minutes     │
└─────────────────┘       │ time_minutes         ││      │ activity_type_filter │
                          │ base_points          ││      │ valid_from           │
                          │ weight_bonus_points  ││      │ valid_until          │
                          │ elevation_bonus_points│      │ is_active            │
                          │ special_mission_id (FK)─┘     │ max_completions      │
                          │ mission_bonus_points │       │ created_at           │
                          │ total_points         │       │ updated_at           │
                          │ created_at           │       └──────────────────────┘
                          │ message_id           │
                          │ message_timestamp    │
                          │ ai_comment           │
                          └──────────────────────┘
```

## Tables

### `users`
Przechowuje informacje o użytkownikach Discord.

| Column         | Type        | Description                    |
|----------------|-------------|--------------------------------|
| id             | UUID        | Primary key                    |
| discord_id     | VARCHAR(20) | Discord user ID (UNIQUE)       |
| display_name   | TEXT        | Display name/nick              |
| username       | TEXT        | Discord username               |
| avatar_url     | TEXT        | Avatar URL                     |
| created_at     | TIMESTAMP   | Account creation               |
| updated_at     | TIMESTAMP   | Last update                    |

**Indexes:**
- `idx_users_discord_id` on `discord_id` (dla szybkiego lookup)

### `activities`
Przechowuje sportowe aktywności użytkowników.

| Column                  | Type                | Description                      |
|-------------------------|---------------------|----------------------------------|
| id                      | UUID                | Primary key                      |
| user_id                 | UUID                | FK → users.id                    |
| iid                     | VARCHAR(255)        | Internal unique ID (UNIQUE)      |
| activity_type           | VARCHAR(50)         | Typ aktywności (CHECK constraint)|
| distance_km             | DECIMAL(10,2)       | Dystans w km                     |
| weight_kg               | DECIMAL(5,2)        | Ciężar/obciążenie (opcjonalnie)  |
| elevation_m             | INTEGER             | Przewyższenie (opcjonalnie)      |
| time_minutes            | INTEGER             | Czas trwania (opcjonalnie)       |
| pace                    | VARCHAR(10)         | Tempo (np. "5:30")              |
| heart_rate_avg          | INTEGER             | Średnie tętno (opcjonalnie)      |
| calories                | INTEGER             | Kalorie (opcjonalnie)            |
| base_points             | INTEGER             | Punkty bazowe                    |
| weight_bonus_points     | INTEGER             | Bonus za ciężar                  |
| elevation_bonus_points  | INTEGER             | Bonus za przewyższenie           |
| special_mission_id      | UUID                | FK → special_missions.id (NULL)  |
| mission_bonus_points    | INTEGER             | Bonus za misję specjalną         |
| total_points            | INTEGER             | Suma wszystkich punktów          |
| created_at              | TIMESTAMP           | Data aktywności                  |
| message_id              | VARCHAR(20)         | Discord message ID               |
| message_timestamp       | VARCHAR(30)         | Message timestamp                |
| ai_comment              | TEXT                | Komentarz wygenerowany przez AI  |

**Indexes:**
- `idx_activities_user_id` on `user_id`
- `idx_activities_created_at` on `created_at`
- `idx_activities_special_mission_id` on `special_mission_id`

**CHECK Constraints:**
- `activity_type` must be one of: `bieganie_teren`, `bieganie_asfalt`, `marsz`, `rower`, `nordic_walking`, `kajak`

### `special_missions`
Definicje misji specjalnych (np. wyzwania miesięczne).

| Column                  | Type         | Description                           |
|-------------------------|--------------|---------------------------------------|
| id                      | UUID         | Primary key                           |
| name                    | TEXT         | Nazwa misji                           |
| description             | TEXT         | Opis misji                            |
| emoji                   | VARCHAR(10)  | Emoji misji                           |
| bonus_points            | INTEGER      | Punkty bonusowe za ukończenie         |
| min_distance_km         | DECIMAL(10,2)| Minimalny dystans (NULL = bez limitu) |
| min_time_minutes        | INTEGER      | Minimalny czas (NULL = bez limitu)    |
| activity_type_filter    | VARCHAR(50)  | Typ aktywności (NULL = wszystkie)     |
| valid_from              | TIMESTAMP    | Start okresu ważności                 |
| valid_until             | TIMESTAMP    | Koniec okresu ważności                |
| is_active               | BOOLEAN      | Czy misja jest aktywna                |
| max_completions_per_user| INTEGER      | Max. wykonań na użytkownika (NULL)    |
| created_at              | TIMESTAMP    | Data utworzenia                       |
| updated_at              | TIMESTAMP    | Data aktualizacji                     |

**Indexes:**
- `idx_special_missions_dates` on `valid_from, valid_until` (dla aktywnych misji)

## Views

### `user_rankings`
Ranking użytkowników z sumarycznymi statystykami.

```sql
SELECT 
    display_name,
    total_activities,
    total_distance_km,
    total_points,
    base_points,
    bonus_points,
    mission_bonus_points,
    last_activity_at
FROM user_rankings
ORDER BY total_points DESC;
```

### `activity_type_stats`
Statystyki według typu aktywności.

```sql
SELECT 
    activity_type,
    total_activities,
    total_distance_km,
    total_points,
    avg_distance_km
FROM activity_type_stats
ORDER BY total_points DESC;
```

### `mission_completions`
Liczba ukończeń każdej misji przez użytkowników.

```sql
SELECT 
    mission_name,
    user_name,
    completions,
    total_bonus_points
FROM mission_completions
ORDER BY mission_name, completions DESC;
```

## Point Calculation System

Każda aktywność otrzymuje punkty według następujących zasad:

### 1. Punkty Bazowe
```
base_points = distance_km * activity_multiplier
```

**Mnożniki aktywności:**
- `bieganie_teren`: 1000 (10km = 10,000 pts)
- `bieganie_asfalt`: 1000 (10km = 10,000 pts)
- `marsz`: 600 (10km = 6,000 pts)
- `rower`: 300 (10km = 3,000 pts)
- `nordic_walking`: 800 (10km = 8,000 pts)
- `kajak`: 500 (10km = 5,000 pts)

### 2. Bonus za Ciężar
```
weight_bonus_points = (weight_kg / 5) * base_points * 0.1
```

Przykład: 15kg na 10km biegania = 3,000 pts bonus

### 3. Bonus za Przewyższenie
```
elevation_bonus_points = (elevation_m / 100) * base_points * 0.05
```

Przykład: 200m przewyższenia na 10km = 1,000 pts bonus

### 4. Bonus za Misję Specjalną
Jeśli aktywność spełnia warunki misji specjalnej:
```
mission_bonus_points = special_missions.bonus_points
```

### 5. Suma Końcowa
```
total_points = base_points + weight_bonus_points + elevation_bonus_points + mission_bonus_points
```

## Triggers

### `update_updated_at_column`
Automatycznie aktualizuje pole `updated_at` przy modyfikacji rekordów:
- Stosowane do: `users`, `special_missions`

## Seed Data

### Default Special Mission
```sql
INSERT INTO special_missions (name, description, emoji, bonus_points, ...)
VALUES ('Rozruch Zimowy', '...', '❄️', 2000, ...);
```

**Rozruch Zimowy ❄️**
- Bonus: +2000 punktów
- Wymogi: min. 5km
- Okres: 1-31 grudnia 2025
- Wszystkie typy aktywności

## Usage Examples

### Add User and Activity
```python
# Get or create user
user_id = await db.get_or_create_user(
    discord_id="123456789012345678",
    display_name="JanKowalski"
)

# Add activity (automatic mission detection)
success, activity_id, total_points = await db.add_activity(
    discord_id="123456789012345678",
    display_name="JanKowalski",
    iid="unique_activity_id",
    activity_type="bieganie_teren",
    distance_km=10.0,
    base_points=10000,
    weight_kg=15.0,
    weight_bonus_points=3000,
    elevation_m=200,
    elevation_bonus_points=1000
    # Mission will be auto-detected and applied
)

print(f"Total points: {total_points}")
# Output: Total points: 16000 (10000 + 3000 + 1000 + 2000 mission bonus)
```

### Get Rankings
```python
rankings = await db.get_rankings(limit=10)

for i, user in enumerate(rankings, 1):
    print(f"{i}. {user['display_name']}: {user['total_points']} pts")
```

### Check Active Missions
```python
missions = await db.get_active_missions()

for mission in missions:
    print(f"{mission['emoji']} {mission['name']}")
    print(f"  Bonus: +{mission['bonus_points']} pts")
    print(f"  Min distance: {mission['min_distance_km']}km")
```

## Deployment

See [postgres_migration.md](../../docs/postgres_migration.md) for deployment instructions.

## Files

- `init.sql` - Full schema definition with seed data
- `../../services/discord-bot-szczypior/bot/db_manager.py` - Python database client
- `../../tools/deploy_schema.py` - Deployment script
