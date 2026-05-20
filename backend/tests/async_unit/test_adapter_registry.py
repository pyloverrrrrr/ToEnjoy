import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.model_adapter.adapter_registry import AdapterRegistry, AllAdaptersFailedError


@pytest.fixture
def mock_dashscope():
    adapter = MagicMock()
    adapter.name = "dashscope"
    adapter.generate = AsyncMock(return_value="dashscope result")
    adapter.generate_stream = MagicMock()
    adapter.embed = AsyncMock(return_value=[[0.1, 0.2, 0.3]])
    adapter.rerank = AsyncMock(return_value=[{"index": 0, "relevance_score": 0.9}])
    return adapter


@pytest.fixture
def registry_with_mocks(mock_dashscope):
    registry = AdapterRegistry()
    registry._chains = {
        "inference": [mock_dashscope],
        "embedding": [mock_dashscope],
        "reranker": [mock_dashscope],
    }
    return registry


class TestAdapterRegistryGenerate:
    async def test_single_adapter_succeeds(self, registry_with_mocks, mock_dashscope):
        result = await registry_with_mocks.generate([{"role": "user", "content": "test"}])
        assert result == "dashscope result"
        mock_dashscope.generate.assert_awaited_once()

    async def test_failure_raises_error(self, registry_with_mocks, mock_dashscope):
        mock_dashscope.generate.side_effect = RuntimeError("API down")

        with pytest.raises(AllAdaptersFailedError):
            await registry_with_mocks.generate([{"role": "user", "content": "test"}])


class TestAdapterRegistryStream:
    async def test_stream_success(self, registry_with_mocks, mock_dashscope):
        async def dashscope_stream(*args, **kwargs):
            yield "chunk1"
            yield "chunk2"

        mock_dashscope.generate_stream = dashscope_stream

        chunks = []
        async for chunk in registry_with_mocks.generate_stream([{"role": "user", "content": "t"}]):
            chunks.append(chunk)

        assert chunks == ["chunk1", "chunk2"]

    async def test_stream_failure_raises_error(self, registry_with_mocks, mock_dashscope):
        mock_dashscope.generate_stream.side_effect = RuntimeError("stream failed")

        with pytest.raises(AllAdaptersFailedError):
            async for _ in registry_with_mocks.generate_stream([{"role": "user", "content": "t"}]):
                pass


class TestAdapterRegistryEmbed:
    async def test_embed_uses_embedding_chain(self, registry_with_mocks, mock_dashscope):
        result = await registry_with_mocks.embed(["test text"])
        assert result == [[0.1, 0.2, 0.3]]
        mock_dashscope.embed.assert_awaited_once()


class TestAdapterRegistryRerank:
    async def test_rerank_uses_reranker_chain(self, registry_with_mocks, mock_dashscope):
        result = await registry_with_mocks.rerank("query", ["doc1"], top_n=3)
        assert result == [{"index": 0, "relevance_score": 0.9}]
        mock_dashscope.rerank.assert_awaited_once_with("query", ["doc1"], 3)
