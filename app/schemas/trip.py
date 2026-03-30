from datetime import datetime, date
from pydantic import BaseModel, Field, model_validator
from uuid import UUID
# FIX ⚠️-7b: import DayPlanBriefOut từ day_plan.py — single source of truth
from app.schemas.day_plan import DayPlanBriefOut


class TripCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    destination: str = Field(min_length=1, max_length=200)
    start_date: date  # ← FIX TRIP-2: dùng date thay vì datetime
    end_date: date    # ← FIX TRIP-2: nhất quán với DB và TripOut
    budget: int | None = Field(default=None, ge=0)
    num_travelers: int = Field(default=1, ge=1)
    preferences: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def check_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("Ngày kết thúc phải sau ngày bắt đầu")
        return self


class TripUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    destination: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    budget: int | None = Field(default=None, ge=0)
    num_travelers: int | None = Field(default=None, ge=1)  # FIX 💡-6: thêm field theo spec
    preferences: str | None = None
    status: str | None = Field(default=None, pattern="^(draft|active|completed)$")
    cover_image_url: str | None = None


class TripOut(BaseModel):
    id: UUID
    # user_id đã bỏ — FIX TRIP-3: spec không yêu cầu expose user_id
    title: str
    destination: str
    start_date: date
    end_date: date
    budget: int | None
    num_travelers: int
    status: str
    preferences: str | None
    cover_image_url: str | None
    created_at: datetime
    updated_at: datetime | None = None  # ← FIX DB-2: trả updated_at khi PUT

    model_config = {"from_attributes": True}


class TripListOut(BaseModel):
    items: list[TripOut]  # ← FIX TRIP-1: "trips" → "items" theo API spec
    total: int
    page: int
    limit: int


# DayPlanBriefOut được import từ app.schemas.day_plan (FIX ⚠️-7b)
# Định nghĩa đã được xóa khỏi đây để tránh conflict
__all__ = ["DayPlanBriefOut"]  # re-export để các route import từ trip hoặc day_plan đều được


class TripDetailOut(TripOut):
    day_plans: list[DayPlanBriefOut] = []


class BudgetCategoryOut(BaseModel):
    planned: int
    actual: int


class TripSummaryOut(BaseModel):
    """Response cho GET /trips/{id}/summary."""

    trip_id: UUID
    total_days: int
    total_activities: int
    budget_total: int
    budget_planned: int
    budget_actual: int
    budget_remaining: int
    budget_used_percent: int
    by_category: dict[str, BudgetCategoryOut]
