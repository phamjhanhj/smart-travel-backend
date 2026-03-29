import uuid
from sqlalchemy import Date, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class DayPlan(Base):
    __tablename__ = "day_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False
    )
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[Date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        UniqueConstraint("trip_id", "day_number", name="uq_trip_day_number"),
    )

    trip: Mapped["Trip"] = relationship("Trip", back_populates="day_plans")


# Đặt import ở cuối để tránh circular import
# from app.models.trip import Trip
