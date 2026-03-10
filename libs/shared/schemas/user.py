"""User schema placeholder shared across services."""

from pydantic import BaseModel


class UserSchema(BaseModel):
    user_id: str
    username: str
