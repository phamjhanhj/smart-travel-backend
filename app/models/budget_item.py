from datetime import datetime, timezone, date
from typing import Optional
import uuid

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from app.db.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID


class BudgetItem(Base):
    __tablename__ = "budget_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String, nullable=False
    )  # food | transport | hotel | activity | other
    label: Mapped[str] = mapped_column(String, nullable=False)
    planned_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    actual_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    trip: Mapped[Trip] = relationship("Trip", back_populates="budget_items")
