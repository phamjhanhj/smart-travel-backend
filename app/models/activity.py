from __future__ import annotations

import uuid
from typing import Optional
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from app.db.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        Index("ix_activities_day_plan_order", "day_plan_id", "order_index"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    day_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("day_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # meal | attraction | hotel | transport | other
    start_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # "08:00"
    end_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # "11:00"
    estimated_cost: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    booking_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    day_plan: Mapped[DayPlan] = relationship("DayPlan", back_populates="activities")
    location: Mapped[Optional[Location]] = relationship(
        "Location", back_populates="activities"
    )
