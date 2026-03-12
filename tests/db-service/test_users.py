"""
test_users.py — Testy UsersManager
====================================

Testujemy BEZPOŚREDNIO klasę UsersManager, a nie przez HTTP API.

DLACZEGO TAK?
  Testowanie przez API (FastAPI TestClient) sprawdzałoby również
  routing, serializację Pydantic i warstwę HTTP — to jest przydatne,
  ale wolniejsze i bardziej złożone. Tutaj interesuje nas LOGIKA
  persystencji: czy dane faktycznie trafiają do bazy i czy możemy
  je odczytać/usunąć. Dlatego wywołujemy metody managera wprost.
"""

import pytest

from app.schemas.user import UserUpsert
from app.services.users_manager import UsersManager


class TestUpsertUser:
    """Tworzenie i aktualizacja użytkownika."""

    def test_create_new_user(self, db):
        """Nowy użytkownik powinien zostać dodany do bazy."""
        manager = UsersManager(db)
        payload = UserUpsert(
            discord_id="111000111",
            display_name="Testowy Gracz",
            username="testgracz",
            avatar_url="https://cdn.discord.com/avatars/111000111/abc.png",
        )

        user = manager.upsert_user(payload)

        assert user.id is not None
        assert user.discord_id == "111000111"
        assert user.display_name == "Testowy Gracz"
        assert user.username == "testgracz"

    def test_upsert_updates_existing_user(self, db):
        """
        Ponowne wywołanie upsert na tym samym discord_id powinno
        zaktualizować dane, a NIE stworzyć drugiego rekordu.

        To zachowanie jest kluczowe: Discord może zmienić nick
        użytkownika i bot powinien to odzwierciedlić w bazie.
        """
        manager = UsersManager(db)
        base = UserUpsert(discord_id="222000222", display_name="Stary Nick")
        manager.upsert_user(base)

        updated = UserUpsert(discord_id="222000222", display_name="Nowy Nick")
        user = manager.upsert_user(updated)

        assert user.display_name == "Nowy Nick"
        # Sprawdzamy, że w bazie nadal jest JEDEN rekord
        all_users = manager.list_users()
        matching = [u for u in all_users if u.discord_id == "222000222"]
        assert len(matching) == 1


class TestGetUser:
    """Odczyt użytkownika po discord_id."""

    def test_get_existing_user(self, db):
        manager = UsersManager(db)
        manager.upsert_user(UserUpsert(discord_id="333000333", display_name="Gracz"))

        found = manager.get_user_by_discord_id("333000333")

        assert found is not None
        assert found.discord_id == "333000333"

    def test_get_nonexistent_user_returns_none(self, db):
        """Nieistniejący użytkownik — powinniśmy dostać None, nie wyjątek."""
        manager = UsersManager(db)

        result = manager.get_user_by_discord_id("999999999_nieistniejacy")

        assert result is None


class TestDeleteUser:
    """Usuwanie użytkownika z bazy."""

    def test_delete_existing_user(self, db):
        """Po usunięciu użytkownik nie powinien być dostępny w bazie."""
        manager = UsersManager(db)
        manager.upsert_user(UserUpsert(discord_id="444000444", display_name="DoUsuniecia"))

        deleted = manager.delete_user("444000444")

        assert deleted is True
        assert manager.get_user_by_discord_id("444000444") is None

    def test_delete_nonexistent_user_returns_false(self, db):
        """
        Próba usunięcia nieistniejącego użytkownika powinna zwrócić False,
        a NIE rzucać wyjątku — bot nie powinien crashować w takiej sytuacji.
        """
        manager = UsersManager(db)

        result = manager.delete_user("999999999_nieistniejacy")

        assert result is False


class TestListUsers:
    """Listowanie użytkowników."""

    def test_list_contains_created_users(self, db):
        manager = UsersManager(db)
        manager.upsert_user(UserUpsert(discord_id="555000001", display_name="Alfa"))
        manager.upsert_user(UserUpsert(discord_id="555000002", display_name="Beta"))

        users = manager.list_users()
        discord_ids = {u.discord_id for u in users}

        assert "555000001" in discord_ids
        assert "555000002" in discord_ids
