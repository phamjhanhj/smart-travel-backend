from __future__ import annotations

from typing import Optional
import uuid
from datetime import datetime, timezone, date
from sqlalchemy import UUID, CheckConstraint, Date, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base
from app.core.enums import TripStatus


class Trip(Base):
    __tablename__ = "trips"

    __table_args__ = (
        CheckConstraint(
            f"status IN ({', '.join(repr(s.value) for s in TripStatus)})",
            name="ck_trips_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    destination: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    budget: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    num_travelers: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    preferences: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String, default=TripStatus.DRAFT.value, nullable=False, index=True
    )  # TripStatus enum value
    cover_image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    owner: Mapped[User] = relationship("User", back_populates="trips")
    day_plans: Mapped[list[DayPlan]] = relationship(
        "DayPlan",
        back_populates="trip",
        cascade="all, delete-orphan",
        order_by="DayPlan.day_number",
    )
    chat_history: Mapped[list[ChatHistory]] = relationship(
        "ChatHistory", back_populates="trip", cascade="all, delete-orphan"
    )
    ai_suggestions: Mapped[list[AISuggestion]] = relationship(
        "AISuggestion", back_populates="trip", cascade="all, delete-orphan"
    )
    budget_items: Mapped[list[BudgetItem]] = relationship(
        "BudgetItem", back_populates="trip", cascade="all, delete-orphan"
    )
