"""Client HTTP do komunikacji z db-service."""

from __future__ import annotations

import json
from typing import Any
from urllib import error, parse, request

from config_manager import config_manager
from libs.shared.schemas.activity import ActivityCreate, ActivityRead, ActivityUpdate, UserRankingRead
from libs.shared.schemas.activity_rule import ActivityRuleRead
from libs.shared.schemas.challenge import ChallengeRead
from libs.shared.schemas.event import AirsoftEventRead


class APIManagerError(Exception):
	"""Błąd warstwy komunikacji z db-service."""


class APIManagerHTTPError(APIManagerError):
	"""Błąd HTTP zwrócony przez db-service."""

	def __init__(self, status_code: int, detail: str, url: str):
		self.status_code = status_code
		self.detail = detail
		self.url = url
		super().__init__(f"HTTP {status_code} for {url}: {detail}")


class APIManager:
	"""Klient API dla operacji na db-service."""

	def __init__(self, base_url: str | None = None, timeout_seconds: int = 15):
		configured_base_url = base_url or config_manager.get_db_service_base_url()
		self.api_base_url = self._normalize_api_base_url(configured_base_url)
		self.timeout_seconds = timeout_seconds

	def __enter__(self) -> "APIManager":
		return self

	def __exit__(self, exc_type, exc, tb) -> None:
		self.close()

	@staticmethod
	def _normalize_api_base_url(base_url: str) -> str:
		normalized = base_url.rstrip("/")
		if normalized.endswith("/api/v1"):
			return normalized
		return f"{normalized}/api/v1"

	def close(self) -> None:
		return None

	def _request(
		self,
		method: str,
		path: str,
		*,
		json_payload: dict[str, Any] | None = None,
		params: dict[str, Any] | None = None,
	) -> Any:
		base_url = f"{self.api_base_url}/{path.lstrip('/')}"
		query = parse.urlencode(params or {}, doseq=True)
		url = f"{base_url}?{query}" if query else base_url

		try:
			body = None
			headers = {}
			if json_payload is not None:
				body = json.dumps(json_payload).encode("utf-8")
				headers["Content-Type"] = "application/json"

			http_request = request.Request(url=url, method=method.upper(), data=body, headers=headers)

			with request.urlopen(http_request, timeout=self.timeout_seconds) as response:
				raw_body = response.read().decode("utf-8")
				if not raw_body:
					return None

				try:
					return json.loads(raw_body)
				except json.JSONDecodeError:
					return raw_body
		except error.HTTPError as exc:
			error_body = exc.read().decode("utf-8") if exc.fp else ""
			try:
				parsed_error = json.loads(error_body) if error_body else None
			except json.JSONDecodeError:
				parsed_error = error_body

			if isinstance(parsed_error, dict):
				detail = str(parsed_error.get("detail", parsed_error))
			elif parsed_error:
				detail = str(parsed_error)
			else:
				detail = exc.reason

			raise APIManagerHTTPError(status_code=exc.code, detail=detail, url=url) from exc
		except (error.URLError, TimeoutError) as exc:
			raise APIManagerError(f"Błąd połączenia z db-service ({url}): {exc}") from exc

	def save_activity(self, payload: ActivityCreate) -> ActivityRead:
		"""Zapisuje nową aktywność przez API db-service."""
		response_data = self._request(
			"POST",
			"/activities",
			json_payload=payload.model_dump(mode="json"),
		)
		return ActivityRead.model_validate(response_data)

	def get_user_activities(self, discord_id: str, limit: int = 20) -> list[ActivityRead]:
		"""Pobiera historię aktywności użytkownika po `discord_id`."""
		response_data = self._request(
			"GET",
			f"/users/{discord_id}/history",
			params={"limit": limit},
		)
		return [ActivityRead.model_validate(item) for item in (response_data or [])]

	def get_activity(self, activity_iid: str) -> ActivityRead:
		"""Pobiera pojedynczą aktywność po identyfikatorze `iid`."""
		response_data = self._request("GET", f"/activities/{activity_iid}")
		return ActivityRead.model_validate(response_data)

	def update_activity(self, activity_iid: str, payload: ActivityUpdate) -> ActivityRead:
		"""Edytuje aktywność przez API db-service."""
		response_data = self._request(
			"PATCH",
			f"/activities/{activity_iid}",
			json_payload=payload.model_dump(mode="json", exclude_unset=True),
		)
		return ActivityRead.model_validate(response_data)

	def get_event(self, event_id: int) -> AirsoftEventRead:
		"""Pobiera informacje o evencie po `event_id`."""
		response_data = self._request("GET", f"/events/{event_id}")
		return AirsoftEventRead.model_validate(response_data)

	def list_events(self, upcoming_only: bool = False) -> list[AirsoftEventRead]:
		"""Pobiera listę wszystkich eventów."""
		response_data = self._request(
			"GET",
			"/events",
			params={"upcoming_only": str(upcoming_only).lower()},
		)
		return [AirsoftEventRead.model_validate(item) for item in (response_data or [])]

	def get_active_events(self) -> list[AirsoftEventRead]:
		"""Pobiera listę aktualnie aktywnych eventów (trwających)."""
		response_data = self._request("GET", "/events/active")
		return [AirsoftEventRead.model_validate(item) for item in (response_data or [])]

	def get_rankings(self, limit: int = 10) -> list[UserRankingRead]:
		"""Pobiera ranking użytkowników według punktów."""
		response_data = self._request("GET", "/rankings", params={"limit": limit})
		return [UserRankingRead.model_validate(item) for item in (response_data or [])]

	def get_active_challenges(self) -> list[ChallengeRead]:
		"""Pobiera listę aktualnie aktywnych challenge'y."""
		response_data = self._request("GET", "/challenges/active")
		return [ChallengeRead.model_validate(item) for item in (response_data or [])]

	def get_activity_rules(self, challenge_id: int) -> list[ActivityRuleRead]:
		"""Pobiera reguły aktywności dla danego challenge'u."""
		response_data = self._request("GET", f"/challenges/{challenge_id}/activity-rules")
		return [ActivityRuleRead.model_validate(item) for item in (response_data or [])]
