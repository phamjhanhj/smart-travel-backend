from datetime import datetime, timezone
import uuid
from app.db.database import Base
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # user_id: Mapped[uuid.UUID] = mapped_column(
    #     UUID(as_uuid=True),
    #     ForeignKey("users.id", ondelete="CASCADE"),
    #     nullable=False,
    #     index=True,
    # )
    role: Mapped[str] = mapped_column(String, nullable=False)  # user | assistant
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    trip: Mapped[Trip] = relationship("Trip", back_populates="chat_history")
    # user: Mapped[User] = relationship("User", back_populates="chat_history")
