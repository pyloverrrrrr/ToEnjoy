import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.memory.memory_service import MemoryService
from app.core.memory.memory_reader import MemoryContext, UserProfileSummary


class TestMemoryService:
    async def test_get_context_delegates_to_reader(self, mock_adapter):
        with patch("app.core.memory.memory_reader.async_session") as mock_async_session:
            mock_session = AsyncMock()
            mock_session.execute.return_value.scalar_one_or_none.return_value = MagicMock(
                gender="male", allergies=None, medical_history=None
            )
            mock_async_session.return_value.__aenter__.return_value = mock_session

            svc = MemoryService()
            ctx = await svc.get_context(user_id=1, session_id="sess_x", current_query="test")

        assert isinstance(ctx, MemoryContext)
        assert ctx.user_profile.gender == "male"

    async def test_save_turn_calls_short_term_save(self):
        mock_redis = AsyncMock()

        with patch("app.core.memory.short_term.get_redis", return_value=mock_redis):
            svc = MemoryService()
            await svc.save_turn(
                user_id=1, session_id="sess_x",
                user_message="头痛", assistant_response="建议休息", intent="consult",
            )

        assert mock_redis.lpush.call_count == 2
        # Check user entry — saved first in save_turn
        call_args_0 = mock_redis.lpush.call_args_list[0]
        data = json.loads(call_args_0[0][1])
        assert data["role"] == "user"
        assert data["content"] == "头痛"
        # Check assistant entry — saved second
        call_args_1 = mock_redis.lpush.call_args_list[1]
        data = json.loads(call_args_1[0][1])
        assert data["role"] == "assistant"
        assert data["content"] == "建议休息"
