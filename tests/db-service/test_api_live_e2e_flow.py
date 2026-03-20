"""
test_api_live_e2e_flow.py
=========================

Test E2E po realnym HTTP do działającego FastAPI i realnej bazy.
Kolejność scenariusza:
1) dodanie użytkownika,
2) operacje eventowe (create/list/get/register/list/unregister),
3) dodanie aktywności,
4) operacje challenge (create/join/list/leave),
5) cleanup (delete challenge, event, user).

Uruchomienie:
    pytest tests/db-service/test_api_live_e2e_flow.py -q -s

Wymaganie:
    FastAPI musi działać lokalnie pod BASE_URL (domyślnie http://127.0.0.1:8000).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

import pytest


BASE_URL = os.getenv("DB_SERVICE_BASE_URL", "http://127.0.0.1:8000")
API_BASE = f"{BASE_URL}/api/v1"
API_KEY_HEADER = os.getenv("DB_SERVICE_API_KEY_HEADER", "X-API-Key")
API_KEY_VALUE = os.getenv("DB_SERVICE_API_KEY", "")


def _api_request(method: str, path: str, payload: dict | None = None) -> tuple[int, dict | list | None]:
    data = None
    headers: dict[str, str] = {}

    if API_KEY_VALUE:
        headers[API_KEY_HEADER] = API_KEY_VALUE

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(API_BASE + path, data=data, method=method, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8")
            parsed = json.loads(body) if body else None
            return response.status, parsed
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "ignore")
        raise AssertionError(f"{method} {path} -> {exc.code}, body={body}") from exc


def _safe_delete(path: str) -> None:
    headers = {API_KEY_HEADER: API_KEY_VALUE} if API_KEY_VALUE else {}
    req = urllib.request.Request(API_BASE + path, method="DELETE", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20):
            return
    except urllib.error.HTTPError as exc:
        if exc.code not in (404, 204):
            body = exc.read().decode("utf-8", "ignore")
            raise AssertionError(f"DELETE {path} cleanup failed: {exc.code}, body={body}") from exc


@pytest.mark.integration
def test_live_api_user_event_activity_challenge_flow() -> None:
    test_id = f"e2e-{uuid.uuid4().hex[:10]}"
    discord_id = test_id
    event_id: int | None = None
    challenge_id: int | None = None

    try:
        status, health = _api_request("GET", "/health")
        assert status == 200
        assert health == {"status": "ok"}

        status, user = _api_request(
            "POST",
            "/users/upsert",
            {
                "discord_id": discord_id,
                "display_name": "E2E Tester",
                "username": "e2e_user",
                "avatar_url": None,
            },
        )
        assert status == 200
        assert isinstance(user, dict)
        assert user["discord_id"] == discord_id

        status, users = _api_request("GET", "/users")
        assert status == 200
        assert isinstance(users, list)
        assert any(u["discord_id"] == discord_id for u in users)

        status, one_user = _api_request("GET", f"/users/{discord_id}")
        assert status == 200
        assert isinstance(one_user, dict)
        assert one_user["discord_id"] == discord_id

        now = datetime.now(timezone.utc)
        status, event = _api_request(
            "POST",
            "/events",
            {
                "name": f"E2E Event {test_id}",
                "description": "E2E test event",
                "start_date": (now + timedelta(days=2)).isoformat(),
                "end_date": (now + timedelta(days=2, hours=5)).isoformat(),
                "location": "Warsaw",
                "event_type": "airsoft",
                "price": 150.0,
                "currency": "PLN",
                "event_url": "https://example.com/e2e-event",
            },
        )
        assert status == 200
        assert isinstance(event, dict)
        event_id = event["id"]

        status, events = _api_request("GET", "/events")
        assert status == 200
        assert isinstance(events, list)
        assert any(e["id"] == event_id for e in events)

        status, one_event = _api_request("GET", f"/events/{event_id}")
        assert status == 200
        assert isinstance(one_event, dict)
        assert one_event["id"] == event_id

        status, registration = _api_request(
            "POST",
            "/events/register",
            {"discord_id": discord_id, "event_id": event_id},
        )
        assert status == 200
        assert isinstance(registration, dict)
        assert registration["event_id"] == event_id

        status, regs_for_event = _api_request("GET", f"/events/{event_id}/registrations")
        assert status == 200
        assert isinstance(regs_for_event, list)
        assert any(r["event_id"] == event_id for r in regs_for_event)

        status, regs_for_user = _api_request("GET", f"/users/{discord_id}/events")
        assert status == 200
        assert isinstance(regs_for_user, list)
        assert any(r["event_id"] == event_id for r in regs_for_user)

        activity_iid = f"e2e-iid-{uuid.uuid4().hex[:10]}"
        status, activity = _api_request(
            "POST",
            "/activities",
            {
                "discord_id": discord_id,
                "display_name": "E2E Tester",
                "iid": activity_iid,
                "activity_type": "bieganie_teren",
                "distance_km": 5.0,
                "base_points": 12,
                "weight_kg": None,
                "elevation_m": 30,
                "weight_bonus_points": 0,
                "elevation_bonus_points": 2,
                "mission_bonus_points": 0,
                "total_points": 14,
                "special_mission_id": None,
                "challenge_id": None,
                "time_minutes": 28,
                "pace": "5:36",
                "heart_rate_avg": 148,
                "calories": 360,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "message_id": None,
                "message_timestamp": None,
                "ai_comment": "E2E activity",
            },
        )
        assert status == 200
        assert isinstance(activity, dict)
        assert activity["iid"] == activity_iid

        status, history = _api_request("GET", f"/users/{discord_id}/history?limit=20")
        assert status == 200
        assert isinstance(history, list)
        assert any(a["iid"] == activity_iid for a in history)

        status, challenge = _api_request(
            "POST",
            "/challenges",
            {
                "name": f"E2E Challenge {test_id}",
                "description": "E2E challenge",
                "start_date": datetime.now(timezone.utc).isoformat(),
                "end_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                "rules": {"goal": "distance", "km": 20},
                "is_active": True,
            },
        )
        assert status == 200
        assert isinstance(challenge, dict)
        challenge_id = challenge["id"]

        status, participant = _api_request(
            "POST",
            "/challenges/participants",
            {"discord_id": discord_id, "challenge_id": challenge_id},
        )
        assert status == 200
        assert isinstance(participant, dict)
        assert participant["challenge_id"] == challenge_id

        status, challenge_participants = _api_request("GET", f"/challenges/{challenge_id}/participants")
        assert status == 200
        assert isinstance(challenge_participants, list)
        assert len(challenge_participants) >= 1

        status, user_challenges = _api_request("GET", f"/users/{discord_id}/challenges")
        assert status == 200
        assert isinstance(user_challenges, list)
        assert any(item["challenge_id"] == challenge_id for item in user_challenges)

    finally:
        if challenge_id is not None:
            _safe_delete(f"/challenges/{challenge_id}/participants/{discord_id}")
            _safe_delete(f"/challenges/{challenge_id}")

        if event_id is not None:
            _safe_delete(f"/events/{event_id}/register/{discord_id}")
            _safe_delete(f"/events/{event_id}")

        _safe_delete(f"/users/{discord_id}")

    final_headers = {API_KEY_HEADER: API_KEY_VALUE} if API_KEY_VALUE else {}
    req = urllib.request.Request(API_BASE + f"/users/{discord_id}", method="GET", headers=final_headers)
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req, timeout=20)
    assert exc_info.value.code == 404

    if event_id is not None:
        req_event = urllib.request.Request(
            API_BASE + f"/events/{event_id}", method="GET", headers=final_headers
        )
        with pytest.raises(urllib.error.HTTPError) as exc_event:
            urllib.request.urlopen(req_event, timeout=20)
        assert exc_event.value.code == 404

    if challenge_id is not None:
        req_challenge = urllib.request.Request(
            API_BASE + f"/challenges/{challenge_id}", method="GET", headers=final_headers
        )
        with pytest.raises(urllib.error.HTTPError) as exc_challenge:
            urllib.request.urlopen(req_challenge, timeout=20)
        assert exc_challenge.value.code == 404
