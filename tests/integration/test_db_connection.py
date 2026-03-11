"""
test_db_connection.py — Testy integracyjne połączenia db-service z bazą danych
================================================================================

URUCHAMIANIE:
    pytest -m integration -v

WYMAGANIA:
    Ustawiona zmienna środowiskowa DATABASE_URL wskazująca na działający Postgres
    (lokalny Docker lub Supabase). Plik .env jest automatycznie wczytywany.

DLACZEGO TE TESTY SĄ OSOBNO OD tests/db-service/?
    Testy w tests/db-service/ używają SQLite in-memory — są szybkie, izolowane
    i nie wymagają żadnej infrastruktury. Weryfikują logikę Python.

    Ten plik robi coś innego: sprawdza, czy kod FAKTYCZNIE działa z prawdziwym
    PostgreSQL. To wykrywa:
    - Błędy w schemacie bazy (nieistniejące tabele, złe typy kolumn)
    - Problemy z siecią / credentials
    - Różnice między SQLite a Postgres (np. JSONB, SERIAL, case sensitivity)
    - Poprawność migracji (czy init.sql był wykonany na docelowej bazie)

    Takie testy są wolniejsze i wymagają działającego serwera, dlatego
    oznaczamy je @pytest.mark.integration i NIE uruchamiamy ich domyślnie.

CZYSZCZENIE DANYCH:
    Każdy test, który zapisuje coś do bazy, USUWA to po sobie (try/finally).
    Dzięki temu testy można uruchamiać na staging/produkcji bez zaśmiecania danych.
"""

import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv()

# Ścieżka do db-service tak samo jak w conftest.py testów jednostkowych
DB_SERVICE_ROOT = Path(__file__).parent.parent.parent / "services" / "db-service"
sys.path.insert(0, str(DB_SERVICE_ROOT))

import os  # noqa: E402

from sqlalchemy import create_engine, inspect, text  # noqa: E402
from sqlalchemy.engine import URL  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402


# ── Pomocnicze ────────────────────────────────────────────────────────────────

def _get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    user = os.getenv("user")
    password = os.getenv("password")
    host = os.getenv("host")
    port = os.getenv("port")
    dbname = os.getenv("dbname")

    if not all([user, password, host, port, dbname]):
        pytest.skip(
            "Brak DATABASE_URL i kompletu user/password/host/port/dbname w środowisku — pomiń test integracyjny"
        )

    return URL.create(
        "postgresql+psycopg2",
        username=user,
        password=password,
        host=host,
        port=int(port),
        database=dbname,
        query={"sslmode": "require"},
    ).render_as_string(hide_password=False)


def _make_session():
    url = _get_database_url()
    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return engine, Session()


# ── Testy połączenia ──────────────────────────────────────────────────────────

@pytest.mark.integration
def test_database_url_is_configured():
    """
    Sprawdza, że konfiguracja połączenia jest ustawiona i wskazuje na Postgres.
    To pierwszy test — jeśli on padnie, nie ma sensu sprawdzać reszty.
    """
    url = _get_database_url()
    assert url.startswith("postgresql"), (
        f"Konfiguracja bazy powinna wskazywać na PostgreSQL, a zaczyna się od: {url[:30]}..."
    )


@pytest.mark.integration
def test_database_connection():
    """
    Próbuje nawiązać połączenie i wykonać SELECT 1.
    Weryfikuje, że serwer Postgres jest osiągalny i credentials są poprawne.
    """
    engine, db = _make_session()
    try:
        result = db.execute(text("SELECT 1")).scalar()
        assert result == 1
    finally:
        db.close()
        engine.dispose()


@pytest.mark.integration
def test_all_expected_tables_exist():
    """
    Sprawdza, że wszystkie tabele zdefiniowane w init.sql faktycznie istnieją
    w bazie danych. Wykrywa sytuację, gdy schema nie została zastosowana.
    """
    expected_tables = {
        "users",
        "activities",
        "special_missions",
        "challenges",
        "challenge_participants",
        "airsoft_events",
        "event_registrations",
    }

    engine, db = _make_session()
    try:
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names(schema="public"))
        missing = expected_tables - existing_tables
        assert not missing, (
            f"Brakujące tabele w bazie danych: {missing}\n"
            "Prawdopodobnie init.sql nie został wykonany na tej bazie."
        )
    finally:
        db.close()
        engine.dispose()


@pytest.mark.integration
def test_users_table_has_correct_columns():
    """
    Weryfikuje, że tabela users ma wszystkie wymagane kolumny.
    Chroni przed sytuacją, gdy schemat jest częściowy lub nieaktualny.
    """
    required_columns = {"id", "discord_id", "display_name", "username", "avatar_url", "created_at", "updated_at"}

    engine, db = _make_session()
    try:
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("users", schema="public")}
        missing = required_columns - columns
        assert not missing, f"Brakujące kolumny w tabeli users: {missing}"
    finally:
        db.close()
        engine.dispose()


@pytest.mark.integration
def test_activities_table_has_correct_columns():
    """Weryfikuje schemat tabeli activities, w tym nowe kolumny challenge_id."""
    required_columns = {
        "id", "user_id", "iid", "activity_type", "distance_km",
        "base_points", "total_points", "created_at", "challenge_id",
        "special_mission_id", "mission_bonus_points",
    }

    engine, db = _make_session()
    try:
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("activities", schema="public")}
        missing = required_columns - columns
        assert not missing, f"Brakujące kolumny w tabeli activities: {missing}"
    finally:
        db.close()
        engine.dispose()


# ── Testy CRUD przez managery ─────────────────────────────────────────────────

@pytest.mark.integration
def test_users_manager_crud_on_real_db():
    """
    Pełny cykl CRUD użytkownika na prawdziwym Postgresie:
      UTWÓRZ → ODCZYTAJ → ZAKTUALIZUJ (upsert) → USUŃ → POTWIERDŹ BRAK

    Test używa discord_id z prefiksem 'TEST_' żeby łatwo identyfikować
    dane testowe. Zawsze sprząta po sobie w bloku finally.
    """
    from app.schemas.user import UserUpsert
    from app.services.users_manager import UsersManager

    engine, db = _make_session()
    test_discord_id = "TEST_integration_user_001"

    try:
        manager = UsersManager(db)

        # Upewnij się, że nie ma śmieci po poprzednich uruchomieniach
        manager.delete_user(test_discord_id)

        # UTWÓRZ
        user = manager.upsert_user(UserUpsert(
            discord_id=test_discord_id,
            display_name="Integration Test User",
            username="testintegration",
        ))
        assert user.id is not None
        assert user.discord_id == test_discord_id

        # ODCZYTAJ
        fetched = manager.get_user_by_discord_id(test_discord_id)
        assert fetched is not None
        assert fetched.id == user.id

        # ZAKTUALIZUJ (upsert)
        updated = manager.upsert_user(UserUpsert(
            discord_id=test_discord_id,
            display_name="Updated Display Name",
        ))
        assert updated.display_name == "Updated Display Name"
        assert updated.id == user.id  # ten sam rekord, nie nowy

    finally:
        manager.delete_user(test_discord_id)
        # Potwierdź usunięcie
        assert manager.get_user_by_discord_id(test_discord_id) is None
        db.close()
        engine.dispose()


@pytest.mark.integration
def test_challenges_manager_crud_on_real_db():
    """
    Pełny cykl CRUD challenge na prawdziwym Postgresie.
    Weryfikuje m.in. zapis i odczyt pola JSONB (rules).
    """
    from datetime import datetime, timezone

    from app.schemas.challenge import ChallengeCreate
    from app.services.challenges_manager import ChallengesManager

    engine, db = _make_session()
    created_id = None

    try:
        manager = ChallengesManager(db)

        # UTWÓRZ
        challenge = manager.create_challenge(ChallengeCreate(
            name="[TEST] Integration Challenge",
            description="Automatyczny test integracyjny",
            start_date=datetime(2026, 4, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 4, 30, tzinfo=timezone.utc),
            rules={"min_distance_km": 5, "types": ["bieganie_teren"]},
            is_active=False,  # nieaktywny żeby nie wpływał na live dane
        ))
        created_id = challenge.id
        assert created_id is not None

        # ODCZYTAJ i sprawdź JSONB
        fetched = manager.get_challenge(created_id)
        assert fetched is not None
        assert fetched.rules["min_distance_km"] == 5

    finally:
        if created_id:
            manager.delete_challenge(created_id)
        db.close()
        engine.dispose()


@pytest.mark.integration
def test_activity_manager_crud_on_real_db():
    """
    Pełny cykl CRUD aktywności na prawdziwym Postgresie.
    Tworzy tymczasowego użytkownika, dodaje aktywność, weryfikuje odczyt,
    a następnie usuwa wszystko.
    """
    from datetime import datetime, timezone

    from app.schemas.activity import ActivityCreate
    from app.services.activity_manager import ActivityManager
    from app.services.users_manager import UsersManager

    engine, db = _make_session()
    test_discord_id = "TEST_integration_activity_user_001"
    test_iid = "TEST_1710000000_integration_001"

    try:
        activity_manager = ActivityManager(db)
        users_manager = UsersManager(db)

        # Wyczyść ewentualne śmieci
        activity_manager.delete_activity(test_iid)
        users_manager.delete_user(test_discord_id)

        # UTWÓRZ aktywność (automatycznie tworzy użytkownika)
        activity = activity_manager.create_activity(ActivityCreate(
            discord_id=test_discord_id,
            display_name="Integration Test Runner",
            iid=test_iid,
            activity_type="bieganie_teren",
            distance_km=10.0,
            base_points=5000,
            weight_bonus_points=0,
            elevation_bonus_points=0,
            mission_bonus_points=0,
            total_points=5000,
            created_at=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
            ai_comment="Test integracyjny",
        ))
        assert activity.id is not None
        assert activity.total_points == 5000

        # ODCZYTAJ przez historię użytkownika
        history = activity_manager.get_user_history(test_discord_id)
        assert any(a.iid == test_iid for a in history)

        # ZAKTUALIZUJ typ aktywności
        updated = activity_manager.update_activity(test_iid, activity_type="bieganie_bieznia")
        assert updated.activity_type == "bieganie_bieznia"

    finally:
        activity_manager.delete_activity(test_iid)
        users_manager.delete_user(test_discord_id)
        db.close()
        engine.dispose()


@pytest.mark.integration
def test_user_rankings_view_is_accessible():
    """
    Sprawdza, że widok user_rankings (używany przez get_rankings) istnieje
    i daje się odpytać. Widoki nie są tworzone przez SQLAlchemy create_all(),
    tylko przez init.sql — ten test wykrywa brak migracji widoków.
    """
    engine, db = _make_session()
    try:
        rows = db.execute(text("SELECT * FROM user_rankings LIMIT 1")).fetchall()
        # Nie sprawdzamy wartości — tylko że zapytanie się wykonało bez błędu
        assert isinstance(rows, list)
    finally:
        db.close()
        engine.dispose()
