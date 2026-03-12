from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import ActivityRule, Challenge, ChallengeParticipant, User
from app.schemas.activity_rule import ActivityRulePatchPayload, ActivityRulePayload
from app.schemas.challenge import ChallengeCreate, ChallengeParticipantCreate
from libs.shared.constants import ACTIVITY_TYPES


class ChallengesManager:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _default_activity_rules_payload() -> list[ActivityRulePayload]:
        return [
            ActivityRulePayload(activity_type=activity_type, **definition)
            for activity_type, definition in ACTIVITY_TYPES.items()
        ]

    @staticmethod
    def _normalize_activity_rules_payload(
        payloads: list[ActivityRulePayload] | None,
    ) -> list[ActivityRulePayload]:
        return payloads or ChallengesManager._default_activity_rules_payload()

    def _create_activity_rule_records(
        self,
        challenge_id: int,
        payloads: list[ActivityRulePayload] | None,
    ) -> list[ActivityRule]:
        normalized_payloads = self._normalize_activity_rules_payload(payloads)
        created_rules: list[ActivityRule] = []
        for payload in normalized_payloads:
            activity_rule = ActivityRule(
                challenge_id=challenge_id,
                **payload.model_dump(),
            )
            self.db.add(activity_rule)
            created_rules.append(activity_rule)
        self.db.flush()
        return created_rules

    def create_challenge(self, payload: ChallengeCreate) -> Challenge:
        challenge = Challenge(
            name=payload.name,
            description=payload.description,
            start_date=payload.start_date,
            end_date=payload.end_date,
            rules=payload.rules,
            is_active=payload.is_active,
            discord_channel_id=payload.discord_channel_id,
            created_at=datetime.utcnow(),
        )
        self.db.add(challenge)
        self.db.flush()
        self._create_activity_rule_records(challenge.id, payload.activity_rules)
        self.db.commit()
        self.db.refresh(challenge)
        return challenge

    def list_activity_rules(self, challenge_id: int) -> list[ActivityRule]:
        return (
            self.db.query(ActivityRule)
            .filter(ActivityRule.challenge_id == challenge_id)
            .order_by(ActivityRule.id.asc())
            .all()
        )

    def create_activity_rules(
        self,
        challenge_id: int,
        payloads: list[ActivityRulePayload] | None,
    ) -> list[ActivityRule]:
        challenge = self.get_challenge(challenge_id)
        if not challenge:
            raise ValueError(f"Challenge with id={challenge_id} not found")

        if self.list_activity_rules(challenge_id):
            raise ValueError(f"Challenge with id={challenge_id} already has activity rules")

        self._create_activity_rule_records(challenge_id, payloads)
        self.db.commit()
        return self.list_activity_rules(challenge_id)

    def replace_activity_rules(
        self,
        challenge_id: int,
        payloads: list[ActivityRulePayload] | None,
    ) -> list[ActivityRule]:
        challenge = self.get_challenge(challenge_id)
        if not challenge:
            raise ValueError(f"Challenge with id={challenge_id} not found")

        (
            self.db.query(ActivityRule)
            .filter(ActivityRule.challenge_id == challenge_id)
            .delete(synchronize_session=False)
        )
        self.db.flush()
        self._create_activity_rule_records(challenge_id, payloads)
        self.db.commit()
        return self.list_activity_rules(challenge_id)

    def patch_activity_rules(
        self,
        challenge_id: int,
        payloads: list[ActivityRulePatchPayload],
    ) -> list[ActivityRule]:
        challenge = self.get_challenge(challenge_id)
        if not challenge:
            raise ValueError(f"Challenge with id={challenge_id} not found")

        if not payloads:
            return self.list_activity_rules(challenge_id)

        existing_rules = self.list_activity_rules(challenge_id)
        by_activity_type = {rule.activity_type: rule for rule in existing_rules}

        for patch in payloads:
            target = by_activity_type.get(patch.activity_type)
            if not target:
                raise ValueError(
                    f"Activity rule with activity_type={patch.activity_type!r} not found "
                    f"for challenge id={challenge_id}"
                )

            update_fields = patch.model_dump(exclude_unset=True, exclude={"activity_type"})
            for field_name, field_value in update_fields.items():
                setattr(target, field_name, field_value)

        self.db.commit()
        return self.list_activity_rules(challenge_id)

    def get_challenge(self, challenge_id: int) -> Challenge | None:
        return self.db.query(Challenge).filter(Challenge.id == challenge_id).first()

    def list_challenges(self, active_only: bool = False) -> list[Challenge]:
        query = self.db.query(Challenge)
        if active_only:
            query = query.filter(Challenge.is_active.is_(True))
        return query.order_by(Challenge.start_date.desc()).all()

    def get_active_challenges(self) -> list[Challenge]:
        """Zwraca aktualnie aktywne challenge (is_active=True oraz w przedziale dat)."""
        now = datetime.utcnow()
        return (
            self.db.query(Challenge)
            .filter(
                Challenge.is_active.is_(True),
                Challenge.start_date <= now,
                Challenge.end_date >= now,
            )
            .order_by(Challenge.start_date.asc())
            .all()
        )

    def delete_challenge(self, challenge_id: int) -> bool:
        challenge = self.get_challenge(challenge_id)
        if not challenge:
            return False
        self.db.delete(challenge)
        self.db.commit()
        return True

    def add_participant(self, payload: ChallengeParticipantCreate) -> ChallengeParticipant:
        user = self.db.query(User).filter(User.discord_id == payload.discord_id).first()
        if not user:
            raise ValueError(f"User with discord_id={payload.discord_id} not found")

        challenge = self.get_challenge(payload.challenge_id)
        if not challenge:
            raise ValueError(f"Challenge with id={payload.challenge_id} not found")

        participant = ChallengeParticipant(
            challenge_id=payload.challenge_id,
            user_id=user.id,
            joined_at=datetime.utcnow(),
        )
        self.db.add(participant)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ValueError("User is already a participant in this challenge") from exc

        self.db.refresh(participant)
        return participant

    def remove_participant(self, discord_id: str, challenge_id: int) -> bool:
        user = self.db.query(User).filter(User.discord_id == discord_id).first()
        if not user:
            return False
        participant = (
            self.db.query(ChallengeParticipant)
            .filter(ChallengeParticipant.user_id == user.id)
            .filter(ChallengeParticipant.challenge_id == challenge_id)
            .first()
        )
        if not participant:
            return False
        self.db.delete(participant)
        self.db.commit()
        return True

    def list_challenge_participants(self, challenge_id: int) -> list[ChallengeParticipant]:
        return (
            self.db.query(ChallengeParticipant)
            .filter(ChallengeParticipant.challenge_id == challenge_id)
            .order_by(ChallengeParticipant.joined_at.asc())
            .all()
        )

    def list_user_challenges(self, discord_id: str) -> list[ChallengeParticipant]:
        user = self.db.query(User).filter(User.discord_id == discord_id).first()
        if not user:
            return []
        return (
            self.db.query(ChallengeParticipant)
            .filter(ChallengeParticipant.user_id == user.id)
            .order_by(ChallengeParticipant.joined_at.desc())
            .all()
        )
