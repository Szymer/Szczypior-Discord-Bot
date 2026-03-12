from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models import User
from app.schemas.user import UserUpsert


class UsersManager:
    def __init__(self, db: Session):
        self.db = db

    def upsert_user(self, payload: UserUpsert) -> User:
        existing = self.db.query(User).filter(User.discord_id == payload.discord_id).first()
        if existing:
            existing.display_name = payload.display_name
            existing.username = payload.username
            existing.avatar_url = payload.avatar_url
            self.db.add(existing)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        created = User(
            discord_id=payload.discord_id,
            display_name=payload.display_name,
            username=payload.username,
            avatar_url=payload.avatar_url,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(created)
        self.db.commit()
        self.db.refresh(created)
        return created

    def get_user_by_discord_id(self, discord_id: str) -> User | None:
        return self.db.query(User).filter(User.discord_id == discord_id).first()

    def delete_user(self, discord_id: str) -> bool:
        user = self.get_user_by_discord_id(discord_id)
        if not user:
            return False
        self.db.delete(user)
        self.db.commit()
        return True

    def list_users(self) -> list[User]:
        return self.db.query(User).order_by(User.display_name).all()
