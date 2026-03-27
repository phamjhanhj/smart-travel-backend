from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.crud.user import update_user
from app.db.database import get_db
from app.schemas.user import BaseResponse, UserProfileOut, UserPublicOut, UserUpdateRequest


router = APIRouter(prefix = "/users", tags = ["Users"])

@router.get("/me")
def get_me(current_user = Depends(get_current_user)):
    return BaseResponse(
        status_code = 200,
        message = "Lấy thông tin người dùng thành công",
        data = UserPublicOut.model_validate(current_user)
    )

@router.patch("/me")
def update_me(
    payload: UserUpdateRequest,
    current_user = Depends(get_current_user),
    db:Session = Depends(get_db),
):
    update = update_user(
        db, 
        current_user,
        payload.model_dump(exclude_none = True)
    )
    return BaseResponse(
        status_code = 200,
        message = "Cập nhật thông tin người dùng thành công",
        data = UserProfileOut.from_orm_with_preferences(update),
    )