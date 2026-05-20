import pytest


class TestMCPToolsEndpoint:
    @pytest.mark.asyncio
    async def test_list_tools_returns_list(self, async_client, auth_token):
        resp = await async_client.get(
            "/api/mcp/tools",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2
        tool_names = {t["name"] for t in data}
        assert "identity.verify_patient" in tool_names

    @pytest.mark.asyncio
    async def test_list_tools_requires_auth(self, async_client):
        resp = await async_client.get("/api/mcp/tools")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_list_tools_schemas_have_required_keys(self, async_client, auth_token):
        resp = await async_client.get(
            "/api/mcp/tools",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        for tool in resp.json():
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool


class TestMCPInvokeEndpoint:
    @pytest.mark.asyncio
    async def test_invoke_valid_tool(self, async_client, auth_token):
        resp = await async_client.post(
            "/api/mcp/invoke",
            json={"tool": "identity.verify_patient", "params": {"username": "testuser"}},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tool"] == "identity.verify_patient"
        assert data["status"] == "success"
        assert data["data"]["verified"] is True

    @pytest.mark.asyncio
    async def test_invoke_unknown_tool(self, async_client, auth_token):
        resp = await async_client.post(
            "/api/mcp/invoke",
            json={"tool": "nonexistent.tool", "params": {}},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "error"
        assert "Unknown tool" in data["error"]

    @pytest.mark.asyncio
    async def test_invoke_requires_auth(self, async_client):
        resp = await async_client.post(
            "/api/mcp/invoke",
            json={"tool": "identity.verify_patient", "params": {"username": "testuser"}},
        )
        assert resp.status_code == 403
