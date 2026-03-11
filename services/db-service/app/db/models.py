from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    discord_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    username: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    activities: Mapped[list["Activity"]] = relationship(back_populates="user")
    event_registrations: Mapped[list["EventRegistration"]] = relationship(back_populates="user")
    challenge_participations: Mapped[list["ChallengeParticipant"]] = relationship(back_populates="user")


class SpecialMission(Base):
    __tablename__ = "special_missions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    emoji: Mapped[str | None] = mapped_column(Text)
    bonus_points: Mapped[int] = mapped_column(Integer, nullable=False)
    min_distance_km: Mapped[float | None] = mapped_column(Numeric(10, 2))
    min_time_minutes: Mapped[int | None] = mapped_column(Integer)
    activity_type_filter: Mapped[str | None] = mapped_column(Text)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    max_completions_per_user: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    activities: Mapped[list["Activity"]] = relationship(back_populates="special_mission")


class Challenge(Base):
    __tablename__ = "challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rules: Mapped[dict | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    activities: Mapped[list["Activity"]] = relationship(back_populates="challenge")
    participants: Mapped[list["ChallengeParticipant"]] = relationship(back_populates="challenge")


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        CheckConstraint(
            "activity_type IN ('bieganie_teren','bieganie_bieznia','plywanie','rower','spacer','cardio')",
            name="chk_activity_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    iid: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    activity_type: Mapped[str] = mapped_column(Text, nullable=False)
    distance_km: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    weight_kg: Mapped[float | None] = mapped_column(Numeric(10, 2))
    elevation_m: Mapped[int | None] = mapped_column(Integer)
    time_minutes: Mapped[int | None] = mapped_column(Integer)
    pace: Mapped[str | None] = mapped_column(Text)
    heart_rate_avg: Mapped[int | None] = mapped_column(Integer)
    calories: Mapped[int | None] = mapped_column(Integer)
    base_points: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_bonus_points: Mapped[int] = mapped_column(Integer, nullable=False)
    elevation_bonus_points: Mapped[int] = mapped_column(Integer, nullable=False)
    special_mission_id: Mapped[int | None] = mapped_column(
        ForeignKey("special_missions.id", ondelete="SET NULL")
    )
    mission_bonus_points: Mapped[int] = mapped_column(Integer, nullable=False)
    total_points: Mapped[int] = mapped_column(Integer, nullable=False)
    challenge_id: Mapped[int | None] = mapped_column(ForeignKey("challenges.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    message_id: Mapped[str | None] = mapped_column(Text)
    message_timestamp: Mapped[str | None] = mapped_column(Text)
    ai_comment: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="activities")
    special_mission: Mapped[SpecialMission | None] = relationship(back_populates="activities")
    challenge: Mapped[Challenge | None] = relationship(back_populates="activities")


class AirsoftEvent(Base):
    __tablename__ = "airsoft_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    location: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float | None] = mapped_column(Numeric)
    currency: Mapped[str] = mapped_column(Text, default="PLN", nullable=False)
    event_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    registrations: Mapped[list["EventRegistration"]] = relationship(back_populates="event")


class EventRegistration(Base):
    __tablename__ = "event_registrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_id: Mapped[int] = mapped_column(ForeignKey("airsoft_events.id", ondelete="CASCADE"), nullable=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[User] = relationship(back_populates="event_registrations")
    event: Mapped[AirsoftEvent] = relationship(back_populates="registrations")


class ChallengeParticipant(Base):
    __tablename__ = "challenge_participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    challenge: Mapped[Challenge] = relationship(back_populates="participants")
    user: Mapped[User] = relationship(back_populates="challenge_participations")
