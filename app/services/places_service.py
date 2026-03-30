"""
Google Places API service.
Endpoints được dùng:
  - Text Search  → GET /locations/search
  - Nearby Search → GET /locations/nearby
  - Place Details → (internal, dùng để enrich data)
"""
from __future__ import annotations

import math

import httpx

from app.core.config import settings

# ─── Base URLs ────────────────────────────────────────────────────────────────

_BASE = "https://maps.googleapis.com/maps/api/place"


# ─── Photo URL helper ─────────────────────────────────────────────────────────

def build_photo_url(photo_reference: str, max_width: int = 800) -> str:
    return (
        f"{_BASE}/photo"
        f"?maxwidth={max_width}"
        f"&photo_reference={photo_reference}"
        f"&key={settings.GOOGLE_PLACES_API_KEY}"
    )


# ─── Text Search ──────────────────────────────────────────────────────────────

async def search_places(
    query: str,
    destination: str | None = None,
    limit: int = 10,
    language: str = "vi",
) -> list[dict]:
    """
    Text Search — tìm địa điểm theo từ khoá + điểm đến.
    Trả về tối đa `limit` kết quả.
    """
    full_query = f"{query} {destination}".strip() if destination else query
    params = {
        "query": full_query,
        "language": language,
        "key": settings.GOOGLE_PLACES_API_KEY,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{_BASE}/textsearch/json", params=params)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for place in data.get("results", [])[:limit]:
        photo_ref = (place.get("photos") or [{}])[0].get("photo_reference")
        location = place.get("geometry", {}).get("location", {})
        results.append(
            {
                "name": place.get("name"),
                "address": place.get("formatted_address"),
                "lat": location.get("lat"),
                "lng": location.get("lng"),
                "category": _map_types(place.get("types", [])),
                "google_place_id": place.get("place_id"),
                "photo_url": build_photo_url(photo_ref) if photo_ref else None,
                "rating": place.get("rating"),
            }
        )
    return results


# ─── Nearby Search ────────────────────────────────────────────────────────────

async def search_nearby(
    lat: float,
    lng: float,
    radius: int = 1000,
    category: str | None = None,
    language: str = "vi",
) -> list[dict]:
    """
    Nearby Search — tìm địa điểm quanh tọa độ (lat, lng) trong bán kính `radius` mét.
    Trả về danh sách kèm `distance_meters` (haversine).
    """
    params: dict = {
        "location": f"{lat},{lng}",
        "radius": radius,
        "language": language,
        "key": settings.GOOGLE_PLACES_API_KEY,
    }
    # Map category nội bộ → Google type
    google_type = _category_to_google_type(category)
    if google_type:
        params["type"] = google_type

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{_BASE}/nearbysearch/json", params=params)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for place in data.get("results", []):
        photo_ref = (place.get("photos") or [{}])[0].get("photo_reference")
        loc = place.get("geometry", {}).get("location", {})
        place_lat = loc.get("lat")
        place_lng = loc.get("lng")
        distance = _haversine(lat, lng, place_lat, place_lng) if (place_lat and place_lng) else None

        results.append(
            {
                "name": place.get("name"),
                "address": place.get("vicinity"),
                "lat": place_lat,
                "lng": place_lng,
                "category": _map_types(place.get("types", [])),
                "google_place_id": place.get("place_id"),
                "photo_url": build_photo_url(photo_ref) if photo_ref else None,
                "rating": place.get("rating"),
                "distance_meters": int(distance) if distance is not None else None,
            }
        )

    # Sắp xếp theo distance
    results.sort(key=lambda x: x.get("distance_meters") or 999999)
    return results


# ─── Haversine distance ───────────────────────────────────────────────────────

def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Tính khoảng cách (mét) giữa hai toạ độ GPS."""
    R = 6_371_000  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ─── Type mapping ─────────────────────────────────────────────────────────────

_TYPE_MAP: dict[str, str] = {
    "restaurant": "food", "food": "food", "cafe": "food",
    "bakery": "food", "bar": "food", "meal_takeaway": "food",
    "meal_delivery": "food",
    "lodging": "hotel", "hotel": "hotel", "resort": "hotel",
    "motel": "hotel", "hostel": "hotel",
    "transit_station": "transport", "airport": "transport",
    "train_station": "transport", "bus_station": "transport",
    "subway_station": "transport", "taxi_stand": "transport",
    "tourist_attraction": "attraction", "museum": "attraction",
    "park": "attraction", "amusement_park": "attraction",
    "art_gallery": "attraction", "zoo": "attraction",
    "aquarium": "attraction", "natural_feature": "attraction",
    "place_of_worship": "attraction",
    "shopping_mall": "shopping", "store": "shopping",
    "supermarket": "shopping", "clothing_store": "shopping",
}

_CATEGORY_TO_GOOGLE: dict[str, str] = {
    "food": "restaurant",
    "hotel": "lodging",
    "transport": "transit_station",
    "attraction": "tourist_attraction",
    "shopping": "shopping_mall",
}


def _map_types(types: list[str]) -> str:
    for t in types:
        if t in _TYPE_MAP:
            return _TYPE_MAP[t]
    return "other"


def _category_to_google_type(category: str | None) -> str | None:
    if not category:
        return None
    return _CATEGORY_TO_GOOGLE.get(category)
