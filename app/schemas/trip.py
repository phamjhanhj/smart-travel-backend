from datetime import datetime, date
from pydantic import BaseModel, Field, model_validator
from uuid import UUID


class TripCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    destination: str = Field(min_length=1, max_length=200)
    start_date: datetime
    end_date: datetime
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
    budget: int | None = Field(default=None, ge=1)
    preferences: str | None = None
    status: str | None = Field(default=None, pattern="^(draft|active|completed)$")
    cover_image_url: str | None = None


class TripOut(BaseModel):
    id: UUID
    user_id: UUID
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

    model_config = {"from_attributes": True}


class TripListOut(BaseModel):
    trips: list[TripOut]
    total: int
    page: int
    limit: int


class DayPlanBriefOut(BaseModel):
    id: UUID
    day_number: int
    date: date
    activities_count: int = 0

    model_config = {"from_attributes": True}


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
