from app.models.activity import Activity
from app.schemas.activity import (
    ActivityCreateRequest,
    ActivityUpdateRequest,
    ReorderItem,
)
from sqlalchemy.orm import Session
from uuid import UUID


def create_activity(
    db: Session, day_plan_id: UUID, payload: ActivityCreateRequest
) -> Activity:
    if payload.order_index == 0:
        last = (
            db.query(Activity)
            .filter(Activity.day_plan_id == day_plan_id)
            .order_by(Activity.order_index.desc())
            .first()
        )
        order_index = (last.order_index + 1) if last else 0
    else:
        order_index = payload.order_index

    activity = Activity(
        day_plan_id=day_plan_id,
        title=payload.title,
        description=payload.description,
        type=payload.type,
        location_id=payload.location_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        estimated_cost=payload.estimated_cost,
        order_index=order_index,
        booking_url=payload.booking_url,
        notes=payload.notes,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


def update_activity(
    db: Session,
    activity: Activity,
    payload: ActivityUpdateRequest,
) -> Activity:
    data = payload.model_dump(exclude_none=True)
    for field, value in data.items():
        setattr(activity, field, value)
    db.commit()
    db.refresh(activity)
    return activity


def delete_activity(db: Session, activity: Activity) -> None:
    """Xóa activity."""
    db.delete(activity)
    db.commit()


def reorder_activities(
    db: Session,
    day_plan_id: UUID,
    items: list[ReorderItem],
) -> None:
    try:
        for item in items:
            db.query(Activity).filter(
                Activity.id == item.id,
                Activity.day_plan_id == day_plan_id,  # bảo vệ: chỉ update đúng ngày
            ).update({"order_index": item.order_index})

        db.commit()
    except Exception:
        db.rollback()
        raise


def get_activity_by_id(db: Session, activity_id: UUID) -> Activity | None:
    """Lấy 1 activity theo id."""
    return db.query(Activity).filter(Activity.id == activity_id).first()
