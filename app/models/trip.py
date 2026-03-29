from typing import List
import uuid
from datetime import datetime, timezone
from sqlalchemy import UUID, Date, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    destination: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    end_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    budget: Mapped[int | None] = mapped_column(Integer, nullable=True)
    num_travelers: Mapped[int] = mapped_column(Integer, default=1)
    preferences: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True)
    cover_image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship("User", back_populates="trips")

    day_plans: Mapped[List["DayPlan"]] = relationship(
        "DayPlan",
        back_populates="trip",
        cascade="all, delete-orphan",
        order_by="DayPlan.day_number",
    )


# Đặt import ở cuối để tránh circular import
# from app.models.day_plan import DayPlan
# from app.models.user import User
