from datetime import datetime

from pydantic import BaseModel


class AirsoftEventCreate(BaseModel):
    name: str
    description: str | None = None
    organizer: str | None = None
    start_date: datetime
    end_date: datetime | None = None
    location: str
    event_type: str
    price: float | None = None
    currency: str = "PLN"
    event_url: str | None = None
    discord_channel_id: str | None = None


class AirsoftEventRead(BaseModel):
    id: int
    name: str
    description: str | None
    organizer: str | None
    start_date: datetime
    end_date: datetime | None
    location: str
    event_type: str
    price: float | None
    currency: str
    event_url: str | None
    discord_channel_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventRegistrationCreate(BaseModel):
    discord_id: str
    event_id: int


class EventRegistrationRead(BaseModel):
    id: int
    user_id: int
    event_id: int
    registered_at: datetime

    model_config = {"from_attributes": True}
