import json

from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserRegisterRequest

def get_user_by_email(db: Session, email: str) -> User | None: 
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: str) -> User | None: 
    return db.query(User).filter(User.id == user_id).first()

def create_user(db: Session, payload: UserRegisterRequest) -> User: 

    user = User(
        email = payload.email,
        password_hash = hash_password(payload.password),
        full_name = payload.full_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_user(db: Session, user: User, data: dict) -> User:
    if "full_name" in data and data["full_name"] is not None:
        user.full_name = data["full_name"]
    if "avatar_url" in data and data["avatar_url"] is not None:
        user.avatar_url = data["avatar_url"]
    if "preferences_json" in data and data["preferences_json"] is not None:
        user.preferences_json = json.dumps(data["preferences_json"], ensure_ascii = False) # type: ignore

    db.commit()
    db.refresh(user)
    return user