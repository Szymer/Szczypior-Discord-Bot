from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.activity import ActivityCreate, ActivityRead, UserRankingRead
from app.schemas.mission import MissionRead
from app.schemas.user import UserRead, UserUpsert
from app.services.db_manager import DBManager

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    manager = DBManager(db)
    manager.health_check()
    return {"status": "ok"}


@router.post("/users/upsert", response_model=UserRead)
def upsert_user(payload: UserUpsert, db: Session = Depends(get_db)) -> UserRead:
    manager = DBManager(db)
    return manager.upsert_user(payload)


@router.post("/activities", response_model=ActivityRead)
def create_activity(payload: ActivityCreate, db: Session = Depends(get_db)) -> ActivityRead:
    manager = DBManager(db)
    try:
        return manager.create_activity(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/users/{discord_id}/history", response_model=list[ActivityRead])
def user_history(discord_id: str, limit: int = 20, db: Session = Depends(get_db)) -> list[ActivityRead]:
    manager = DBManager(db)
    return manager.get_user_history(discord_id=discord_id, limit=limit)


@router.get("/rankings", response_model=list[UserRankingRead])
def rankings(limit: int = 10, db: Session = Depends(get_db)) -> list[UserRankingRead]:
    manager = DBManager(db)
    return [UserRankingRead(**row) for row in manager.get_rankings(limit=limit)]


@router.get("/missions/active", response_model=list[MissionRead])
def active_missions(db: Session = Depends(get_db)) -> list[MissionRead]:
    manager = DBManager(db)
    return manager.list_active_missions()
