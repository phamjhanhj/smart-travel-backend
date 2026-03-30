from datetime import date as dt_date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ─── Enums / constants ───────────────────────────────────────────────────────

CATEGORY_LABELS: dict[str, str] = {
    "food": "Ăn uống",
    "transport": "Di chuyển",
    "hotel": "Lưu trú",
    "activity": "Hoạt động tham quan",
    "other": "Khác",
}
ALL_CATEGORIES = list(CATEGORY_LABELS.keys())


# ─── Request schemas ──────────────────────────────────────────────────────────

class BudgetItemCreateRequest(BaseModel):
    category: str = Field(pattern="^(food|transport|hotel|activity|other)$")
    label: str = Field(min_length=1, max_length=200)
    planned_amount: int = Field(default=0, ge=0)
    actual_amount: int = Field(default=0, ge=0)
    date: dt_date | None = None


class BudgetItemUpdateRequest(BaseModel):
    """Partial update — chỉ field được truyền mới update."""
    category: str | None = Field(
        default=None, pattern="^(food|transport|hotel|activity|other)$"
    )
    label: str | None = Field(default=None, min_length=1, max_length=200)
    planned_amount: int | None = Field(default=None, ge=0)
    actual_amount: int | None = Field(default=None, ge=0)
    date: dt_date | None = None


# ─── Output schemas ───────────────────────────────────────────────────────────

class BudgetItemOut(BaseModel):
    id: UUID
    trip_id: UUID
    category: str
    label: str
    planned_amount: int
    actual_amount: int
    date: dt_date | None
    created_at: datetime
    updated_at: datetime | None = None  # ← FIX DB-3: trả updated_at khi PUT

    model_config = {"from_attributes": True}


class BudgetCategoryBreakdown(BaseModel):
    category: str
    label: str
    planned: int
    actual: int
    items_count: int


class BudgetSummaryOut(BaseModel):
    trip_id: UUID
    budget_total: int
    budget_planned: int
    budget_actual: int
    budget_remaining: int
    overspent: bool
    categories: list[BudgetCategoryBreakdown]
