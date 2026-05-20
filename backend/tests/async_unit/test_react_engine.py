import pytest
from unittest.mock import AsyncMock, patch

from app.core.agent.react_engine import ReActEngine, MAX_ITERATIONS
from app.schemas.agent import ReActStep


class TestReActEngine:
    @pytest.fixture
    def engine(self):
        return ReActEngine()

    # --- basic execution ---

    async def test_single_step_finish(self, engine, mock_adapter):
        mock_adapter.generate.return_value = (
            "思考: 这是一个简单问题，我可以直接回答。\n"
            "行动: finish\n"
            "行动输入: {\"summary\": \"用户询问问题\"}"
        )

        result = await engine.run("你好", role="patient")

        assert result.iterations == 1
        assert result.steps[0].action == "finish"
        assert result.steps[0].action_input == {"summary": "用户询问问题"}

    async def test_multi_step_with_rag_then_finish(self, engine, mock_adapter):
        mock_adapter.generate.side_effect = [
            # Step 1: fetch RAG results
            "思考: 我需要搜索医学知识库。\n"
            "行动: rag.search\n"
            "行动输入: {\"query\": \"高血压治疗指南\"}",
            # Step 2: finish
            "思考: 已获得足够信息。\n"
            "行动: finish\n"
            "行动输入: {\"summary\": \"高血压需要综合治疗\"}",
        ]

        with patch.object(engine.tool_router, "execute", AsyncMock(return_value="高血压指南内容...")):
            result = await engine.run("怎么治疗高血压", role="patient")

        assert result.iterations == 2
        assert result.steps[0].action == "rag.search"
        assert result.steps[0].observation == "高血压指南内容..."
        assert result.steps[1].action == "finish"

    async def test_mcp_tool_in_react_loop(self, engine, mock_adapter):
        mock_adapter.generate.side_effect = [
            "思考: 需要查询患者病历。\n"
            "行动: patient_record.query_case\n"
            "行动输入: {\"patient_name\": \"张三\"}",
            "思考: 获得了病历信息。\n"
            "行动: finish\n"
            "行动输入: {\"summary\": \"患者有过敏史\"}",
        ]

        with patch.object(engine.tool_router, "execute", AsyncMock(return_value='{"cases": [...]}')):
            result = await engine.run("张三的过敏史", role="doctor", user_id=1)

        assert result.iterations == 2
        assert result.steps[0].action == "patient_record.query_case"
        assert result.steps[1].action == "finish"

    # --- max iterations ---

    async def test_max_iterations_enforced(self, engine, mock_adapter):
        """LLM always returns the same tool call — must stop after MAX_ITERATIONS."""
        mock_adapter.generate.return_value = (
            "思考: 还需要更多信息。\n"
            "行动: rag.search\n"
            "行动输入: {\"query\": \"more info\"}"
        )

        with patch.object(engine.tool_router, "execute", AsyncMock(return_value="results...")):
            result = await engine.run("complex query", role="patient")

        assert result.iterations == MAX_ITERATIONS
        assert all(s.action == "rag.search" for s in result.steps)

    # --- parsing ---

    async def test_parses_chinese_labels(self, engine, mock_adapter):
        """Verify that Chinese-format labels are correctly extracted."""
        mock_adapter.generate.return_value = (
            "思考：患者询问头痛问题\n"
            "行动：rag.search\n"
            "行动输入：{\"query\": \"头痛\"}"
        )

        with patch.object(engine.tool_router, "execute", AsyncMock(return_value="观察: 头痛相关结果...")):
            result = await engine.run("头痛", role="patient")

        assert result.iterations >= 1
        step = result.steps[0]
        assert step.action == "rag.search"
        assert step.action_input == {"query": "头痛"}
        assert "患者询问头痛" in step.thought

    async def test_colon_variants_in_parsing(self, engine, mock_adapter):
        """Support both 思考: and 思考： (full-width colon)."""
        mock_adapter.generate.return_value = (
            "思考：全角冒号\n"
            "行动：finish\n"
            "行动输入：{\"summary\": \"done\"}"
        )

        result = await engine.run("test", role="patient")

        assert result.steps[0].action == "finish"
        assert "全角冒号" in result.steps[0].thought

    async def test_no_action_falls_back_to_finish(self, engine, mock_adapter):
        """If LLM doesn't include an action, stop the loop."""
        mock_adapter.generate.return_value = "这是一段没有行动标记的回复。"

        result = await engine.run("test", role="patient")

        assert result.iterations == 1
        assert result.steps[0].action == "finish"

    # --- tool execution observation ---

    async def test_tool_observation_passed_to_next_iteration(self, engine, mock_adapter):
        mock_adapter.generate.side_effect = [
            "思考: 搜索一下。\n行动: rag.search\n行动输入: {\"query\": \"test\"}",
            "思考: 得到结果，结束。\n行动: finish\n行动输入: {\"summary\": \"ok\"}",
        ]

        with patch.object(engine.tool_router, "execute", AsyncMock(return_value="RAG返回内容ABC")):
            result = await engine.run("test", role="patient")

        # Check that observation was recorded
        assert result.steps[0].observation == "RAG返回内容ABC"

        # Check that the 2nd LLM call received the observation in the conversation
        second_call_msgs = mock_adapter.generate.call_args_list[1].kwargs["messages"]
        observation_found = any("RAG返回内容ABC" in str(m.get("content", "")) for m in second_call_msgs)
        assert observation_found

    # --- memory_context ---

    async def test_memory_context_injected_into_prompt(self, engine, mock_adapter):
        mock_adapter.generate.return_value = (
            "思考: 无需工具。\n行动: finish\n行动输入: {\"summary\": \"ok\"}"
        )

        await engine.run("我又头痛了", role="patient", memory_context="[用户画像] 高血压史")

        user_content = mock_adapter.generate.call_args.kwargs["messages"][1]["content"]
        assert "[用户画像] 高血压史" in user_content
        assert "我又头痛了" in user_content

    # --- tool descriptions ---

    async def test_tool_descriptions_include_mcp_tools(self, engine, mock_adapter):
        mock_adapter.generate.return_value = (
            "思考: 完成。\n行动: finish\n行动输入: {\"summary\": \"ok\"}"
        )

        await engine.run("test", role="patient")

        system_prompt = mock_adapter.generate.call_args.kwargs["messages"][0]["content"]
        assert "rag.search" in system_prompt
        assert "patient_record.query_case" in system_prompt
        assert "identity.verify_patient" in system_prompt
        assert "memory.get_context" in system_prompt
        assert "finish" in system_prompt

    async def test_roles_passed_to_response(self, engine, mock_adapter):
        mock_adapter.generate.return_value = (
            "思考: 直接回答。\n行动: finish\n行动输入: {\"summary\": \"ok\"}"
        )

        result = await engine.run("test", role="doctor", user_id=42, session_id="sess1")

        assert result.iterations == 1
        assert len(result.steps) == 1
