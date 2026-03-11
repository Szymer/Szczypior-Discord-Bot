"""
test_activities.py — Testy ActivityManager
============================================

Scenariusze:
  1. Dodanie aktywności i weryfikacja w bazie
  2. Próba dodania duplikatu (ten sam iid) — oczekiwany błąd
  3. Historia aktywności użytkownika
  4. Modyfikacja aktywności (np. zmiana activity_type)
  5. Usunięcie aktywności

DLACZEGO AKTYWNOŚCI SĄ TRUDNIEJSZE DO TESTOWANIA NIŻ UŻYTKOWNICY?
  Aktywność wymaga istniejącego użytkownika w bazie (foreign key user_id).
  W testach nie mockujemy tego — `create_activity` wewnętrznie wywołuje
  `upsert_user`, co jest celowym zachowaniem: bot może podać dane użytkownika
  razem z aktywnością i serwis sam zadba o jego istnienie w bazie.

  Dlatego payload ActivityCreate zawiera `discord_id` i `display_name` —
  są potrzebne właśnie do tego automatycznego upsert'u.

MODYFIKACJA AKTYWNOŚCI:
  W oryginalnym projekcie ActivityManager nie miał metody update_activity.
  Dodaliśmy ją, bo scenariusz „korekta wpisu" jest realny (np. bot omyłkowo
  zinterpretował typ aktywności). Logika pozostaje w managerze — bot podaje
  gotowe wartości, bez przeliczania punktów po stronie serwisu.
"""

from datetime import datetime, timezone

import pytest

from app.schemas.activity import ActivityCreate
from app.services.activity_manager import ActivityManager


def _make_activity_payload(
    iid: str = "1710000000_9990000001",
    discord_id: str = "100200300",
    display_name: str = "Biegacz Jan",
    activity_type: str = "bieganie_teren",
    distance_km: float = 10.0,
    total_points: int = 5000,
) -> ActivityCreate:
    """Pomocnik: minimalny poprawny payload aktywności."""
    return ActivityCreate(
        discord_id=discord_id,
        display_name=display_name,
        iid=iid,
        activity_type=activity_type,
        distance_km=distance_km,
        base_points=total_points,
        weight_bonus_points=0,
        elevation_bonus_points=0,
        mission_bonus_points=0,
        total_points=total_points,
        created_at=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
    )


class TestCreateActivity:
    """Dodawanie aktywności do bazy."""

    def test_create_activity_returns_object_with_id(self, db):
        """Nowa aktywność powinna dostać ID z bazy i zachować wszystkie dane."""
        manager = ActivityManager(db)
        payload = _make_activity_payload()

        activity = manager.create_activity(payload)

        assert activity.id is not None
        assert activity.iid == "1710000000_9990000001"
        assert activity.activity_type == "bieganie_teren"
        assert activity.distance_km == 10.0
        assert activity.total_points == 5000

    def test_create_activity_auto_creates_user(self, db):
        """
        create_activity powinno automatycznie stworzyć użytkownika,
        jeśli nie istnieje — weryfikujemy przez user_id na aktywności.
        """
        manager = ActivityManager(db)
        payload = _make_activity_payload(iid="1710000001_9990000002", discord_id="555111222")

        activity = manager.create_activity(payload)

        assert activity.user_id is not None

    def test_create_duplicate_iid_raises(self, db):
        """
        IID musi być unikalne. Drugi zapis z tym samym iid
        powinien rzucić ValueError — nie pozwalamy na duplikaty.
        """
        manager = ActivityManager(db)
        payload = _make_activity_payload(iid="1710000002_DUPLIKAT")
        manager.create_activity(payload)

        with pytest.raises(ValueError, match="already exists"):
            manager.create_activity(
                _make_activity_payload(iid="1710000002_DUPLIKAT", distance_km=5.0)
            )

    def test_activity_with_points_breakdown(self, db):
        """
        Weryfikujemy, że serwis ZAPISUJE punkty dokładnie tak jak bot je podał
        — bez żadnego przeliczania po stronie serwisu.
        """
        manager = ActivityManager(db)
        payload = ActivityCreate(
            discord_id="100200301",
            display_name="Górski Marek",
            iid="1710000003_9990000003",
            activity_type="bieganie_teren",
            distance_km=15.0,
            base_points=7500,
            weight_bonus_points=500,
            elevation_bonus_points=200,
            mission_bonus_points=2000,
            total_points=10200,
            created_at=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc),
        )

        activity = manager.create_activity(payload)

        assert activity.base_points == 7500
        assert activity.weight_bonus_points == 500
        assert activity.elevation_bonus_points == 200
        assert activity.mission_bonus_points == 2000
        assert activity.total_points == 10200


class TestGetUserHistory:
    """Historia aktywności użytkownika."""

    def test_history_returns_user_activities_ordered_by_date(self, db):
        """Historia powinna zawierać aktywności danego użytkownika, od najnowszej."""
        manager = ActivityManager(db)
        discord_id = "200300400"
        manager.create_activity(_make_activity_payload(
            iid="1710001000_HIST1", discord_id=discord_id,
            display_name="Gracz",
        ))
        manager.create_activity(_make_activity_payload(
            iid="1710001001_HIST2", discord_id=discord_id,
            display_name="Gracz",
        ))

        history = manager.get_user_history(discord_id)

        assert len(history) == 2
        iids = [a.iid for a in history]
        assert "1710001000_HIST1" in iids
        assert "1710001001_HIST2" in iids

    def test_history_respects_limit(self, db):
        """Parametr limit powinien ograniczać liczbę zwracanych wyników."""
        manager = ActivityManager(db)
        discord_id = "200300401"
        for i in range(5):
            manager.create_activity(_make_activity_payload(
                iid=f"1710002000_LIM{i}", discord_id=discord_id, display_name="X"
            ))

        history = manager.get_user_history(discord_id, limit=3)

        assert len(history) == 3

    def test_history_empty_for_unknown_user(self, db):
        manager = ActivityManager(db)

        history = manager.get_user_history("999_nieznany_user")

        assert history == []


class TestUpdateActivity:
    """
    Modyfikacja aktywności.

    DLACZEGO MODYFIKACJA JEST OSOBNĄ KLASĄ TESTÓW?
    Po pierwsze, weryfikujemy, że update działa poprawnie.
    Po drugie, chcemy upewnić się, że zmieniamy TYLKO wskazane pole,
    a pozostałe dane pozostają nienaruszone (brak efektów ubocznych).
    """

    def test_update_activity_type(self, db):
        """
        Scenariusz: bot błędnie rozpoznał typ aktywności jako 'spacer'
        zamiast 'bieganie_bieznia'. Admin koryguje wpis.
        """
        manager = ActivityManager(db)
        payload = _make_activity_payload(
            iid="1710003000_UPD1",
            activity_type="spacer",
        )
        manager.create_activity(payload)

        updated = manager.update_activity("1710003000_UPD1", activity_type="bieganie_bieznia")

        assert updated.activity_type == "bieganie_bieznia"
        # Pozostałe pola powinny być niezmienione
        assert updated.total_points == 5000
        assert updated.distance_km == 10.0

    def test_update_multiple_fields(self, db):
        """Można zaktualizować kilka pól jednocześnie."""
        manager = ActivityManager(db)
        manager.create_activity(_make_activity_payload(iid="1710003001_UPD2"))

        updated = manager.update_activity(
            "1710003001_UPD2",
            ai_comment="Świetny wynik!",
            total_points=6000,
        )

        assert updated.ai_comment == "Świetny wynik!"
        assert updated.total_points == 6000

    def test_update_nonexistent_activity_raises(self, db):
        """Próba aktualizacji nieistniejącej aktywności powinna rzucić ValueError."""
        manager = ActivityManager(db)

        with pytest.raises(ValueError, match="not found"):
            manager.update_activity("NIEISTNIEJACE_IID", activity_type="rower")

    def test_update_disallowed_field_raises(self, db):
        """
        Nie pozwalamy zmieniać pól takich jak iid czy user_id przez update_activity.
        To zabezpieczenie przed przypadkowym uszkodzeniem danych.
        """
        manager = ActivityManager(db)
        manager.create_activity(_make_activity_payload(iid="1710003002_UPD3"))

        with pytest.raises(ValueError, match="Niedozwolone pola"):
            # `iid` jest chronione — przekazujemy je jako pole w **fields
            manager.update_activity("1710003002_UPD3", **{"iid": "ZMIENIONY_IID"})


class TestDeleteActivity:
    """Usuwanie aktywności."""

    def test_delete_existing_activity(self, db):
        """Aktywność powinna zniknąć z bazy po wywołaniu delete_activity."""
        manager = ActivityManager(db)
        payload = _make_activity_payload(iid="1710004000_DEL1")
        manager.create_activity(payload)

        deleted = manager.delete_activity("1710004000_DEL1")

        assert deleted is True
        assert manager.get_activity_by_iid("1710004000_DEL1") is None

    def test_delete_nonexistent_activity_returns_false(self, db):
        """Usunięcie nieistniejącej aktywności zwraca False — nie wyjątek."""
        manager = ActivityManager(db)

        result = manager.delete_activity("NIEISTNIEJACE_IID")

        assert result is False

    def test_full_lifecycle_create_update_delete(self, db):
        """
        Pełny cykl życia aktywności:
          DODAJ → ZMODYFIKUJ TYP → USUŃ → POTWIERDŹ BRAK

        To scenariusz end-to-end przetestowany bez HTTP,
        bezpośrednio na warstwie persystencji.
        """
        manager = ActivityManager(db)
        iid = "1710005000_LIFECYCLE"

        # 1. Utwórz
        activity = manager.create_activity(
            _make_activity_payload(iid=iid, activity_type="rower", total_points=3000)
        )
        assert activity.activity_type == "rower"

        # 2. Zmodyfikuj typ
        updated = manager.update_activity(iid, activity_type="cardio", total_points=2500)
        assert updated.activity_type == "cardio"
        assert updated.total_points == 2500

        # 3. Usuń
        deleted = manager.delete_activity(iid)
        assert deleted is True

        # 4. Potwierdź brak
        assert manager.get_activity_by_iid(iid) is None
