"""Test suite cho Locations endpoints."""
from unittest.mock import patch, AsyncMock
from uuid import UUID
import pytest

# Fake datas
FAKE_SEARCH_RESULTS = [
    {
        "name": "Chợ Bến Thành",
        "address": "Le Loi, Ben Thanh, District 1",
        "lat": 10.7725,
        "lng": 106.6981,
        "category": "shopping",
        "google_place_id": "ChIJT_2n3-EpdTERO42B4X2SgG4",
        "photo_url": "http://photo.url",
        "rating": 4.5,
    }
]

FAKE_NEARBY_RESULTS = [
    {
        "name": "Bến Thành Metro",
        "address": "Ben Thanh Market",
        "lat": 10.7725,
        "lng": 106.6981,
        "category": "transport",
        "google_place_id": "ChIJxyz123abcde",
        "photo_url": None,
        "rating": 4.0,
        "distance_meters": 500,
    }
]

@pytest.fixture(autouse=True)
def mock_settings():
    with patch("app.api.routes.location.settings.GOOGLE_PLACES_API_KEY", "fake_key"):
        yield

class TestLocations:
    @patch("app.api.routes.location.places_service.search_places", new_callable=AsyncMock)
    def test_search_locations_success(self, mock_search, client, auth_headers):
        mock_search.return_value = FAKE_SEARCH_RESULTS
        
        res = client.get("/api/locations/search?q=ben+thanh&destination=hcm", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) == 1
        assert data[0]["name"] == "Chợ Bến Thành"
        assert data[0]["google_place_id"] == "ChIJT_2n3-EpdTERO42B4X2SgG4"
        assert "id" in data[0]

        # Verify mock called correctly
        mock_search.assert_called_once_with(
            query="ben thanh", destination="hcm", limit=10, language="vi"
        )

    def test_search_locations_requires_auth(self, client):
        res = client.get("/api/locations/search?q=hanoi")
        assert res.status_code in [401, 403]

    @patch("app.api.routes.location.places_service.search_nearby", new_callable=AsyncMock)
    def test_nearby_locations_success(self, mock_nearby, client, auth_headers):
        mock_nearby.return_value = FAKE_NEARBY_RESULTS
        
        res = client.get(
            "/api/locations/nearby?lat=10.77&lng=106.69&radius=2000&category=transport",
            headers=auth_headers
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) == 1
        assert data[0]["distance_meters"] == 500
        assert data[0]["category"] == "transport"

        mock_nearby.assert_called_once_with(
            lat=10.77, lng=106.69, radius=2000, category="transport", language="vi"
        )

    def test_save_location(self, client, auth_headers):
        payload = {
            "name": "Landmark 81",
            "google_place_id": "ChIJT_2n3-EpdTERO42Babc",
            "lat": 10.793,
            "lng": 106.722,
            "address": "Binh Thanh, HCMC",
            "category": "attraction",
            "photo_url": "http://img",
            "rating": 4.8
        }
        res = client.post("/api/locations", json=payload, headers=auth_headers)
        # Assuming HTTP 201 Created for new location
        assert res.status_code == 201
        data = res.json()["data"]
        assert data["name"] == "Landmark 81"
        assert "id" in data
        
        saved_id = data["id"]
        
        # Test Get Location By ID
        get_res = client.get(f"/api/locations/{saved_id}", headers=auth_headers)
        assert get_res.status_code == 200
        get_data = get_res.json()["data"]
        assert get_data["google_place_id"] == payload["google_place_id"]

    def test_save_location_already_exists(self, client, auth_headers):
        payload = {
            "name": "Hoan Kiem Lake",
            "google_place_id": "ChIJxyzHK_HoanKiem",
            "lat": 21.028,
            "lng": 105.852,
            "category": "attraction"
        }
        # First save
        client.post("/api/locations", json=payload, headers=auth_headers)
        
        # Second save should return 200 OK (updated/already exists) instead of 201
        res2 = client.post("/api/locations", json=payload, headers=auth_headers)
        assert res2.status_code == 200

    def test_get_location_not_found(self, client, auth_headers):
        fake_uuid = "12345678-1234-5678-1234-567812345678"
        res = client.get(f"/api/locations/{fake_uuid}", headers=auth_headers)
        assert res.status_code == 404

    def test_delete_location_success(self, client, auth_headers):
        # Create a temp location
        payload = {
            "name": "Temp Location",
            "google_place_id": "ChIJTEMP_123",
            "lat": 1.0,
            "lng": 1.0,
        }
        save_res = client.post("/api/locations", json=payload, headers=auth_headers)
        location_id = save_res.json()["data"]["id"]

        # Delete it
        del_res = client.delete(f"/api/locations/{location_id}", headers=auth_headers)
        assert del_res.status_code == 200

        # Verify it's gone
        get_res = client.get(f"/api/locations/{location_id}", headers=auth_headers)
        assert get_res.status_code == 404

    def test_delete_location_conflict(self, client, auth_headers, sample_trip, sample_day_id):
        """Cannot delete location if used in an activity"""
        # Save a location
        payload = {
            "name": "Linked Location",
            "google_place_id": "ChIJLINKED_123",
            "lat": 1.0,
            "lng": 1.0,
        }
        save_res = client.post("/api/locations", json=payload, headers=auth_headers)
        location_id = save_res.json()["data"]["id"]

        # Add an activity using this location
        trip_id = sample_trip["id"]
        act_res = client.post(
            f"/api/trips/{trip_id}/days/{sample_day_id}/activities",
            json={
                "title": "Visit Linked Location",
                "type": "attraction",
                "start_time": "14:00",
                "end_time": "16:00",
                "estimated_cost": 0,
                "location_id": location_id,
            },
            headers=auth_headers,
        )
        assert act_res.status_code == 201

        # Attempt to delete the location should fail with 409
        del_res = client.delete(f"/api/locations/{location_id}", headers=auth_headers)
        assert del_res.status_code == 409
