from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.crud.budget import (
    create_budget_item,
    delete_budget_item,
    get_budget_item_by_id,
    get_budget_items,
    get_budget_summary,
    update_budget_item,
)
from app.crud.trip import get_trip_by_id
from app.db.database import get_db
from app.models.user import User
from app.schemas.budget import (
    BudgetItemCreateRequest,
    BudgetItemOut,
    BudgetItemUpdateRequest,
)
from app.schemas.user import BaseResponse

router = APIRouter(tags=["Budget"])


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_trip_or_raise(db: Session, trip_id: UUID, current_user: User):
    """Lấy trip và kiểm tra quyền sở hữu. Raise 404/403 nếu vi phạm."""
    trip = get_trip_by_id(db, trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy chuyến đi")
    if trip.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập chuyến đi này")
    return trip


def _get_item_and_verify_ownership(db: Session, item_id: UUID, current_user: User):
    """Lấy budget item, sau đó verify trip thuộc user. Raise 404/403 nếu vi phạm."""
    item = get_budget_item_by_id(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy khoản chi")
    # Kiểm tra trip thuộc user
    trip = get_trip_by_id(db, item.trip_id)
    if trip is None or trip.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền thao tác khoản chi này")
    return item


# ─── Budget summary ───────────────────────────────────────────────────────────

@router.get("/trips/{trip_id}/budget")
def get_trip_budget(
    trip_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Tổng quan ngân sách chuyến đi, phân category."""
    trip = _get_trip_or_raise(db, trip_id, current_user)
    summary = get_budget_summary(db, trip_id, budget_total=trip.budget or 0)
    return BaseResponse(status_code=200, message="OK", data=summary)


# ─── Budget items ─────────────────────────────────────────────────────────────

@router.get("/trips/{trip_id}/budget/items")
def list_budget_items(
    trip_id: UUID,
    category: str | None = Query(
        default=None,
        pattern="^(food|transport|hotel|activity|other)$",
        description="Lọc theo danh mục",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy danh sách khoản chi của chuyến đi."""
    _get_trip_or_raise(db, trip_id, current_user)
    items = get_budget_items(db, trip_id, category=category)
    return BaseResponse(
        status_code=200,
        message="OK",
        data=[BudgetItemOut.model_validate(i) for i in items],
    )


@router.post("/trips/{trip_id}/budget/items", status_code=201)
def create_item(
    trip_id: UUID,
    payload: BudgetItemCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Thêm khoản chi mới cho chuyến đi."""
    _get_trip_or_raise(db, trip_id, current_user)
    item = create_budget_item(db, trip_id, payload)
    return BaseResponse(
        status_code=201,
        message="Thêm khoản chi thành công",  # FIX BUDGET-1: "Tạo" → "Thêm" theo spec
        data=BudgetItemOut.model_validate(item),
    )


@router.put("/budget/items/{item_id}")
def update_item(
    item_id: UUID,
    payload: BudgetItemUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cập nhật khoản chi (partial update)."""
    item = _get_item_and_verify_ownership(db, item_id, current_user)
    updated = update_budget_item(db, item, payload)
    return BaseResponse(
        status_code=200,
        message="Cập nhật thành công",  # FIX ⚠️-3: khớp với spec
        data=BudgetItemOut.model_validate(updated),
    )


@router.delete("/budget/items/{item_id}")
def delete_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Xóa khoản chi."""
    item = _get_item_and_verify_ownership(db, item_id, current_user)
    delete_budget_item(db, item)
    return BaseResponse(status_code=200, message="Đã xóa khoản chi", data=None)
