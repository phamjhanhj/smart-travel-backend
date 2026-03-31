"""
Groq AI service for AI Chat.

Hỗ trợ:
- Xây dựng system prompt giàu context (trip + schedule + budget + preferences)
- Gửi message và nhận response (non-stream)
- Streaming qua SSE (stream=True)
- Trích xuất structured suggestion từ response text của AI

Sử dụng Groq API (free tier) với Llama 3.3 70B model.
"""

from __future__ import annotations

import json
import re
from typing import AsyncIterator

from groq import AsyncGroq

from app.core.config import settings

# ─── Model ────────────────────────────────────────────────────────────────────

_MODEL = "llama-3.3-70b-versatile"  # Mạnh, nhanh, free trên Groq
_MAX_TOKENS = 2048


# ─── Client factory ───────────────────────────────────────────────────────────


def _client() -> AsyncGroq:
    return AsyncGroq(api_key=settings.GROQ_API_KEY)


# ─── System prompt ────────────────────────────────────────────────────────────


def build_system_prompt(trip_context: dict) -> str:
    """
    Tạo system prompt giàu context từ thông tin chuyến đi.
    trip_context gồm: destination, start_date, end_date, budget,
                      num_travelers, preferences, day_plans (list ngày + activities)
    """
    destination = trip_context.get("destination", "không xác định")
    start_date = trip_context.get("start_date", "")
    end_date = trip_context.get("end_date", "")
    budget = trip_context.get("budget")
    num_travelers = trip_context.get("num_travelers", 1)
    preferences = trip_context.get("preferences", "")
    day_plans = trip_context.get("day_plans", [])

    budget_str = f"{budget:,}đ" if budget else "chưa đặt"

    schedule_lines = []
    for dp in day_plans:
        day_num = dp.get("day_number")
        date_str = dp.get("date", "")
        activities = dp.get("activities", [])
        if activities:
            acts = ", ".join(
                f"{a.get('title')} ({a.get('start_time', '?')}-{a.get('end_time', '?')})"
                for a in activities
            )
            schedule_lines.append(f"  Ngày {day_num} ({date_str}): {acts}")
        else:
            schedule_lines.append(f"  Ngày {day_num} ({date_str}): chưa có lịch")

    schedule_str = (
        "\n".join(schedule_lines) if schedule_lines else "  Chưa có lịch trình"
    )

    return f"""Bạn là trợ lý du lịch thông minh, chuyên tư vấn lịch trình và địa điểm tại Việt Nam.
Bạn đang hỗ trợ chuyến đi với thông tin sau:

THÔNG TIN CHUYẾN ĐI:
- Điểm đến: {destination}
- Thời gian: {start_date} → {end_date}
- Ngân sách tổng: {budget_str}
- Số người: {num_travelers}
- Sở thích / ghi chú: {preferences or "không có"}

LỊCH TRÌNH HIỆN TẠI:
{schedule_str}

HƯỚNG DẪN:
- Trả lời bằng tiếng Việt, thân thiện và cụ thể.
- Khi gợi ý địa điểm ăn uống, tham quan: đưa tên, địa chỉ, giá ước tính.
- Khi gợi ý lịch trình theo ngày: đưa đầy đủ giờ bắt đầu, kết thúc, loại hoạt động.
- Nếu nhận diện được đây là gợi ý có thể áp dụng vào lịch (itinerary) hoặc danh sách địa điểm (place),
  hãy thêm một block JSON ở cuối response theo format sau (KHÔNG hiện trong text bình thường):

  Cho itinerary:
  <!--SUGGESTION:itinerary
  {{"title": "...", "day_number": 1, "activities": [{{"title": "...", "type": "...", "start_time": "HH:MM", "end_time": "HH:MM", "estimated_cost": 0}}]}}
  -->

  Cho place:
  <!--SUGGESTION:place
  {{"title": "...", "places": [{{"name": "...", "address": "...", "category": "...", "estimated_cost": 0, "note": "..."}}]}}
  -->

- Nếu không có gợi ý có thể áp dụng, KHÔNG thêm block JSON.
"""


# ─── Chat (non-stream) ────────────────────────────────────────────────────────


async def chat(
    system: str,
    history: list[dict],  # [{"role": "user"|"assistant", "content": "..."}]
    user_message: str,
) -> str:
    """Gửi message và trả về full response text."""
    messages = [{"role": "system", "content": system}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    client = _client()
    response = await client.chat.completions.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        messages=messages,
    )

    return response.choices[0].message.content


# ─── Chat (stream) ────────────────────────────────────────────────────────────


async def chat_stream(
    system: str,
    history: list[dict],
    user_message: str,
) -> AsyncIterator[str]:
    """Yield từng delta text từ Groq streaming API."""
    messages = [{"role": "system", "content": system}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    client = _client()
    stream = await client.chat.completions.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        messages=messages,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


# ─── Suggestion extractor ─────────────────────────────────────────────────────

_SUGGESTION_RE = re.compile(
    r"<!--SUGGESTION:(?P<type>\w+)\s+(?P<json>\{.*?\})\s*-->",
    re.DOTALL,
)


def extract_suggestion(text: str) -> tuple[str | None, dict | None]:
    """
    Trích xuất suggestion từ response text.
    Returns: (suggestion_type, content_dict) hoặc (None, None).
    """
    match = _SUGGESTION_RE.search(text)
    if not match:
        return None, None
    try:
        sug_type = match.group("type")
        content = json.loads(match.group("json"))
        return sug_type, content
    except (json.JSONDecodeError, KeyError):
        return None, None


def strip_suggestion_block(text: str) -> str:
    """Xóa block <!--SUGGESTION:...--> khỏi response trước khi lưu vào chat_history."""
    return _SUGGESTION_RE.sub("", text).strip()
