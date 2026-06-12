from pydantic import BaseModel, Field
from datetime import datetime

from ai.models import get_chat_model
from ai.prompts import build_message_and_picture_analyze_prompt




class Activity(BaseModel):
    activity_type: str
    distance_km: float = Field(gt=0)
    weight_kg: float | None = None
    elevation_m: int | None = None
    time_minutes: int | None = None
    pace: str | None = None
    heart_rate_avg: int | None = None
    calories: int | None = None









async def anlize_message_and_picture(user_mesage: str, pict_url: str, context: str) -> Activity:
    openai = get_chat_model('gpt-4o-mini')
    gemini = get_chat_model("gemini-3.1-flash-lite")
    prompt = build_message_and_picture_analyze_prompt()
    llm = openai.with_fallbacks([gemini])
    structured_data = llm.with_structured_output(Activity)
    chain = prompt | structured_data
    return await chain.ainvoke(
        {
            "user_mesage": user_mesage,
            "pict_url": pict_url,
            "context": context,
        }
    )
