from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.crud.trip import (
    create_trip,
    delete_trip,
    get_trip_by_id,
    get_trip_summary,
    get_trips_by_user,
    update_trip,
)
from app.db.database import get_db
from app.models.user import User
from app.schemas.trip import (
    TripCreateRequest,
    TripDetailOut,
    TripListOut,
    TripOut,
    TripSummaryOut,
    TripUpdateRequest,
    DayPlanBriefOut,
)
from app.schemas.user import BaseResponse


router = APIRouter(prefix="/trips", tags=["Trips"])


def check_trip_user(trip, current_user: User):
    if trip is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy chuyến đi")
    if trip.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Bạn không có quyền truy cập chuyến đi này"
        )


@router.get("")
def list_trips(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = get_trips_by_user(db, current_user.id, status, page, limit)
    return BaseResponse(
        status_code=200,
        message="Lấy danh sách chuyến đi thành công",
        data=TripListOut(
            trips=[TripOut.model_validate(item) for item in items],
            total=total,
            page=page,
            limit=limit,
        ),
    )


@router.post("")
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


@router.get("/{trip_id}")
def get_detail(
    trip_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = get_trip_by_id(db, trip_id)
    check_trip_user(trip, current_user)

    # Build day_plans kèm số lượng activities
    day_plans_out = []
    for dp in trip.day_plans:
        day_plans_out.append(
            DayPlanBriefOut(
                id=dp.id,
                day_number=dp.day_number,
                date=dp.date,
                activities_count=len(dp.activities),
            )
        )

    detail = TripDetailOut(
        **TripOut.model_validate(trip).model_dump(),
        day_plans=day_plans_out,
    )
    return BaseResponse(status_code=200, message="OK", data=detail)


@router.put("/{trip_id}")
def update(
    trip_id: UUID,
    payload: TripUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = get_trip_by_id(db, trip_id)
    check_trip_user(trip, current_user)

    # Validate dates nếu cả 2 được truyền
    start = payload.start_date or trip.start_date
    end = payload.end_date or trip.end_date
    if end < start:
        raise HTTPException(status_code=400, detail="end_date phải sau start_date")

    updated = update_trip(db, trip, payload)
    return BaseResponse(
        status_code=200,
        message="Cập nhật thành công",
        data=TripOut.model_validate(updated),
    )


@router.delete("/{trip_id}")
def delete(
    trip_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = get_trip_by_id(db, trip_id)
    check_trip_user(trip, current_user)

    delete_trip(db, trip)
    return BaseResponse(status_code=200, message="Đã xóa chuyến đi", data=None)


@router.get("/{trip_id}/summary")
def summary(
    trip_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = get_trip_by_id(db, trip_id)
    check_trip_user(trip, current_user)

    data = get_trip_summary(db, trip)
    return BaseResponse(
        status_code=200,
        message="OK",
        data=TripSummaryOut(**data),
    )
