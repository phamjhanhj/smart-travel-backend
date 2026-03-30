from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.crud.activity import create_activity
from app.crud.day_plan import (
    generate_day_plans,
    get_day_plan_by_id,
    get_day_plans_by_trip,
)
from app.crud.trip import get_trip_by_id
from app.db.database import get_db
from app.models.user import User
from app.schemas.activity import ActivityBriefOut, ActivityCreateRequest, ActivityOut
from app.schemas.day_plan import (
    DayPlanBriefOut,
    DayPlanOut,
    DayPlanWithActivitiesOut,
    GenerateDayPlansRequest,
)
from app.schemas.user import BaseResponse


def _get_trip_or_404(db: Session, trip_id: UUID, current_user: User):
    """Lấy trip, kiểm tra tồn tại và quyền sở hữu."""
    trip = get_trip_by_id(db, trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Không tìm thấy chuyến đi")
    if trip.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Bạn không có quyền truy cập chuyến đi này"
        )
    return trip


def _get_day_or_404(db: Session, day_id: UUID, trip_id: UUID):
    """Lấy day_plan, kiểm tra tồn tại và thuộc đúng trip."""
    day = get_day_plan_by_id(db, day_id)
    if not day:
        raise HTTPException(status_code=404, detail="Không tìm thấy ngày")
    if day.trip_id != trip_id:
        raise HTTPException(status_code=400, detail="Ngày không thuộc chuyến đi này")
    return day


day_router = APIRouter(prefix="/trips", tags=["Day Plans"])


# -----------------------------------------------------------------------
# GET /trips/{trip_id}/days — toàn bộ ngày kèm activities + location
# -----------------------------------------------------------------------
@day_router.get("/{trip_id}/days")
def list_days(
    trip_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_trip_or_404(db, trip_id, current_user)

    day_plans = get_day_plans_by_trip(db, trip_id)

    data = []
    for dp in day_plans:
        activities_out = []
        for act in dp.activities:
            activities_out.append(
                ActivityOut(
                    id=act.id,
                    day_plan_id=act.day_plan_id,
                    title=act.title,
                    description=act.description,
                    type=act.type,
                    start_time=act.start_time,
                    end_time=act.end_time,
                    estimated_cost=act.estimated_cost,
                    order_index=act.order_index,
                    booking_url=act.booking_url,
                    notes=act.notes,
                    location=act.location,  # relationship — None nếu không có
                )
            )
        data.append(
            DayPlanWithActivitiesOut(
                id=dp.id,
                day_number=dp.day_number,
                date=dp.date,
                activities=activities_out,
            )
        )

    return BaseResponse(status_code=200, message="OK", data=data)


# -----------------------------------------------------------------------
# GET /trips/{trip_id}/days/{day_id} — chi tiết 1 ngày
# -----------------------------------------------------------------------
@day_router.get("/{trip_id}/days/{day_id}")
def get_day_detail(
    trip_id: UUID,
    day_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_trip_or_404(db, trip_id, current_user)
    day = _get_day_or_404(db, day_id, trip_id)

    activities_out = [ActivityBriefOut.model_validate(act) for act in day.activities]

    return BaseResponse(
        status_code=200,
        message="OK",
        data=DayPlanOut(
            id=day.id,
            trip_id=day.trip_id,
            day_number=day.day_number,
            date=day.date,
            activities=activities_out,
        ),
    )


# -----------------------------------------------------------------------
# POST /trips/{trip_id}/days/{day_id}/activities — thêm activity
# -----------------------------------------------------------------------
@day_router.post("/{trip_id}/days/{day_id}/activities", status_code=201)
def add_activity(
    trip_id: UUID,
    day_id: UUID,
    payload: ActivityCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_trip_or_404(db, trip_id, current_user)
    day = _get_day_or_404(db, day_id, trip_id)

    activity = create_activity(db, day.id, payload)

    return BaseResponse(
        status_code=201,
        message="Thêm hoạt động thành công",
        data=ActivityOut(
            id=activity.id,
            day_plan_id=activity.day_plan_id,
            title=activity.title,
            description=activity.description,
            type=activity.type,
            start_time=activity.start_time,
            end_time=activity.end_time,
            estimated_cost=activity.estimated_cost,
            order_index=activity.order_index,
            booking_url=activity.booking_url,
            notes=activity.notes,
            location=activity.location,
        ),
    )


# -----------------------------------------------------------------------
# POST /trips/{trip_id}/days/generate — AI tạo day_plans trống
# -----------------------------------------------------------------------
@day_router.post("/{trip_id}/days/generate", status_code=201)
def generate_days(
    trip_id: UUID,
    payload: GenerateDayPlansRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trip = _get_trip_or_404(db, trip_id, current_user)

    day_plans = generate_day_plans(
        db,
        trip_id=trip.id,
        start_date=trip.start_date,
        end_date=trip.end_date,
        overwrite=payload.overwrite,
    )

    total = len(day_plans)
    return BaseResponse(
        status_code=201,
        message=f"Đã tạo {total} ngày cho chuyến đi",
        data=[DayPlanBriefOut.model_validate(dp) for dp in day_plans],
    )
