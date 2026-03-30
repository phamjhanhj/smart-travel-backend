from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session
from app.core.security import decode_token
from app.crud.user import get_user_by_id
from app.db.database import get_db


bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise ValueError()
        user_id = payload["sub"]
    except (JWTError, ValueError, KeyError):
        raise HTTPException(
            status_code=401, detail="Token không hợp lệ hoặc đã hết hạn"
        )

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Người dùng không tồn tại")
    return user
