"""
AI Chat & Suggestions routes.

POST   /trips/{trip_id}/chat              — Gửi message, AI trả lời (stream hoặc không)
GET    /trips/{trip_id}/chat/history      — Lịch sử hội thoại
GET    /trips/{trip_id}/suggestions       — Danh sách gợi ý AI
PATCH  /suggestions/{suggestion_id}/status — Accept / Reject gợi ý
"""
import asyncio
import json
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.enums import ChatRole, SuggestionStatus, SuggestionType
from app.crud.ai_chat import (
    create_suggestion,
    get_chat_history,
    get_recent_history_for_context,
    get_suggestion_by_id,
    get_suggestions,
    save_message,
    update_suggestion_status,
)
from app.crud.day_plan import get_day_plans_by_trip
from app.crud.trip import get_trip_by_id
from app.db.database import get_db
from app.models.user import User
from app.schemas.ai_chat import (
    AISuggestionOut,
    ChatHistoryItemOut,
    ChatMessageOut,
    ChatRequest,
    SuggestionStatusOut,
    SuggestionStatusRequest,
)
from app.schemas.user import BaseResponse
from app.services import ai_service
from app.services.itinerary_service import apply_itinerary

router = APIRouter(tags=["AI Chat"])


# ─── Guards & helpers ─────────────────────────────────────────────────────────

def _require_groq_key() -> None:
    if not settings.GROQ_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Groq API key chưa được cấu hình",
        )


def _get_trip_or_raise(db: Session, trip_id: UUID, current_user: User):
    trip = get_trip_by_id(db, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy chuyến đi")
    if trip.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập chuyến đi này")
    return trip


def _build_trip_context(db: Session, trip) -> dict:
    """Chuyển đổi Trip ORM object → dict context cho AI system prompt."""
    day_plans = get_day_plans_by_trip(db, trip.id)
    days = [
        {
            "day_number": dp.day_number,
            "date": str(dp.date),
            "activities": [
                {
                    "title": a.title,
                    "type": a.type,
                    "start_time": a.start_time,
                    "end_time": a.end_time,
                    "estimated_cost": a.estimated_cost,
                }
                for a in dp.activities
            ],
        }
        for dp in day_plans
    ]
    return {
        "destination": trip.destination,
        "start_date": str(trip.start_date),
        "end_date": str(trip.end_date),
        "budget": trip.budget,
        "num_travelers": trip.num_travelers,
        "preferences": trip.preferences,
        "day_plans": days,
    }


def _parse_suggestion_content(raw: str) -> dict:
    """Parse content_json string → dict để trả ra API."""
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except Exception:
        return {"raw": raw}


# ─── POST /trips/{trip_id}/chat ───────────────────────────────────────────────

@router.post("/trips/{trip_id}/chat")
async def chat(
    trip_id: UUID,
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Gửi tin nhắn tới AI. Hỗ trợ stream=true (SSE) và stream=false (JSON).
    AI nhận đầy đủ context: điểm đến, ngân sách, preferences, lịch trình.
    """
    _require_groq_key()
    trip = _get_trip_or_raise(db, trip_id, current_user)

    context = _build_trip_context(db, trip)
    system_prompt = ai_service.build_system_prompt(context)
    history = get_recent_history_for_context(db, trip_id)

    save_message(db, trip_id, role=ChatRole.USER.value, message=payload.message)

    # ── Stream mode ──────────────────────────────────────────────────────────
    if payload.stream:
        def _sse(payload_obj: dict) -> str:
            return f"data: {json.dumps(payload_obj, ensure_ascii=False)}\n\n"

        async def event_generator():
            full_text = ""
            try:
                async for delta in ai_service.chat_stream(system_prompt, history, payload.message):
                    full_text += delta
                    yield _sse({"status_code": 200, "message": "OK", "data": {"delta": delta}})
            except Exception as exc:
                yield _sse({
                    "status_code": 502,
                    "message": f"Lỗi AI: {exc}",
                    "data": {"error": str(exc)},
                })
                return

            clean_text = ai_service.strip_suggestion_block(full_text)
            assistant_msg = save_message(
                db, trip_id, role=ChatRole.ASSISTANT.value, message=clean_text
            )

            sug_type, sug_content = ai_service.extract_suggestion(full_text)
            suggestion_id = None
            if sug_type and sug_content:
                sug = create_suggestion(db, trip_id, sug_type, sug_content)
                suggestion_id = str(sug.id)

            yield _sse({
                "status_code": 200,
                "message": "OK",
                "data": {
                    "done": True,
                    "message_id": str(assistant_msg.id),
                    "suggestion_id": suggestion_id,
                },
            })

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # ── Non-stream mode ───────────────────────────────────────────────────────
    try:
        full_text = await asyncio.wait_for(
            ai_service.chat(system_prompt, history, payload.message),
            timeout=60.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="AI response timeout, vui lòng thử lại")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Lỗi Groq API: {exc}")

    clean_text = ai_service.strip_suggestion_block(full_text)
    assistant_msg = save_message(
        db, trip_id, role=ChatRole.ASSISTANT.value, message=clean_text
    )

    sug_type, sug_content = ai_service.extract_suggestion(full_text)
    suggestion_id = None
    if sug_type and sug_content:
        sug = create_suggestion(db, trip_id, sug_type, sug_content)
        suggestion_id = sug.id

    return BaseResponse(
        status_code=200,
        message="OK",
        data=ChatMessageOut(
            message_id=assistant_msg.id,
            role=ChatRole.ASSISTANT.value,
            message=clean_text,
            suggestion_id=suggestion_id,
            created_at=assistant_msg.created_at,
        ),
    )


# ─── GET /trips/{trip_id}/chat/history ───────────────────────────────────────

@router.get("/trips/{trip_id}/chat/history", response_model=BaseResponse)
def chat_history(
    trip_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    before: datetime | None = Query(
        default=None, description="ISO datetime — lấy messages trước mốc này"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lịch sử hội thoại AI của chuyến đi, tăng dần theo thời gian."""
    _get_trip_or_raise(db, trip_id, current_user)
    messages = get_chat_history(db, trip_id, limit=limit, before=before)
    data = [ChatHistoryItemOut.model_validate(m) for m in messages]
    return BaseResponse(status_code=200, message="OK", data=data)


# ─── GET /trips/{trip_id}/suggestions ────────────────────────────────────────

@router.get("/trips/{trip_id}/suggestions", response_model=BaseResponse)
def list_suggestions(
    trip_id: UUID,
    status: str | None = Query(
        default=None,
        description="Lọc theo trạng thái: pending | accepted | rejected",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Danh sách gợi ý AI đã tạo cho chuyến đi."""
    _get_trip_or_raise(db, trip_id, current_user)
    suggestions = get_suggestions(db, trip_id, status=status)

    data = [
        AISuggestionOut(
            id=s.id,
            trip_id=s.trip_id,
            type=s.type,
            status=s.status,
            content_json=_parse_suggestion_content(s.content_json),
            created_at=s.created_at,
        )
        for s in suggestions
    ]
    return BaseResponse(status_code=200, message="OK", data=data)


# ─── PATCH /suggestions/{suggestion_id}/status ───────────────────────────────

@router.patch("/suggestions/{suggestion_id}/status", response_model=BaseResponse)
def update_status(
    suggestion_id: UUID,
    payload: SuggestionStatusRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Accept hoặc Reject gợi ý AI.
    Nếu status='accepted' và type='itinerary' → tự động tạo activities vào day_plan.
    """
    suggestion = get_suggestion_by_id(db, suggestion_id)
    if suggestion is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy gợi ý")

    trip = get_trip_by_id(db, suggestion.trip_id)
    if trip is None or trip.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền thao tác gợi ý này")

    if suggestion.status == payload.status:
        raise HTTPException(
            status_code=409,
            detail=f"Gợi ý đã ở trạng thái '{suggestion.status}'",
        )
    if suggestion.status == SuggestionStatus.ACCEPTED.value:
        raise HTTPException(
            status_code=409,
            detail="Gợi ý đã được áp dụng, không thể đổi trạng thái",
        )

    activities_created = 0

    # ── Auto-apply itinerary (delegated to service layer) ─────────────────────
    if (
        payload.status == SuggestionStatus.ACCEPTED.value
        and suggestion.type == SuggestionType.ITINERARY.value
    ):
        activities_created, apply_error = apply_itinerary(db, suggestion, trip)
        if apply_error:
            raise HTTPException(status_code=400, detail=apply_error)

    update_suggestion_status(db, suggestion, payload.status)

    if payload.status == SuggestionStatus.ACCEPTED.value:
        msg = "Đã áp dụng gợi ý vào lịch trình" if activities_created else "Đã chấp nhận gợi ý"
    else:
        msg = "Đã bỏ qua gợi ý"

    return BaseResponse(
        status_code=200,
        message=msg,
        data=SuggestionStatusOut(
            suggestion_id=suggestion_id,
            status=payload.status,
            activities_created=activities_created,
        ),
    )
