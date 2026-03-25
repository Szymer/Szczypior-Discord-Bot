import json
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import jwt
from jwt import PyJWKClient
from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .models import Activity, AirsoftEvent, EventRegistration, Challenge, DiscordUser, SpecialMission

# Klient JWKS — pobiera i cachuje klucze publiczne Supabase (ES256)
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_client


def _verify_supabase_token(token: str) -> dict:
    """Decode and verify a Supabase-issued JWT (ES256 via JWKS)."""
    client = _get_jwks_client()
    signing_key = client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256"],
        options={"verify_aud": False},
    )


def _extract_discord_id_from_identity_data(data: dict | None) -> str:
    if not data:
        return ""

    for key in ("provider_id", "sub", "user_id", "id"):
        value = data.get(key)
        if value:
            return str(value)

    return ""


def _fetch_supabase_user(token: str) -> dict:
    request = Request(
        f"{settings.SUPABASE_URL}/auth/v1/user",
        headers={"Authorization": f"Bearer {token}"},
    )

    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _resolve_discord_id(token: str, payload: dict) -> str:
    user_meta = payload.get("user_metadata") or {}
    app_meta = payload.get("app_metadata") or {}

    for data in (user_meta, app_meta):
        discord_id = _extract_discord_id_from_identity_data(data)
        if discord_id:
            return discord_id

    try:
        supabase_user = _fetch_supabase_user(token)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return ""

    for identity in supabase_user.get("identities") or []:
        if identity.get("provider") != "discord":
            continue

        discord_id = _extract_discord_id_from_identity_data(
            identity.get("identity_data") or {}
        )
        if discord_id:
            return discord_id

    return _extract_discord_id_from_identity_data(
        supabase_user.get("user_metadata") or {}
    )


def _extract_bearer_token(request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return ""
    return auth_header.split(" ", 1)[1]


def _get_request_user(request):
    token = _extract_bearer_token(request)
    if not token:
        return None

    try:
        payload = _verify_supabase_token(token)
    except jwt.InvalidTokenError:
        return None

    discord_id = _resolve_discord_id(token, payload)
    if not discord_id:
        return None

    try:
        return DiscordUser.objects.get(discord_id=discord_id)
    except DiscordUser.DoesNotExist:
        return None


def _require_admin(request):
    user = _get_request_user(request)
    if not user:
        return None, JsonResponse({"error": "Unauthorized"}, status=401)
    if user.role != "admin":
        return None, JsonResponse({"error": "Forbidden"}, status=403)
    return user, None


def _pace_to_float(pace_value: str | None) -> float | None:
    if not pace_value:
        return None
    try:
        mins, secs = str(pace_value).split(":", 1)
        return round(int(mins) + int(secs) / 60, 2)
    except Exception:
        return None


@require_http_methods(["GET", "OPTIONS"])
def me(request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "Unauthorized"}, status=401)

    token = auth_header.split(" ", 1)[1]

    try:
        payload = _verify_supabase_token(token)
    except jwt.ExpiredSignatureError:
        return JsonResponse({"error": "Token expired"}, status=401)
    except jwt.InvalidTokenError:
        return JsonResponse({"error": "Invalid token"}, status=401)

    discord_id = _resolve_discord_id(token, payload)

    if not discord_id:
        return JsonResponse({"error": "Discord ID missing in token"}, status=401)

    try:
        user = DiscordUser.objects.get(discord_id=discord_id)
    except DiscordUser.DoesNotExist:
        from django.conf import settings as _s

        extra = {"discord_id": discord_id} if _s.DEBUG else {}
        return JsonResponse({"error": "Access denied", **extra}, status=403)

    return JsonResponse(
        {
            "id": user.id,
            "discord_id": user.discord_id,
            "username": user.display_name,
            "role": user.role,
        }
    )


@require_http_methods(["GET", "OPTIONS"])
def challenges(request):
    from .serializers import ChallengeSerializer
    from .models import Challenge

    qs = Challenge.objects.all().order_by("-is_active", "start_date")
    data = ChallengeSerializer(qs, many=True).data
    return JsonResponse(list(data), safe=False)


@require_http_methods(["GET", "OPTIONS"])
def activities(request):
    from .serializers import ActivitySerializer
    from .models import Activity

    qs = Activity.objects.select_related("user").order_by("-created_at")

    challenge_id = request.GET.get("challengeId")
    if challenge_id:
        qs = qs.filter(challenge_id=challenge_id)

    user_id = request.GET.get("userId")
    if user_id:
        qs = qs.filter(user__discord_id=user_id)

    limit = int(request.GET.get("limit", 200))
    qs = qs[:limit]

    data = ActivitySerializer(qs, many=True).data
    return JsonResponse(list(data), safe=False)


@require_http_methods(["GET", "OPTIONS"])
def players(request):
    from .serializers import PlayerSerializer

    challenge_id_raw = request.GET.get("challengeId")
    challenge_id = None
    if challenge_id_raw:
        try:
            challenge_id = int(challenge_id_raw)
        except ValueError:
            return JsonResponse({"error": "Invalid challengeId"}, status=400)

    qs = DiscordUser.objects.prefetch_related("activity_set").all()
    data = PlayerSerializer(qs, many=True, context={"challenge_id": challenge_id}).data
    # Sort by totalPoints desc, add rank
    sorted_data = sorted(data, key=lambda p: p["totalPoints"], reverse=True)
    for i, p in enumerate(sorted_data):
        p["rank"] = i + 1
        p["pointsDiff"] = (
            sorted_data[0]["totalPoints"] - p["totalPoints"] if i > 0 else 0
        )

        user_obj = next((u for u in qs if u.discord_id == p["id"]), None)
        if user_obj is None:
            p["bestPaceMinPerKm"] = None
            continue

        running_acts = [
            a
            for a in user_obj.activity_set.all()
            if a.activity_type in ("bieganie_teren", "bieganie_bieznia")
        ]
        paces = [
            pv
            for pv in (_pace_to_float(a.pace) for a in running_acts)
            if pv is not None
        ]
        p["bestPaceMinPerKm"] = min(paces) if paces else None

    return JsonResponse(sorted_data, safe=False)


@require_http_methods(["GET", "OPTIONS"])
def ranking(request):
    return players(request)


@require_http_methods(["GET", "OPTIONS"])
def stats_summary(request):
    from .serializers import StatsSummarySerializer

    user = _get_request_user(request)
    if not user:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    acts = list(user.activity_set.all().order_by("-created_at"))
    last5 = acts[:5]

    avg5_points = round(sum(a.total_points for a in last5) / len(last5)) if last5 else 0
    best_activity = max(acts, key=lambda a: a.total_points) if acts else None

    running_acts = [
        a for a in acts if a.activity_type in ("bieganie_teren", "bieganie_bieznia")
    ]
    running_paces = [
        pv for pv in (_pace_to_float(a.pace) for a in running_acts) if pv is not None
    ]
    avg_running_pace = (
        round(sum(running_paces) / len(running_paces), 2) if running_paces else None
    )

    payload = {
        "avg5Points": int(avg5_points),
        "bestActivityPoints": int(best_activity.total_points) if best_activity else 0,
        "bestActivityDate": (
            best_activity.created_at.strftime("%Y-%m-%d") if best_activity else None
        ),
        "avgRunningPace": avg_running_pace,
        "totalDurationMin": int(sum(a.time_minutes or 0 for a in acts)),
    }
    return JsonResponse(StatsSummarySerializer(payload).data)


@require_http_methods(["GET", "OPTIONS"])
def stats_weekly(request):
    from .serializers import WeeklyStatsPointSerializer

    user = _get_request_user(request)
    if not user:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    acts = list(user.activity_set.all().order_by("created_at"))
    week_map = {}
    for a in acts:
        year, week, _ = a.created_at.isocalendar()
        key = f"{year}-W{week:02d}"
        if key not in week_map:
            week_map[key] = {"name": key, "points": 0, "distance": 0.0}
        week_map[key]["points"] += int(a.total_points)
        week_map[key]["distance"] += float(a.distance_km)

    weekly = list(week_map.values())[-12:]
    for row in weekly:
        row["distance"] = round(row["distance"], 2)

    return JsonResponse(WeeklyStatsPointSerializer(weekly, many=True).data, safe=False)


@require_http_methods(["GET", "OPTIONS"])
def stats_distribution(request):
    from .serializers import ActivityDistributionSerializer

    user = _get_request_user(request)
    if not user:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    labels = {
        "bieganie_teren": "Bieganie (Teren)",
        "bieganie_bieznia": "Bieganie (Bieżnia)",
        "plywanie": "Pływanie",
        "rower": "Rower/Rolki",
        "spacer": "Spacer/Trekking",
        "cardio": "Inne Cardio",
    }
    mapping = getattr(settings, "ACTIVITY_MAP", {})

    buckets = {}
    for a in user.activity_set.all():
        frontend_type = mapping.get(a.activity_type, a.activity_type)
        if frontend_type not in buckets:
            buckets[frontend_type] = {
                "type": frontend_type,
                "label": labels.get(a.activity_type, frontend_type),
                "count": 0,
                "distance": 0.0,
                "points": 0,
            }
        buckets[frontend_type]["count"] += 1
        buckets[frontend_type]["distance"] += float(a.distance_km)
        buckets[frontend_type]["points"] += int(a.total_points)

    payload = list(buckets.values())
    payload.sort(key=lambda x: x["points"], reverse=True)
    for row in payload:
        row["distance"] = round(row["distance"], 2)

    return JsonResponse(
        ActivityDistributionSerializer(payload, many=True).data, safe=False
    )


def _event_type_emoji(event_type: str) -> str:
    return {
        "milsim": "🎖️",
        "cqb": "🏢",
        "woodland": "🌲",
        "scenario": "📜",
        "other": "🔫",
    }.get(event_type, "🔫")


@require_http_methods(["GET", "POST", "OPTIONS"])
def admin_events(request):
    _, error = _require_admin(request)
    if error:
        return error

    from .serializers import AsgEventSerializer

    if request.method == "GET":
        events = (
            AirsoftEvent.objects.prefetch_related("registrations__user")
            .all()
            .order_by("start_date", "id")
        )
        data = AsgEventSerializer(events, many=True).data
        return JsonResponse(list(data), safe=False)

    body = json.loads(request.body or "{}")
    date_raw = body.get("date")
    start_date = (
        timezone.make_aware(datetime.strptime(date_raw, "%Y-%m-%d"))
        if date_raw
        else timezone.now()
    )

    event = AirsoftEvent.objects.create(
        name=body.get("name", "").strip(),
        start_date=start_date,
        end_date=start_date,
        location=body.get("location") or "TBD",
        description=body.get("description", ""),
        organizer=body.get("organizer", ""),
        event_type=body.get("type", "other"),
        currency="PLN",
    )

    participant_ids = body.get("participants") or []
    if participant_ids:
        users = DiscordUser.objects.filter(discord_id__in=participant_ids)
        for u in users:
            EventRegistration.objects.get_or_create(event=event, user=u)

    data = AsgEventSerializer(event).data
    return JsonResponse(data, status=201)


@require_http_methods(["PATCH", "DELETE", "OPTIONS"])
def admin_event_detail(request, event_id: int):
    _, error = _require_admin(request)
    if error:
        return error

    try:
        event = AirsoftEvent.objects.get(id=event_id)
    except AirsoftEvent.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    if request.method == "DELETE":
        event.delete()
        return JsonResponse({"ok": True})

    body = json.loads(request.body or "{}")
    fields_map = {
        "name": "name",
        "location": "location",
        "description": "description",
        "organizer": "organizer",
        "type": "event_type",
    }

    if "date" in body and body.get("date"):
        parsed = timezone.make_aware(datetime.strptime(body["date"], "%Y-%m-%d"))
        event.start_date = parsed
        event.end_date = parsed

    for k, v in body.items():
        if k in fields_map:
            setattr(event, fields_map[k], v)
    event.save()

    if "participants" in body:
        event.registrations.all().delete()
        users = DiscordUser.objects.filter(
            discord_id__in=(body.get("participants") or [])
        )
        for u in users:
            EventRegistration.objects.create(event=event, user=u)

    from .serializers import AsgEventSerializer

    return JsonResponse(AsgEventSerializer(event).data)


@require_http_methods(["GET", "POST", "OPTIONS"])
def admin_challenges(request):
    _, error = _require_admin(request)
    if error:
        return error

    from .serializers import ChallengeAdminSerializer

    if request.method == "GET":
        qs = Challenge.objects.all().order_by("-start_date", "-id")
        data = ChallengeAdminSerializer(qs, many=True).data
        return JsonResponse(list(data), safe=False)

    body = json.loads(request.body or "{}")
    rules = {
        "emoji": body.get("emoji", "🏆"),
        "goal": body.get("goal", ""),
        "bonus_points": int(body.get("bonusPoints") or 0),
    }
    start_date = datetime.strptime(body.get("startDate"), "%Y-%m-%d")
    end_date = datetime.strptime(body.get("endDate"), "%Y-%m-%d")
    challenge = Challenge.objects.create(
        name=body.get("name", "").strip(),
        description=body.get("description", ""),
        start_date=timezone.make_aware(start_date),
        end_date=timezone.make_aware(end_date),
        rules=rules,
        is_active=bool(body.get("isActive", False)),
    )
    return JsonResponse(ChallengeAdminSerializer(challenge).data, status=201)


@require_http_methods(["PATCH", "DELETE", "OPTIONS"])
def admin_challenge_detail(request, challenge_id: int):
    _, error = _require_admin(request)
    if error:
        return error

    try:
        challenge = Challenge.objects.get(id=challenge_id)
    except Challenge.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    if request.method == "DELETE":
        challenge.delete()
        return JsonResponse({"ok": True})

    body = json.loads(request.body or "{}")
    if "name" in body:
        challenge.name = body["name"]
    if "description" in body:
        challenge.description = body["description"]
    if "startDate" in body:
        challenge.start_date = timezone.make_aware(
            datetime.strptime(body["startDate"], "%Y-%m-%d")
        )
    if "endDate" in body:
        challenge.end_date = timezone.make_aware(
            datetime.strptime(body["endDate"], "%Y-%m-%d")
        )
    if "isActive" in body:
        challenge.is_active = bool(body["isActive"])

    rules = dict(challenge.rules or {})
    if "emoji" in body:
        rules["emoji"] = body["emoji"]
    if "goal" in body:
        rules["goal"] = body["goal"]
    if "bonusPoints" in body:
        rules["bonus_points"] = int(body["bonusPoints"] or 0)
    challenge.rules = rules

    challenge.save()

    from .serializers import ChallengeAdminSerializer

    return JsonResponse(ChallengeAdminSerializer(challenge).data)


@require_http_methods(["GET", "OPTIONS"])
def admin_activities(request):
    _, error = _require_admin(request)
    if error:
        return error

    from .serializers import ActivitySerializer

    qs = Activity.objects.select_related("user").order_by("-created_at")

    user_id = request.GET.get("userId")
    if user_id and user_id != "all":
        qs = qs.filter(user__discord_id=user_id)

    activity_type = request.GET.get("type")
    if activity_type and activity_type != "all":
        reverse_map = {v: k for k, v in getattr(settings, "ACTIVITY_MAP", {}).items()}
        db_type = reverse_map.get(activity_type, activity_type)
        qs = qs.filter(activity_type=db_type)

    challenge_id = request.GET.get("challengeId")
    if challenge_id and challenge_id != "all":
        try:
            qs = qs.filter(challenge_id=int(challenge_id))
        except (ValueError, TypeError):
            return JsonResponse({"error": "Invalid challengeId"}, status=400)

    date_from = request.GET.get("dateFrom")
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)

    date_to = request.GET.get("dateTo")
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    search = request.GET.get("search")
    if search:
        qs = qs.filter(
            Q(user__display_name__icontains=search)
            | Q(user__discord_id__icontains=search)
        )

    limit = int(request.GET.get("limit", 200))
    data = ActivitySerializer(qs[:limit], many=True).data
    return JsonResponse(list(data), safe=False)


@require_http_methods(["GET", "OPTIONS"])
def admin_missions(request):
    _, error = _require_admin(request)
    if error:
        return error

    qs = SpecialMission.objects.filter(is_active=True).order_by("name")
    data = [
        {
            "id": m.id,
            "name": m.name,
            "emoji": m.emoji,
            "bonusPoints": m.bonus_points,
            "description": m.description or "",
        }
        for m in qs
    ]
    return JsonResponse(data, safe=False)


@require_http_methods(["PATCH", "OPTIONS"])
def admin_activity_detail(request, activity_id: int):
    _, error = _require_admin(request)
    if error:
        return error

    try:
        activity = Activity.objects.get(id=activity_id)
    except Activity.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    body = json.loads(request.body or "{}")

    from .serializers import ActivitySerializer

    # Resolve new activity type if provided
    new_frontend_type = body.get("activityType")
    if new_frontend_type:
        reverse_map = {v: k for k, v in getattr(settings, "ACTIVITY_MAP", {}).items()}
        db_type = reverse_map.get(new_frontend_type, new_frontend_type)
        activity.activity_type = db_type

    # Load activity rules from shared constants
    from libs.shared.constants import ACTIVITY_TYPES
    activity_info = ACTIVITY_TYPES.get(activity.activity_type, {})

    distance = float(activity.distance_km or 0)
    base_pts_per_km = activity_info.get("base_points", 0)
    base_points = int(distance * base_pts_per_km)
    activity.base_points = base_points

    # Weight / load bonus
    weight_kg_raw = body.get("weightKg")
    weight_kg = float(weight_kg_raw) if weight_kg_raw not in (None, "") else None
    activity.weight_kg = weight_kg

    if weight_kg and weight_kg > 0 and "obciążenie" in activity_info.get("bonuses", []):
        weight_bonus = int((weight_kg / 5) * (distance * base_pts_per_km * 0.1))
    else:
        weight_bonus = 0
    activity.weight_bonus_points = weight_bonus

    # Elevation bonus
    elevation_m_raw = body.get("elevationM")
    elevation_m = int(elevation_m_raw) if elevation_m_raw not in (None, "") else None
    activity.elevation_m = elevation_m

    if elevation_m and elevation_m > 0 and "przewyższenie" in activity_info.get("bonuses", []):
        elevation_bonus = int((elevation_m / 100) * (distance * base_pts_per_km * 0.05))
    else:
        elevation_bonus = 0
    activity.elevation_bonus_points = elevation_bonus

    # Special mission bonus – set via FK
    mission_id_raw = body.get("specialMissionId")
    if mission_id_raw == "" or mission_id_raw is None:
        activity.special_mission = None
        activity.mission_bonus_points = 0
    else:
        try:
            mission = SpecialMission.objects.get(id=int(mission_id_raw))
            activity.special_mission = mission
            activity.mission_bonus_points = mission.bonus_points
        except SpecialMission.DoesNotExist:
            return JsonResponse({"error": "Mission not found"}, status=404)

    activity.total_points = (
        activity.base_points
        + activity.weight_bonus_points
        + activity.elevation_bonus_points
        + (activity.mission_bonus_points or 0)
    )

    activity.save(update_fields=[
        "activity_type", "weight_kg", "elevation_m",
        "base_points", "weight_bonus_points", "elevation_bonus_points",
        "special_mission", "mission_bonus_points", "total_points",
    ])

    return JsonResponse(ActivitySerializer(activity).data)


@require_http_methods(["POST", "OPTIONS"])
def admin_activity_bonus(request, activity_id: int):
    _, error = _require_admin(request)
    if error:
        return error

    try:
        activity = Activity.objects.get(id=activity_id)
    except Activity.DoesNotExist:
        return JsonResponse({"error": "Not found"}, status=404)

    body = json.loads(request.body or "{}")
    points = int(body.get("points") or 0)
    if points <= 0:
        return JsonResponse({"error": "points must be > 0"}, status=400)

    activity.mission_bonus_points = (activity.mission_bonus_points or 0) + points
    activity.total_points = (activity.total_points or 0) + points
    activity.save(update_fields=["mission_bonus_points", "total_points"])

    from .serializers import ActivitySerializer

    return JsonResponse(ActivitySerializer(activity).data)
