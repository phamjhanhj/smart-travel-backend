from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_current_user
from app.crud.trip import create_trip
from app.db.database import get_db
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.trip import TripCreateRequest, TripOut
from app.schemas.user import BaseResponse


router = APIRouter(prefix="/trips", tags=["Trips"])


def check_trip_user(trip, current_user: User):
    if trip is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy chuyến đi")
    if trip.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Bạn không có quyền truy cập chuyến đi này"
        )


@router.post("/", status_code=201)
def create(
    payload: TripCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.start_date > payload.end_date:
        raise HTTPException(
            status_code=400, detail="Ngày bắt đầu phải trước ngày kết thúc"
        )
    trip = create_trip(db, current_user.id, payload)
    return BaseResponse(
        status_code=201,
        message="Tạo chuyến đi thành công",
        data=TripOut.model_validate(trip),
    )
