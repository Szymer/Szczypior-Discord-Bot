"""Conversation schema placeholder shared across services."""

from typing import List

from pydantic import BaseModel

from .message import MessageSchema


class ConversationSchema(BaseModel):
    messages: List[MessageSchema]
