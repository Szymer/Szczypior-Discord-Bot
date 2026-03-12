"""
test_challenges.py — Testy ChallengesManager
==============================================

Testujemy cykl życia challenge:
  tworzenie → odczyt → dołączanie uczestników → usuwanie uczestnika → usuwanie challenge

UWAGA NA KOLEJNOŚĆ W TESTACH:
  Każdy test dostaje ROLLBACK po zakończeniu (patrz conftest.py).
  Dlatego każdy test musi sam stworzyć dane, od których zależy.
  Nie można polegać na danych stworzonych przez poprzedni test.
"""

from datetime import datetime, timezone

import pytest

from app.db.models import Challenge
from app.schemas.activity_rule import ActivityRulePatchPayload, ActivityRulePayload
from app.schemas.challenge import ChallengeCreate, ChallengeParticipantCreate
from app.schemas.user import UserUpsert
from app.services.challenges_manager import ChallengesManager
from app.services.users_manager import UsersManager
from libs.shared.constants import ACTIVITY_TYPES


def _make_challenge(name: str = "Testowy Challenge") -> ChallengeCreate:
    """Pomocnik: zwraca gotowy payload do tworzenia challenge."""
    return ChallengeCreate(
        name=name,
        description="Opis challange'u testowego",
        start_date=datetime(2026, 4, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 4, 30, tzinfo=timezone.utc),
        rules={"min_distance_km": 5, "activity_types": ["bieganie_teren", "rower"]},
        is_active=True,
    )


def _make_user(db, discord_id: str = "777000777", display_name: str = "Uczestnik") :
    """Pomocnik: tworzy użytkownika i zwraca obiekt User."""
    return UsersManager(db).upsert_user(
        UserUpsert(discord_id=discord_id, display_name=display_name)
    )


class TestCreateChallenge:
    """Tworzenie nowego challenge."""

    def test_create_returns_challenge_with_id(self, db):
        """Po zapisie challenge powinien mieć przypisane ID z bazy."""
        manager = ChallengesManager(db)

        challenge = manager.create_challenge(_make_challenge())

        assert challenge.id is not None
        assert challenge.name == "Testowy Challenge"
        assert challenge.is_active is True

    def test_challenge_rules_are_persisted(self, db):
        """
        Pole `rules` to JSONB — sprawdzamy, że słownik Python
        jest poprawnie serializowany i deserializowany.
        """
        manager = ChallengesManager(db)
        challenge = manager.create_challenge(_make_challenge())

        fetched = manager.get_challenge(challenge.id)

        assert fetched is not None
        assert fetched.rules["min_distance_km"] == 5

    def test_create_challenge_adds_default_activity_rules_when_missing(self, db):
        manager = ChallengesManager(db)
        payload = ChallengeCreate(
            name="Challenge z default rules",
            description="Brak jawnych activity rules",
            start_date=datetime(2026, 4, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 4, 30, tzinfo=timezone.utc),
            rules={"goal": "distance"},
            is_active=True,
        )

        challenge = manager.create_challenge(payload)
        activity_rules = manager.list_activity_rules(challenge.id)

        assert len(activity_rules) == len(ACTIVITY_TYPES)
        assert {rule.activity_type for rule in activity_rules} == set(ACTIVITY_TYPES)

    def test_create_challenge_uses_custom_activity_rules_when_provided(self, db):
        manager = ChallengesManager(db)
        payload = ChallengeCreate(
            name="Challenge z custom rules",
            description="Custom activity rules",
            start_date=datetime(2026, 4, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 4, 30, tzinfo=timezone.utc),
            rules={"goal": "distance"},
            activity_rules=[
                ActivityRulePayload(
                    activity_type="rower",
                    emoji="🚲",
                    display_name="Szybki rower",
                    base_points=555,
                    unit="km",
                    min_distance=10,
                    bonuses=["przewyższenie"],
                )
            ],
            is_active=True,
        )

        challenge = manager.create_challenge(payload)
        activity_rules = manager.list_activity_rules(challenge.id)

        assert len(activity_rules) == 1
        assert activity_rules[0].activity_type == "rower"
        assert activity_rules[0].base_points == 555
        assert activity_rules[0].display_name == "Szybki rower"


class TestGetChallenge:
    """Odczyt pojedynczego challenge."""

    def test_get_existing_challenge(self, db):
        manager = ChallengesManager(db)
        created = manager.create_challenge(_make_challenge("March Run"))

        found = manager.get_challenge(created.id)

        assert found is not None
        assert found.name == "March Run"

    def test_get_nonexistent_challenge_returns_none(self, db):
        manager = ChallengesManager(db)

        result = manager.get_challenge(99999)

        assert result is None


class TestActivityRules:
    def test_create_activity_rules_for_existing_challenge(self, db):
        manager = ChallengesManager(db)
        challenge = Challenge(
            name="Legacy Challenge",
            description="Utworzony bez activity rules",
            start_date=datetime(2026, 4, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 4, 30, tzinfo=timezone.utc),
            rules={"goal": "distance"},
            is_active=True,
            discord_channel_id=None,
            created_at=datetime.utcnow(),
        )
        db.add(challenge)
        db.commit()
        db.refresh(challenge)

        created_rules = manager.create_activity_rules(challenge.id, None)

        assert len(created_rules) == len(ACTIVITY_TYPES)
        assert {rule.activity_type for rule in created_rules} == set(ACTIVITY_TYPES)

    def test_create_activity_rules_fails_when_challenge_already_has_rules(self, db):
        manager = ChallengesManager(db)
        challenge = manager.create_challenge(_make_challenge())

        with pytest.raises(ValueError, match="already has activity rules"):
            manager.create_activity_rules(challenge.id, None)

    def test_replace_activity_rules_overwrites_existing_set(self, db):
        manager = ChallengesManager(db)
        challenge = manager.create_challenge(_make_challenge())

        replaced = manager.replace_activity_rules(
            challenge.id,
            [
                ActivityRulePayload(
                    activity_type="cardio",
                    emoji="🎯",
                    display_name="Cardio Premium",
                    base_points=999,
                    unit="km",
                    min_distance=2.5,
                    bonuses=["obciążenie"],
                )
            ],
        )

        assert len(replaced) == 1
        assert replaced[0].activity_type == "cardio"
        assert replaced[0].base_points == 999
        assert replaced[0].display_name == "Cardio Premium"

    def test_patch_activity_rules_updates_selected_fields_only(self, db):
        manager = ChallengesManager(db)
        challenge = manager.create_challenge(_make_challenge())
        before = {rule.activity_type: rule for rule in manager.list_activity_rules(challenge.id)}

        patched = manager.patch_activity_rules(
            challenge.id,
            [
                ActivityRulePatchPayload(
                    activity_type="rower",
                    base_points=777,
                    min_distance=12,
                )
            ],
        )
        after = {rule.activity_type: rule for rule in patched}

        assert after["rower"].base_points == 777
        assert float(after["rower"].min_distance) == 12
        assert after["rower"].display_name == before["rower"].display_name

    def test_patch_activity_rules_fails_for_unknown_activity_type(self, db):
        manager = ChallengesManager(db)
        challenge = manager.create_challenge(_make_challenge())

        with pytest.raises(ValueError, match="not found"):
            manager.patch_activity_rules(
                challenge.id,
                [
                    ActivityRulePatchPayload(
                        activity_type="nieistniejacy_typ",
                        base_points=1,
                    )
                ],
            )


class TestListChallenges:
    """Listowanie i filtrowanie challenge'y."""

    def test_list_all_challenges(self, db):
        manager = ChallengesManager(db)
        manager.create_challenge(_make_challenge("Challenge A"))
        manager.create_challenge(_make_challenge("Challenge B"))

        all_challenges = manager.list_challenges()
        names = {c.name for c in all_challenges}

        assert "Challenge A" in names
        assert "Challenge B" in names

    def test_list_active_only(self, db):
        """active_only=True powinno zwrócić tylko is_active=True."""
        manager = ChallengesManager(db)
        active_payload = _make_challenge("Aktywny")
        inactive_payload = ChallengeCreate(
            name="Nieaktywny",
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
            is_active=False,
        )
        manager.create_challenge(active_payload)
        manager.create_challenge(inactive_payload)

        active = manager.list_challenges(active_only=True)
        names = {c.name for c in active}

        assert "Aktywny" in names
        assert "Nieaktywny" not in names


class TestChallengeParticipants:
    """Dołączanie i odchodzenie z challenge."""

    def test_add_participant(self, db):
        """Użytkownik powinien móc dołączyć do challenge."""
        manager = ChallengesManager(db)
        user = _make_user(db, "888000001", "Gracz1")
        challenge = manager.create_challenge(_make_challenge())

        participant = manager.add_participant(
            ChallengeParticipantCreate(discord_id=user.discord_id, challenge_id=challenge.id)
        )

        assert participant.id is not None
        assert participant.user_id == user.id
        assert participant.challenge_id == challenge.id

    def test_list_challenge_participants(self, db):
        manager = ChallengesManager(db)
        user1 = _make_user(db, "888000002", "Gracz2")
        user2 = _make_user(db, "888000003", "Gracz3")
        challenge = manager.create_challenge(_make_challenge())

        manager.add_participant(ChallengeParticipantCreate(discord_id=user1.discord_id, challenge_id=challenge.id))
        manager.add_participant(ChallengeParticipantCreate(discord_id=user2.discord_id, challenge_id=challenge.id))

        participants = manager.list_challenge_participants(challenge.id)
        user_ids = {p.user_id for p in participants}

        assert user1.id in user_ids
        assert user2.id in user_ids

    def test_remove_participant(self, db):
        """Po opuszczeniu challenge uczestnik nie powinien być na liście."""
        manager = ChallengesManager(db)
        user = _make_user(db, "888000004", "Gracz4")
        challenge = manager.create_challenge(_make_challenge())
        manager.add_participant(ChallengeParticipantCreate(discord_id=user.discord_id, challenge_id=challenge.id))

        removed = manager.remove_participant(discord_id=user.discord_id, challenge_id=challenge.id)

        assert removed is True
        participants = manager.list_challenge_participants(challenge.id)
        assert all(p.user_id != user.id for p in participants)

    def test_add_participant_user_not_found(self, db):
        """Próba dołączenia nieistniejącego użytkownika powinna rzucić ValueError."""
        manager = ChallengesManager(db)
        challenge = manager.create_challenge(_make_challenge())

        with pytest.raises(ValueError, match="not found"):
            manager.add_participant(
                ChallengeParticipantCreate(discord_id="999_nieistniejacy", challenge_id=challenge.id)
            )


class TestDeleteChallenge:
    """Usuwanie challenge z bazy."""

    def test_delete_existing_challenge(self, db):
        """Challenge powinien zniknąć z bazy po usunięciu."""
        manager = ChallengesManager(db)
        challenge = manager.create_challenge(_make_challenge("DoUsuniecia"))

        deleted = manager.delete_challenge(challenge.id)

        assert deleted is True
        assert manager.get_challenge(challenge.id) is None

    def test_delete_nonexistent_challenge_returns_false(self, db):
        manager = ChallengesManager(db)

        result = manager.delete_challenge(99999)

        assert result is False
