import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.mcp import ToolStatus


class TestPatientRecordModule:
    @pytest.fixture
    def module(self):
        from app.core.mcp.patient_record import PatientRecordModule
        return PatientRecordModule()

    def test_module_name(self, module):
        assert module.module_name == "patient_record"

    def test_get_tools_has_three_tools(self, module):
        tools = module.get_tools()
        assert len(tools) == 3
        names = {t.name for t in tools}
        assert names == {
            "patient_record.query_case",
            "patient_record.query_visit",
            "patient_record.query_prescription",
        }

    def test_tool_schemas_have_required_fields(self, module):
        for tool in module.get_tools():
            assert "patient_name" in tool.inputSchema.get("required", [])

    @pytest.mark.asyncio
    async def test_execute_missing_patient_name(self, module):
        resp = await module.execute("patient_record.query_case", {})
        assert resp.status == ToolStatus.ERROR
        assert "patient_name" in resp.error

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, module):
        module._resolve_patient = AsyncMock(return_value=1)
        resp = await module.execute("patient_record.unknown", {"patient_name": "test"})
        assert resp.status == ToolStatus.ERROR
        assert "不支持工具" in resp.error

    @pytest.mark.asyncio
    async def test_query_case_patient_not_found(self, module):
        module._resolve_patient = AsyncMock(return_value=None)
        resp = await module.execute("patient_record.query_case", {"patient_name": "不存在"})
        assert resp.status == ToolStatus.ERROR
        assert "未找到患者" in resp.error

    @pytest.mark.asyncio
    async def test_query_case_returns_cases(self, module):
        module._resolve_patient = AsyncMock(return_value=1)
        resp = await module.execute("patient_record.query_case", {"patient_name": "张三"})
        assert resp.status == ToolStatus.SUCCESS
        assert resp.data["patient_id"] == 1
        assert len(resp.data["cases"]) == 2
        assert resp.data["cases"][0]["case_id"] == "C2025001"

    @pytest.mark.asyncio
    async def test_query_case_user_without_mock_data(self, module):
        module._resolve_patient = AsyncMock(return_value=999)
        resp = await module.execute("patient_record.query_case", {"patient_name": "Nobody"})
        assert resp.status == ToolStatus.SUCCESS
        assert resp.data["cases"] == []
        assert resp.data["total"] == 0

    @pytest.mark.asyncio
    async def test_query_visit_with_date_filter(self, module):
        module._resolve_patient = AsyncMock(return_value=1)
        resp = await module.execute("patient_record.query_visit", {
            "patient_name": "张三",
            "start_date": "2025-01-01",
        })
        assert resp.status == ToolStatus.SUCCESS
        assert len(resp.data["visits"]) == 1
        assert resp.data["visits"][0]["visit_id"] == "V2025120"

    @pytest.mark.asyncio
    async def test_query_visit_end_date_filter(self, module):
        module._resolve_patient = AsyncMock(return_value=1)
        resp = await module.execute("patient_record.query_visit", {
            "patient_name": "张三",
            "end_date": "2024-12-31",
        })
        assert resp.status == ToolStatus.SUCCESS
        assert len(resp.data["visits"]) == 1
        assert resp.data["visits"][0]["visit_id"] == "V2024100"

    @pytest.mark.asyncio
    async def test_query_prescription_returns_rx(self, module):
        module._resolve_patient = AsyncMock(return_value=1)
        resp = await module.execute("patient_record.query_prescription", {"patient_name": "张三"})
        assert resp.status == ToolStatus.SUCCESS
        assert len(resp.data["prescriptions"]) == 2
        assert resp.data["prescriptions"][0]["drug_name"] == "布洛芬"

    @pytest.mark.asyncio
    async def test_execute_catches_handler_exception(self, module):
        module._resolve_patient = AsyncMock(return_value=1)
        module._query_case = AsyncMock(side_effect=RuntimeError("Boom"))
        resp = await module.execute("patient_record.query_case", {"patient_name": "张三"})
        assert resp.status == ToolStatus.ERROR
        assert "Boom" in resp.error
