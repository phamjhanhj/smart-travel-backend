"""Test suite cho Auth endpoints — POST /auth/register, login, refresh, me."""
import pytest


class TestRegister:
    def test_register_success(self, client):
        res = client.post("/api/auth/register", json={
            "email": "new@example.com",
            "password": "Test1234",
            "full_name": "New User",
        })
        assert res.status_code == 201
        body = res.json()
        assert body["status_code"] == 201
        assert body["message"] == "Đăng ký thành công"
        data = body["data"]
        assert data["email"] == "new@example.com"
        assert data["full_name"] == "New User"
        assert "id" in data
        assert "created_at" in data
        assert "password" not in data           # không lộ password
        assert "password_hash" not in data      # không lộ hash

    def test_register_duplicate_email(self, client, registered_user):
        res = client.post("/api/auth/register", json={
            "email": registered_user["email"],  # email đã tồn tại
            "password": "Test1234",
            "full_name": "Another User",
        })
        assert res.status_code == 400

    def test_register_invalid_email(self, client):
        res = client.post("/api/auth/register", json={
            "email": "not-an-email",
            "password": "Test1234",
            "full_name": "User",
        })
        assert res.status_code == 422

    def test_register_weak_password(self, client):
        res = client.post("/api/auth/register", json={
            "email": "user2@example.com",
            "password": "password",  # không có số, không có chữ hoa
            "full_name": "User",
        })
        assert res.status_code == 422

    def test_register_missing_field(self, client):
        res = client.post("/api/auth/register", json={
            "email": "user3@example.com",
            # thiếu password và full_name
        })
        assert res.status_code == 422


class TestLogin:
    def test_login_success(self, client, registered_user):
        res = client.post("/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        assert res.status_code == 200
        data = res.json()["data"]
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        assert data["user"]["email"] == registered_user["email"]

    def test_login_wrong_password(self, client, registered_user):
        res = client.post("/api/auth/login", json={
            "email": registered_user["email"],
            "password": "WrongPass99",
        })
        assert res.status_code == 401

    def test_login_nonexistent_email(self, client):
        res = client.post("/api/auth/login", json={
            "email": "nobody@example.com",
            "password": "Test1234",
        })
        assert res.status_code == 401

    def test_login_missing_field(self, client):
        res = client.post("/api/auth/login", json={"email": "test@example.com"})
        assert res.status_code == 422


class TestRefreshToken:
    def test_refresh_success(self, client, registered_user):
        login_res = client.post("/api/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        refresh_token = login_res.json()["data"]["refresh_token"]

        res = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        assert res.status_code == 200
        data = res.json()["data"]
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_invalid_token(self, client):
        res = client.post("/api/auth/refresh", json={"refresh_token": "invalid.token.here"})
        assert res.status_code == 401

    def test_refresh_with_access_token_should_fail(self, client, auth_headers):
        """Access token không được dùng làm refresh token."""
        access_token = auth_headers["Authorization"].replace("Bearer ", "")
        res = client.post("/api/auth/refresh", json={"refresh_token": access_token})
        assert res.status_code == 401


class TestGetMe:
    def test_get_me_success(self, client, auth_headers, registered_user):
        res = client.get("/api/auth/me", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["email"] == registered_user["email"]

    def test_get_me_no_token(self, client):
        res = client.get("/api/auth/me")
        assert res.status_code == 401  # missing token → 401 Unauthorized (RFC 7235)

    def test_get_me_invalid_token(self, client):
        res = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid"})
        assert res.status_code == 401
