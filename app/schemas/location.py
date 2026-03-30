from typing import Optional
from uuid import UUID

from pydantic import BaseModel


# ─── DB-backed location output ────────────────────────────────────────────────

class LocationBriefOut(BaseModel):
    """Dùng trong ActivityOut (embed nhỏ gọn)."""
    id: UUID
    name: str
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    category: Optional[str] = None
    photo_url: Optional[str] = None
    rating: Optional[float] = None

    model_config = {"from_attributes": True}


class LocationOut(BaseModel):
    """Full location đã lưu trong DB."""
    id: UUID
    name: str
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    category: Optional[str] = None
    google_place_id: Optional[str] = None
    photo_url: Optional[str] = None
    rating: Optional[float] = None

    model_config = {"from_attributes": True}


class LocationNearbyOut(LocationOut):
    """LocationOut kèm khoảng cách (dùng cho /locations/nearby)."""
    distance_meters: Optional[int] = None


# ─── Save / upsert ────────────────────────────────────────────────────────────

class LocationSaveRequest(BaseModel):
    """
    Body của POST /locations.
    Nếu google_place_id đã tồn tại → upsert (200).
    Nếu chưa có → tạo mới (201).
    """
    name: str
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    category: Optional[str] = None
    google_place_id: Optional[str] = None
    photo_url: Optional[str] = None
    rating: Optional[float] = None
