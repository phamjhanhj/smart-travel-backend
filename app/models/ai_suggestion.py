from __future__ import annotations

from datetime import datetime, timezone
import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base
from app.core.enums import SuggestionStatus, SuggestionType


class AISuggestion(Base):
    __tablename__ = "ai_suggestions"

    __table_args__ = (
        CheckConstraint(
            f"type IN ({', '.join(repr(t.value) for t in SuggestionType)})",
            name="ck_ai_suggestions_type",
        ),
        CheckConstraint(
            f"status IN ({', '.join(repr(s.value) for s in SuggestionStatus)})",
            name="ck_ai_suggestions_status",
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
    type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # SuggestionType enum value
    content_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    status: Mapped[str] = mapped_column(
        String, default=SuggestionStatus.PENDING.value, nullable=False, index=True
    )  # SuggestionStatus enum value
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    trip: Mapped[Trip] = relationship("Trip", back_populates="ai_suggestions")
