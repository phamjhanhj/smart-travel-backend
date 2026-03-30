import json
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.ai_suggestion import AISuggestion
from app.models.chat_history import ChatHistory


# ─── ChatHistory ──────────────────────────────────────────────────────────────

def save_message(db: Session, trip_id: UUID, role: str, message: str) -> ChatHistory:
    """Lưu 1 tin nhắn (user hoặc assistant) vào DB."""
    entry = ChatHistory(trip_id=trip_id, role=role, message=message)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_chat_history(
    db: Session,
    trip_id: UUID,
    limit: int = 50,
    before: datetime | None = None,
) -> list[ChatHistory]:
    """
    Lấy lịch sử hội thoại của trip, sắp xếp tăng dần theo thời gian.
    Nếu `before` được truyền, chỉ lấy các message có created_at < before.
    """
    query = (
        db.query(ChatHistory)
        .filter(ChatHistory.trip_id == trip_id)
    )
    if before:
        query = query.filter(ChatHistory.created_at < before)

    return (
        query.order_by(ChatHistory.created_at.asc())
        .limit(limit)
        .all()
    )


def get_recent_history_for_context(
    db: Session,
    trip_id: UUID,
    max_turns: int = 10,
) -> list[dict]:
    """
    Lấy N turn gần nhất để truyền vào Anthropic messages[].
    Trả về list[{"role": ..., "content": ...}].
    """
    rows = (
        db.query(ChatHistory)
        .filter(ChatHistory.trip_id == trip_id)
        .order_by(ChatHistory.created_at.desc())
        .limit(max_turns * 2)  # mỗi turn = 2 message
        .all()
    )
    rows.reverse()
    return [{"role": r.role, "content": r.message} for r in rows]


# ─── AISuggestion ─────────────────────────────────────────────────────────────

def create_suggestion(
    db: Session,
    trip_id: UUID,
    sug_type: str,
    content: dict,
) -> AISuggestion:
    """Tạo suggestion mới với status='pending'."""
    suggestion = AISuggestion(
        trip_id=trip_id,
        type=sug_type,
        content_json=json.dumps(content, ensure_ascii=False),
        status="pending",
    )
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)
    return suggestion


def get_suggestions(
    db: Session,
    trip_id: UUID,
    status: str | None = None,
) -> list[AISuggestion]:
    """Lấy danh sách suggestions của trip, filter theo status nếu có."""
    query = db.query(AISuggestion).filter(AISuggestion.trip_id == trip_id)
    if status:
        query = query.filter(AISuggestion.status == status)
    return query.order_by(AISuggestion.created_at.desc()).all()


def get_suggestion_by_id(db: Session, suggestion_id: UUID) -> AISuggestion | None:
    return db.query(AISuggestion).filter(AISuggestion.id == suggestion_id).first()


def update_suggestion_status(
    db: Session,
    suggestion: AISuggestion,
    status: str,
) -> AISuggestion:
    suggestion.status = status
    db.commit()
    db.refresh(suggestion)
    return suggestion
