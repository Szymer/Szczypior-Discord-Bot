from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Activity, SpecialMission, User
from app.schemas.activity import ActivityCreate
from app.schemas.user import UserUpsert
from app.services.users_manager import UsersManager


class ActivityManager:
    def __init__(self, db: Session):
        self.db = db
        self._users = UsersManager(db)

    def create_activity(self, payload: ActivityCreate) -> Activity:
        user = self._users.upsert_user(
            UserUpsert(discord_id=payload.discord_id, display_name=payload.display_name)
        )

        row = Activity(
            user_id=user.id,
            iid=payload.iid,
            activity_type=payload.activity_type,
            distance_km=payload.distance_km,
            weight_kg=payload.weight_kg,
            elevation_m=payload.elevation_m,
            time_minutes=payload.time_minutes,
            pace=payload.pace,
            heart_rate_avg=payload.heart_rate_avg,
            calories=payload.calories,
            base_points=payload.base_points,
            weight_bonus_points=payload.weight_bonus_points,
            elevation_bonus_points=payload.elevation_bonus_points,
            special_mission_id=payload.special_mission_id,
            mission_bonus_points=payload.mission_bonus_points,
            total_points=payload.total_points,
            challenge_id=payload.challenge_id,
            created_at=payload.created_at,
            message_id=payload.message_id,
            message_timestamp=payload.message_timestamp,
            ai_comment=payload.ai_comment,
        )

        self.db.add(row)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ValueError("Activity with this IID already exists") from exc

        self.db.refresh(row)
        return row

    def get_user_history(self, discord_id: str, limit: int = 20) -> list[Activity]:
        return (
            self.db.query(Activity)
            .join(User, User.id == Activity.user_id)
            .filter(User.discord_id == discord_id)
            .order_by(Activity.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_activity_by_iid(self, iid: str) -> Activity | None:
        return self.db.query(Activity).filter(Activity.iid == iid).first()

    def update_activity(self, activity_iid: str, **fields) -> Activity:
        """
        Aktualizuje wybrane pola aktywności identyfikowanej przez iid.
        Dozwolone pola: activity_type, distance_km, ai_comment, pace,
                        heart_rate_avg, calories, total_points itp.
        Rzuca ValueError jeśli aktywność nie istnieje.
        """
        activity = self.get_activity_by_iid(activity_iid)
        if not activity:
            raise ValueError(f"Activity with iid={activity_iid} not found")

        allowed = {
            "activity_type", "distance_km", "weight_kg", "elevation_m",
            "time_minutes", "pace", "heart_rate_avg", "calories",
            "base_points", "weight_bonus_points", "elevation_bonus_points",
            "mission_bonus_points", "total_points", "ai_comment",
            "challenge_id", "special_mission_id",
        }
        invalid = set(fields) - allowed
        if invalid:
            raise ValueError(f"Niedozwolone pola do aktualizacji: {invalid}")

        for field, value in fields.items():
            setattr(activity, field, value)

        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)
        return activity

    def delete_activity(self, activity_iid: str) -> bool:
        """Usuwa aktywność z bazy. Zwraca True jeśli istniała, False jeśli nie."""
        activity = self.get_activity_by_iid(activity_iid)
        if not activity:
            return False
        self.db.delete(activity)
        self.db.commit()
        return True

    def get_rankings(self, limit: int = 10) -> list[dict]:
        rows = self.db.execute(
            text(
                """
                SELECT id, discord_id, display_name, total_activities,
                       total_distance_km, total_points, base_points,
                       weight_bonus_points, elevation_bonus_points,
                       mission_bonus_points, last_activity_at
                FROM user_rankings
                ORDER BY total_points DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings()

        return [dict(row) for row in rows]

    def list_active_missions(self) -> list[SpecialMission]:
        from datetime import datetime
        now = datetime.utcnow()
        return (
            self.db.query(SpecialMission)
            .filter(SpecialMission.is_active.is_(True))
            .filter(SpecialMission.valid_from <= now)
            .filter(SpecialMission.valid_until >= now)
            .order_by(SpecialMission.valid_until.asc())
            .all()
        )
