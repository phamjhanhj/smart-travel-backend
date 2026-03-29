from datetime import timedelta, date
from app.models.day_plan import DayPlan
from app.models.trip import Trip
from app.schemas.trip import TripCreateRequest
from sqlalchemy.orm import Session
from uuid import UUID


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
