"""Warstwa serwisowa AI spinajaca modele, chainy i narzedzia."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_activity_graph = None


def _get_activity_graph() -> Any:
	global _activity_graph
	if _activity_graph is None:
		# Lazy import prevents module-load failure when graph deps are unavailable.
		from ai.graphs import build_activity_state_graph

		_activity_graph = build_activity_state_graph()
	return _activity_graph


def _request_to_graph_state(request: Any) -> dict[str, Any]:
	# Accepts dataclass request object from bot layer or plain dict payload.
	if isinstance(request, dict):
		image_urls = request.get("image_urls") or []
		return {
			"message_id": request.get("message_id"),
			"author_id": request.get("author_id"),
			"author_display_name": request.get("author_display_name"),
			"channel_id": request.get("channel_id"),
			"content": request.get("content") or "",
			"image_url": image_urls[0] if image_urls else None,
			"created_at": request.get("created_at"),
		}

	image_urls = getattr(request, "image_urls", []) or []
	return {
		"message_id": getattr(request, "message_id", None),
		"author_id": getattr(request, "author_id", None),
		"author_display_name": getattr(request, "author_display_name", None),
		"channel_id": getattr(request, "channel_id", None),
		"content": getattr(request, "content", "") or "",
		"image_url": image_urls[0] if image_urls else None,
		"created_at": getattr(request, "created_at", None),
	}


async def invoke_message_analysis(request: Any) -> dict[str, Any]:
	"""Runs the activity graph for a Discord message payload."""
	graph = _get_activity_graph()
	state = _request_to_graph_state(request)

	if hasattr(graph, "ainvoke"):
		result = await graph.ainvoke(state)
	else:
		result = graph.invoke(state)

	if not isinstance(result, dict):
		return {"status": "processed"}

	return {
		"status": str(result.get("status", "processed")),
		"reaction": result.get("reaction", "✅"),
		"reply_text": result.get("reply_text") or result.get("comment"),
		"reply_embed": result.get("reply_embed"),
	}


async def process_discord_message(request: Any) -> dict[str, Any]:
	"""Compatibility entrypoint used by bot.message_handler."""
	try:
		return await invoke_message_analysis(request)
	except Exception:
		logger.exception("invoke_message_analysis failed")
		return {"status": "ignored"}

