from datetime import datetime

from pydantic import BaseModel, Field


class ActivityCreate(BaseModel):
    discord_id: str
    display_name: str
    iid: str
    activity_type: str
    distance_km: float = Field(gt=0)
    base_points: int = Field(ge=0)
    weight_kg: float | None = None
    elevation_m: int | None = None
    weight_bonus_points: int = Field(default=0, ge=0)
    elevation_bonus_points: int = Field(default=0, ge=0)
    mission_bonus_points: int = Field(default=0, ge=0)
    total_points: int = Field(ge=0)
    special_mission_id: int | None = None
    challenge_id: int | None = None
    time_minutes: int | None = None
    pace: str | None = None
    heart_rate_avg: int | None = None
    calories: int | None = None
    created_at: datetime
    message_id: str | None = None
    message_timestamp: str | None = None
    ai_comment: str | None = None


class ActivityRead(BaseModel):
    id: int
    iid: str
    activity_type: str
    distance_km: float
    base_points: int
    weight_bonus_points: int
    elevation_bonus_points: int
    mission_bonus_points: int
    total_points: int
    special_mission_id: int | None
    challenge_id: int | None
    created_at: datetime
    ai_comment: str | None

    model_config = {"from_attributes": True}


class UserRankingRead(BaseModel):
    id: int
    discord_id: str
    display_name: str
    total_activities: int
    total_distance_km: float
    total_points: int
    base_points: int
    weight_bonus_points: int
    elevation_bonus_points: int
    mission_bonus_points: int
    last_activity_at: datetime | None

    model_config = {"from_attributes": True}
