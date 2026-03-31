from datetime import datetime
import json
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class BaseResponse(BaseModel):
    status_code: int
    message: str
    data: Any = None  # FIX ❌-4: Any thay vì object — rõ ràng hơn, tương thích Pydantic v2


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=100)

    @field_validator("password")
    @classmethod
    def check_strength(cls, value):
        if not any(c.isupper() for c in value):
            raise ValueError("Cần ít nhất một chữ cái viết hoa")
        if not any(c.islower() for c in value):
            raise ValueError("Cần ít nhất một chữ cái viết thường")
        if not any(c.isdigit() for c in value):
            raise ValueError("Cần ít nhất một chữ số")
        return value


class UserPublicOut(BaseModel):
    id: UUID
    email: str
    full_name: str
    avatar_url: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublicOut


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class AccessTokenOut(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int


class UserUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    avatar_url: str | None = None
    preferences_json: dict | None = None


class UserProfileOut(BaseModel):
    id: UUID
    email: str
    full_name: str
    avatar_url: str | None
    preferences_json: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_preferences(cls, user) -> "UserProfileOut":
        prefs = None
        if user.preferences_json:
            try:
                prefs = json.loads(user.preferences_json)
            except Exception:
                prefs = None
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            preferences_json=prefs,
            created_at=user.created_at,
        )
