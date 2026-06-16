from dataclasses import field
from venv import logger
import json

from discord import Activity
from pydantic import BaseModel, Field
from datetime import datetime

from langchain_core.output_parsers import StrOutputParser

from ai.models import get_chat_model
from ai.prompts import build_activity_text_only_analyze_prompt, build_activity_text_only_analyze_prompt, build_message_and_picture_analyze_prompt, build_progress_comment_prompt

from libs.shared.schemas.activity import ActivityRead





class ActivityParams(BaseModel):
    activity_type: str
    distance_km: float = Field(gt=0)
    weight_kg: float | None = None
    elevation_m: int | None = None
    time_minutes: int | None = None
    pace: str | None = None
    heart_rate_avg: int | None = None
    calories: int | None = None


async def analyze_message_and_picture(
    user_message: str,
    picture_url: str,
    activities_context: str | None = None,
) -> ActivityParams:

    openai = get_chat_model('gpt-4o-mini')
    gemini = get_chat_model("gemini-3.1-flash-lite")
    prompt = build_message_and_picture_analyze_prompt()
    llm = openai.with_fallbacks([gemini])
    structured_data = llm.with_structured_output(ActivityParams)
    chain = prompt | structured_data
    return await chain.ainvoke(
        {
            "user_message": user_message,
            "picture_url": picture_url,
            "activities_context": activities_context or "",
        }
    )


async def analyze_message_only(user_message: str) -> ActivityParams:
 
    openai = get_chat_model('gpt-4o-mini')
    gemini = get_chat_model("gemini-3.1-flash-lite")
    prompt = build_activity_text_only_analyze_prompt()
    llm = openai.with_fallbacks([gemini])
    structured_data = llm.with_structured_output(ActivityParams)
    chain = prompt | structured_data
    return await chain.ainvoke(
        {
            "user_message": user_message,
        }
    )




async def generate_activity_comment(
    new_activity: ActivityParams,
    historic_activities: list[ActivityRead],
    user_display_name: str,
    meets_minimum_distance_rule: bool = True,
    comment_style: str = "usmc_drill_sergeant",
) -> str:
    openai = get_chat_model("gpt-4o-mini", temperature=0.7)
    gemini = get_chat_model("gemini-3.1-flash-lite", temperature=0.7)

    llm = openai.with_fallbacks([gemini])

    prompt = build_progress_comment_prompt()

    chain = prompt | llm | StrOutputParser()

    new_activity_json = new_activity.model_dump_json(indent=2)

    historic_activities_json = (
        json.dumps(
            [
                activity.model_dump(mode="json")
                for activity in historic_activities
            ],
            ensure_ascii=False,
            indent=2,
        )
        if historic_activities
        else "No activity history available"
    )

    comment = await chain.ainvoke(
        {
            "user_display_name": user_display_name,
            "comment_style": comment_style,
            "new_activity": new_activity_json,
            "historic_activities": historic_activities_json,
            "meets_minimum_distance_rule": meets_minimum_distance_rule,
        }
    )

    return comment.strip()
# # Backward-compatible aliases for older imports kept during refactor.
# anlize_message_and_picture = analyze_message_and_picture
# anlize_message_only = analyze_message_only
# generete_activity_coment = generate_activity_comment