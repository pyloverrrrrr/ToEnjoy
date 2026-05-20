import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.agent.orchestrator import Orchestrator


class TestOrchestrator:
    @pytest.fixture
    def orch(self):
        return Orchestrator()

    def _setup_mocks(self, orch, mock_adapter):
        """Wire all internal dependencies so run() can execute without real I/O."""
        orch.react_engine.run = AsyncMock()
        orch.memory_service.get_context = AsyncMock()
        orch.response_gen.generate = MagicMock()

    # --- basic flow ---

    async def test_yields_chunks_and_done(self, orch, mock_adapter):
        self._setup_mocks(orch, mock_adapter)
        orch.memory_service.get_context.return_value = None
        orch.react_engine.run.return_value = MagicMock(steps=[])

        async def _stream(*a, **kw):
            yield "hello"
            yield " world"
        orch.response_gen.generate.return_value = _stream()

        events = []
        async for event in orch.run("test", "patient", "patient", "sess1", user_id=1):
            events.append(event)

        types = [e["type"] for e in events]
        assert "chunk" in types
        assert "done" in types
        assert events[-1]["type"] == "done"

    async def test_yields_reasoning_steps(self, orch, mock_adapter):
        self._setup_mocks(orch, mock_adapter)
        orch.memory_service.get_context.return_value = None
        orch.react_engine.run.return_value = MagicMock(steps=[])

        async def _stream(*a, **kw):
            yield "x"
        orch.response_gen.generate.return_value = _stream()

        events = []
        async for event in orch.run("test", "doctor", "doctor", "s1", user_id=2):
            events.append(event)

        types = [e["type"] for e in events]
        # reasoning_steps emitted even when empty list (for doctor-facing UI)
        assert "reasoning_steps" in types

    async def test_yields_sources(self, orch, mock_adapter):
        self._setup_mocks(orch, mock_adapter)
        orch.memory_service.get_context.return_value = None
        orch.react_engine.run.return_value = MagicMock(steps=[])

        async def _stream(*a, **kw):
            yield "answer"
        orch.response_gen.generate.return_value = _stream()

        events = []
        async for event in orch.run("test", "doctor", "doctor", "s1", user_id=3):
            events.append(event)

        assert any(e["type"] == "sources" for e in events)

    # --- memory integration ---

    async def test_memory_context_not_loaded_for_user_zero(self, orch, mock_adapter):
        self._setup_mocks(orch, mock_adapter)
        orch.react_engine.run.return_value = MagicMock(steps=[])

        async def _stream(*a, **kw):
            yield "hi"
        orch.response_gen.generate.return_value = _stream()

        async for _ in orch.run("hello", "patient", "patient", "s1", user_id=0):
            pass

        orch.memory_service.get_context.assert_not_called()

    async def test_memory_passed_to_response_gen(self, orch, mock_adapter):
        self._setup_mocks(orch, mock_adapter)
        mock_ctx = MagicMock()
        mock_ctx.formatted_prompt = "[用户画像] 测试"
        orch.memory_service.get_context.return_value = mock_ctx
        orch.react_engine.run.return_value = MagicMock(steps=[])

        async def _stream(*a, **kw):
            yield "response"
        orch.response_gen.generate.return_value = _stream()

        async for _ in orch.run("question", "patient", "patient", "s1", user_id=1):
            pass

        call_kwargs = orch.response_gen.generate.call_args.kwargs
        assert call_kwargs["memory_context"] == "[用户画像] 测试"

    # --- react steps passed to response_gen ---

    async def test_react_steps_passed_to_response_gen(self, orch, mock_adapter):
        self._setup_mocks(orch, mock_adapter)
        orch.memory_service.get_context.return_value = None

        from app.schemas.agent import ReActStep, ReActResult
        steps = [
            ReActStep(thought="需要搜索", action="rag.search",
                       action_input={"query": "高血压"}, observation="找到了3条结果"),
            ReActStep(thought="信息充足", action="finish",
                       action_input={"summary": "ok"}, observation=""),
        ]
        orch.react_engine.run.return_value = ReActResult(steps=steps, iterations=2)

        async def _stream(*a, **kw):
            yield "answer"
        orch.response_gen.generate.return_value = _stream()

        async for _ in orch.run("高血压怎么治", "patient", "patient", "s1", user_id=1):
            pass

        call_kwargs = orch.response_gen.generate.call_args.kwargs
        passed_steps = call_kwargs["react_steps"]
        assert len(passed_steps) == 2
        assert passed_steps[0].action == "rag.search"
