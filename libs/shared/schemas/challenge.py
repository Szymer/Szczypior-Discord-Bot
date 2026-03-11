from datetime import datetime

from pydantic import BaseModel


class ChallengeCreate(BaseModel):
    name: str
    description: str | None = None
    start_date: datetime
    end_date: datetime
    rules: dict | None = None
    is_active: bool = True


class ChallengeRead(BaseModel):
    id: int
    name: str
    description: str | None
    start_date: datetime
    end_date: datetime
    rules: dict | None
    is_active: bool
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
