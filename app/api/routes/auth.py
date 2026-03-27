from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.crud.user import create_user, get_user_by_email, get_user_by_id
from app.db.database import get_db
from app.core.config import settings
from app.schemas.user import AccessTokenOut, BaseResponse, RefreshTokenRequest, TokenOut, UserLoginRequest, UserPublicOut, UserRegisterRequest


router = APIRouter(prefix = "/auth", tags = ["Auth"])

@router.post("/register", status_code = 201)
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    if get_user_by_email(db, payload.email):
        raise HTTPException(400, detail = "Email đã được sử dụng")
    user = create_user(db, payload)
    return BaseResponse(
        status_code = 201,
        message = "Đăng ký thành công",
        data = UserPublicOut.model_validate(user)
    )

@router.post("/login")
def login(payload: UserLoginRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, detail = "Email hoặc mật khẩu không đúng")
    return BaseResponse(
        status_code = 200,
        message = "Đăng nhập thành công",
        data = TokenOut(
            access_token = create_access_token(str(user.id)),
            refresh_token = create_refresh_token(str(user.id)),
            expires_in = settings. ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user = UserPublicOut.model_validate(user)
        )
    )

@router.post("/refresh")
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    try: 
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh": raise ValueError()
    except Exception:
        raise HTTPException(401, detail = "Refresh token không hợp lệ hoặc đã hết hạn")
    user = get_user_by_id(db, data["sub"])
    if not user:
        raise HTTPException(401, detail = "Người dùng không tồn tại")
    return BaseResponse(
        status_code = 200,
        message = "Làm mới token thành công",
        data = AccessTokenOut(
            access_token = create_access_token(str(user.id)),
            expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    )

@router.get("/me")
def get_me(current_user = Depends(get_current_user)):
    return BaseResponse(
        status_code = 200,
        message = "Lấy thông tin người dùng thành công",
        data = UserPublicOut.model_validate(current_user)
    )