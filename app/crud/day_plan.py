from datetime import date, timedelta
from uuid import UUID
from sqlalchemy.orm import Session, selectinload
from app.models.activity import Activity
from app.models.day_plan import DayPlan


def get_day_plans_by_trip(db: Session, trip_id: UUID) -> list[DayPlan]:
    """Lấy tất cả ngày của trip, kèm activities + location (eager load)."""
    return (
        db.query(DayPlan)
        .filter(DayPlan.trip_id == trip_id)
        .options(
            selectinload(DayPlan.activities).selectinload(Activity.location),
        )
        .order_by(DayPlan.day_number)
        .all()
    )


def get_day_plan_by_id(db: Session, day_id: UUID) -> DayPlan | None:
    """Lấy 1 ngày theo id."""
    return db.query(DayPlan).filter(DayPlan.id == day_id).first()


def generate_day_plans(
    db: Session,
    trip_id: UUID,
    start_date: date,
    end_date: date,
    overwrite: bool = False,
) -> list[DayPlan]:
    """
    Tạo day_plans trống cho toàn bộ số ngày trong trip.
    overwrite=True: xóa hết day_plans cũ (kéo theo activities) rồi tạo lại.
    overwrite=False: chỉ tạo nếu chưa có ngày nào.
    """
    if overwrite:
        # Xóa tất cả day_plans cũ — cascade tự xóa activities
        db.query(DayPlan).filter(DayPlan.trip_id == trip_id).delete()
        db.flush()
    else:
        # Không ghi đè nếu đã có
        existing = db.query(DayPlan).filter(DayPlan.trip_id == trip_id).count()
        if existing > 0:
            return (
                db.query(DayPlan)
                .filter(DayPlan.trip_id == trip_id)
                .order_by(DayPlan.day_number)
                .all()
            )

    # Tạo mới
    current = start_date
    day_number = 1
    new_days: list[DayPlan] = []

    while current <= end_date:
        dp = DayPlan(
            trip_id=trip_id,
            day_number=day_number,
            date=current,
        )
        db.add(dp)
        new_days.append(dp)
        current += timedelta(days=1)
        day_number += 1

    db.commit()
    for dp in new_days:
        db.refresh(dp)

    return new_days
