import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.memory.long_term import LongTermMemory
from app.core.memory.event_extractor import ExtractedEvents


class TestLongTermMemory:
    async def test_search_embeds_query_and_queries_chroma(self, mock_adapter):
        mock_col = MagicMock()
        mock_col.query.return_value = {
            "ids": [["evt1", "evt2"]],
            "documents": [["migraine history", "hypertension diagnosed March"]],
            "distances": [[0.12, 0.18]],
        }
        mock_chroma = MagicMock()
        mock_chroma.get_collection.return_value = mock_col
        mock_adapter.embed = AsyncMock(return_value=[[0.1] * 4096])

        with patch("app.core.memory.long_term.get_chroma", return_value=mock_chroma), \
             patch("app.core.memory.long_term.get_adapter_registry", return_value=mock_adapter):
            memory = LongTermMemory()
            results = await memory.search("headache", user_id=1, top_k=3)

        assert len(results) == 2
        assert results[0] == "migraine history"
        mock_adapter.embed.assert_called_once_with(["headache"])
        mock_col.query.assert_called_once()
        call_kwargs = mock_col.query.call_args.kwargs
        assert call_kwargs["n_results"] == 3
        assert call_kwargs["where"] == {"user_id": 1}

    async def test_search_chroma_unavailable_returns_empty(self, mock_adapter):
        mock_chroma = MagicMock()
        mock_chroma.get_collection.side_effect = Exception("ChromaDB down")
        mock_adapter.embed = AsyncMock(return_value=[[0.1] * 4096])

        with patch("app.core.memory.long_term.get_chroma", return_value=mock_chroma), \
             patch("app.core.memory.long_term.get_adapter_registry", return_value=mock_adapter):
            memory = LongTermMemory()
            results = await memory.search("query", user_id=1)

        assert results == []

    async def test_save_embeds_and_upserts_to_chroma(self, mock_adapter):
        mock_col = MagicMock()
        mock_chroma = MagicMock()
        mock_chroma.get_collection.return_value = mock_col
        mock_adapter.embed = AsyncMock(return_value=[[0.2] * 4096])

        events = ExtractedEvents(
            symptoms=["fever"],
            diagnosis=[],
            medications=[],
            allergies=[],
            key_events=["patient had fever for 2 days"],
        )

        with patch("app.core.memory.long_term.get_chroma", return_value=mock_chroma), \
             patch("app.core.memory.long_term.get_adapter_registry", return_value=mock_adapter):
            memory = LongTermMemory()
            await memory.save(user_id=1, events=events)

        mock_col.upsert.assert_called_once()
        call_kwargs = mock_col.upsert.call_args.kwargs
        assert "ids" in call_kwargs
        assert "documents" in call_kwargs
        assert "embeddings" in call_kwargs
        assert "metadatas" in call_kwargs
        assert call_kwargs["metadatas"][0]["user_id"] == 1

    async def test_save_empty_events_skips_chroma(self, mock_adapter):
        mock_col = MagicMock()
        mock_chroma = MagicMock()
        mock_chroma.get_collection.return_value = mock_col

        events = ExtractedEvents()

        with patch("app.core.memory.long_term.get_chroma", return_value=mock_chroma), \
             patch("app.core.memory.long_term.get_adapter_registry", return_value=mock_adapter):
            memory = LongTermMemory()
            await memory.save(user_id=1, events=events)

        mock_col.upsert.assert_not_called()

    async def test_save_includes_all_event_fields(self, mock_adapter):
        mock_col = MagicMock()
        mock_chroma = MagicMock()
        mock_chroma.get_collection.return_value = mock_col
        mock_adapter.embed = AsyncMock(return_value=[[0.3] * 4096])

        events = ExtractedEvents(
            symptoms=["headache"],
            diagnosis=["migraine"],
            medications=["ibuprofen"],
            allergies=["aspirin"],
            key_events=["patient has chronic migraine"],
        )

        with patch("app.core.memory.long_term.get_chroma", return_value=mock_chroma), \
             patch("app.core.memory.long_term.get_adapter_registry", return_value=mock_adapter):
            memory = LongTermMemory()
            await memory.save(user_id=1, events=events)

        call_kwargs = mock_col.upsert.call_args.kwargs
        docs = call_kwargs["documents"]
        assert "headache" in docs
        assert "migraine" in docs
        assert "ibuprofen" in docs
        assert "aspirin" in docs
        assert "patient has chronic migraine" in docs
