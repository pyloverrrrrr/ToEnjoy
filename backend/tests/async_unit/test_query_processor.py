import pytest

from app.core.rag.query_processor import QueryProcessor


class TestQueryProcessorProcess:
    async def test_short_query_returns_empty_sub_queries(self, mock_adapter):
        mock_adapter.generate.return_value = "rewritten short query"

        processor = QueryProcessor()
        result = await processor.process("headache", "patient")

        assert result.original == "headache"
        assert result.rewritten == "rewritten short query"
        assert result.sub_queries == []

    async def test_long_query_decomposes(self, mock_adapter):
        mock_adapter.generate.side_effect = [
            "hypertension diabetes medication interaction and daily management guide",
            '["drug interaction for hypertension and diabetes", "daily diet management", "blood glucose monitoring"]',
        ]

        processor = QueryProcessor()
        long_msg = "I have hypertension and diabetes, taking amlodipine and metformin, need guidance on medication safety and daily management tips"
        result = await processor.process(long_msg, "patient")

        assert len(result.sub_queries) == 3
        assert "drug interaction" in result.sub_queries[0]

    async def test_rewrite_preserves_medical_terms(self, mock_adapter):
        mock_adapter.generate.return_value = "migraine preventive treatment flunarizine"

        processor = QueryProcessor()
        result = await processor.process("migraine prevention", "patient")

        assert "migraine" in result.rewritten.lower()

    async def test_decompose_invalid_json_returns_empty(self, mock_adapter):
        long_query = "X" * 50 + " complex medical question about multiple symptoms"
        mock_adapter.generate.side_effect = [
            "rewritten query text",
            "not valid json at all",
        ]

        processor = QueryProcessor()
        result = await processor.process(long_query, "patient")

        assert result.sub_queries == []

    async def test_context_is_included_in_rewrite_prompt(self, mock_adapter):
        mock_adapter.generate.return_value = "rewritten query"

        processor = QueryProcessor()
        await processor.process("fever what to do", "patient", context="previous discussion about cold")

        call_content = mock_adapter.generate.call_args.kwargs["messages"][1]["content"]
        assert "cold" in call_content
