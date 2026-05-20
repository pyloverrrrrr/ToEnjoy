import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.memory.memory_reader import MemoryReader, MemoryContext, UserProfileSummary


class TestMemoryReader:
    def _make_reader_with_mocks(self):
        reader = MemoryReader()

        mock_short = AsyncMock()
        mock_long = AsyncMock()
        mock_db_session = AsyncMock()
        mock_db = AsyncMock()

        return reader, mock_short, mock_long, mock_db_session, mock_db

    def test_read_fuses_all_three_layers(self):
        import asyncio
        reader, mock_short, mock_long, mock_db_session, mock_db = self._make_reader_with_mocks()

        from app.core.memory.short_term import TurnSummary
        mock_short.load.return_value = [
            TurnSummary(role="user", content="headache", intent="consult", timestamp="1.0"),
        ]
        mock_long.search.return_value = ["hypertension diagnosed 2026-03"]
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = MagicMock(
            gender="male", birthday=None, allergies="penicillin",
            medical_history={"chronic": "hypertension"}
        )
        mock_db.__aenter__.return_value = mock_db_session

        with patch("app.core.memory.memory_reader.async_session", return_value=mock_db):
            with patch.object(reader, "short_term", mock_short):
                with patch.object(reader, "long_term", mock_long):
                    result = asyncio.run(reader.read(user_id=1, session_id="sess_x", current_query="test"))

        assert isinstance(result, MemoryContext)
        assert result.user_profile.allergies == "penicillin"
        assert len(result.recent_conversations) == 1
        assert "hypertension" in result.relevant_history[0]
        assert "[用户画像]" in result.formatted_prompt
        assert "penicillin" in result.formatted_prompt
        assert "[近期对话]" in result.formatted_prompt
        assert "[相关历史]" in result.formatted_prompt

    def test_read_all_layers_unavailable_returns_defaults(self):
        import asyncio
        reader, mock_short, mock_long, mock_db_session, mock_db = self._make_reader_with_mocks()

        mock_short.load.return_value = []
        mock_long.search.return_value = []
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        mock_db.__aenter__.return_value = mock_db_session

        with patch("app.core.memory.memory_reader.async_session", return_value=mock_db):
            with patch.object(reader, "short_term", mock_short):
                with patch.object(reader, "long_term", mock_long):
                    result = asyncio.run(reader.read(user_id=1, session_id="sess_x", current_query="test"))

        assert result.user_profile.allergies is None
        assert result.recent_conversations == []
        assert result.relevant_history == []
        assert "暂无历史上下文" in result.formatted_prompt

    def test_read_short_term_fails_degrades_gracefully(self):
        import asyncio
        reader, mock_short, mock_long, mock_db_session, mock_db = self._make_reader_with_mocks()

        mock_short.load.side_effect = Exception("Redis down")
        mock_long.search.return_value = ["event1"]
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = MagicMock(
            gender="female", birthday=None, allergies=None, medical_history=None
        )
        mock_db.__aenter__.return_value = mock_db_session

        with patch("app.core.memory.memory_reader.async_session", return_value=mock_db):
            with patch.object(reader, "short_term", mock_short):
                with patch.object(reader, "long_term", mock_long):
                    result = asyncio.run(reader.read(user_id=1, session_id="sess_x", current_query="test"))

        assert result.recent_conversations == []
        assert result.relevant_history == ["event1"]
        assert result.user_profile.gender == "female"

    def test_read_long_term_fails_degrades_gracefully(self):
        import asyncio
        reader, mock_short, mock_long, mock_db_session, mock_db = self._make_reader_with_mocks()

        from app.core.memory.short_term import TurnSummary
        mock_short.load.return_value = [
            TurnSummary(role="user", content="test", intent="consult", timestamp="1.0"),
        ]
        mock_long.search.side_effect = Exception("ChromaDB down")
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = MagicMock(
            gender="male", birthday=None, allergies=None, medical_history=None
        )
        mock_db.__aenter__.return_value = mock_db_session

        with patch("app.core.memory.memory_reader.async_session", return_value=mock_db):
            with patch.object(reader, "short_term", mock_short):
                with patch.object(reader, "long_term", mock_long):
                    result = asyncio.run(reader.read(user_id=1, session_id="sess_x", current_query="test"))

        assert len(result.recent_conversations) == 1
        assert result.relevant_history == []
        assert result.user_profile.gender == "male"

    def test_read_profile_fails_degrades_gracefully(self):
        import asyncio
        reader, mock_short, mock_long, mock_db_session, mock_db = self._make_reader_with_mocks()

        mock_short.load.return_value = []
        mock_long.search.return_value = ["event1"]
        mock_db_session.execute.side_effect = Exception("MySQL down")
        mock_db.__aenter__.return_value = mock_db_session

        with patch("app.core.memory.memory_reader.async_session", return_value=mock_db):
            with patch.object(reader, "short_term", mock_short):
                with patch.object(reader, "long_term", mock_long):
                    result = asyncio.run(reader.read(user_id=1, session_id="sess_x", current_query="test"))

        assert result.recent_conversations == []
        assert result.relevant_history == ["event1"]
        assert result.user_profile.gender is None
