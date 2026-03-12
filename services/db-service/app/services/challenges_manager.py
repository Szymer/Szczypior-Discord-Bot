from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Challenge, ChallengeParticipant, User
from app.schemas.challenge import ChallengeCreate, ChallengeParticipantCreate


class ChallengesManager:
    def __init__(self, db: Session):
        self.db = db

    def create_challenge(self, payload: ChallengeCreate) -> Challenge:
        challenge = Challenge(
            name=payload.name,
            description=payload.description,
            start_date=payload.start_date,
            end_date=payload.end_date,
            rules=payload.rules,
            is_active=payload.is_active,
            created_at=datetime.utcnow(),
        )
        self.db.add(challenge)
        self.db.commit()
        self.db.refresh(challenge)
        return challenge

    def get_challenge(self, challenge_id: int) -> Challenge | None:
        return self.db.query(Challenge).filter(Challenge.id == challenge_id).first()

    def list_challenges(self, active_only: bool = False) -> list[Challenge]:
        query = self.db.query(Challenge)
        if active_only:
            query = query.filter(Challenge.is_active.is_(True))
        return query.order_by(Challenge.start_date.desc()).all()

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
