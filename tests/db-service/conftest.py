"""
conftest.py — Konfiguracja bazy danych na potrzeby testów
==========================================================

DLACZEGO SQLITE ZAMIAST POSTGRES?
-----------------------------------
Testy jednostkowe menedżerów bazy danych używają silnika SQLite
działającego w pamięci RAM (:memory:), a NIE prawdziwego PostgreSQL.

Różnice i konsekwencje:

1. SZYBKOŚĆ I IZOLACJA
   SQLite in-memory tworzy się w milisekundach i jest niszczony po każdym
   teście. Nie wymaga uruchomionego kontenera Docker ani zewnętrznego serwera.
   Dzięki temu testy można uruchamiać lokalnie i w CI bez żadnej infrastruktury.

2. JSONB → TEXT (via @compiles)
   PostgreSQL obsługuje typ JSONB (binarny JSON z indeksowaniem). SQLite nie zna
   JSONB. Zamiast modyfikować modele produkcyjne, używamy dekoratora
   @compiles(JSONB, "sqlite"), który mówi SQLAlchemy: „gdy kompilujesz JSONB
   dla dialektu SQLite, emituj po prostu TEXT". To eleganckie rozwiązanie bez
   żadnych łatek w kodzie produkcyjnym.

3. BRAK SERIAL / SEQUENCES
   PostgreSQL używa SERIAL/SEQUENCE do auto-increment. SQLite używa
   AUTOINCREMENT. SQLAlchemy obsługuje tę różnicę transparentnie.

4. OGRANICZENIA CHECK i CASCADE
   SQLite domyślnie NIE wymusza check constraints ani foreign keys (o ile nie
   włączymy PRAGMA foreign_keys = ON). Testy weryfikują logikę aplikacji,
   a nie silnik bazy — dlatego to akceptowalne na tym poziomie.

5. TESTY JEDNOSTKOWE vs. INTEGRACYJNE
   - Testy tutaj (tests/db-service/) = testy jednostkowe menedżerów.
     Weryfikują LOGIKĘ kodu Python, używając lekkiej bazy in-memory.
   - Testy w tests/integration/ = testy integracyjne na rzeczywistym Postgres.
     Weryfikują, że cały stos (sieć, Docker, real DB) działa razem.

FIXTURES
---------
- `engine`  — jednorazowy silnik SQLite in-memory dla całej sesji testowej
- `tables`  — tworzy wszystkie tabele przed testami, usuwa po
- `db`      — świeża transakcja SQLAlchemy Session dla każdego testu;
              po każdym teście robi ROLLBACK, więc testy nie zaśmiecają się nawzajem
"""

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

# ── Ścieżki ──────────────────────────────────────────────────────────────────
# Dorzucamy katalog db-service do sys.path, żeby `app.*` importowało się
# tak samo jak podczas normalnego uruchomienia serwisu.
DB_SERVICE_ROOT = Path(__file__).parent.parent.parent / "services" / "db-service"
sys.path.insert(0, str(DB_SERVICE_ROOT))

# ── Patch JSONB → TEXT dla dialektu SQLite ────────────────────────────────────
# Zamiast modyfikować typy w modelach, rejestrujemy „kompilator" specyficzny
# dla SQLite. Gdy SQLAlchemy napotka kolumnę JSONB budując DDL dla SQLite,
# wyemituje po prostu TEXT. Modele produkcyjne pozostają nienaruszone.
@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(element, compiler, **kw):  # noqa: ARG001
    return "TEXT"


from app.db.base import Base  # noqa: E402
from app.db.models import (  # noqa: E402, F401
    Activity,
    AirsoftEvent,
    Challenge,
    ChallengeParticipant,
    EventRegistration,
    SpecialMission,
    User,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def engine():
    """
    Tworzy silnik SQLite in-memory RAZ dla całej sesji testowej.
    scope="session" oznacza, że ten sam silnik jest współdzielony
    przez wszystkie pliki testowe — wystarczy jeden create_all().
    """
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )


@pytest.fixture(scope="session")
def tables(engine):
    """
    Tworzy schemat (wszystkie tabele) przed uruchomieniem testów
    i usuwa go po zakończeniu całej sesji.
    """
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db(engine, tables):
    """
    Dostarcza świeżą Session dla każdego testu.

    DLACZEGO ROLLBACK zamiast commit + DELETE?
    Każdy test startuje nową transakcję, a po jego zakończeniu
    wywołujemy rollback() — baza wraca do stanu sprzed testu.
    Dzięki temu:
    - Testy są od siebie izolowane (żaden test nie „brudzi" danych dla kolejnego)
    - Rollback jest szybszy niż DELETE wszystkich wierszy
    - Nie musimy dbać o kolejność czyszczenia tabel (foreign keys)
    """
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection, autoflush=False, autocommit=False)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()

