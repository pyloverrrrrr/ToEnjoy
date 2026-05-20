import pytest


class TestChatHistory:
    async def test_history_requires_auth(self, async_client):
        resp = await async_client.get("/api/chat/history")
        assert resp.status_code == 403

    async def test_history_empty_returns_empty_list(self, async_client, auth_token):
        resp = await async_client.get(
            "/api/chat/history",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_history_detail_requires_auth(self, async_client):
        resp = await async_client.get("/api/chat/history/sess-1")
        assert resp.status_code == 403

    async def test_history_detail_returns_empty_for_no_messages(self, async_client, auth_token):
        resp = await async_client.get(
            "/api/chat/history/sess-nonexistent",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "sess-nonexistent"
        assert data["messages"] == []
