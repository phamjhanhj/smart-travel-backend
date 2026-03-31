"""
Service layer: áp dụng gợi ý lịch trình (itinerary) từ AI vào DayPlan.

Tách khỏi route để dễ unit-test và tái sử dụng.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.ai_suggestion import AISuggestion
from app.models.day_plan import DayPlan


def apply_itinerary(
    db: Session,
    suggestion: AISuggestion,
    trip,
) -> tuple[int, str | None]:
    """
    Khi user accept gợi ý 'itinerary':
    - Đọc content_json.day_number → tìm DayPlan tương ứng
    - Tạo Activity cho mỗi item trong content_json.activities

    Returns:
        (activities_created: int, error_message: str | None)
    """
    try:
        content = json.loads(suggestion.content_json)
    except Exception:
        return 0, "Nội dung gợi ý không hợp lệ"

    day_number = content.get("day_number")
    activities_data = content.get("activities", [])
    if not day_number or not activities_data:
        return 0, "Gợi ý itinerary thiếu day_number hoặc activities"

    day_plan = (
        db.query(DayPlan)
        .filter(
            DayPlan.trip_id == trip.id,
            DayPlan.day_number == day_number,
        )
        .first()
    )
    if day_plan is None:
        return 0, f"Không tìm thấy ngày thứ {day_number} trong chuyến đi"

    # Lấy order_index tiếp theo (sau activity cuối cùng hiện có)
    last = (
        db.query(Activity)
        .filter(Activity.day_plan_id == day_plan.id)
        .order_by(Activity.order_index.desc())
        .first()
    )
    next_order = (last.order_index + 1) if last else 0

    count = 0
    for item in activities_data:
        activity = Activity(
            day_plan_id=day_plan.id,
            title=item.get("title", "Hoạt động"),
            type=item.get("type"),
            start_time=item.get("start_time"),
            end_time=item.get("end_time"),
            estimated_cost=item.get("estimated_cost"),
            order_index=next_order,
        )
        db.add(activity)
        next_order += 1
        count += 1

    db.commit()
    return count, None
