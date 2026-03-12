from datetime import datetime

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Activity, SpecialMission, User
from app.schemas.activity import ActivityCreate
from app.schemas.user import UserUpsert


class DBManager:
    def __init__(self, db: Session):
        self.db = db

    def health_check(self) -> bool:
        self.db.execute(text("SELECT 1"))
        return True

    def upsert_user(self, payload: UserUpsert) -> User:
        existing = self.db.query(User).filter(User.discord_id == payload.discord_id).first()
        if existing:
            existing.display_name = payload.display_name
            existing.username = payload.username
            existing.avatar_url = payload.avatar_url
            self.db.add(existing)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        created = User(
            discord_id=payload.discord_id,
            display_name=payload.display_name,
            username=payload.username,
            avatar_url=payload.avatar_url,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(created)
        self.db.commit()
        self.db.refresh(created)
        return created

    def _resolve_matching_mission(self, payload: ActivityCreate) -> SpecialMission | None:
        query = (
            self.db.query(SpecialMission)
            .filter(SpecialMission.is_active.is_(True))
            .filter(SpecialMission.valid_from <= payload.created_at)
            .filter(SpecialMission.valid_until >= payload.created_at)
        )

        missions = query.all()
        for mission in missions:
            if mission.activity_type_filter and mission.activity_type_filter != payload.activity_type:
                continue
            if mission.min_distance_km is not None and payload.distance_km < float(mission.min_distance_km):
                continue
            if mission.min_time_minutes is not None:
                if payload.time_minutes is None or payload.time_minutes < mission.min_time_minutes:
                    continue
            return mission
        return None

    def create_activity(self, payload: ActivityCreate) -> Activity:
        user = self.upsert_user(
            UserUpsert(discord_id=payload.discord_id, display_name=payload.display_name)
        )

        mission = self._resolve_matching_mission(payload)
        mission_bonus_points = mission.bonus_points if mission else 0
        total_points = (
            payload.base_points
            + payload.weight_bonus_points
            + payload.elevation_bonus_points
            + mission_bonus_points
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
            special_mission_id=mission.id if mission else None,
            mission_bonus_points=mission_bonus_points,
            total_points=total_points,
            created_at=payload.created_at,
            message_id=payload.message_id,
            message_timestamp=payload.message_timestamp,
            ai_comment=payload.ai_comment,
        )

        self.db.add(row)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Activity with this IID already exists")

        self.db.refresh(row)
        return row

    def list_active_missions(self) -> list[SpecialMission]:
        now = datetime.utcnow()
        return (
            self.db.query(SpecialMission)
            .filter(SpecialMission.is_active.is_(True))
            .filter(SpecialMission.valid_from <= now)
            .filter(SpecialMission.valid_until >= now)
            .order_by(SpecialMission.valid_until.asc())
            .all()
        )

    def get_user_history(self, discord_id: str, limit: int = 20) -> list[Activity]:
        return (
            self.db.query(Activity)
            .join(User, User.id == Activity.user_id)
            .filter(User.discord_id == discord_id)
            .order_by(Activity.created_at.desc())
            .limit(limit)
            .all()
        )

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
