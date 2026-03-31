# Hướng dẫn chạy test

## 1. Tạo database test

```bash
# Vào container PostgreSQL
docker exec -it <tên_container> psql -U postgres

# Tạo DB test
CREATE DATABASE smart_travel_test;
\q
```

## 2. Cài thư viện test

```bash
pip install pytest httpx pytest-asyncio
```

## 3. Cấu trúc thư mục

```
smart-travel-backend/
├── app/
├── tests/
│   ├── conftest.py          ← fixtures dùng chung
│   ├── test_auth.py         ← test auth endpoints
│   ├── test_trips.py        ← test trips + day plans + activities
│   └── test_budget_users.py ← test budget + users
├── pytest.ini
└── requirements.txt
```

## 4. Chạy test

```bash
# Chạy tất cả
pytest

# Chạy 1 file
pytest tests/test_auth.py

# Chạy 1 class
pytest tests/test_auth.py::TestRegister

# Chạy 1 test cụ thể
pytest tests/test_auth.py::TestRegister::test_register_success

# Chạy với output chi tiết hơn
pytest -v

# Dừng khi gặp lỗi đầu tiên
pytest -x

# Chạy test có keyword nhất định
pytest -k "auth"
pytest -k "trip and not delete"
```

## 5. Xem coverage (optional)

```bash
pip install pytest-cov

# Chạy với coverage report
pytest --cov=app --cov-report=term-missing

# Tạo HTML report
pytest --cov=app --cov-report=html
# Mở htmlcov/index.html
```

## 6. Output mẫu khi pass

```
tests/test_auth.py::TestRegister::test_register_success        PASSED
tests/test_auth.py::TestRegister::test_register_duplicate      PASSED
tests/test_auth.py::TestLogin::test_login_success              PASSED
...

========== 35 passed in 4.32s ==========
```

## 7. Output mẫu khi fail

```
FAILED tests/test_trips.py::TestTrips::test_create_trip_auto_creates_day_plans
AssertionError: assert 0 == 3
  → Trip tạo xong nhưng day_plans không được tạo tự động
```

## Lưu ý quan trọng

- Test chạy trên `smart_travel_test` — **không đụng data production**
- Mỗi test tự dọn dẹp data sau khi chạy (fixture `clean_db`)
- Không cần chạy `uvicorn` — `TestClient` xử lý in-process
- Nếu test fail do DB chưa có bảng: `conftest.py` tự `create_all` cho DB test
