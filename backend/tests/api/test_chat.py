import json
import pytest


class TestChatStream:
    async def test_chat_stream_returns_sse(self, async_client, auth_token):
        resp = await async_client.post("/api/chat/stream", json={
            "message": "headache for three days",
            "session_id": "test-session",
        }, headers={"Authorization": f"Bearer {auth_token}"})

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

    async def test_chat_stream_requires_auth(self, async_client):
        resp = await async_client.post("/api/chat/stream", json={
            "message": "test",
        })
        assert resp.status_code == 403

    async def test_chat_stream_has_chunks_and_done(self, async_client, auth_token):
        resp = await async_client.post("/api/chat/stream", json={
            "message": "test query",
        }, headers={"Authorization": f"Bearer {auth_token}"})

        lines = resp.text.strip().split("\n")
        sse_events = []
        for line in lines:
            if line.startswith("data: "):
                data = json.loads(line[6:])
                sse_events.append(data)

        types = [e.get("type") for e in sse_events]
        assert "chunk" in types
        assert "done" in types
