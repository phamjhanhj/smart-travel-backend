from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.budget_item import BudgetItem
from app.schemas.budget import (
    ALL_CATEGORIES,
    CATEGORY_LABELS,
    BudgetCategoryBreakdown,
    BudgetItemCreateRequest,
    BudgetItemUpdateRequest,
    BudgetSummaryOut,
)


# ─── Read ─────────────────────────────────────────────────────────────────────

def get_budget_items(
    db: Session,
    trip_id: UUID,
    category: str | None = None,
) -> list[BudgetItem]:
    """Lấy tất cả BudgetItem của trip, filter theo category nếu có."""
    query = db.query(BudgetItem).filter(BudgetItem.trip_id == trip_id)
    if category:
        query = query.filter(BudgetItem.category == category)
    return query.order_by(BudgetItem.created_at.asc()).all()


def get_budget_item_by_id(db: Session, item_id: UUID) -> BudgetItem | None:
    """Lấy 1 BudgetItem theo id."""
    return db.query(BudgetItem).filter(BudgetItem.id == item_id).first()


def get_budget_summary(db: Session, trip_id: UUID, budget_total: int) -> BudgetSummaryOut:
    """
    Tính tổng từ tất cả budget_items của trip.
    Group by category và so sánh với trip.budget.
    """
    items = db.query(BudgetItem).filter(BudgetItem.trip_id == trip_id).all()

    budget_planned = sum(i.planned_amount or 0 for i in items)
    budget_actual = sum(i.actual_amount or 0 for i in items)
    budget_remaining = budget_total - budget_actual
    overspent = budget_actual > budget_total

    categories: list[BudgetCategoryBreakdown] = []
    for cat in ALL_CATEGORIES:
        cat_items = [i for i in items if i.category == cat]
        categories.append(
            BudgetCategoryBreakdown(
                category=cat,
                label=CATEGORY_LABELS[cat],
                planned=sum(i.planned_amount or 0 for i in cat_items),
                actual=sum(i.actual_amount or 0 for i in cat_items),
                items_count=len(cat_items),
            )
        )

    return BudgetSummaryOut(
        trip_id=trip_id,
        budget_total=budget_total,
        budget_planned=budget_planned,
        budget_actual=budget_actual,
        budget_remaining=budget_remaining,
        overspent=overspent,
        categories=categories,
    )


# ─── Write ────────────────────────────────────────────────────────────────────

def create_budget_item(
    db: Session,
    trip_id: UUID,
    payload: BudgetItemCreateRequest,
) -> BudgetItem:
    """Tạo mới BudgetItem cho trip."""
    item = BudgetItem(
        trip_id=trip_id,
        category=payload.category,
        label=payload.label,
        planned_amount=payload.planned_amount,
        actual_amount=payload.actual_amount,
        date=payload.date,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_budget_item(
    db: Session,
    item: BudgetItem,
    payload: BudgetItemUpdateRequest,
) -> BudgetItem:
    """Partial update — chỉ cập nhật field được truyền."""
    data = payload.model_dump(exclude_none=True)
    # FIX ❌-2b: SQLAlchemy onupdate không trigger với setattr pattern → set thủ công
    data["updated_at"] = datetime.now(timezone.utc)
    for field, value in data.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def delete_budget_item(db: Session, item: BudgetItem) -> None:
    """Xóa BudgetItem."""
    db.delete(item)
    db.commit()
