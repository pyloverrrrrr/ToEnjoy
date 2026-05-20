import pytest
from app.core.mcp.base import BaseMCPModule
from app.schemas.mcp import ToolDefinition, ToolCallResponse, ToolStatus


class TestBaseMCPModule:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            BaseMCPModule()

    def test_concrete_subclass_can_be_instantiated(self):
        class MinModule(BaseMCPModule):
            @property
            def module_name(self):
                return "min"

            def get_tools(self):
                return []

            async def execute(self, tool_name, params):
                return ToolCallResponse(tool="min.x", status=ToolStatus.SUCCESS)

        m = MinModule()
        assert m.module_name == "min"
        assert m.get_tools() == []

    def test_default_timeout_from_settings(self):
        from app.config import settings

        class TimeModule(BaseMCPModule):
            @property
            def module_name(self):
                return "time"

            def get_tools(self):
                return []

            async def execute(self, tool_name, params):
                return ToolCallResponse(tool="time.x", status=ToolStatus.SUCCESS)

        m = TimeModule()
        assert m.timeout == settings.mcp_default_timeout

    def test_custom_timeout_override(self):
        class FastModule(BaseMCPModule):
            @property
            def module_name(self):
                return "fast"

            @property
            def timeout(self):
                return 3.0

            def get_tools(self):
                return []

            async def execute(self, tool_name, params):
                return ToolCallResponse(tool="fast.x", status=ToolStatus.SUCCESS)

        m = FastModule()
        assert m.timeout == 3.0

    def test_validate_params_default_is_noop(self):
        class NoopModule(BaseMCPModule):
            @property
            def module_name(self):
                return "noop"

            def get_tools(self):
                return []

            async def execute(self, tool_name, params):
                return ToolCallResponse(tool="noop.x", status=ToolStatus.SUCCESS)

        m = NoopModule()
        # Should not raise
        m.validate_params("noop.x", {"anything": "goes"})

    def test_get_tools_returns_tool_definitions(self):
        class ToolsModule(BaseMCPModule):
            @property
            def module_name(self):
                return "tools"

            def get_tools(self):
                return [
                    ToolDefinition(
                        name="tools.one",
                        description="Tool one",
                        inputSchema={"type": "object", "properties": {}},
                    ),
                    ToolDefinition(
                        name="tools.two",
                        description="Tool two",
                        inputSchema={"type": "object", "properties": {}},
                    ),
                ]

            async def execute(self, tool_name, params):
                return ToolCallResponse(tool="tools.x", status=ToolStatus.SUCCESS)

        m = ToolsModule()
        tools = m.get_tools()
        assert len(tools) == 2
        assert tools[0].name == "tools.one"
        assert tools[1].name == "tools.two"
