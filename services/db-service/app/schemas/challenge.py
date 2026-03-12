from datetime import datetime
from typing import Any

from pydantic import BaseModel, model_validator

from app.schemas.activity_rule import ActivityRulePayload


class ChallengeCreate(BaseModel):
    name: str
    description: str | None = None
    start_date: datetime
    end_date: datetime
    rules: dict | None = None
    activity_rules: list[ActivityRulePayload] | None = None
    is_active: bool = True
    discord_channel_id: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_activity_rules(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        raw_rules = data.get("activity_rules")
        if not isinstance(raw_rules, dict):
            return data

        normalized_rules: list[dict[str, Any]] = []
        for activity_type, definition in raw_rules.items():
            if not isinstance(definition, dict):
                continue
            normalized = dict(definition)
            normalized.setdefault("activity_type", activity_type)
            normalized_rules.append(normalized)

        updated = dict(data)
        updated["activity_rules"] = normalized_rules
        return updated


class ChallengeRead(BaseModel):
    id: int
    name: str
    description: str | None
    start_date: datetime
    end_date: datetime
    rules: dict | None
    is_active: bool
    discord_channel_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChallengeParticipantCreate(BaseModel):
    discord_id: str
    challenge_id: int


class ChallengeParticipantRead(BaseModel):
    id: int
    challenge_id: int
    user_id: int
    joined_at: datetime

    model_config = {"from_attributes": True}
