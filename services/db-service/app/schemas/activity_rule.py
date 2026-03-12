from pydantic import BaseModel, Field


class ActivityRulePayload(BaseModel):
    activity_type: str
    emoji: str = "🏃"
    display_name: str
    base_points: int = 0
    unit: str = "km"
    min_distance: float = 0.0
    bonuses: list[str] = Field(default_factory=list)


class ActivityRuleCreate(ActivityRulePayload):
    challenge_id: int


class ActivityRulePatchPayload(BaseModel):
    activity_type: str
    emoji: str | None = None
    display_name: str | None = None
    base_points: int | None = None
    unit: str | None = None
    min_distance: float | None = None
    bonuses: list[str] | None = None


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
