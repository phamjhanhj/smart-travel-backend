from datetime import datetime
from typing import Optional, Any, Literal
from uuid import UUID

from pydantic import BaseModel


# ─── Chat ─────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    stream: bool = False


class ChatMessageOut(BaseModel):
    """Response cho 1 tin nhắn AI (non-stream)."""
    message_id: UUID
    role: str
    message: str
    suggestion_id: Optional[UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatHistoryItemOut(BaseModel):
    """1 entry trong lịch sử hội thoại."""
    id: UUID
    role: str
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Suggestions ──────────────────────────────────────────────────────────────

class AISuggestionOut(BaseModel):
    id: UUID
    trip_id: UUID
    type: str
    status: str
    content_json: Any  # parsed từ JSON string trong DB
    created_at: datetime

    model_config = {"from_attributes": True}


class SuggestionStatusRequest(BaseModel):
    # FIX AI-1: dùng Literal thay str → Pydantic tự validate, trả 422 chuẩn
    status: Literal["accepted", "rejected"]


class SuggestionStatusOut(BaseModel):
    suggestion_id: UUID
    status: str
    activities_created: int
