import asyncio
import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from app.db.session import async_session
from app.models.patient import PatientProfile
from app.core.memory.short_term import ShortTermMemory, TurnSummary
from app.core.memory.long_term import LongTermMemory

logger = logging.getLogger(__name__)


@dataclass
class UserProfileSummary:
    gender: str | None = None
    allergies: str | None = None
    medical_history: dict | None = None


@dataclass
class MemoryContext:
    user_profile: UserProfileSummary = field(default_factory=UserProfileSummary)
    recent_conversations: list[TurnSummary] = field(default_factory=list)
    relevant_history: list[str] = field(default_factory=list)
    formatted_prompt: str = ""


class MemoryReader:
    MAX_TURN_CONTENT_LENGTH = 200

    def __init__(self):
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()

    async def read(self, user_id: int, session_id: str, current_query: str) -> MemoryContext:
        recent_task = self._load_short_term(session_id)
        long_task = self._load_long_term(current_query, user_id)
        profile_task = self._load_user_profile(user_id)

        recent, long, profile = await asyncio.gather(
            recent_task, long_task, profile_task,
            return_exceptions=True,
        )

        if isinstance(recent, Exception):
            logger.warning(f"Short-term read failed: {recent}")
            recent = []
        if isinstance(long, Exception):
            logger.warning(f"Long-term read failed: {long}")
            long = []
        if isinstance(profile, Exception):
            logger.warning(f"User profile read failed: {profile}")
            profile = UserProfileSummary()

        return MemoryContext(
            user_profile=profile,
            recent_conversations=recent,
            relevant_history=long,
            formatted_prompt=self._format(recent, long, profile),
        )

    async def _load_short_term(self, session_id: str) -> list[TurnSummary]:
        return await self.short_term.load(session_id)

    async def _load_long_term(self, query: str, user_id: int) -> list[str]:
        return await self.long_term.search(query, user_id)

    async def _load_user_profile(self, user_id: int) -> UserProfileSummary:
        async with async_session() as session:
            result = await session.execute(
                select(PatientProfile).where(PatientProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            if profile is None:
                return UserProfileSummary()
            return UserProfileSummary(
                gender=profile.gender,
                allergies=profile.allergies,
                medical_history=profile.medical_history,
            )

    def _format(
        self,
        recent: list[TurnSummary],
        long: list[str],
        profile: UserProfileSummary,
    ) -> str:
        parts = []

        profile_items = []
        if profile.gender:
            profile_items.append(f"性别: {profile.gender}")
        if profile.allergies:
            profile_items.append(f"过敏: {profile.allergies}")
        if profile.medical_history:
            history_str = ", ".join(f"{k}: {v}" for k, v in profile.medical_history.items())
            if history_str:
                profile_items.append(f"病史: {history_str}")
        if profile_items:
            parts.append(f"[用户画像] {' | '.join(profile_items)}")

        if recent:
            recent_lines = []
            for turn in recent:
                role_label = "用户" if turn.role == "user" else "助手"
                recent_lines.append(f"  {role_label}: {turn.content[:self.MAX_TURN_CONTENT_LENGTH]}")
            parts.append(f"[近期对话]\n" + "\n".join(recent_lines))

        if long:
            parts.append(f"[相关历史] " + " | ".join(long))

        if not parts:
            return "暂无历史上下文"

        return "\n\n".join(parts)
