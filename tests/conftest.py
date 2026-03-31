"""
conftest.py — Setup test database và fixtures dùng chung cho toàn bộ test suite.
Chạy trên DB test riêng biệt, không đụng vào DB production.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.database import Base, get_db
from app.main import app

# -----------------------------------------------------------------------
# Database test riêng — thêm "_test" vào tên DB
# postgresql://postgres:123456@localhost:5432/smart_travel_test
# -----------------------------------------------------------------------
TEST_DATABASE_URL = settings.DATABASE_URL.rsplit("/", 1)[0] + "/smart_travel_test"

engine_test = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


# -----------------------------------------------------------------------
# Override get_db dependency — dùng DB test thay vì DB thật
# -----------------------------------------------------------------------
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# -----------------------------------------------------------------------
# Tạo/xóa bảng trước và sau toàn bộ test session
# -----------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Tạo tất cả bảng trong DB test trước khi chạy test."""
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


# -----------------------------------------------------------------------
# Xóa data sau mỗi test — đảm bảo các test độc lập nhau
# -----------------------------------------------------------------------
@pytest.fixture(autouse=True)
def clean_db():
    """Truncate tất cả bảng sau mỗi test để tránh data conflict."""
    yield
    db = TestingSessionLocal()
    try:
        # Xóa theo đúng thứ tự để tránh FK violation
        db.execute(text("TRUNCATE TABLE activities, ai_suggestions, budget_items, chat_history, day_plans, locations, trips, users RESTART IDENTITY CASCADE"))
        db.commit()
    finally:
        db.close()


# -----------------------------------------------------------------------
# HTTP client
# -----------------------------------------------------------------------
@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient — không cần chạy uvicorn."""
    with TestClient(app) as c:
        yield c


# -----------------------------------------------------------------------
# Fixtures tái sử dụng
# -----------------------------------------------------------------------
@pytest.fixture
def registered_user(client):
    """Tạo user và trả về thông tin đăng ký."""
    payload = {
        "email": "test@example.com",
        "password": "Test1234",
        "full_name": "Test User"
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 201
    return payload  # trả về payload gốc để dùng login


@pytest.fixture
def auth_headers(client, registered_user):
    """Đăng nhập và trả về headers có JWT token."""
    res = client.post("/api/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    assert res.status_code == 200
    token = res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_trip(client, auth_headers):
    """Tạo trip mẫu và trả về data."""
    payload = {
        "title": "Đà Nẵng hè 2024",
        "destination": "Đà Nẵng, Việt Nam",
        "start_date": "2024-07-10",
        "end_date": "2024-07-12",  # 3 ngày
        "budget": 5000000,
        "num_travelers": 2,
        "preferences": "Thích hải sản"
    }
    res = client.post("/api/trips", json=payload, headers=auth_headers)
    assert res.status_code == 201
    return res.json()["data"]


@pytest.fixture
def sample_day_id(client, auth_headers, sample_trip):
    """Lấy day_id đầu tiên của trip mẫu."""
    trip_id = sample_trip["id"]
    res = client.get(f"/api/trips/{trip_id}/days", headers=auth_headers)
    assert res.status_code == 200
    days = res.json()["data"]
    assert len(days) > 0
    return days[0]["id"]


@pytest.fixture
def sample_activity(client, auth_headers, sample_trip, sample_day_id):
    """Tạo activity mẫu."""
    trip_id = sample_trip["id"]
    payload = {
        "title": "Tham quan Ngũ Hành Sơn",
        "type": "attraction",
        "start_time": "08:00",
        "end_time": "11:00",
        "estimated_cost": 40000,
    }
    res = client.post(
        f"/api/trips/{trip_id}/days/{sample_day_id}/activities",
        json=payload,
        headers=auth_headers,
    )
    assert res.status_code == 201
    return res.json()["data"]


@pytest.fixture
def sample_budget_item(client, auth_headers, sample_trip):
    """Tạo budget item mẫu."""
    trip_id = sample_trip["id"]
    payload = {
        "category": "food",
        "label": "Ăn tối Bà Duẫn",
        "planned_amount": 300000,
        "actual_amount": 0,
        "date": "2024-07-10",
    }
    res = client.post(
        f"/api/trips/{trip_id}/budget/items",
        json=payload,
        headers=auth_headers,
    )
    assert res.status_code == 201
    return res.json()["data"]
