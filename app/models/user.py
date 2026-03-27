import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String, Text, null
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid = True), primary_key = True, default = uuid.uuid4)
    email = Column(String, unique = True, nullable = False, index = True)
    password_hash = Column(Text, nullable = False)
    full_name = Column(String, nullable = False)
    avatar_url = Column(String, nullable = True)
    preferences_json = Column(Text, nullable = True)
    created_at = Column(DateTime(timezone = True), default = lambda: datetime.now(timezone.utc))