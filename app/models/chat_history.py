from __future__ import annotations

from datetime import datetime, timezone
import uuid
from app.db.database import Base
from app.core.enums import ChatRole
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class ChatHistory(Base):
    __tablename__ = "chat_history"

    __table_args__ = (
        Index("ix_chat_history_trip_created", "trip_id", "created_at"),
        CheckConstraint(
            f"role IN ({', '.join(repr(r.value) for r in ChatRole)})",
            name="ck_chat_history_role",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String, nullable=False)  # ChatRole enum value
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    trip: Mapped[Trip] = relationship("Trip", back_populates="chat_history")
