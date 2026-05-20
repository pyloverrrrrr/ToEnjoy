import pytest


class TestSearch:
    async def test_search_returns_results(self, async_client, auth_token):
        resp = await async_client.post("/api/search", json={
            "query": "headache treatment",
        }, headers={"Authorization": f"Bearer {auth_token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "sources" in data
        assert "total" in data
        assert data["query"] == "headache treatment"
        assert data["total"] >= 0

    async def test_search_requires_auth(self, async_client):
        resp = await async_client.post("/api/search", json={
            "query": "test",
        })
        assert resp.status_code == 403

    async def test_search_result_structure(self, async_client, auth_token):
        resp = await async_client.post("/api/search", json={
            "query": "test query",
        }, headers={"Authorization": f"Bearer {auth_token}"})

        data = resp.json()
        if data["results"]:
            item = data["results"][0]
            assert "id" in item
            assert "title" in item
            assert "content" in item
            assert "source_type" in item
            assert "score" in item
            assert "source" in item
