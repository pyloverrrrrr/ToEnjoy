import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from app.core.mcp.registry import MCPToolRegistry, get_mcp_registry
from app.core.mcp.base import BaseMCPModule
from app.schemas.mcp import ToolDefinition, ToolCallResponse, ToolStatus


class MockModule(BaseMCPModule):
    def __init__(self, name="mock", tools=None, execute_fn=None, timeout=None):
        self._name = name
        self._tools = tools or [
            ToolDefinition(name=f"{name}.echo", description="Echo", inputSchema={}),
        ]
        self._execute_fn = execute_fn or (lambda tn, p: ToolCallResponse(
            tool=tn, status=ToolStatus.SUCCESS, data=p,
        ))
        self._timeout = timeout

    @property
    def module_name(self):
        return self._name

    @property
    def timeout(self):
        if self._timeout is not None:
            return self._timeout
        return super().timeout

    def get_tools(self):
        return self._tools

    async def execute(self, tool_name, params):
        import asyncio as _asyncio
        result = self._execute_fn(tool_name, params)
        if _asyncio.iscoroutine(result):
            result = await result
        return result


class TestMCPRegistryRegistration:
    def test_register_module(self):
        registry = MCPToolRegistry()
        mod = MockModule()
        registry.register(mod)
        assert "mock.echo" in registry._tool_index
        assert registry._tool_index["mock.echo"] == "mock"

    def test_get_all_tools_empty(self):
        registry = MCPToolRegistry()
        assert registry.get_all_tools() == []

    def test_get_all_tools_returns_all_module_tools(self):
        registry = MCPToolRegistry()
        mod = MockModule(name="a", tools=[
            ToolDefinition(name="a.t1", description="T1", inputSchema={}),
            ToolDefinition(name="a.t2", description="T2", inputSchema={}),
        ])
        registry.register(mod)
        tools = registry.get_all_tools()
        assert len(tools) == 2
        names = {t.name for t in tools}
        assert names == {"a.t1", "a.t2"}

    def test_register_multiple_modules(self):
        registry = MCPToolRegistry()
        a = MockModule(name="alpha", tools=[
            ToolDefinition(name="alpha.x", description="X", inputSchema={}),
        ])
        b = MockModule(name="beta", tools=[
            ToolDefinition(name="beta.y", description="Y", inputSchema={}),
        ])
        registry.register(a)
        registry.register(b)
        tools = registry.get_all_tools()
        assert len(tools) == 2
        assert registry._tool_index["alpha.x"] == "alpha"
        assert registry._tool_index["beta.y"] == "beta"


class TestMCPRegistryInvoke:
    @pytest.mark.asyncio
    async def test_invoke_success(self):
        registry = MCPToolRegistry()
        registry.register(MockModule())
        resp = await registry.invoke("mock.echo", {"key": "val"})
        assert resp.status == ToolStatus.SUCCESS
        assert resp.data == {"key": "val"}

    @pytest.mark.asyncio
    async def test_invoke_unknown_tool(self):
        registry = MCPToolRegistry()
        resp = await registry.invoke("nonexistent.tool", {})
        assert resp.status == ToolStatus.ERROR
        assert "Unknown tool" in resp.error

    @pytest.mark.asyncio
    async def test_invoke_execution_error(self):
        def failing(tool_name, params):
            raise ValueError("Something broke")

        registry = MCPToolRegistry()
        registry.register(MockModule(execute_fn=failing))
        resp = await registry.invoke("mock.echo", {})
        assert resp.status == ToolStatus.ERROR
        assert "Something broke" in resp.error

    @pytest.mark.asyncio
    async def test_invoke_timeout(self):
        async def slow(tool_name, params):
            await asyncio.sleep(10)

        registry = MCPToolRegistry()
        registry.register(MockModule(timeout=0.05, execute_fn=slow))
        resp = await registry.invoke("mock.echo", {})
        assert resp.status == ToolStatus.TIMEOUT
        assert "timed out" in resp.error


class TestGetMCPRegistrySingleton:
    def test_returns_same_instance(self):
        r1 = get_mcp_registry()
        r2 = get_mcp_registry()
        assert r1 is r2

    def test_singleton_isolated_in_tests(self):
        import app.core.mcp.registry as reg
        old = reg._mcp_registry
        reg._mcp_registry = None
        try:
            r = get_mcp_registry()
            assert isinstance(r, MCPToolRegistry)
        finally:
            reg._mcp_registry = old
