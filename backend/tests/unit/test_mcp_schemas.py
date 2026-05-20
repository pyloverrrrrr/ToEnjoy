import pytest
from pydantic import ValidationError
from app.schemas.mcp import ToolStatus, ToolDefinition, ToolCallRequest, ToolCallResponse


class TestToolStatus:
    def test_enum_values(self):
        assert ToolStatus.SUCCESS.value == "success"
        assert ToolStatus.TIMEOUT.value == "timeout"
        assert ToolStatus.ERROR.value == "error"

    def test_enum_members_count(self):
        assert len(ToolStatus) == 3


class TestToolDefinition:
    def test_create_minimal(self):
        tool = ToolDefinition(
            name="test.echo",
            description="Echo tool",
            inputSchema={"type": "object", "properties": {}},
        )
        assert tool.name == "test.echo"
        assert tool.description == "Echo tool"
        assert tool.inputSchema == {"type": "object", "properties": {}}

    def test_inputSchema_accepts_complex_dict(self):
        tool = ToolDefinition(
            name="test.search",
            description="Search tool",
            inputSchema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        )
        assert "required" in tool.inputSchema

    def test_missing_required_field_name_raises(self):
        with pytest.raises(ValidationError):
            ToolDefinition(description="No name", inputSchema={})

    def test_missing_required_field_description_raises(self):
        with pytest.raises(ValidationError):
            ToolDefinition(name="test", inputSchema={})

    def test_missing_required_field_inputSchema_raises(self):
        with pytest.raises(ValidationError):
            ToolDefinition(name="test", description="No schema")


class TestToolCallRequest:
    def test_create_full(self):
        req = ToolCallRequest(tool="test.echo", params={"key": "value"})
        assert req.tool == "test.echo"
        assert req.params == {"key": "value"}

    def test_params_defaults_to_empty_dict(self):
        req = ToolCallRequest(tool="test.echo")
        assert req.params == {}

    def test_missing_tool_raises(self):
        with pytest.raises(ValidationError):
            ToolCallRequest()


class TestToolCallResponse:
    def test_success_response(self):
        resp = ToolCallResponse(
            tool="test.echo",
            status=ToolStatus.SUCCESS,
            data={"result": "ok"},
        )
        assert resp.status == ToolStatus.SUCCESS
        assert resp.data == {"result": "ok"}
        assert resp.error is None

    def test_error_response(self):
        resp = ToolCallResponse(
            tool="test.echo",
            status=ToolStatus.ERROR,
            error="Something went wrong",
        )
        assert resp.status == ToolStatus.ERROR
        assert resp.data is None
        assert resp.error == "Something went wrong"

    def test_timeout_response(self):
        resp = ToolCallResponse(
            tool="test.slow",
            status=ToolStatus.TIMEOUT,
            error="Timed out after 10s",
        )
        assert resp.status == ToolStatus.TIMEOUT

    def test_data_is_optional(self):
        resp = ToolCallResponse(tool="test.echo", status=ToolStatus.SUCCESS)
        assert resp.data is None
        assert resp.error is None

    def test_error_is_optional(self):
        resp = ToolCallResponse(tool="test.echo", status=ToolStatus.SUCCESS, data={})
        assert resp.error is None
