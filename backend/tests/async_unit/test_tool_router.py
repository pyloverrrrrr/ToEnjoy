import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.agent.tool_router import ToolRouter
from app.schemas.mcp import ToolCallResponse, ToolStatus


class TestToolRouter:
    @pytest.fixture
    def router(self):
        return ToolRouter()

    # --- rag.search ---

    async def test_rag_search_returns_formatted_results(self, router):
        bm25 = [{"id": "b1", "content": "BM25 result", "metadata": {"title": "BM25 Doc"}}]
        vec = [{"id": "v1", "content": "Vector result", "metadata": {"title": "Vec Doc"}}]
        final = [
            {"content": "Merged BM25", "metadata": {"title": "BM25 Doc"}},
            {"content": "Merged Vector", "metadata": {"title": "Vec Doc"}},
        ]

        with patch.object(router.hybrid_retriever, "search", AsyncMock(return_value=(bm25, vec))), \
             patch.object(router.post_processor, "process", AsyncMock(return_value=final)):
            result = await router.execute("rag.search", {"query": "headache"}, role="doctor")

        assert "[1] BM25 Doc" in result
        assert "[2] Vec Doc" in result
        assert "Merged BM25" in result

    async def test_rag_search_missing_query_param(self, router):
        result = await router.execute("rag.search", {})
        assert "需要 'query'" in result

    async def test_rag_search_no_results(self, router):
        with patch.object(router.hybrid_retriever, "search", AsyncMock(return_value=([], []))), \
             patch.object(router.post_processor, "process", AsyncMock(return_value=[])):
            result = await router.execute("rag.search", {"query": "rare-disease-xyz"})

        assert "未找到" in result

    async def test_rag_search_uses_correct_collection_for_role(self, router):
        with patch.object(router.hybrid_retriever, "search", AsyncMock(return_value=([], []))) as mock_search, \
             patch.object(router.post_processor, "process", AsyncMock(return_value=[{"content": "ok", "metadata": {"title": "T"}}])):
            await router.execute("rag.search", {"query": "test"}, role="patient")

        call_kwargs = mock_search.call_args.kwargs
        assert call_kwargs["collection"] == "kb_patient"

    # --- mcp.* ---

    async def test_mcp_invoke_success(self, router):
        response = ToolCallResponse(
            tool="identity.verify_patient",
            status=ToolStatus.SUCCESS,
            data={"verified": True, "user_id": 1},
        )
        with patch("app.core.agent.tool_router.get_mcp_registry") as mock_reg:
            mock_reg.return_value.invoke = AsyncMock(return_value=response)
            result = await router.execute("identity.verify_patient", {"username": "test"})

        assert "verified" in result
        assert "true" in result

    async def test_mcp_invoke_error(self, router):
        response = ToolCallResponse(
            tool="patient_record.query_case",
            status=ToolStatus.ERROR,
            error="Patient not found",
        )
        with patch("app.core.agent.tool_router.get_mcp_registry") as mock_reg:
            mock_reg.return_value.invoke = AsyncMock(return_value=response)
            result = await router.execute("patient_record.query_case", {"patient_name": "nobody"})

        assert "Patient not found" in result

    # --- memory.get_context ---

    async def test_memory_context_with_valid_user(self, router):
        mock_ctx = MagicMock()
        mock_ctx.formatted_prompt = "[用户画像] 测试用户画像信息"

        with patch.object(router.memory_service, "get_context", AsyncMock(return_value=mock_ctx)):
            result = await router.execute("memory.get_context", {}, user_id=1, session_id="s1", message="test")

        assert "测试用户画像信息" in result

    async def test_memory_context_with_zero_user_id(self, router):
        result = await router.execute("memory.get_context", {}, user_id=0)
        assert "未认证" in result

    async def test_memory_context_none_result(self, router):
        mock_ctx = MagicMock()
        mock_ctx.formatted_prompt = None

        with patch.object(router.memory_service, "get_context", AsyncMock(return_value=mock_ctx)):
            result = await router.execute("memory.get_context", {}, user_id=1, session_id="s1", message="test")

        assert "暂无" in result

    # --- edge cases ---

    async def test_unknown_tool_routes_to_mcp(self, router):
        response = ToolCallResponse(
            tool="nonexistent.tool",
            status=ToolStatus.ERROR,
            error="Unknown tool: 'nonexistent.tool'",
        )
        with patch("app.core.agent.tool_router.get_mcp_registry") as mock_reg:
            mock_reg.return_value.invoke = AsyncMock(return_value=response)
            result = await router.execute("nonexistent.tool", {})
        assert "Unknown tool" in result

    async def test_execution_exception_is_caught(self, router):
        with patch.object(router.hybrid_retriever, "search", side_effect=RuntimeError("Boom")):
            result = await router.execute("rag.search", {"query": "test"})

        assert "Boom" in result or "工具执行异常" in result
