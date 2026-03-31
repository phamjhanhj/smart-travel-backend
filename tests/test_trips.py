"""Test suite cho Trips và Day Plans & Activities endpoints."""
import pytest


class TestTrips:
    def test_create_trip_success(self, client, auth_headers):
        res = client.post("/api/trips", json={
            "title": "Hà Nội thu 2024",
            "destination": "Hà Nội, Việt Nam",
            "start_date": "2024-09-01",
            "end_date": "2024-09-03",
            "budget": 3000000,
            "num_travelers": 1,
        }, headers=auth_headers)
        assert res.status_code == 201
        data = res.json()["data"]
        assert data["title"] == "Hà Nội thu 2024"
        assert data["status"] == "draft"
        assert "id" in data

    def test_create_trip_auto_creates_day_plans(self, client, auth_headers):
        """Tạo trip 3 ngày → phải tự sinh ra 3 day_plans."""
        res = client.post("/api/trips", json={
            "title": "Test Trip",
            "destination": "Đà Lạt",
            "start_date": "2024-10-01",
            "end_date": "2024-10-03",  # 3 ngày
            "budget": 2000000,
            "num_travelers": 2,
        }, headers=auth_headers)
        assert res.status_code == 201
        trip_id = res.json()["data"]["id"]

        days_res = client.get(f"/api/trips/{trip_id}/days", headers=auth_headers)
        assert days_res.status_code == 200
        days = days_res.json()["data"]
        assert len(days) == 3
        assert days[0]["day_number"] == 1
        assert days[0]["date"] == "2024-10-01"
        assert days[2]["day_number"] == 3
        assert days[2]["date"] == "2024-10-03"

    def test_create_trip_invalid_dates(self, client, auth_headers):
        """end_date trước start_date → 400."""
        res = client.post("/api/trips", json={
            "title": "Bad Trip",
            "destination": "Đâu đó",
            "start_date": "2024-09-05",
            "end_date": "2024-09-01",  # end trước start
            "budget": 1000000,
            "num_travelers": 1,
        }, headers=auth_headers)
        assert res.status_code == 422

    def test_create_trip_requires_auth(self, client):
        res = client.post("/api/trips", json={
            "title": "No Auth",
            "destination": "Đâu đó",
            "start_date": "2024-09-01",
            "end_date": "2024-09-03",
        })
        assert res.status_code in [401, 403]

    def test_list_trips(self, client, auth_headers, sample_trip):
        res = client.get("/api/trips", headers=auth_headers)
        assert res.status_code == 200
        body = res.json()["data"]
        assert "items" in body
        assert "total" in body
        assert body["total"] >= 1

    def test_list_trips_filter_status(self, client, auth_headers, sample_trip):
        res = client.get("/api/trips?status=draft", headers=auth_headers)
        assert res.status_code == 200
        items = res.json()["data"]["items"]
        for item in items:
            assert item["status"] == "draft"

    def test_get_trip_detail(self, client, auth_headers, sample_trip):
        trip_id = sample_trip["id"]
        res = client.get(f"/api/trips/{trip_id}", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["id"] == trip_id
        assert "day_plans" in data

    def test_get_trip_not_found(self, client, auth_headers):
        res = client.get("/api/trips/00000000-0000-0000-0000-000000000000", headers=auth_headers)
        assert res.status_code == 404

    def test_get_trip_other_user(self, client, auth_headers):
        """User khác không được xem trip của mình."""
        # Tạo user thứ 2
        client.post("/api/auth/register", json={
            "email": "other@example.com",
            "password": "Other1234",
            "full_name": "Other User",
        })
        login_res = client.post("/api/auth/login", json={
            "email": "other@example.com",
            "password": "Other1234",
        })
        other_token = login_res.json()["data"]["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        # Tạo trip bằng user gốc
        trip_res = client.post("/api/trips", json={
            "title": "Private Trip",
            "destination": "Phú Quốc",
            "start_date": "2024-08-01",
            "end_date": "2024-08-03",
            "budget": 5000000,
            "num_travelers": 1,
        }, headers=auth_headers)
        trip_id = trip_res.json()["data"]["id"]

        # User khác cố xem → 403
        res = client.get(f"/api/trips/{trip_id}", headers=other_headers)
        assert res.status_code == 403

    def test_update_trip(self, client, auth_headers, sample_trip):
        trip_id = sample_trip["id"]
        res = client.put(f"/api/trips/{trip_id}", json={
            "title": "Đà Nẵng hè 2024 — Updated",
            "status": "active",
        }, headers=auth_headers)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["title"] == "Đà Nẵng hè 2024 — Updated"
        assert data["status"] == "active"

    def test_delete_trip(self, client, auth_headers, sample_trip):
        trip_id = sample_trip["id"]
        res = client.delete(f"/api/trips/{trip_id}", headers=auth_headers)
        assert res.status_code == 200

        # Verify đã xóa
        get_res = client.get(f"/api/trips/{trip_id}", headers=auth_headers)
        assert get_res.status_code == 404

    def test_trip_summary(self, client, auth_headers, sample_trip, sample_budget_item):
        trip_id = sample_trip["id"]
        res = client.get(f"/api/trips/{trip_id}/summary", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()["data"]
        assert "total_days" in data
        assert "budget_total" in data
        assert "budget_planned" in data
        assert "budget_actual" in data
        assert "budget_remaining" in data
        assert "by_category" in data
        assert data["total_days"] == 3  # trip 3 ngày
        # Kiểm tra không chia zero khi budget = 0


class TestDayPlans:
    def test_list_days_with_activities(self, client, auth_headers, sample_trip, sample_activity):
        trip_id = sample_trip["id"]
        res = client.get(f"/api/trips/{trip_id}/days", headers=auth_headers)
        assert res.status_code == 200
        days = res.json()["data"]
        assert len(days) == 3

        # Ngày 1 có activity
        day1 = days[0]
        assert "activities" in day1
        assert len(day1["activities"]) == 1
        act = day1["activities"][0]
        assert act["title"] == "Tham quan Ngũ Hành Sơn"
        assert "location" in act  # có field location dù là null

    def test_get_day_detail(self, client, auth_headers, sample_trip, sample_day_id):
        trip_id = sample_trip["id"]
        res = client.get(f"/api/trips/{trip_id}/days/{sample_day_id}", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["id"] == sample_day_id
        assert data["trip_id"] == trip_id
        assert "activities" in data

    def test_generate_days_overwrite(self, client, auth_headers, sample_trip):
        """overwrite=true xóa day_plans cũ rồi tạo lại."""
        trip_id = sample_trip["id"]
        res = client.post(
            f"/api/trips/{trip_id}/days/generate",
            json={"overwrite": True},
            headers=auth_headers,
        )
        assert res.status_code == 201
        data = res.json()["data"]
        assert len(data) == 3  # trip 3 ngày → 3 day_plans

    def test_generate_days_no_overwrite_when_exists(self, client, auth_headers, sample_trip):
        """overwrite=false không tạo lại nếu đã có."""
        trip_id = sample_trip["id"]
        res = client.post(
            f"/api/trips/{trip_id}/days/generate",
            json={"overwrite": False},
            headers=auth_headers,
        )
        assert res.status_code == 201


class TestActivities:
    def test_add_activity_success(self, client, auth_headers, sample_trip, sample_day_id):
        trip_id = sample_trip["id"]
        res = client.post(
            f"/api/trips/{trip_id}/days/{sample_day_id}/activities",
            json={
                "title": "Ăn tối Bà Duẫn",
                "type": "meal",
                "start_time": "18:30",
                "end_time": "20:00",
                "estimated_cost": 200000,
                "location_id": None,
            },
            headers=auth_headers,
        )
        assert res.status_code == 201
        data = res.json()["data"]
        assert data["title"] == "Ăn tối Bà Duẫn"
        assert data["day_plan_id"] == sample_day_id
        assert data["estimated_cost"] == 200000

    def test_add_activity_without_location(self, client, auth_headers, sample_trip, sample_day_id):
        """location_id là optional."""
        trip_id = sample_trip["id"]
        res = client.post(
            f"/api/trips/{trip_id}/days/{sample_day_id}/activities",
            json={"title": "Nghỉ tại phòng", "type": "other"},
            headers=auth_headers,
        )
        assert res.status_code == 201
        assert res.json()["data"]["location"] is None

    def test_update_activity(self, client, auth_headers, sample_activity):
        act_id = sample_activity["id"]
        res = client.put(f"/api/activities/{act_id}", json={
            "title": "Tham quan Ngũ Hành Sơn (đã đặt vé)",
            "estimated_cost": 45000,
        }, headers=auth_headers)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["title"] == "Tham quan Ngũ Hành Sơn (đã đặt vé)"
        assert data["estimated_cost"] == 45000

    def test_delete_activity(self, client, auth_headers, sample_trip, sample_day_id, sample_activity):
        act_id = sample_activity["id"]
        res = client.delete(f"/api/activities/{act_id}", headers=auth_headers)
        assert res.status_code == 200

        # Verify đã xóa khỏi ngày
        trip_id = sample_trip["id"]
        days_res = client.get(f"/api/trips/{trip_id}/days", headers=auth_headers)
        day1 = days_res.json()["data"][0]
        act_ids = [a["id"] for a in day1["activities"]]
        assert act_id not in act_ids

    def test_reorder_activities(self, client, auth_headers, sample_trip, sample_day_id):
        """Thêm 2 activities rồi reorder."""
        trip_id = sample_trip["id"]

        def add_act(title, order):
            return client.post(
                f"/api/trips/{trip_id}/days/{sample_day_id}/activities",
                json={"title": title, "order_index": order},
                headers=auth_headers,
            ).json()["data"]

        act1 = add_act("Activity 1", 0)
        act2 = add_act("Activity 2", 1)

        # Đổi thứ tự
        res = client.patch("/api/activities/reorder", json={
            "day_plan_id": sample_day_id,
            "items": [
                {"id": act2["id"], "order_index": 0},
                {"id": act1["id"], "order_index": 1},
            ]
        }, headers=auth_headers)
        assert res.status_code == 200

    def test_reorder_wrong_day_plan(self, client, auth_headers, sample_trip, sample_day_id, sample_activity):
        """Không thể reorder activity của ngày khác."""
        fake_day_id = "00000000-0000-0000-0000-000000000000"
        res = client.patch("/api/activities/reorder", json={
            "day_plan_id": fake_day_id,
            "items": [{"id": sample_activity["id"], "order_index": 0}]
        }, headers=auth_headers)
        assert res.status_code == 404
