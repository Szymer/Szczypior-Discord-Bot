from pydantic import BaseModel


class ActivityRuleCreate(BaseModel):
    challenge_id: int
    activity_type: str
    emoji: str = "🏃"
    display_name: str
    base_points: int = 0
    unit: str = "km"
    min_distance: float = 0.0
    bonuses: list[str] = []


class ActivityRuleRead(BaseModel):
    id: int
    challenge_id: int
    activity_type: str
    emoji: str
    display_name: str
    base_points: int
    unit: str
    min_distance: float
    bonuses: list[str]

    model_config = {"from_attributes": True}
