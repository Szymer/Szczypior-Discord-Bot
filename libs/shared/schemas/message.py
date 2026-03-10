"""Message schema placeholder shared across services."""

from pydantic import BaseModel


class MessageSchema(BaseModel):
    message_id: str
    content: str
