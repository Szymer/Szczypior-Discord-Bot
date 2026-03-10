from datetime import datetime

from pydantic import BaseModel


class MissionRead(BaseModel):
    id: int
    name: str
    description: str | None
    emoji: str | None
    bonus_points: int
    min_distance_km: float | None
    min_time_minutes: int | None
    activity_type_filter: str | None
    valid_from: datetime
    valid_until: datetime
    is_active: bool

    model_config = {"from_attributes": True}
