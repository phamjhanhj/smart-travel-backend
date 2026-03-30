from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.day_plan import _get_day_or_404, _get_trip_or_404
from app.crud.activity import (
    create_activity,
    delete_activity,
    get_activity_by_id,
    reorder_activities,
    update_activity,
)
from app.crud.day_plan import get_day_plan_by_id
from app.db.database import get_db
from app.schemas.activity import (
    ActivityCreateRequest,
    ActivityOut,
    ActivityReorderRequest,
    ActivityUpdateRequest,
)
from app.models.user import User
from app.schemas.user import BaseResponse

activity_router = APIRouter(prefix="/activities", tags=["Activities"])


def _get_activity_or_404(db: Session, activity_id: UUID, current_user: User):
    """
    Lấy activity, kiểm tra tồn tại và quyền sở hữu
    bằng cách đi qua day_plan → trip → user.
    """
    activity = get_activity_by_id(db, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Không tìm thấy hoạt động")
    # Kiểm tra quyền qua relationship
    if activity.day_plan.trip.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Bạn không có quyền thao tác hoạt động này"
        )
    return activity


# -----------------------------------------------------------------------
# PUT /activities/{activity_id} — cập nhật activity
# -----------------------------------------------------------------------
@activity_router.put("/{activity_id}")
def update(
    activity_id: UUID,
    payload: ActivityUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    activity = _get_activity_or_404(db, activity_id, current_user)
    updated = update_activity(db, activity, payload)

    return BaseResponse(
        status_code=200,
        message="Cập nhật thành công",
        data=ActivityOut(
            id=updated.id,
            day_plan_id=updated.day_plan_id,
            title=updated.title,
            description=updated.description,
            type=updated.type,
            start_time=(
                updated.start_time.strftime("%H:%M") if updated.start_time else None
            ),
            end_time=updated.end_time.strftime("%H:%M") if updated.end_time else None,
            estimated_cost=updated.estimated_cost,
            order_index=updated.order_index,
            booking_url=updated.booking_url,
            notes=updated.notes,
            location=updated.location,
        ),
    )


# -----------------------------------------------------------------------
# DELETE /activities/{activity_id} — xóa activity
# -----------------------------------------------------------------------
@activity_router.delete("/{activity_id}")
def delete(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    activity = _get_activity_or_404(db, activity_id, current_user)
    delete_activity(db, activity)

    return BaseResponse(status_code=200, message="Đã xóa hoạt động", data=None)


# -----------------------------------------------------------------------
# PATCH /activities/reorder — cập nhật thứ tự kéo thả
# QUAN TRỌNG: route này phải đặt TRƯỚC /{activity_id}
# vì FastAPI match từ trên xuống — "reorder" sẽ bị hiểu là {activity_id}
# -----------------------------------------------------------------------
@activity_router.patch("/reorder")
def reorder(
    payload: ActivityReorderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Kiểm tra day_plan tồn tại và thuộc về user
    day = get_day_plan_by_id(db, payload.day_plan_id)
    if not day:
        raise HTTPException(status_code=404, detail="Không tìm thấy ngày")
    if day.trip.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền thao tác")

    reorder_activities(db, payload.day_plan_id, payload.items)

    return BaseResponse(status_code=200, message="Đã cập nhật thứ tự", data=None)
