import pytest

from app.core.agent.response_gen import ResponseGenerator


class StreamWrapper:
    """Wraps an async generator to record call args like MagicMock."""
    def __init__(self, chunks):
        self._chunks = chunks
        self.call_args = None
        self.called = False

    def __call__(self, messages, temperature, max_tokens):
        from unittest.mock import call, MagicMock
        m = MagicMock()
        m.kwargs = {"messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        self.call_args = m
        self.called = True
        return self._stream(messages, temperature, max_tokens)

    async def _stream(self, messages, temperature, max_tokens):
        for c in self._chunks:
            yield c


class TestResponseGenerator:
    async def test_patient_uses_patient_prompt(self, mock_adapter):
        wrapper = StreamWrapper(["chunk_a", "chunk_b"])
        mock_adapter.generate_stream = wrapper

        gen = ResponseGenerator()
        chunks = []
        async for chunk in gen.generate("what to do", "consult", [], "patient"):
            chunks.append(chunk)

        assert chunks == ["chunk_a", "chunk_b"]
        assert wrapper.called
        system_prompt = wrapper.call_args.kwargs["messages"][0]["content"]
        assert "layperson" in system_prompt.lower() or "patient" in system_prompt.lower() or "通俗" in system_prompt

    async def test_doctor_uses_professional_prompt(self, mock_adapter):
        wrapper = StreamWrapper(["evidence", "guideline"])
        mock_adapter.generate_stream = wrapper

        gen = ResponseGenerator()
        chunks = []
        async for chunk in gen.generate("NSCLC treatment", "decision_support", [], "doctor"):
            chunks.append(chunk)

        assert chunks == ["evidence", "guideline"]
        system_prompt = wrapper.call_args.kwargs["messages"][0]["content"]
        assert "临床医生" in system_prompt

    async def test_search_results_injected_into_prompt(self, mock_adapter):
        wrapper = StreamWrapper(["answer"])
        mock_adapter.generate_stream = wrapper

        search_results = [
            {"id": "doc1", "content": "headache causes", "metadata": {"title": "Headache Guide"}},
            {"id": "doc2", "content": "migraine treatment", "metadata": {"title": "Migraine Guide"}},
        ]

        gen = ResponseGenerator()
        async for chunk in gen.generate("headache", "consult", search_results, "patient"):
            pass

        user_prompt = wrapper.call_args.kwargs["messages"][1]["content"]
        assert "[1] Headache Guide" in user_prompt
        assert "[2] Migraine Guide" in user_prompt
        assert "headache causes" in user_prompt

    async def test_empty_search_results_uses_default_text(self, mock_adapter):
        wrapper = StreamWrapper(["generic"])
        mock_adapter.generate_stream = wrapper

        gen = ResponseGenerator()
        async for _ in gen.generate("question", "chitchat", [], "patient"):
            pass

        user_prompt = wrapper.call_args.kwargs["messages"][1]["content"]
        assert "暂无" in user_prompt or "knowledge" in user_prompt.lower()

    async def test_max_5_search_results_in_context(self, mock_adapter):
        wrapper = StreamWrapper(["x"])
        mock_adapter.generate_stream = wrapper

        results = [{"id": f"doc{i}", "content": f"content{i}", "metadata": {"title": f"Title{i}"}} for i in range(10)]

        gen = ResponseGenerator()
        async for _ in gen.generate("q", "knowledge_search", results, "patient"):
            pass

        user_prompt = wrapper.call_args.kwargs["messages"][1]["content"]
        assert "[6]" not in user_prompt
        assert "[5]" in user_prompt
