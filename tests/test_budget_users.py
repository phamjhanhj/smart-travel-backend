"""Test suite cho Budget và Users endpoints."""
import pytest


class TestBudget:
    def test_get_budget_summary(self, client, auth_headers, sample_trip, sample_budget_item):
        trip_id = sample_trip["id"]
        res = client.get(f"/api/trips/{trip_id}/budget", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()["data"]

        assert data["budget_total"] == sample_trip["budget"]
        assert data["budget_planned"] >= 300000      # planned_amount của sample_budget_item
        assert "budget_actual" in data
        assert "budget_remaining" in data
        assert "overspent" in data
        assert "categories" in data

        # Kiểm tra có đủ 5 categories
        categories = {c["category"] for c in data["categories"]}
        assert "food" in categories
        assert "transport" in categories
        assert "hotel" in categories
        assert "activity" in categories
        assert "other" in categories

    def test_budget_remaining_calculation(self, client, auth_headers, sample_trip):
        trip_id = sample_trip["id"]

        # Thêm budget item với actual_amount
        client.post(f"/api/trips/{trip_id}/budget/items", json={
            "category": "transport",
            "label": "Taxi sân bay",
            "planned_amount": 200000,
            "actual_amount": 185000,
            "date": "2024-07-10",
        }, headers=auth_headers)

        res = client.get(f"/api/trips/{trip_id}/budget", headers=auth_headers)
        data = res.json()["data"]
        expected_remaining = data["budget_total"] - data["budget_actual"]
        assert data["budget_remaining"] == expected_remaining

    def test_budget_overspent_flag(self, client, auth_headers, sample_trip):
        trip_id = sample_trip["id"]

        # Chi tiêu vượt budget
        client.post(f"/api/trips/{trip_id}/budget/items", json={
            "category": "other",
            "label": "Chi tiêu vượt mức",
            "planned_amount": 99999999,
            "actual_amount": 99999999,   # vượt budget 5tr
            "date": "2024-07-10",
        }, headers=auth_headers)

        res = client.get(f"/api/trips/{trip_id}/budget", headers=auth_headers)
        data = res.json()["data"]
        assert data["overspent"] is True

    def test_list_budget_items(self, client, auth_headers, sample_trip, sample_budget_item):
        trip_id = sample_trip["id"]
        res = client.get(f"/api/trips/{trip_id}/budget/items", headers=auth_headers)
        assert res.status_code == 200
        items = res.json()["data"]
        assert len(items) >= 1
        assert items[0]["category"] == "food"

    def test_list_budget_items_filter_category(self, client, auth_headers, sample_trip, sample_budget_item):
        trip_id = sample_trip["id"]
        res = client.get(f"/api/trips/{trip_id}/budget/items?category=food", headers=auth_headers)
        assert res.status_code == 200
        items = res.json()["data"]
        for item in items:
            assert item["category"] == "food"

    def test_create_budget_item(self, client, auth_headers, sample_trip):
        trip_id = sample_trip["id"]
        res = client.post(f"/api/trips/{trip_id}/budget/items", json={
            "category": "transport",
            "label": "Taxi sân bay — khách sạn",
            "planned_amount": 200000,
            "actual_amount": 0,
            "date": "2024-07-10",
        }, headers=auth_headers)
        assert res.status_code == 201
        data = res.json()["data"]
        assert data["category"] == "transport"
        assert data["label"] == "Taxi sân bay — khách sạn"
        assert data["planned_amount"] == 200000
        assert data["trip_id"] == trip_id

    def test_update_budget_item_actual_amount(self, client, auth_headers, sample_budget_item):
        """Cập nhật actual_amount sau khi chi tiêu thực tế."""
        item_id = sample_budget_item["id"]
        res = client.put(f"/api/budget/items/{item_id}", json={
            "actual_amount": 280000,
        }, headers=auth_headers)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["actual_amount"] == 280000
        # planned_amount không đổi
        assert data["planned_amount"] == sample_budget_item["planned_amount"]

    def test_delete_budget_item(self, client, auth_headers, sample_trip, sample_budget_item):
        trip_id = sample_trip["id"]
        item_id = sample_budget_item["id"]

        res = client.delete(f"/api/budget/items/{item_id}", headers=auth_headers)
        assert res.status_code == 200

        # Verify đã xóa
        items_res = client.get(f"/api/trips/{trip_id}/budget/items", headers=auth_headers)
        item_ids = [i["id"] for i in items_res.json()["data"]]
        assert item_id not in item_ids

    def test_budget_item_negative_amount_rejected(self, client, auth_headers, sample_trip):
        trip_id = sample_trip["id"]
        res = client.post(f"/api/trips/{trip_id}/budget/items", json={
            "category": "food",
            "label": "Invalid",
            "planned_amount": -1000,  # âm → invalid
        }, headers=auth_headers)
        assert res.status_code == 422


class TestUsers:
    def test_get_profile(self, client, auth_headers, registered_user):
        res = client.get("/api/users/me", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["email"] == registered_user["email"]
        assert data["full_name"] == registered_user["full_name"]
        assert "preferences_json" in data

    def test_update_full_name(self, client, auth_headers):
        res = client.patch("/api/users/me", json={"full_name": "Updated Name"}, headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["data"]["full_name"] == "Updated Name"

    def test_update_preferences(self, client, auth_headers):
        prefs = {
            "travel_style": "budget",
            "interests": ["food", "culture"],
            "budget_range": "medium",
        }
        res = client.patch("/api/users/me", json={"preferences_json": prefs}, headers=auth_headers)
        assert res.status_code == 200
        data = res.json()["data"]
        # preferences_json phải trả về dict, không phải string
        assert isinstance(data["preferences_json"], dict)
        assert data["preferences_json"]["travel_style"] == "budget"
        assert data["preferences_json"]["interests"] == ["food", "culture"]

    def test_update_partial(self, client, auth_headers, registered_user):
        """Partial update — chỉ update full_name, email không đổi."""
        res = client.patch("/api/users/me", json={"full_name": "New Name Only"}, headers=auth_headers)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["full_name"] == "New Name Only"
        assert data["email"] == registered_user["email"]  # không đổi

    def test_profile_requires_auth(self, client):
        res = client.get("/api/users/me")
        assert res.status_code in [401, 403]
