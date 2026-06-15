"""Schematy danych wejsciowych i wyjsciowych."""

from typing import NotRequired, TypedDict

from libs.shared.schemas.activity import ActivityRead





class ActivityState(TypedDict):
    activity_type: NotRequired[str]
    distance_km: NotRequired[float]
    weight_kg: NotRequired[float | None]
    elevation_m: NotRequired[int | None]
    time_minutes: NotRequired[int | None]
    pace: NotRequired[str | None]
    heart_rate_avg: NotRequired[int | None]
    calories: NotRequired[int | None]
    message_id: str
    author_id: str
    author_display_name: str
    channel_id: str
    content: str
    image_url: NotRequired[str | None]
    created_at: NotRequired[str | None]
    comment: NotRequired[str]
    historic_activities: NotRequired[list[ActivityRead]]
    