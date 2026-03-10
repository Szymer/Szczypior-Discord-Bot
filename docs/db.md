Poniżej masz **propozycję schematu bazy danych dla PostgreSQL**, zaprojektowaną tak, aby:

* integrować się z **Discord OAuth (Django login przez Discord)**
* przechowywać **aktywności fizyczne**
* liczyć **punkty i ranking**
* obsługiwać **misje specjalne**
* obsługiwać **wydarzenia / kalendarz imprez**
* umożliwiać **statystyki i dashboard użytkownika**

Schemat jest przygotowany tak, aby dobrze działał z:

* **Django ORM**
* **PostgreSQL**
* **SQLAlchemy (opcjonalnie)**

---

# Główna koncepcja modelu danych

System składa się z kilku głównych obszarów:

```
users
│
├── activities
│
├── activity_types
│
├── missions
│
├── mission_completions
│
├── events
│
└── event_participants
```

---

# 1️⃣ tabela użytkowników

Źródłem danych jest **Discord API**.

Tabela przechowuje dane konta oraz dane profilowe.

```sql
users
```

| kolumna            | typ           | opis                      |
| ------------------ | ------------- | ------------------------- |
| id                 | uuid / serial | wewnętrzny identyfikator  |
| discord_user_id    | bigint        | ID użytkownika z Discord  |
| username           | varchar       | username                  |
| global_name        | varchar       | global name               |
| display_name       | varchar       | display name              |
| nick               | varchar       | nick na serwerze          |
| avatar_url         | text          | avatar                    |
| is_bot             | boolean       | czy bot                   |
| joined_at          | timestamp     | kiedy dołączył do serwera |
| discord_created_at | timestamp     | kiedy utworzył konto      |
| created_at         | timestamp     | kiedy dodany do systemu   |

Indeksy:

```
unique(discord_user_id)
```

---

# 2️⃣ role z Discord

Użytkownik może mieć wiele ról.

```sql
discord_roles
```

| kolumna | typ     |
| ------- | ------- |
| id      | bigint  |
| name    | varchar |
| color   | varchar |

---

### tabela łącząca

```sql
user_roles
```

| kolumna |
| ------- |
| user_id |
| role_id |

---

# 3️⃣ typy aktywności

Tabela konfiguracyjna.

```sql
activity_types
```

| kolumna         | typ     |
| --------------- | ------- |
| id              | serial  |
| name            | varchar |
| points_per_km   | int     |
| min_distance_km | numeric |
| allow_elevation | boolean |
| allow_weight    | boolean |

Przykładowe dane:

| name              | points_per_km |
| ----------------- | ------------- |
| running_outdoor   | 1000          |
| running_treadmill | 800           |
| swimming          | 4000          |
| cycling           | 300           |
| walking           | 200           |
| cardio            | 800           |

---

# 4️⃣ aktywności użytkowników

Najważniejsza tabela.

```sql
activities
```

| kolumna          | typ       |
| ---------------- | --------- |
| id               | uuid      |
| user_id          | FK        |
| activity_type_id | FK        |
| distance_km      | numeric   |
| duration_minutes | int       |
| elevation_gain   | int       |
| extra_weight_kg  | numeric   |
| points           | int       |
| activity_date    | date      |
| created_at       | timestamp |
| notes            | text      |

---

### przykład

```
user: Adaś
activity: running_outdoor
distance: 5km
points: 5000
```

---

# 5️⃣ tabela misji specjalnych

Misje mogą się zmieniać.

```sql
missions
```

| kolumna          | typ           |
| ---------------- | ------------- |
| id               | uuid          |
| name             | varchar       |
| description      | text          |
| start_date       | date          |
| end_date         | date          |
| bonus_points     | int           |
| min_distance_km  | numeric       |
| activity_type_id | FK (nullable) |

---

### przykład

```
Rozruch Zimowy
min_distance = 5km
bonus = 2000
```

---

# 6️⃣ wykonanie misji

```sql
mission_completions
```

| kolumna      |
| ------------ |
| id           |
| mission_id   |
| user_id      |
| activity_id  |
| bonus_points |
| completed_at |

---

# 7️⃣ ranking

Ranking można liczyć dynamicznie lub cacheować.

Opcjonalna tabela:

```sql
user_stats
```

| kolumna          |
| ---------------- |
| user_id          |
| total_points     |
| total_distance   |
| total_activities |
| rank_position    |
| updated_at       |

---

# 8️⃣ wydarzenia / kalendarz

```sql
events
```

| kolumna          | typ       |
| ---------------- | --------- |
| id               | uuid      |
| name             | varchar   |
| description      | text      |
| event_date       | date      |
| location         | varchar   |
| max_participants | int       |
| created_by       | FK user   |
| created_at       | timestamp |

---

# 9️⃣ zapis na wydarzenie

```sql
event_participants
```

| kolumna                                     |
| ------------------------------------------- |
| event_id                                    |
| user_id                                     |
| status (registered / confirmed / cancelled) |
| registered_at                               |

---

# 🔟 historia punktów

Opcjonalna tabela do audytu.

```sql
points_log
```

| kolumna     |
| ----------- |
| id          |
| user_id     |
| activity_id |
| points      |
| reason      |
| created_at  |

---

# Relacje między tabelami

```
users
 │
 ├── activities
 │
 ├── mission_completions
 │
 ├── user_roles
 │
 └── event_participants


activity_types
     │
     └── activities


missions
    │
    └── mission_completions


events
    │
    └── event_participants
```

---

# Co będzie można pokazać w panelu użytkownika

Dashboard:

```
Twoje miejsce w rankingu
Twoje punkty
Twoja liczba aktywności
Dystans całkowity
```

Statystyki:

```
punkty w tym miesiącu
ostatnie aktywności
wykres aktywności
najlepsza aktywność
```

Ranking:

```
top users
twoja pozycja
```

---

# Co zobaczy administrator (Django admin)

* lista użytkowników
* lista aktywności
* ranking
* misje
* wydarzenia
* statystyki

---

# Technologie które będzie widać w portfolio

Projekt pokaże:

```
Django
PostgreSQL
Discord OAuth
Data analytics
Leaderboard system
Gamification
REST API
```

---

✅ Jeśli chcesz, mogę też przygotować:

* **pełny diagram ERD tej bazy (bardzo dobry do README)**
* **gotowe Django models.py dla całego systemu**
* **algorytm liczenia rankingu i punktów**
* **SQL migracje dla PostgreSQL**.
