from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import AirsoftEvent, EventRegistration, User
from app.schemas.event import AirsoftEventCreate, EventRegistrationCreate


class EventsManager:
    def __init__(self, db: Session):
        self.db = db

    def create_event(self, payload: AirsoftEventCreate) -> AirsoftEvent:
        now = datetime.utcnow()
        event = AirsoftEvent(
            name=payload.name,
            description=payload.description,
            organizer=payload.organizer,
            start_date=payload.start_date,
            end_date=payload.end_date,
            location=payload.location,
            event_type=payload.event_type,
            price=payload.price,
            currency=payload.currency,
            event_url=payload.event_url,
            discord_channel_id=payload.discord_channel_id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_event(self, event_id: int) -> AirsoftEvent | None:
        return self.db.query(AirsoftEvent).filter(AirsoftEvent.id == event_id).first()

    def list_events(self, upcoming_only: bool = False) -> list[AirsoftEvent]:
        query = self.db.query(AirsoftEvent)
        if upcoming_only:
            query = query.filter(AirsoftEvent.start_date >= datetime.utcnow())
        return query.order_by(AirsoftEvent.start_date.asc()).all()

    def get_active_events(self) -> list[AirsoftEvent]:
        """Zwraca eventy aktualnie trwające (start_date <= now <= end_date lub without end_date)."""
        now = datetime.utcnow()
        query = self.db.query(AirsoftEvent).filter(AirsoftEvent.start_date <= now)
        query = query.filter(
            (AirsoftEvent.end_date == None) | (AirsoftEvent.end_date >= now)  # noqa: E711
        )
        return query.order_by(AirsoftEvent.start_date.asc()).all()

    def delete_event(self, event_id: int) -> bool:
        event = self.get_event(event_id)
        if not event:
            return False
        self.db.delete(event)
        self.db.commit()
        return True

    def register_user(self, payload: EventRegistrationCreate) -> EventRegistration:
        user = self.db.query(User).filter(User.discord_id == payload.discord_id).first()
        if not user:
            raise ValueError(f"User with discord_id={payload.discord_id} not found")

        event = self.get_event(payload.event_id)
        if not event:
            raise ValueError(f"Event with id={payload.event_id} not found")

        registration = EventRegistration(
            user_id=user.id,
            event_id=payload.event_id,
            registered_at=datetime.utcnow(),
        )
        self.db.add(registration)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ValueError("User is already registered for this event") from exc

        self.db.refresh(registration)
        return registration

    def unregister_user(self, discord_id: str, event_id: int) -> bool:
        user = self.db.query(User).filter(User.discord_id == discord_id).first()
        if not user:
            return False
        registration = (
            self.db.query(EventRegistration)
            .filter(EventRegistration.user_id == user.id)
            .filter(EventRegistration.event_id == event_id)
            .first()
        )
        if not registration:
            return False
        self.db.delete(registration)
        self.db.commit()
        return True

    def list_event_registrations(self, event_id: int) -> list[EventRegistration]:
        return (
            self.db.query(EventRegistration)
            .filter(EventRegistration.event_id == event_id)
            .order_by(EventRegistration.registered_at.asc())
            .all()
        )

    def list_user_registrations(self, discord_id: str) -> list[EventRegistration]:
        user = self.db.query(User).filter(User.discord_id == discord_id).first()
        if not user:
            return []
        return (
            self.db.query(EventRegistration)
            .filter(EventRegistration.user_id == user.id)
            .order_by(EventRegistration.registered_at.desc())
            .all()
        )
