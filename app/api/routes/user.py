from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.crud.user import update_user
from app.db.database import get_db
from app.schemas.user import BaseResponse, UserProfileOut, UserUpdateRequest


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me")
def get_me(current_user=Depends(get_current_user)):
    # FIX AUTH-2: message "OK" theo spec (nhất quán với GET /auth/me)
    return BaseResponse(
        status_code=200,
        message="OK",
        data=UserProfileOut.from_orm_with_preferences(current_user),
    )


@router.patch("/me")
def update_me(
    payload: UserUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated = update_user(db, current_user, payload.model_dump(exclude_none=True))
    return BaseResponse(
        status_code=200,
        message="Cập nhật thành công",
        data=UserProfileOut.from_orm_with_preferences(updated),
    )