import pytest
from unittest.mock import AsyncMock, patch


class TestRegister:
    async def test_register_success(self, async_client):
        resp = await async_client.post("/api/auth/register", json={
            "username": "alice", "password": "pass123", "name": "Alice", "role": "patient",
        })
        assert resp.status_code == 201
        assert resp.json()["message"] == "Registration successful"

    async def test_register_duplicate_username(self, async_client):
        await async_client.post("/api/auth/register", json={
            "username": "bob", "password": "pass123", "name": "Bob", "role": "patient",
        })
        resp = await async_client.post("/api/auth/register", json={
            "username": "bob", "password": "pass456", "name": "Bob2", "role": "patient",
        })
        assert resp.status_code == 409

    async def test_register_doctor_role(self, async_client):
        resp = await async_client.post("/api/auth/register", json={
            "username": "drdave", "password": "pass123", "name": "Dr. Dave", "role": "doctor",
        })
        assert resp.status_code == 201


class TestLogin:
    async def test_login_success(self, async_client):
        await async_client.post("/api/auth/register", json={
            "username": "charlie", "password": "pass123", "name": "Charlie",
        })
        resp = await async_client.post("/api/auth/login", json={
            "username": "charlie", "password": "pass123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["user"]["username"] == "charlie"
        assert data["user"]["role"] == "patient"

    async def test_login_wrong_password(self, async_client):
        await async_client.post("/api/auth/register", json={
            "username": "diana", "password": "pass123", "name": "Diana",
        })
        resp = await async_client.post("/api/auth/login", json={
            "username": "diana", "password": "wrongpass",
        })
        assert resp.status_code == 401
        assert resp.json()["detail"] == "密码错误"

    async def test_login_nonexistent_user(self, async_client):
        resp = await async_client.post("/api/auth/login", json={
            "username": "nobody", "password": "pass123",
        })
        assert resp.status_code == 401
        assert resp.json()["detail"] == "用户名不存在"


class TestMe:
    async def test_me_authenticated(self, async_client, auth_token):
        resp = await async_client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {auth_token}",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "testuser"
        assert data["name"] == "Test User"
        assert data["role"] == "patient"
        assert "avatar_url" in data

    async def test_me_no_token(self, async_client):
        resp = await async_client.get("/api/auth/me")
        assert resp.status_code == 403


class TestUpdateMe:
    async def test_name_is_readonly(self, async_client, auth_token):
        """Name set at registration cannot be changed via update."""
        resp = await async_client.put(
            "/api/auth/me",
            json={"name": "新名字"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] != "新名字"  # name is read-only after registration

    async def test_update_phone_and_email(self, async_client, auth_token):
        resp = await async_client.put(
            "/api/auth/me",
            json={"phone": "13800138000", "email": "test@example.com"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["phone"] == "13800138000"
        assert data["email"] == "test@example.com"

    async def test_partial_update_preserves_other_fields(self, async_client, auth_token):
        await async_client.put(
            "/api/auth/me",
            json={"phone": "13800138000"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        resp = await async_client.put(
            "/api/auth/me",
            json={"email": "test@example.com"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["phone"] == "13800138000"
        assert data["email"] == "test@example.com"

    async def test_requires_auth(self, async_client):
        resp = await async_client.put("/api/auth/me", json={"name": "x"})
        assert resp.status_code == 403


class TestUploadAvatar:
    async def test_upload_png(self, async_client, auth_token):
        with patch("app.api.auth.upload_to_minio", new_callable=AsyncMock) as mock_upload:
            mock_upload.return_value = "2026/05/11/abc_avatar.png"
            resp = await async_client.post(
                "/api/auth/avatar",
                files={"file": ("avatar.png", b"fake-png-data", "image/png")},
                headers={"Authorization": f"Bearer {auth_token}"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "avatar_url" in data
        assert mock_upload.called

    async def test_rejects_non_image(self, async_client, auth_token):
        resp = await async_client.post(
            "/api/auth/avatar",
            files={"file": ("doc.txt", b"text", "text/plain")},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 400

    async def test_requires_auth(self, async_client):
        resp = await async_client.post(
            "/api/auth/avatar",
            files={"file": ("avatar.png", b"data", "image/png")},
        )
        assert resp.status_code == 403


class TestChangePassword:
    async def test_change_password_success(self, async_client, auth_token):
        resp = await async_client.put(
            "/api/auth/password",
            json={"old_password": "testpass", "new_password": "newpass123"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "密码修改成功"

        resp2 = await async_client.post("/api/auth/login", json={
            "username": "testuser", "password": "newpass123",
        })
        assert resp2.status_code == 200

    async def test_wrong_old_password(self, async_client, auth_token):
        resp = await async_client.put(
            "/api/auth/password",
            json={"old_password": "wrongpass", "new_password": "newpass123"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 400
        assert "原密码错误" in resp.json()["detail"]

    async def test_short_new_password(self, async_client, auth_token):
        resp = await async_client.put(
            "/api/auth/password",
            json={"old_password": "testpass", "new_password": "ab"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 422

    async def test_requires_auth(self, async_client):
        resp = await async_client.put("/api/auth/password", json={
            "old_password": "old", "new_password": "new",
        })
        assert resp.status_code == 403
