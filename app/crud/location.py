from uuid import UUID

from sqlalchemy.orm import Session

from app.models.location import Location
from app.schemas.location import LocationSaveRequest


# ─── Read ─────────────────────────────────────────────────────────────────────

def get_location_by_id(db: Session, location_id: UUID) -> Location | None:
    return db.query(Location).filter(Location.id == location_id).first()


def get_location_by_place_id(db: Session, google_place_id: str) -> Location | None:
    return (
        db.query(Location)
        .filter(Location.google_place_id == google_place_id)
        .first()
    )


# ─── Upsert ───────────────────────────────────────────────────────────────────

def upsert_location(db: Session, payload: LocationSaveRequest) -> tuple[Location, bool]:
    """
    Lưu location vào DB.
    Returns:
        (location, is_new)
        is_new = True  → vừa tạo mới (HTTP 201)
        is_new = False → đã tồn tại, được cập nhật (HTTP 200)
    """
    if payload.google_place_id:
        existing = get_location_by_place_id(db, payload.google_place_id)
        if existing:
            # Cập nhật thông tin có thể thay đổi
            existing.name = payload.name
            existing.address = payload.address
            existing.lat = payload.lat
            existing.lng = payload.lng
            existing.category = payload.category
            existing.photo_url = payload.photo_url
            existing.rating = payload.rating
            db.commit()
            db.refresh(existing)
            return existing, False

    location = Location(
        name=payload.name,
        address=payload.address,
        lat=payload.lat,
        lng=payload.lng,
        category=payload.category,
        google_place_id=payload.google_place_id,
        photo_url=payload.photo_url,
        rating=payload.rating,
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    return location, True


def upsert_many(db: Session, places: list[dict]) -> list[Location]:
    """
    Upsert nhiều địa điểm (kết quả từ Google Places search) vào DB.
    Trả về list Location theo thứ tự input.
    """
    results = []
    for place in places:
        payload = LocationSaveRequest(**place)
        location, _ = upsert_location(db, payload)
        results.append(location)
    return results


# ─── Delete ───────────────────────────────────────────────────────────────────

def delete_location(db: Session, location: Location) -> None:
    db.delete(location)
    db.commit()
