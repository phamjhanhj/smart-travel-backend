from uuid import UUID
from datetime import date
from pydantic import BaseModel

from app.schemas.activity import ActivityBriefOut, ActivityOut


class DayPlanOut(BaseModel):
    """Response GET /days/{day_id} — activities không kèm full location."""

    id: UUID
    trip_id: UUID
    day_number: int
    date: date
    activities: list[ActivityBriefOut] = []

    model_config = {"from_attributes": True}


class DayPlanWithActivitiesOut(BaseModel):
    """Response GET /days — activities kèm full location lồng nhau."""

    id: UUID
    day_number: int
    date: date
    activities: list[ActivityOut] = []

    model_config = {"from_attributes": True}

    @classmethod
    def from_day_plan(cls, dp) -> "DayPlanWithActivitiesOut":
        """Build từ ORM DayPlan, map activities kèm location."""
        return cls(
            id=dp.id,
            day_number=dp.day_number,
            date=dp.date,
            activities=[ActivityOut.model_validate(act) for act in dp.activities],
        )


class DayPlanBriefOut(BaseModel):
    """Tóm tắt ngày — dùng trong response trip detail và generate.
    FIX ⚠️-7: Single source of truth, gộp với phiên bản trong trip.py
    """

    id: UUID
    day_number: int
    date: date
    activities_count: int = 0  # FIX ⚠️-7: thêm field — trước đây chỉ có trong trip.py

    model_config = {"from_attributes": True}

    @classmethod
    def from_day_plan(cls, dp) -> "DayPlanBriefOut":
        """Build từ ORM DayPlan — tính activities_count từ relationship."""
        return cls(
            id=dp.id,
            day_number=dp.day_number,
            date=dp.date,
            activities_count=len(dp.activities),
        )


# -----------------------------------------------------------------------
# Generate day plans
# -----------------------------------------------------------------------
class GenerateDayPlansRequest(BaseModel):
    overwrite: bool = False
