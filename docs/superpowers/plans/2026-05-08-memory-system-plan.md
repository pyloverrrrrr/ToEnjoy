# 记忆系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现三层记忆架构（Redis 短期 + ChromaDB 长期 + MySQL 持久），集成到 orchestrator 对话管道中。

**Architecture:** MemoryService 作为统一入口提供 get_context() 和 save_turn() 两个薄接口，内部分别委托给 ShortTermMemory（Redis）、LongTermMemory（ChromaDB）、EventExtractor（LLM异步抽取）和 MemoryReader（三层融合）。Orchestrator 在 Intent 分类前读取记忆，Chat API 在流式结束后触发写入。

**Tech Stack:** Redis (aioredis) · ChromaDB (chromadb-client) · SQLAlchemy 2.0 async · Qwen3-Embedding-8B · pytest-asyncio (auto mode)

---

## 文件清单

**Create (7 files):**
- `backend/app/models/conversation.py` — Conversation ORM 模型
- `backend/app/core/memory/short_term.py` — Redis 短期记忆
- `backend/app/core/memory/event_extractor.py` — LLM 事件抽取
- `backend/app/core/memory/long_term.py` — ChromaDB 长期记忆
- `backend/app/core/memory/memory_reader.py` — 三层融合读取
- `backend/app/core/memory/memory_service.py` — 统一入口

**Modify (5 files):**
- `backend/app/models/__init__.py` — 导出 Conversation
- `backend/app/core/memory/__init__.py` — 导出 MemoryService, MemoryContext
- `backend/app/core/agent/response_gen.py` — generate() 新增 memory_context 参数
- `backend/app/core/agent/orchestrator.py` — 集成 MemoryService
- `backend/app/api/chat.py` — 流式结束后触发 save_turn

**Test files (5 files):**
- `backend/tests/unit/test_short_term.py`
- `backend/tests/unit/test_event_extractor.py`
- `backend/tests/unit/test_memory_reader.py`
- `backend/tests/async_unit/test_long_term.py`
- `backend/tests/async_unit/test_memory_service.py`

---

### Task 1: Conversation ORM 模型

**Files:**
- Create: `backend/app/models/conversation.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/unit/test_schemas.py` (extend — no new test file; Conversation 是纯 ORM 无需单独单元测试)

- [ ] **Step 1: 创建 Conversation 模型**

```python
# backend/app/models/conversation.py
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sources: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    token_count: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 2: 更新 models/__init__.py 导出**

```python
# backend/app/models/__init__.py
from app.models.base import Base
from app.models.user import User
from app.models.patient import PatientProfile
from app.models.doctor import DoctorProfile
from app.models.conversation import Conversation

__all__ = ["Base", "User", "PatientProfile", "DoctorProfile", "Conversation"]
```

- [ ] **Step 3: 验证模型可导入**

Run: `cd backend && /c/Users/20530/AppData/Local/Programs/Python/Python312/python.exe -c "from app.models import Conversation; print('OK')"`
Expected: `OK`

---

### Task 2: ShortTermMemory (Redis 短期记忆)

**Files:**
- Create: `backend/app/core/memory/short_term.py`
- Create: `backend/tests/unit/test_short_term.py`

- [ ] **Step 1: 编写失败测试**

```python
# backend/tests/unit/test_short_term.py
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

        assert "short_term" in caplog.text.lower() or "redis" in caplog.text.lower()
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && /c/Users/20530/AppData/Local/Programs/Python/Python312/python.exe -m pytest tests/unit/test_short_term.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.core.memory.short_term'`

- [ ] **Step 3: 实现 ShortTermMemory**

```python
# backend/app/core/memory/short_term.py
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
    def _deserialize(data: str) -> TurnSummary:
        d = json.loads(data)
        return TurnSummary(
            role=d["role"],
            content=d["content"],
            intent=d.get("intent"),
            timestamp=str(d.get("timestamp", "")),
        )

    async def save(self, session_id: str, entry: TurnEntry) -> None:
        try:
            redis = await get_redis()
            key = self._key(session_id)
            await redis.lpush(key, self._serialize(entry))
            await redis.ltrim(key, 0, self.MAX_TURNS - 1)
            await redis.expire(key, self.TTL_SECONDS)
        except Exception as e:
            logger.warning(f"Short-term memory save failed: {e}")

    async def load(self, session_id: str, n: int = 10) -> list[TurnSummary]:
        try:
            redis = await get_redis()
            key = self._key(session_id)
            raw = await redis.lrange(key, 0, n - 1)
            return [self._deserialize(r) for r in raw]
        except Exception as e:
            logger.warning(f"Short-term memory load failed: {e}")
            return []
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && /c/Users/20530/AppData/Local/Programs/Python/Python312/python.exe -m pytest tests/unit/test_short_term.py -v`
Expected: 5 PASSED

---

### Task 3: EventExtractor (LLM 事件异步抽取)

**Files:**
- Create: `backend/app/core/memory/event_extractor.py`
- Create: `backend/tests/unit/test_event_extractor.py`

- [ ] **Step 1: 编写失败测试**

```python
# backend/tests/unit/test_event_extractor.py
import json
import pytest
from unittest.mock import AsyncMock, patch
from app.core.memory.event_extractor import EventExtractor, ExtractedEvents


class TestEventExtractor:
    def test_extract_valid_json_parses_events(self):
        mock_adapter = AsyncMock()
        mock_adapter.generate.return_value = json.dumps({
            "symptoms": ["headache", "nausea"],
            "diagnosis": [],
            "medications": [],
            "allergies": [],
            "key_events": ["patient reports 3-day headache"],
        })

        with patch("app.core.memory.event_extractor.get_adapter_registry", return_value=mock_adapter):
            import asyncio
            extractor = EventExtractor()
            result = asyncio.run(extractor.extract("I have a headache", "You should rest"))

        assert result.symptoms == ["headache", "nausea"]
        assert result.diagnosis == []
        assert result.key_events == ["patient reports 3-day headache"]

    def test_extract_invalid_json_falls_back_to_empty(self):
        mock_adapter = AsyncMock()
        mock_adapter.generate.return_value = "not json at all {{{"

        with patch("app.core.memory.event_extractor.get_adapter_registry", return_value=mock_adapter):
            import asyncio
            extractor = EventExtractor()
            result = asyncio.run(extractor.extract("hello", "hi"))

        assert result.symptoms == []
        assert result.key_events == []

    def test_extract_merges_with_previous_events(self):
        mock_adapter = AsyncMock()
        mock_adapter.generate.return_value = json.dumps({
            "symptoms": ["cough"],
            "diagnosis": [],
            "medications": ["amoxicillin"],
            "allergies": [],
            "key_events": ["prescribed amoxicillin"],
        })

        previous = {
            "symptoms": ["fever"],
            "diagnosis": ["flu"],
            "medications": [],
            "allergies": ["penicillin"],
            "key_events": ["diagnosed with flu"],
        }

        with patch("app.core.memory.event_extractor.get_adapter_registry", return_value=mock_adapter):
            import asyncio
            extractor = EventExtractor()
            result = asyncio.run(extractor.extract("coughing", "take amoxicillin", previous))

        assert "fever" in result.symptoms
        assert "cough" in result.symptoms
        assert "penicillin" in result.allergies
        assert "flu" in result.diagnosis

    def test_extract_llm_failure_retries_once_then_empty(self):
        mock_adapter = AsyncMock()
        mock_adapter.generate.side_effect = Exception("API timeout")

        with patch("app.core.memory.event_extractor.get_adapter_registry", return_value=mock_adapter):
            import asyncio
            extractor = EventExtractor()
            result = asyncio.run(extractor.extract("test", "response"))

        assert result.symptoms == []
        assert mock_adapter.generate.call_count == 2
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && /c/Users/20530/AppData/Local/Programs/Python/Python312/python.exe -m pytest tests/unit/test_event_extractor.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 EventExtractor**

```python
# backend/app/core/memory/event_extractor.py
import json
import logging
from dataclasses import dataclass, field

from app.core.model_adapter.adapter_registry import get_adapter_registry

logger = logging.getLogger(__name__)

EXTRACT_PROMPT = """You are a medical event extraction expert. Extract key medical events from the conversation.

Output JSON format:
{
  "symptoms": ["symptom1", "symptom2"],
  "diagnosis": ["diagnosis1"],
  "medications": ["med1", "med2"],
  "allergies": ["allergy1"],
  "key_events": ["event summary 1", "event summary 2"]
}

Rules:
- Only extract events explicitly mentioned by the user
- symptoms: reported symptoms (headache, nausea, etc.)
- diagnosis: confirmed diagnoses only, not speculation
- medications: prescribed or mentioned medications
- allergies: known allergies
- key_events: 1-2 sentence summaries of important medical events in this conversation"""


@dataclass
class ExtractedEvents:
    symptoms: list[str] = field(default_factory=list)
    diagnosis: list[str] = field(default_factory=list)
    medications: list[str] = field(default_factory=list)
    allergies: list[str] = field(default_factory=list)
    key_events: list[str] = field(default_factory=list)


class EventExtractor:
    MAX_RETRIES = 1

    async def extract(
        self,
        user_message: str,
        assistant_response: str,
        previous_events: dict | None = None,
    ) -> ExtractedEvents:
        adapter = get_adapter_registry()
        conversation = f"User: {user_message}\nAssistant: {assistant_response}"

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                result = await adapter.generate(
                    messages=[
                        {"role": "system", "content": EXTRACT_PROMPT},
                        {"role": "user", "content": conversation},
                    ],
                    temperature=0.1,
                    max_tokens=256,
                )
                data = json.loads(result.strip().removeprefix("```json").removesuffix("```"))
                new_events = ExtractedEvents(
                    symptoms=data.get("symptoms", []),
                    diagnosis=data.get("diagnosis", []),
                    medications=data.get("medications", []),
                    allergies=data.get("allergies", []),
                    key_events=data.get("key_events", []),
                )
                if previous_events:
                    return self._merge(new_events, previous_events)
                return new_events
            except Exception as e:
                logger.warning(f"Event extraction attempt {attempt + 1} failed: {e}")
                if attempt >= self.MAX_RETRIES:
                    break
        return ExtractedEvents()

    def _merge(self, new_events: ExtractedEvents, previous_events: dict) -> ExtractedEvents:
        prev = ExtractedEvents(
            symptoms=previous_events.get("symptoms", []),
            diagnosis=previous_events.get("diagnosis", []),
            medications=previous_events.get("medications", []),
            allergies=previous_events.get("allergies", []),
            key_events=previous_events.get("key_events", []),
        )
        return ExtractedEvents(
            symptoms=list(set(prev.symptoms + new_events.symptoms)),
            diagnosis=list(set(prev.diagnosis + new_events.diagnosis)),
            medications=list(set(prev.medications + new_events.medications)),
            allergies=list(set(prev.allergies + new_events.allergies)),
            key_events=list(set(prev.key_events + new_events.key_events)),
        )
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && /c/Users/20530/AppData/Local/Programs/Python/Python312/python.exe -m pytest tests/unit/test_event_extractor.py -v`
Expected: 4 PASSED

---

### Task 4: LongTermMemory (ChromaDB 长期记忆)

**Files:**
- Create: `backend/app/core/memory/long_term.py`
- Create: `backend/tests/async_unit/test_long_term.py`
- Note: 使用 `tests/async_unit/conftest.py` 中的 `mock_adapter` fixture

- [ ] **Step 1: 编写失败测试**

```python
# backend/tests/async_unit/test_long_term.py
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
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && /c/Users/20530/AppData/Local/Programs/Python/Python312/python.exe -m pytest tests/async_unit/test_long_term.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 LongTermMemory**

```python
# backend/app/core/memory/long_term.py
import logging
import uuid

from app.db.chroma import get_chroma
from app.core.model_adapter.adapter_registry import get_adapter_registry
from app.core.memory.event_extractor import ExtractedEvents

logger = logging.getLogger(__name__)


class LongTermMemory:
    COLLECTION = "user_memory"

    async def search(self, query: str, user_id: int, top_k: int = 5) -> list[str]:
        try:
            adapter = get_adapter_registry()
            embeddings = await adapter.embed([query])
            chroma = get_chroma()
            col = chroma.get_collection(self.COLLECTION)
            result = col.query(
                query_embeddings=embeddings,
                n_results=top_k,
                where={"user_id": user_id},
            )
            return result.get("documents", [[]])[0]
        except Exception as e:
            logger.warning(f"Long-term memory search failed: {e}")
            return []

    async def save(self, user_id: int, events: ExtractedEvents) -> None:
        texts = events.key_events + events.symptoms + events.diagnosis
        texts = [t for t in texts if t.strip()]
        if not texts:
            return

        try:
            adapter = get_adapter_registry()
            embeddings = await adapter.embed(texts)
            chroma = get_chroma()
            col = chroma.get_collection(self.COLLECTION)
            ids = [f"mem_{user_id}_{uuid.uuid4().hex[:12]}" for _ in texts]
            metadatas = [{"user_id": user_id, "type": "event"} for _ in texts]
            col.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)
        except Exception as e:
            logger.warning(f"Long-term memory save failed: {e}")
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && /c/Users/20530/AppData/Local/Programs/Python/Python312/python.exe -m pytest tests/async_unit/test_long_term.py -v`
Expected: 4 PASSED

---

### Task 5: MemoryReader (三层融合读取)

**Files:**
- Create: `backend/app/core/memory/memory_reader.py`
- Create: `backend/tests/unit/test_memory_reader.py`

- [ ] **Step 1: 编写失败测试**

```python
# backend/tests/unit/test_memory_reader.py
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

        with patch("app.core.memory.memory_reader.get_db", return_value=mock_db):
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

        with patch("app.core.memory.memory_reader.get_db", return_value=mock_db):
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

        with patch("app.core.memory.memory_reader.get_db", return_value=mock_db):
            result = asyncio.run(reader.read(user_id=1, session_id="sess_x", current_query="test"))

        assert result.recent_conversations == []
        assert result.relevant_history == ["event1"]
        assert result.user_profile.gender == "female"
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && /c/Users/20530/AppData/Local/Programs/Python/Python312/python.exe -m pytest tests/unit/test_memory_reader.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 MemoryReader**

```python
# backend/app/core/memory/memory_reader.py
import asyncio
import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from app.db.session import get_db
from app.models.patient import PatientProfile
from app.core.memory.short_term import ShortTermMemory, TurnSummary
from app.core.memory.long_term import LongTermMemory

logger = logging.getLogger(__name__)


@dataclass
class UserProfileSummary:
    gender: str | None = None
    age_group: str | None = None
    allergies: str | None = None
    medical_history: dict | None = None


@dataclass
class MemoryContext:
    user_profile: UserProfileSummary = field(default_factory=UserProfileSummary)
    recent_conversations: list[TurnSummary] = field(default_factory=list)
    relevant_history: list[str] = field(default_factory=list)
    formatted_prompt: str = ""


class MemoryReader:
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
        async with get_db() as session:
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
            profile_items.append(f"病史: {history_str}")
        if profile_items:
            parts.append(f"[用户画像] {' | '.join(profile_items)}")

        if recent:
            recent_lines = []
            for turn in recent:
                role_label = "用户" if turn.role == "user" else "助手"
                recent_lines.append(f"  {role_label}: {turn.content[:200]}")
            parts.append(f"[近期对话]\n" + "\n".join(recent_lines))

        if long:
            parts.append(f"[相关历史] " + " | ".join(long))

        if not parts:
            return "暂无历史上下文"

        return "\n\n".join(parts)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && /c/Users/20530/AppData/Local/Programs/Python/Python312/python.exe -m pytest tests/unit/test_memory_reader.py -v`
Expected: 3 PASSED

---

### Task 6: MemoryService (统一入口)

**Files:**
- Create: `backend/app/core/memory/memory_service.py`
- Modify: `backend/app/core/memory/__init__.py`
- Create: `backend/tests/async_unit/test_memory_service.py`

- [ ] **Step 1: 编写失败测试**

```python
# backend/tests/async_unit/test_memory_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.memory.memory_service import MemoryService
from app.core.memory.memory_reader import MemoryContext, UserProfileSummary


class TestMemoryService:
    async def test_get_context_delegates_to_reader(self, mock_adapter):
        with patch("app.core.memory.memory_reader.get_db") as mock_get_db:
            mock_session = AsyncMock()
            mock_session.execute.return_value.scalar_one_or_none.return_value = MagicMock(
                gender="male", allergies=None, medical_history=None
            )
            mock_get_db.return_value.__aenter__.return_value = mock_session

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

        mock_redis.lpush.assert_called_once()
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && /c/Users/20530/AppData/Local/Programs/Python/Python312/python.exe -m pytest tests/async_unit/test_memory_service.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 MemoryService + 更新 __init__.py**

```python
# backend/app/core/memory/memory_service.py
import logging

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
        import time
        entry = TurnEntry(
            role="user",
            content=user_message,
            intent=intent,
            timestamp=time.time(),
        )
        await self.short_term.save(session_id, entry)

        entry_assistant = TurnEntry(
            role="assistant",
            content=assistant_response,
            intent=intent,
            timestamp=time.time(),
        )
        await self.short_term.save(session_id, entry_assistant)
```

```python
# backend/app/core/memory/__init__.py
from app.core.memory.memory_service import MemoryService
from app.core.memory.memory_reader import MemoryContext, UserProfileSummary
from app.core.memory.short_term import TurnEntry, TurnSummary
from app.core.memory.event_extractor import ExtractedEvents

__all__ = [
    "MemoryService",
    "MemoryContext",
    "UserProfileSummary",
    "TurnEntry",
    "TurnSummary",
    "ExtractedEvents",
]
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && /c/Users/20530/AppData/Local/Programs/Python/Python312/python.exe -m pytest tests/async_unit/test_memory_service.py -v`
Expected: 2 PASSED

---

### Task 7: ResponseGen 支持 memory_context 参数

**Files:**
- Modify: `backend/app/core/agent/response_gen.py`
- Test: 不新增测试文件 — 现有 `test_response_gen.py` 测试向后兼容（不加参数的行为不变）

- [ ] **Step 1: 运行现有测试确认基线通过**

Run: `cd backend && /c/Users/20530/AppData/Local/Programs/Python/Python312/python.exe -m pytest tests/async_unit/test_response_gen.py -v`
Expected: 5 PASSED

- [ ] **Step 2: 修改 ResponseGenerator.generate() 签名**

```python
# backend/app/core/agent/response_gen.py  — 在 generate() 方法签名和 system prompt 拼接处修改

async def generate(
    self,
    message: str,
    intent: str,
    search_results: list[dict],
    role: str,
    sources: list[dict] | None = None,
    memory_context: str | None = None,  # NEW
) -> AsyncGenerator[str, None]:
    adapter = get_adapter_registry()

    system = PATIENT_SYSTEM if role != "doctor" else DOCTOR_SYSTEM

    # Inject memory context into system prompt
    if memory_context:
        system = f"{system}\n\n## 用户历史上下文\n{memory_context}"

    context_parts = []
    for i, doc in enumerate(search_results[:5]):
        content = doc.get("content", "")
        meta = doc.get("metadata", {})
        src_title = meta.get("title", f"来源{i+1}")
        context_parts.append(f"[{i+1}] {src_title}\n{content}")

    context_text = "\n\n".join(context_parts) if context_parts else "暂无相关知识库结果"

    user_prompt = f"""## 知识库检索结果
{context_text}

## 用户问题
{message}

## 意图类型
{intent}

请根据上述知识库内容回答用户问题："""

    async for chunk in adapter.generate_stream(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=2048,
    ):
        yield chunk
```

改动点：`generate()` 方法签名末尾加 `memory_context: str | None = None`，在 `system` 变量赋值后加 3 行注入逻辑。

- [ ] **Step 3: 运行现有测试验证向后兼容**

Run: `cd backend && /c/Users/20530/AppData/Local/Programs/Python/Python312/python.exe -m pytest tests/async_unit/test_response_gen.py -v`
Expected: 5 PASSED (不加参数调用 generate() 的行为与之前一致)

---

### Task 8: Orchestrator 集成 MemoryService

**Files:**
- Modify: `backend/app/core/agent/orchestrator.py`

- [ ] **Step 1: 运行现有 API 测试确认基线**

Run: `cd backend && /c/Users/20530/AppData/Local/Programs/Python/Python312/python.exe -m pytest tests/api/ -v`
Expected: 至少 test_chat.py 和 test_search.py 全部通过

- [ ] **Step 2: 修改 Orchestrator**

```python
# backend/app/core/agent/orchestrator.py
from typing import AsyncGenerator

from app.core.agent.intent import IntentClassifier
from app.core.agent.response_gen import ResponseGenerator
from app.core.rag.query_processor import QueryProcessor
from app.core.rag.adaptive_router import AdaptiveRouter
from app.core.rag.hybrid_retriever import HybridRetriever
from app.core.rag.post_processor import PostProcessor
from app.core.rag.citation import annotate_citations
from app.core.memory.memory_service import MemoryService  # NEW


class SimpleOrchestrator:
    """MVP orchestrator: linear intent->RAG->generate pipeline without ReAct loops."""

    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.query_processor = QueryProcessor()
        self.adaptive_router = AdaptiveRouter()
        self.hybrid_retriever = HybridRetriever()
        self.post_processor = PostProcessor()
        self.response_gen = ResponseGenerator()
        self.memory_service = MemoryService()  # NEW

    async def run(self, message: str, role: str, role_value: str,
                  session_id: str, user_id: int = 0) -> AsyncGenerator[dict, None]:
        # Step 0: Memory context (NEW)
        memory_ctx = None
        if user_id > 0:
            memory_ctx = await self.memory_service.get_context(user_id, session_id, message)

        # Step 1: Intent classification
        intent_result = await self.intent_classifier.classify(message, role)
        intent = intent_result.intent.value

        # Step 2: Query processing
        processed = await self.query_processor.process(message, role)

        # Step 3: Adaptive routing
        route = self.adaptive_router.route(role, processed.sub_queries)

        # Step 4: Hybrid retrieval
        bm25_docs, vector_docs = await self.hybrid_retriever.search(
            query=processed.rewritten, collection=route.kb_collection, top_k=10
        )

        # Step 5: Post-processing (RRF + rerank)
        final_docs = await self.post_processor.process(bm25_docs, vector_docs, processed.rewritten, top_k=5)

        # Step 6: Citation annotation
        sources = annotate_citations(final_docs)
        sources_data = [{"title": s.title, "type": s.source_type, "url": s.url,
                         "evidence_level": s.evidence_level, "version": s.version} for s in sources]

        # Step 7: Stream response
        memory_prompt = memory_ctx.formatted_prompt if memory_ctx else None
        async for chunk in self.response_gen.generate(
            message, intent, final_docs, role, sources_data,
            memory_context=memory_prompt,  # NEW
        ):
            yield {"type": "chunk", "content": chunk}

        # Final: send sources
        yield {"type": "sources", "sources": sources_data}
        yield {"type": "done"}
```

- [ ] **Step 3: 运行现有测试确认向后兼容**

Run: `cd backend && /c/Users/20530/AppData/Local/Programs/Python/Python312/python.exe -m pytest tests/api/ -v`
Expected: 全部通过 (auth_token 用户的 user_id > 0，会走 memory 路径但各层都为空/降级)

---

### Task 9: Chat API 集成 save_turn

**Files:**
- Modify: `backend/app/api/chat.py`

- [ ] **Step 1: 修改 chat.py**

```python
# backend/app/api/chat.py
import json
import logging

from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse

from app.middleware.identity_router import get_request_context, RequestContext
from app.core.agent.orchestrator import SimpleOrchestrator
from app.schemas.chat import ChatRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])
orchestrator = SimpleOrchestrator()


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    background_tasks: BackgroundTasks,
    ctx: RequestContext = Depends(get_request_context),
):
    async def event_generator():
        full_response = ""
        try:
            async for chunk in orchestrator.run(
                message=req.message,
                role=ctx.role.value,
                role_value=ctx.role.value,
                session_id=req.session_id,
                user_id=ctx.user_id,  # NEW
            ):
                if chunk.get("type") == "chunk":
                    full_response += chunk.get("content", "")
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

            # Schedule memory save after streaming completes
            background_tasks.add_task(
                orchestrator.memory_service.save_turn,
                user_id=ctx.user_id,
                session_id=req.session_id,
                user_message=req.message,
                assistant_response=full_response,
                intent="consult",  # will be replaced by actual intent from orchestrator
            )
        except Exception as e:
            logger.exception(f"Chat stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': '系统繁忙，请稍后再试'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

- [ ] **Step 2: 运行 API 测试**

Run: `cd backend && /c/Users/20530/AppData/Local/Programs/Python/Python312/python.exe -m pytest tests/api/test_chat.py -v`
Expected: 3 PASSED

---

### Task 10: 全量回归测试

- [ ] **Step 1: 运行全部测试**

Run: `cd backend && /c/Users/20530/AppData/Local/Programs/Python/Python312/python.exe -m pytest -v`
Expected: 全部通过（原有 75 + 新增 18 = ~93 个测试）
