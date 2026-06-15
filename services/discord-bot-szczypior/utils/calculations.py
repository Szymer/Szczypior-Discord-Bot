"""Utilities for calculating points and building ActivityCreate payloads."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any, Mapping, Optional

from pydantic import BaseModel

try:
	from api.api_menager import APIManager
except ImportError:
	from services.discord_bot_szczypior.api.api_menager import APIManager  # type: ignore

from bot.config_manager import config_manager
from bot.constants import ACTIVITY_TYPES

from libs.shared.schemas.activity import ActivityCreate


ACTIVITY_TYPE_ALIASES: dict[str, str] = {
	"running_terrain": "bieganie_teren",
	"running_treadmill": "bieganie_bieznia",
	"swimming": "plywanie",
	"cycling": "rower",
	"walking": "spacer",
	"other_cardio": "cardio",
}


def _normalize_bonus_name(value: str) -> str:
	normalized = unicodedata.normalize("NFD", value)
	without_diacritics = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
	return without_diacritics.strip().lower()


def _has_bonus(bonuses: list[str], bonus_name: str) -> bool:
	expected = _normalize_bonus_name(bonus_name)
	return any(_normalize_bonus_name(item) == expected for item in bonuses)


def _to_float(value: Any, default: float = 0.0) -> float:
	try:
		return float(value)
	except (TypeError, ValueError):
		return default


def _to_int(value: Any, default: int = 0) -> int:
	try:
		return int(value)
	except (TypeError, ValueError):
		return default


def _parse_time_to_minutes(raw_time: Any) -> Optional[int]:
	if raw_time in (None, ""):
		return None

	if isinstance(raw_time, (int, float)):
		if raw_time < 0:
			return None
		return int(raw_time)

	text = str(raw_time).strip().lower()
	if not text:
		return None

	# HH:MM:SS or MM:SS
	if ":" in text:
		parts = text.split(":")
		if len(parts) == 2 and all(p.isdigit() for p in parts):
			mm, ss = int(parts[0]), int(parts[1])
			return mm + (1 if ss >= 30 else 0)
		if len(parts) == 3 and all(p.isdigit() for p in parts):
			hh, mm, ss = int(parts[0]), int(parts[1]), int(parts[2])
			return hh * 60 + mm + (1 if ss >= 30 else 0)

	# "45 min", "1h 20m", "90"
	hour_match = re.search(r"(\d+)\s*h", text)
	minute_match = re.search(r"(\d+)\s*m", text)
	if hour_match or minute_match:
		hours = int(hour_match.group(1)) if hour_match else 0
		minutes = int(minute_match.group(1)) if minute_match else 0
		return hours * 60 + minutes

	if text.isdigit():
		return int(text)

	return None


def _normalize_points_rules(raw_points_rules: Optional[dict[str, Any]]) -> dict[str, Any]:
	default_rules = config_manager.get_points_rules()
	if not isinstance(raw_points_rules, dict):
		raw_points_rules = {}

	weight_raw = raw_points_rules.get("weight_bonus")
	elevation_raw = raw_points_rules.get("elevation_bonus")

	return {
		"weight_bonus": {
			"min_weight_kg": _to_float(
				weight_raw.get("min_weight_kg") if isinstance(weight_raw, dict) else None,
				_to_float(default_rules["weight_bonus"].get("min_weight_kg", 5), 5),
			),
			"distance_points_multiplier": _to_float(
				weight_raw.get("distance_points_multiplier") if isinstance(weight_raw, dict) else None,
				_to_float(default_rules["weight_bonus"].get("distance_points_multiplier", 1.5), 1.5),
			),
		},
		"elevation_bonus": {
			"meters_step": _to_int(
				elevation_raw.get("meters_step") if isinstance(elevation_raw, dict) else None,
				_to_int(default_rules["elevation_bonus"].get("meters_step", 50), 50),
			),
			"points_per_step": _to_int(
				elevation_raw.get("points_per_step") if isinstance(elevation_raw, dict) else None,
				_to_int(default_rules["elevation_bonus"].get("points_per_step", 500), 500),
			),
		},
	}


def _resolve_activity_types(api_manager: Optional[APIManager], challenge_id: Optional[int]) -> dict[str, Any]:
	if api_manager is None or challenge_id is None:
		return ACTIVITY_TYPES

	try:
		rules = api_manager.get_activity_rules(challenge_id)
	except Exception:
		return ACTIVITY_TYPES

	mapped = {
		rule.activity_type: {
			"emoji": rule.emoji,
			"base_points": rule.base_points,
			"unit": rule.unit,
			"min_distance": float(rule.min_distance),
			"bonuses": rule.bonuses,
			"display_name": rule.display_name,
		}
		for rule in rules
	}
	return mapped or ACTIVITY_TYPES


def _resolve_points_rules(api_manager: Optional[APIManager], challenge_id: Optional[int]) -> dict[str, Any]:
	if api_manager is None or challenge_id is None:
		return _normalize_points_rules(None)

	raw_points_rules: Optional[dict[str, Any]] = None
	try:
		challenge = api_manager.get_challenge(challenge_id)
		if isinstance(challenge.rules, dict):
			maybe_rules = challenge.rules.get("points_rules")
			if isinstance(maybe_rules, dict):
				raw_points_rules = maybe_rules
	except Exception:
		pass

	return _normalize_points_rules(raw_points_rules)


def _coerce_ai_payload(ai_response: BaseModel | Mapping[str, Any]) -> dict[str, Any]:
	if isinstance(ai_response, BaseModel):
		return ai_response.model_dump()
	return dict(ai_response)


def calculate_points_breakdown(
	*,
	activity_type: str,
	distance_km: float,
	weight_kg: Optional[float],
	elevation_m: Optional[int],
	activity_types: dict[str, Any],
	points_rules: dict[str, Any],
) -> dict[str, int]:
	"""Pure function calculating points from resolved rules."""
	resolved_type = ACTIVITY_TYPE_ALIASES.get(activity_type, activity_type)
	if resolved_type not in activity_types:
		raise ValueError(f"Unknown activity type: {activity_type}")

	activity_info = activity_types[resolved_type]
	min_distance = float(activity_info.get("min_distance", 0) or 0)
	if distance_km < min_distance:
		display_name = activity_info.get("display_name", resolved_type)
		raise ValueError(f"Minimal distance for {display_name}: {min_distance} km")

	base_points_rate = int(activity_info.get("base_points", 0))
	base_points = int(distance_km * base_points_rate)
	bonuses = activity_info.get("bonuses", []) or []

	weight_bonus_cfg = points_rules.get("weight_bonus", {})
	min_weight_kg = float(weight_bonus_cfg.get("min_weight_kg", 5))
	distance_multiplier = float(weight_bonus_cfg.get("distance_points_multiplier", 1.5))
	weight_bonus_points = 0
	if (
		weight_kg
		and weight_kg >= min_weight_kg
		and _has_bonus(bonuses, "obciazenie")
		and distance_multiplier > 1
	):
		weight_bonus_points = int(base_points * (distance_multiplier - 1))

	elevation_bonus_cfg = points_rules.get("elevation_bonus", {})
	meters_step = int(elevation_bonus_cfg.get("meters_step", 50))
	points_per_step = int(elevation_bonus_cfg.get("points_per_step", 500))
	elevation_bonus_points = 0
	if (
		elevation_m
		and elevation_m > 0
		and _has_bonus(bonuses, "przewyzszenie")
		and meters_step > 0
	):
		elevation_bonus_points = int(elevation_m // meters_step) * points_per_step

	total_points = base_points + weight_bonus_points + elevation_bonus_points
	if total_points < 1:
		base_points = 1
		total_points = 1

	return {
		"base_points": base_points,
		"weight_bonus_points": weight_bonus_points,
		"elevation_bonus_points": elevation_bonus_points,
		"total_points": total_points,
	}


def build_activity_create_from_ai_response(
	*,
	ai_response: BaseModel | Mapping[str, Any],
	discord_id: str,
	display_name: str,
	iid: str,
	created_at: datetime,
	api_manager: Optional[APIManager] = None,
	challenge_id: Optional[int] = None,
	message_id: Optional[str] = None,
	message_timestamp: Optional[str] = None,
	special_mission_id: Optional[int] = None,
	mission_bonus_points: int = 0,
	ai_comment: Optional[str] = None,
) -> ActivityCreate:
	"""Build ActivityCreate from AI output using rules fetched through API."""
	data = _coerce_ai_payload(ai_response)

	raw_activity_type = data.get("typ_aktywnosci") or data.get("activity_type")
	if not raw_activity_type:
		raise ValueError("AI response does not contain activity type")

	activity_type = ACTIVITY_TYPE_ALIASES.get(str(raw_activity_type), str(raw_activity_type))

	raw_distance = data.get("dystans") if data.get("dystans") is not None else data.get("distance_km")
	distance_km = _to_float(raw_distance, -1)
	if distance_km <= 0:
		raise ValueError("AI response does not contain valid distance")

	raw_weight = data.get("obciazenie") if data.get("obciazenie") is not None else data.get("weight_kg")
	weight_kg = _to_float(raw_weight, 0.0) or None

	raw_elevation = data.get("przewyzszenie") if data.get("przewyzszenie") is not None else data.get("elevation_m")
	elevation_m = _to_int(raw_elevation, 0) or None

	raw_time = data.get("czas") if data.get("czas") is not None else data.get("time_minutes")
	time_minutes = _parse_time_to_minutes(raw_time)

	activity_types = _resolve_activity_types(api_manager, challenge_id)
	points_rules = _resolve_points_rules(api_manager, challenge_id)
	breakdown = calculate_points_breakdown(
		activity_type=activity_type,
		distance_km=distance_km,
		weight_kg=weight_kg,
		elevation_m=elevation_m,
		activity_types=activity_types,
		points_rules=points_rules,
	)

	total_points = breakdown["total_points"] + max(0, mission_bonus_points)

	return ActivityCreate(
		discord_id=discord_id,
		display_name=display_name,
		iid=iid,
		activity_type=activity_type,
		distance_km=distance_km,
		base_points=breakdown["base_points"],
		weight_kg=weight_kg,
		elevation_m=elevation_m,
		weight_bonus_points=breakdown["weight_bonus_points"],
		elevation_bonus_points=breakdown["elevation_bonus_points"],
		mission_bonus_points=max(0, mission_bonus_points),
		total_points=total_points,
		special_mission_id=special_mission_id,
		challenge_id=challenge_id,
		time_minutes=time_minutes,
		pace=data.get("tempo") or data.get("pace"),
		heart_rate_avg=_to_int(data.get("puls_sredni") if data.get("puls_sredni") is not None else data.get("heart_rate_avg"), 0)
		or None,
		calories=_to_int(data.get("kalorie") if data.get("kalorie") is not None else data.get("calories"), 0)
		or None,
		created_at=created_at,
		message_id=message_id,
		message_timestamp=message_timestamp,
		ai_comment=ai_comment,
	)

