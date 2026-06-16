from __future__ import annotations

from datetime import datetime
import logging
from typing import Any, Awaitable, Callable, Literal


from langgraph.graph import StateGraph, START, END

from ai.chains import (
    ActivityParams,
    analyze_message_and_picture,
    analyze_message_only,
    generate_activity_comment,
)
from api.api_menager import APIManager, get_user_activity_history, save_activity

from libs.shared.schemas.activity import ActivityRead
from ai.schemas import ActivityState
from utils.calculations import build_activity_create_from_ai_response, _resolve_activity_types  
logger = logging.getLogger(__name__)


def _parse_created_at(value: str | None) -> datetime:
    if not value:
        raise ValueError("created_at is required to build ActivityCreate payload")
    return datetime.fromisoformat(value)


def _build_iid(message_id: str, created_at: datetime) -> str:
    return f"{int(created_at.timestamp())}_{message_id}"


    
    
def build_activity_state_graph() -> StateGraph[ActivityState]:
    
    graph = StateGraph(ActivityState)
    api_manager: APIManager | None = None
    channel_to_challenge_cache: dict[str, int | None] = {}

    def get_api_manager() -> APIManager | None:
        nonlocal api_manager
        if api_manager is not None:
            return api_manager

        try:
            api_manager = APIManager()
        except Exception:
            logger.warning("Could not initialize APIManager in activity graph", exc_info=True)
            return None

        return api_manager

    def resolve_challenge_id(channel_id: str | None) -> int | None:
        if not channel_id:
            return None

        if channel_id in channel_to_challenge_cache:
            return channel_to_challenge_cache[channel_id]

        api = get_api_manager()
        if api is None:
            channel_to_challenge_cache[channel_id] = None
            return None

        try:
            active_challenges = api.get_active_challenges()
        except Exception:
            logger.warning(
                "Could not fetch active challenges for channel mapping",
                exc_info=True,
                extra={"channel_id": channel_id},
            )
            channel_to_challenge_cache[channel_id] = None
            return None

        for challenge in active_challenges:
            if challenge.discord_channel_id:
                channel_to_challenge_cache[str(challenge.discord_channel_id)] = challenge.id

        channel_to_challenge_cache.setdefault(channel_id, None)
        return channel_to_challenge_cache[channel_id]

    def image_route(
        state: ActivityState,
    ) -> Literal["process_activity_with_picture_node", "process_activity_text_only_node"]:
        if state.get("image_url"):
            return "process_activity_with_picture_node"
        return "process_activity_text_only_node"
    
    def  min_distance_rule_route( state: ActivityState,) -> Literal["save_activity", "end"]:
        if state.get("meets_minimum_distance_rule", True):
            return "save_activity"
        return "end"
    async def process_activity_with_picture_node(state: ActivityState) -> ActivityState:
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                activity = await analyze_message_and_picture(
                    picture_url=state.get("image_url"),
                    user_message=state["content"],
                )
                break
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "process_activity_with_picture_node failed",
                    exc_info=True,
                    extra={
                        "attempt": attempt,
                        "max_attempts": 3,
                        "message_id": state.get("message_id"),
                    },
                )
        else:
            raise RuntimeError("process_activity_with_picture_node failed after 3 attempts") from last_error
        
        return {
            "activity_type": activity.activity_type,
            "distance_km": activity.distance_km,
            "weight_kg": activity.weight_kg,
            "elevation_m": activity.elevation_m,
            "time_minutes": activity.time_minutes,
            "pace": activity.pace,
            "heart_rate_avg": activity.heart_rate_avg,
            "calories": activity.calories,
            "message_id": state["message_id"],
            "author_id": state["author_id"],
            "author_display_name": state["author_display_name"],
            "channel_id": state["channel_id"],
            "content": state["content"],
            "image_url": state.get("image_url"),
            "created_at": state.get("created_at"),
        }

    async def process_activity_text_only_node(state: ActivityState) -> ActivityState:
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                activity = await analyze_message_only(
                    user_message=state["content"],
                )
                break
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "process_activity_text_only_node failed",
                    exc_info=True,
                    extra={
                        "attempt": attempt,
                        "max_attempts": 3,
                        "message_id": state.get("message_id"),
                    },
                )
        else:
            raise RuntimeError("process_activity_text_only_node failed after 3 attempts") from last_error
        
        return {
            "activity_type": activity.activity_type,
            "distance_km": activity.distance_km,
            "weight_kg": activity.weight_kg,
            "elevation_m": activity.elevation_m,
            "time_minutes": activity.time_minutes,
            "pace": activity.pace,
            "heart_rate_avg": activity.heart_rate_avg,
            "calories": activity.calories,
            "message_id": state["message_id"],
            "author_id": state["author_id"],
            "author_display_name": state["author_display_name"],
            "channel_id": state["channel_id"],
            "content": state["content"],
            "created_at": state.get("created_at"),
        }

    def get_activity_history_node(state: ActivityState) -> ActivityState:
        history = get_user_activity_history(state["author_id"])
        return {"historic_activities": history}

    def validate_activity_distance_rule(state: ActivityState) -> ActivityState:
        distance_km = state.get("distance_km")
        activity_type = state.get("activity_type", "").lower() if state.get("activity_type") else ""
        activity_rules = _resolve_activity_types(api_manager=get_api_manager(), challenge_id=resolve_challenge_id(state.get("channel_id")))
        if distance_km is not None and distance_km <= 0:
            state["meets_minimum_distance_rule"] = False
        if distance_km is not None and activity_type in activity_rules:
            min_distance = activity_rules[activity_type].get("min_distance", 0)
            state["meets_minimum_distance_rule"] = distance_km >= min_distance
        else:
            state["meets_minimum_distance_rule"] = True  
        return state
    
    async def generate_comment_node(state: ActivityState) -> ActivityState:
        historic_activities = state.get("historic_activities", [])
        comment = await generate_activity_comment(
            new_activity=ActivityParams(
                activity_type=state["activity_type"],
                distance_km=state["distance_km"],
                weight_kg=state["weight_kg"],
                elevation_m=state["elevation_m"],
                time_minutes=state["time_minutes"],
                pace=state["pace"],
                heart_rate_avg=state["heart_rate_avg"],
                calories=state["calories"],
            ),
            historic_activities=historic_activities,
            user_display_name=state["author_display_name"],
            meets_minimum_distance_rule=state.get("meets_minimum_distance_rule", True),
        )
        logger.info("Generated activity comment", extra={"comment": comment})
        return {"comment": comment}

    def save_activity_to_db_node(state: ActivityState) -> dict[str, Any]:
        created_at = _parse_created_at(state.get("created_at"))
        iid = _build_iid(state["message_id"], created_at)
        challenge_id = resolve_challenge_id(state.get("channel_id"))
        api = get_api_manager()
        activity_create = build_activity_create_from_ai_response(
            ai_response=state,
            discord_id=state["author_id"],
            display_name=state["author_display_name"],
            iid=iid,
            created_at=created_at,
            api_manager=api,
            challenge_id=challenge_id,
            message_id=state["message_id"],
            message_timestamp=str(int(created_at.timestamp())),
            ai_comment=state.get("comment"),
        )
        saved_activity = save_activity(activity_create)
        comment = state.get("comment", "")
        logger.info(
            "Activity saved",
            extra={
                "saved_activity_id": getattr(saved_activity, "id", None),
                "saved_activity_iid": getattr(saved_activity, "iid", None),
                "total_points": getattr(saved_activity, "total_points", None),
            },
        )
        return {
            "comment": comment,
            "status": "processed",
            "reaction": "✅",
            "reply_text": comment,
            "saved_activity_id": getattr(saved_activity, "id", None),
            "saved_activity_iid": getattr(saved_activity, "iid", iid),
            "total_points": getattr(saved_activity, "total_points", activity_create.total_points),
        }

    graph.add_node("process_activity_with_picture_node", process_activity_with_picture_node)
    graph.add_node("process_activity_text_only", process_activity_text_only_node)
    graph.add_node("get_activity_history", get_activity_history_node)
    graph.add_node("validate_distance_rule", validate_activity_distance_rule)
    graph.add_node("generate_comment", generate_comment_node)
    graph.add_node("save_activity", save_activity_to_db_node)
    
    graph.add_conditional_edges(
        START,
        image_route,
        {
            "process_activity_with_picture_node": "process_activity_with_picture_node",
            "process_activity_text_only_node": "process_activity_text_only",
        },
    )

    graph.add_edge("process_activity_with_picture_node", "get_activity_history")
    graph.add_edge("process_activity_text_only", "get_activity_history")
    graph.add_edge("get_activity_history", "validate_distance_rule")
    graph.add_edge("validate_distance_rule", "generate_comment")
    graph.add_conditional_edges(
       "generate_comment",
       min_distance_rule_route,
       
        {
            "save_activity": "save_activity",
            "end": END,
        },
    )
    graph.add_edge("save_activity", END)
    compiled_graph = graph.compile()

    logger.debug("Activity graph mermaid definition\n%s", compiled_graph.get_graph().draw_mermaid())
    return compiled_graph



