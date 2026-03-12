from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, Text
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    message_id: Mapped[str | None] = mapped_column(Text)
    message_timestamp: Mapped[str | None] = mapped_column(Text)
    ai_comment: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="activities")
    special_mission: Mapped[SpecialMission | None] = relationship(back_populates="activities")
