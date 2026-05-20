import json
import pytest
from unittest.mock import AsyncMock, patch
from app.core.memory.short_term import ShortTermMemory, TurnEntry


class TestShortTermMemory:
    def test_save_pushes_and_trims_and_expires(self):
        mock_redis = AsyncMock()
        memory = ShortTermMemory()

        entry = TurnEntry(role="user", content="头痛怎么办", intent="consult", timestamp=1715700000.0)

        with patch("app.core.memory.short_term.get_redis", return_value=mock_redis):
            import asyncio
            asyncio.run(memory.save("sess_abc", entry))

        key = "session:sess_abc:context"
        mock_redis.lpush.assert_called_once()
        args = mock_redis.lpush.call_args[0]
        assert args[0] == key
        data = json.loads(args[1])
        assert data["role"] == "user"
        assert data["content"] == "头痛怎么办"
        mock_redis.ltrim.assert_called_once_with(key, 0, 19)
        mock_redis.expire.assert_called_once_with(key, 1800)

    def test_load_returns_parsed_turns(self):
        mock_redis = AsyncMock()
        mock_redis.lrange.return_value = [
            json.dumps({"role": "user", "content": "Q1", "intent": "consult", "timestamp": 1.0}),
            json.dumps({"role": "assistant", "content": "A1", "intent": None, "timestamp": 2.0}),
        ]
        memory = ShortTermMemory()

        with patch("app.core.memory.short_term.get_redis", return_value=mock_redis):
            import asyncio
            result = asyncio.run(memory.load("sess_abc"))

        assert len(result) == 2
        assert result[0].role == "user"
        assert result[0].content == "Q1"
        assert result[1].role == "assistant"
        mock_redis.lrange.assert_called_once_with("session:sess_abc:context", 0, 9)

    def test_load_empty_session_returns_empty_list(self):
        mock_redis = AsyncMock()
        mock_redis.lrange.return_value = []
        memory = ShortTermMemory()

        with patch("app.core.memory.short_term.get_redis", return_value=mock_redis):
            import asyncio
            result = asyncio.run(memory.load("sess_abc"))

        assert result == []

    def test_load_redis_unavailable_returns_empty_list(self):
        mock_redis = AsyncMock()
        mock_redis.lrange.side_effect = Exception("connection refused")
        memory = ShortTermMemory()

        with patch("app.core.memory.short_term.get_redis", return_value=mock_redis):
            import asyncio
            result = asyncio.run(memory.load("sess_abc"))

        assert result == []

    def test_save_redis_unavailable_logs_warning(self, caplog):
        import logging
        mock_redis = AsyncMock()
        mock_redis.lpush.side_effect = Exception("connection refused")
        memory = ShortTermMemory()
        entry = TurnEntry(role="user", content="test", intent="consult", timestamp=1.0)

        with patch("app.core.memory.short_term.get_redis", return_value=mock_redis), \
             caplog.at_level(logging.WARNING):
            import asyncio
            asyncio.run(memory.save("sess_abc", entry))

        assert "Short-term memory save failed" in caplog.text
