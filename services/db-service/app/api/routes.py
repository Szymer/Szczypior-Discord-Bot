from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.activity import ActivityCreate, ActivityRead, ActivityUpdate, UserRankingRead
from app.schemas.activity_rule import ActivityRulePatchPayload, ActivityRulePayload, ActivityRuleRead
from app.schemas.challenge import ChallengeCreate, ChallengeParticipantCreate, ChallengeParticipantRead, ChallengeRead
from app.schemas.event import AirsoftEventCreate, AirsoftEventRead, EventRegistrationCreate, EventRegistrationRead
from app.schemas.mission import MissionRead
from app.schemas.user import UserRead, UserUpsert
from app.services.activity_manager import ActivityManager
from app.services.challenges_manager import ChallengesManager
from app.services.events_manager import EventsManager
from app.services.users_manager import UsersManager

router = APIRouter()


# ── Health ─────────────────────────────────────────────────────────────────

@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


# ── Users ──────────────────────────────────────────────────────────────────

@router.post("/users/upsert", response_model=UserRead)
def upsert_user(payload: UserUpsert, db: Session = Depends(get_db)) -> UserRead:
    return UsersManager(db).upsert_user(payload)


@router.get("/users", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db)) -> list[UserRead]:
    return UsersManager(db).list_users()


@router.get("/users/{discord_id}", response_model=UserRead)
def get_user(discord_id: str, db: Session = Depends(get_db)) -> UserRead:
    user = UsersManager(db).get_user_by_discord_id(discord_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete("/users/{discord_id}", status_code=204)
def delete_user(discord_id: str, db: Session = Depends(get_db)) -> None:
    deleted = UsersManager(db).delete_user(discord_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")


# ── Activities ─────────────────────────────────────────────────────────────

@router.post("/activities", response_model=ActivityRead)
def create_activity(payload: ActivityCreate, db: Session = Depends(get_db)) -> ActivityRead:
    try:
        return ActivityManager(db).create_activity(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/users/{discord_id}/history", response_model=list[ActivityRead])
def user_history(discord_id: str, limit: int = 20, db: Session = Depends(get_db)) -> list[ActivityRead]:
    return ActivityManager(db).get_user_history(discord_id=discord_id, limit=limit)


@router.get("/activities/{activity_iid}", response_model=ActivityRead)
def get_activity(activity_iid: str, db: Session = Depends(get_db)) -> ActivityRead:
    activity = ActivityManager(db).get_activity_by_iid(activity_iid)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.patch("/activities/{activity_iid}", response_model=ActivityRead)
def update_activity(activity_iid: str, payload: ActivityUpdate, db: Session = Depends(get_db)) -> ActivityRead:
    update_fields = payload.model_dump(exclude_unset=True)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    try:
        return ActivityManager(db).update_activity(activity_iid, **update_fields)
    except ValueError as exc:
        detail = str(exc)
        if "not found" in detail.lower():
            raise HTTPException(status_code=404, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc


@router.get("/rankings", response_model=list[UserRankingRead])
def rankings(limit: int = 10, db: Session = Depends(get_db)) -> list[UserRankingRead]:
    return [UserRankingRead(**row) for row in ActivityManager(db).get_rankings(limit=limit)]


# ── Missions ───────────────────────────────────────────────────────────────

@router.get("/missions/active", response_model=list[MissionRead])
def active_missions(db: Session = Depends(get_db)) -> list[MissionRead]:
    return ActivityManager(db).list_active_missions()


# ── Events ─────────────────────────────────────────────────────────────────

@router.get("/events/active", response_model=list[AirsoftEventRead])
def list_active_events(db: Session = Depends(get_db)) -> list[AirsoftEventRead]:
    return EventsManager(db).get_active_events()


@router.post("/events", response_model=AirsoftEventRead)
def create_event(payload: AirsoftEventCreate, db: Session = Depends(get_db)) -> AirsoftEventRead:
    return EventsManager(db).create_event(payload)


@router.get("/events", response_model=list[AirsoftEventRead])
def list_events(upcoming_only: bool = False, db: Session = Depends(get_db)) -> list[AirsoftEventRead]:
    return EventsManager(db).list_events(upcoming_only=upcoming_only)


@router.get("/events/{event_id}", response_model=AirsoftEventRead)
def get_event(event_id: int, db: Session = Depends(get_db)) -> AirsoftEventRead:
    event = EventsManager(db).get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.delete("/events/{event_id}", status_code=204)
def delete_event(event_id: int, db: Session = Depends(get_db)) -> None:
    deleted = EventsManager(db).delete_event(event_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Event not found")


@router.post("/events/register", response_model=EventRegistrationRead)
def register_for_event(payload: EventRegistrationCreate, db: Session = Depends(get_db)) -> EventRegistrationRead:
    try:
        return EventsManager(db).register_user(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/events/{event_id}/register/{discord_id}", status_code=204)
def unregister_from_event(event_id: int, discord_id: str, db: Session = Depends(get_db)) -> None:
    removed = EventsManager(db).unregister_user(discord_id=discord_id, event_id=event_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Registration not found")


@router.get("/events/{event_id}/registrations", response_model=list[EventRegistrationRead])
def event_registrations(event_id: int, db: Session = Depends(get_db)) -> list[EventRegistrationRead]:
    return EventsManager(db).list_event_registrations(event_id)


@router.get("/users/{discord_id}/events", response_model=list[EventRegistrationRead])
def user_event_registrations(discord_id: str, db: Session = Depends(get_db)) -> list[EventRegistrationRead]:
    return EventsManager(db).list_user_registrations(discord_id)


# ── Challenges ─────────────────────────────────────────────────────────────

@router.get("/challenges/active", response_model=list[ChallengeRead])
def list_active_challenges(db: Session = Depends(get_db)) -> list[ChallengeRead]:
    return ChallengesManager(db).get_active_challenges()


@router.post("/challenges", response_model=ChallengeRead)
def create_challenge(payload: ChallengeCreate, db: Session = Depends(get_db)) -> ChallengeRead:
    return ChallengesManager(db).create_challenge(payload)


@router.get("/challenges", response_model=list[ChallengeRead])
def list_challenges(active_only: bool = False, db: Session = Depends(get_db)) -> list[ChallengeRead]:
    return ChallengesManager(db).list_challenges(active_only=active_only)


@router.get("/challenges/{challenge_id}/activity-rules", response_model=list[ActivityRuleRead])
def get_challenge_activity_rules(challenge_id: int, db: Session = Depends(get_db)) -> list[ActivityRuleRead]:
    manager = ChallengesManager(db)
    challenge = manager.get_challenge(challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return manager.list_activity_rules(challenge_id)


@router.post("/challenges/{challenge_id}/activity-rules", response_model=list[ActivityRuleRead])
def create_challenge_activity_rules(
    challenge_id: int,
    payload: list[ActivityRulePayload] | None = Body(default=None),
    db: Session = Depends(get_db),
) -> list[ActivityRuleRead]:
    try:
        return ChallengesManager(db).create_activity_rules(challenge_id, payload)
    except ValueError as exc:
        detail = str(exc)
        if "not found" in detail:
            raise HTTPException(status_code=404, detail=detail) from exc
        raise HTTPException(status_code=409, detail=detail) from exc


@router.put("/challenges/{challenge_id}/activity-rules", response_model=list[ActivityRuleRead])
def replace_challenge_activity_rules(
    challenge_id: int,
    payload: list[ActivityRulePayload] | None = Body(default=None),
    db: Session = Depends(get_db),
) -> list[ActivityRuleRead]:
    try:
        return ChallengesManager(db).replace_activity_rules(challenge_id, payload)
    except ValueError as exc:
        detail = str(exc)
        if "not found" in detail:
            raise HTTPException(status_code=404, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc


@router.patch("/challenges/{challenge_id}/activity-rules", response_model=list[ActivityRuleRead])
def patch_challenge_activity_rules(
    challenge_id: int,
    payload: list[ActivityRulePatchPayload] = Body(...),
    db: Session = Depends(get_db),
) -> list[ActivityRuleRead]:
    try:
        return ChallengesManager(db).patch_activity_rules(challenge_id, payload)
    except ValueError as exc:
        detail = str(exc)
        if "not found" in detail:
            raise HTTPException(status_code=404, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc


@router.get("/challenges/{challenge_id}", response_model=ChallengeRead)
def get_challenge(challenge_id: int, db: Session = Depends(get_db)) -> ChallengeRead:
    challenge = ChallengesManager(db).get_challenge(challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return challenge


@router.delete("/challenges/{challenge_id}", status_code=204)
def delete_challenge(challenge_id: int, db: Session = Depends(get_db)) -> None:
    deleted = ChallengesManager(db).delete_challenge(challenge_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Challenge not found")


@router.post("/challenges/participants", response_model=ChallengeParticipantRead)
def join_challenge(payload: ChallengeParticipantCreate, db: Session = Depends(get_db)) -> ChallengeParticipantRead:
    try:
        return ChallengesManager(db).add_participant(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/challenges/{challenge_id}/participants/{discord_id}", status_code=204)
def leave_challenge(challenge_id: int, discord_id: str, db: Session = Depends(get_db)) -> None:
    removed = ChallengesManager(db).remove_participant(discord_id=discord_id, challenge_id=challenge_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Participant not found")


@router.get("/challenges/{challenge_id}/participants", response_model=list[ChallengeParticipantRead])
def challenge_participants(challenge_id: int, db: Session = Depends(get_db)) -> list[ChallengeParticipantRead]:
    return ChallengesManager(db).list_challenge_participants(challenge_id)


@router.get("/users/{discord_id}/challenges", response_model=list[ChallengeParticipantRead])
def user_challenges(discord_id: str, db: Session = Depends(get_db)) -> list[ChallengeParticipantRead]:
    return ChallengesManager(db).list_user_challenges(discord_id)

