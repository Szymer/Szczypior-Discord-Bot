from datetime import datetime

from pydantic import BaseModel


class UserBase(BaseModel):
    discord_id: str
    display_name: str
    username: str | None = None
    avatar_url: str | None = None


class UserUpsert(UserBase):
    pass


class UserRead(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
