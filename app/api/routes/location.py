from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.crud.location import (
    delete_location,
    get_location_by_id,
    upsert_location,
    upsert_many,
)
from app.db.database import get_db
from app.models.user import User
from app.schemas.location import (
    LocationNearbyOut,
    LocationOut,
    LocationSaveRequest,
)
from app.schemas.user import BaseResponse
from app.services import places_service

router = APIRouter(tags=["Locations"])


# ─── Guard ────────────────────────────────────────────────────────────────────

def _require_places_key() -> None:
    if not settings.GOOGLE_PLACES_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Google Places API key chưa được cấu hình",
        )


# ─── GET /locations/search ────────────────────────────────────────────────────

@router.get("/locations/search", response_model=BaseResponse)
async def search_locations(
    q: str = Query(..., min_length=1, description="Từ khoá tìm kiếm"),
    destination: str | None = Query(default=None, description="Thành phố / điểm đến"),
    limit: int = Query(default=10, ge=1, le=20),
    language: str = Query(default="vi"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Tìm kiếm địa điểm qua Google Places Text Search.
    Kết quả được upsert vào DB → trả về LocationOut kèm `id` thực trong DB.
    """
    _require_places_key()
    try:
        raw = await places_service.search_places(
            query=q, destination=destination, limit=limit, language=language
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Lỗi Google Places API: {exc}")

    locations = upsert_many(db, raw)
    data = [LocationOut.model_validate(loc) for loc in locations]
    return BaseResponse(
        status_code=200,
        message="OK",  # FIX ⚠️-6: "Tìm thấy N kết quả" → "OK" theo spec
        data=data,
    )


# ─── GET /locations/nearby ────────────────────────────────────────────────────

@router.get("/locations/nearby", response_model=BaseResponse)
async def nearby_locations(
    lat: float = Query(..., ge=-90, le=90, description="Vĩ độ hiện tại"),
    lng: float = Query(..., ge=-180, le=180, description="Kinh độ hiện tại"),
    radius: int = Query(default=1000, ge=100, le=50000, description="Bán kính tìm kiếm (mét)"),
    category: str | None = Query(
        default=None,
        description="Lọc theo loại: food, hotel, transport, attraction, shopping",
    ),
    language: str = Query(default="vi"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Tìm địa điểm gần toạ độ (lat, lng) trong bán kính `radius` mét.
    Upsert vào DB, trả về kèm `distance_meters`.
    """
    _require_places_key()
    try:
        raw = await places_service.search_nearby(
            lat=lat, lng=lng, radius=radius, category=category, language=language
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Lỗi Google Places API: {exc}")

    # Upsert (bỏ distance_meters trước khi lưu DB)
    places_data = [{k: v for k, v in p.items() if k != "distance_meters"} for p in raw]
    locations = upsert_many(db, places_data)

    # Gắn distance_meters vào response
    data = []
    for loc, raw_item in zip(locations, raw):
        out = LocationNearbyOut.model_validate(loc)
        out.distance_meters = raw_item.get("distance_meters")
        data.append(out)

    return BaseResponse(status_code=200, message="OK", data=data)


# ─── GET /locations/{location_id} ─────────────────────────────────────────────

@router.get("/locations/{location_id}", response_model=BaseResponse)
def get_location(
    location_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lấy chi tiết địa điểm đã có trong DB theo id."""
    location = get_location_by_id(db, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa điểm")
    return BaseResponse(
        status_code=200,
        message="OK",
        data=LocationOut.model_validate(location),
    )


# ─── POST /locations ──────────────────────────────────────────────────────────

@router.post("/locations")
def save_location(
    payload: LocationSaveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lưu (upsert) địa điểm vào DB theo google_place_id.
    - 200 → đã tồn tại trong DB (cập nhật thông tin)
    - 201 → tạo mới
    """
    location, is_new = upsert_location(db, payload)
    brief = {
        "id": str(location.id),
        "name": location.name,
        "google_place_id": location.google_place_id,
    }

    if is_new:
        return JSONResponse(
            status_code=201,
            content={
                "status_code": 201,
                "message": "Lưu địa điểm thành công",
                "data": brief,
            },
        )
    return JSONResponse(
        status_code=200,
        content={
            "status_code": 200,
            "message": "Địa điểm đã có trong hệ thống",
            "data": brief,
        },
    )


# ─── DELETE /locations/{location_id} ──────────────────────────────────────────

# FIX ❌-1: Endpoint này không có trong api_spec.md — ẩn khỏi OpenAPI docs
# Vẫn giữ lại cho admin/internal use nhưng không public
@router.delete("/locations/{location_id}", response_model=BaseResponse, include_in_schema=False)
def remove_location(
    location_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Xóa địa điểm khỏi DB.
    Trả về 409 nếu vẫn còn activity đang dùng địa điểm này.
    """
    location = get_location_by_id(db, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa điểm")
    if location.activities:
        raise HTTPException(
            status_code=409,
            detail=f"Không thể xóa: địa điểm đang dùng trong {len(location.activities)} hoạt động",
        )
    delete_location(db, location)
    return BaseResponse(status_code=200, message="Đã xóa địa điểm", data=None)
