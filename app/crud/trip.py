from datetime import timedelta, date
from fastapi import HTTPException
from app.models.day_plan import DayPlan
from app.models.trip import Trip
from app.schemas.trip import TripCreateRequest, TripUpdateRequest
from sqlalchemy.orm import Session
from uuid import UUID


def get_trips_by_user(
    db: Session,
    user_id: UUID,
    status: str | None = None,
    page: int = 1,
    limit: int = 10,
) -> tuple[list[Trip], int]:
    # Lấy danh sách chuyến đi của người dùng với phân trang
    query = db.query(Trip).filter(Trip.user_id == user_id)
    if status:
        query = query.filter(Trip.status == status)

    total = query.count()
    items = (
        query.order_by(Trip.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return items, total


def get_trip_by_id(db: Session, trip_id: UUID) -> Trip:
    if trip_id is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy chuyến đi")
    return db.query(Trip).filter(Trip.id == trip_id).first()


def create_trip(db: Session, user_id: UUID, payload: TripCreateRequest) -> Trip:
    trip = Trip(
        user_id=user_id,
        title=payload.title,
        destination=payload.destination,
        start_date=payload.start_date,
        end_date=payload.end_date,
        budget=payload.budget,
        num_travelers=payload.num_travelers,
        preferences=payload.preferences,
        status="draft",
    )
    db.add(trip)
    db.flush()  # Lấy ID của trip mới tạo trước khi commit
    create_day_plan(db, trip.id, payload.start_date, payload.end_date)
    db.commit()
    db.refresh(trip)
    return trip


def create_day_plan(db: Session, trip_id: UUID, start_date: date, end_date: date):
    current = start_date
    day_number = 1
    while current <= end_date:
        day_plan = DayPlan(trip_id=trip_id, day_number=day_number, date=current)
        db.add(day_plan)
        current += timedelta(days=1)
        day_number += 1
    db.commit()


def update_trip(db: Session, trip: Trip, payload: TripUpdateRequest) -> Trip:
    """Partial update — chỉ cập nhật field được truyền."""
    data = payload.model_dump(exclude_none=True)
    for field, value in data.items():
        setattr(trip, field, value)
    db.commit()
    db.refresh(trip)
    return trip


def delete_trip(db: Session, trip: Trip):
    db.delete(trip)
    db.commit()


def get_trip_summary(db: Session, trip: Trip) -> dict:
    from app.models.day_plan import DayPlan
    from app.models.activity import Activity
    from app.models.budget_item import BudgetItem

    total_days = db.query(DayPlan).filter(DayPlan.trip_id == trip.id).count()

    total_activities = (
        db.query(Activity)
        .join(DayPlan, Activity.day_plan_id == DayPlan.id)
        .filter(DayPlan.trip_id == trip.id)
        .count()
    )

    budget_items = db.query(BudgetItem).filter(BudgetItem.trip_id == trip.id).all()

    budget_planned = sum(i.planned_amount or 0 for i in budget_items)
    budget_actual = sum(i.actual_amount or 0 for i in budget_items)
    budget_total = trip.budget or 0
    budget_remaining = budget_total - budget_actual
    overspent = budget_actual > budget_total
    budget_used_percent = (
        round(budget_actual / budget_total * 100) if budget_total > 0 else 0
    )

    categories = ["food", "transport", "hotel", "activity", "other"]
    by_category = {}
    for cat in categories:
        items = [i for i in budget_items if i.category == cat]
        by_category[cat] = {
            "planned": sum(i.planned_amount or 0 for i in items),
            "actual": sum(i.actual_amount or 0 for i in items),
        }

    return {
        "trip_id": trip.id,
        "total_days": total_days,
        "total_activities": total_activities,
        "budget_total": budget_total,
        "budget_planned": budget_planned,
        "budget_actual": budget_actual,
        "budget_remaining": budget_remaining,
        "overspent": overspent,
        "budget_used_percent": budget_used_percent,
        "by_category": by_category,
    }
