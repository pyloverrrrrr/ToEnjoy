import json
import logging
from dataclasses import dataclass

from app.db.redis import get_redis

logger = logging.getLogger(__name__)


@dataclass
class TurnEntry:
    role: str
    content: str
    intent: str
    timestamp: float


@dataclass
class TurnSummary:
    role: str
    content: str
    intent: str | None
    timestamp: str


class ShortTermMemory:
    KEY_PREFIX = "session"
    MAX_TURNS = 20
    TTL_SECONDS = 1800

    def _key(self, session_id: str) -> str:
        return f"{self.KEY_PREFIX}:{session_id}:context"

    @staticmethod
    def _serialize(entry: TurnEntry) -> str:
        return json.dumps({
            "role": entry.role,
            "content": entry.content,
            "intent": entry.intent,
            "timestamp": entry.timestamp,
        }, ensure_ascii=False)

    @staticmethod
    def _deserialize(data: str) -> TurnSummary | None:
        try:
            d = json.loads(data)
            return TurnSummary(
                role=d.get("role", ""),
                content=d.get("content", ""),
                intent=d.get("intent"),
                timestamp=str(d.get("timestamp", "")),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Skipping corrupt memory entry: {e}")
            return None

    async def save(self, session_id: str, entry: TurnEntry) -> None:
        try:
            redis = await get_redis()
            if redis is None:
                logger.warning("Short-term memory: Redis not initialized")
                return
            key = self._key(session_id)
            await redis.lpush(key, self._serialize(entry))
            await redis.ltrim(key, 0, self.MAX_TURNS - 1)
            await redis.expire(key, self.TTL_SECONDS)
        except Exception as e:  # Degrade gracefully — Redis is non-critical for conversation flow
            logger.warning(f"Short-term memory save failed: {e}")

    async def delete(self, session_id: str) -> None:
        try:
            redis = await get_redis()
            if redis is None:
                return
            await redis.delete(self._key(session_id))
        except Exception as e:
            logger.warning(f"Short-term memory delete failed: {e}")

    async def load(self, session_id: str, n: int = 10) -> list[TurnSummary]:
        try:
            redis = await get_redis()
            if redis is None:
                logger.warning("Short-term memory: Redis not initialized")
                return []
            key = self._key(session_id)
            n = max(1, min(n, self.MAX_TURNS))
            raw = await redis.lrange(key, 0, n - 1)
            results = []
            for r in raw:
                item = self._deserialize(r)
                if item is not None:
                    results.append(item)
            return results
        except Exception as e:
            logger.warning(f"Short-term memory load failed: {e}")
            return []
