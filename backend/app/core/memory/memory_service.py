import logging
import time

import app.db.session
from app.models.conversation import Conversation
from app.core.memory.short_term import ShortTermMemory, TurnEntry
from app.core.memory.long_term import LongTermMemory
from app.core.memory.event_extractor import EventExtractor
from app.core.memory.memory_reader import MemoryReader, MemoryContext

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(self):
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
        self.event_extractor = EventExtractor()
        self.reader = MemoryReader()

    async def get_context(self, user_id: int, session_id: str, current_query: str) -> MemoryContext:
        return await self.reader.read(user_id, session_id, current_query)

    async def save_turn(
        self,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_response: str,
        intent: str,
    ) -> None:
        try:
            ts = time.time()
            entry = TurnEntry(role="user", content=user_message, intent=intent, timestamp=ts)
            await self.short_term.save(session_id, entry)
            entry_assistant = TurnEntry(role="assistant", content=assistant_response, intent=intent, timestamp=ts)
            await self.short_term.save(session_id, entry_assistant)
        except Exception:
            logger.warning("Failed to save turn to short-term memory", exc_info=True)

        try:
            async with app.db.session.async_session() as db:
                db.add(Conversation(
                    user_id=user_id,
                    session_id=session_id,
                    role="user",
                    content=user_message,
                    intent=intent,
                ))
                db.add(Conversation(
                    user_id=user_id,
                    session_id=session_id,
                    role="assistant",
                    content=assistant_response,
                    intent=intent,
                ))
                await db.commit()
        except Exception:
            logger.warning("Failed to persist turn to MySQL", exc_info=True)

        try:
            events = await self.event_extractor.extract(
                user_message=user_message,
                assistant_response=assistant_response,
                previous_events=None,
            )
            if events.symptoms or events.diagnosis or events.key_events:
                await self.long_term.save(user_id, events)
        except Exception:
            logger.warning("Event extraction failed, skipping", exc_info=True)
