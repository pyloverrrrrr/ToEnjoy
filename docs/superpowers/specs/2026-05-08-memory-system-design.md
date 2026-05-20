# Remediant 记忆系统设计

> 日期：2026-05-08 | 状态：设计完成，待实现

## 一、设计决策

| 决策点 | 选择 |
|--------|------|
| 事件抽取时机 | BackgroundTasks 异步执行（流式结束后触发） |
| 短期记忆窗口 | 最近 N 轮对话（默认 10 轮，Redis 保留 20 条） |
| 长期记忆检索 | 每次对话都查（用当前消息 embedding 检索 ChromaDB） |
| 整体架构 | 独立 MemoryService + 薄接口，内部委托三个存储层 |

## 二、模块结构

```
backend/app/core/memory/
├── __init__.py              # 导出 MemoryService
├── memory_service.py        # 统一入口：get_context() + save_turn()
├── short_term.py            # Redis 短期记忆 (最近N轮)
├── long_term.py             # ChromaDB 长期记忆 (向量检索)
├── event_extractor.py       # LLM 关键事件异步抽取
└── memory_reader.py         # 三层融合读取 → MemoryContext

backend/app/models/
└── conversation.py          # NEW: Conversation ORM 模型

backend/app/core/agent/
└── orchestrator.py          # MODIFY: 集成 MemoryService

backend/app/api/
└── chat.py                  # MODIFY: 流式结束后触发 save_turn

backend/app/middleware/
└── identity_router.py       # MODIFY: RequestContext 增加 user_id
```

## 三、组件接口

### MemoryService (统一入口)

```python
class MemoryService:
    def __init__(self):
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
        self.event_extractor = EventExtractor()
        self.reader = MemoryReader()

    async def get_context(self, user_id: int, session_id: str, current_query: str) -> MemoryContext:
        """在对话开始时调用，返回融合后的记忆上下文"""
        ...

    async def save_turn(self, user_id: int, session_id: str,
                        user_message: str, assistant_response: str,
                        intent: str) -> None:
        """在流式结束后同步调用（保存短期 + 触发后台异步抽取）"""
        ...
```

### MemoryContext

```python
@dataclass
class MemoryContext:
    user_profile: UserProfileSummary        # MySQL 结构化画像
    recent_conversations: list[TurnSummary] # Redis 最近 10 轮
    relevant_history: list[str]             # ChromaDB 相似历史事件
    formatted_prompt: str                   # 拼接好的 Prompt 文本

@dataclass
class UserProfileSummary:
    gender: str | None
    age_group: str | None
    allergies: str | None
    medical_history: dict | None

@dataclass
class TurnSummary:
    role: str
    content: str
    intent: str | None
    timestamp: str
```

### ShortTermMemory

```python
@dataclass
class TurnEntry:
    role: str           # "user" | "assistant"
    content: str        # 消息原文
    intent: str         # 意图分类结果
    timestamp: float

class ShortTermMemory:
    REDIS_KEY_PREFIX = "session"
    MAX_TURNS = 20      # Redis 保留条数
    TTL_SECONDS = 1800  # 30 分钟

    async def save(self, session_id: str, entry: TurnEntry) -> None:
        """LPUSH + LTRIM(保留20条) + EXPIRE(1800s)"""
        ...

    async def load(self, session_id: str, n: int = 10) -> list[TurnSummary]:
        """LRANGE 取最近 n 轮"""
        ...
```

### LongTermMemory

```python
class LongTermMemory:
    COLLECTION = "user_memory"

    async def save(self, user_id: int, events: ExtractedEvents) -> None:
        """事件文本 embed → ChromaDB user_memory.upsert()"""
        ...

    async def search(self, query: str, user_id: int, top_k: int = 5) -> list[str]:
        """query embed → ChromaDB 相似度检索 → 返回事件文本列表"""
        ...
```

### EventExtractor

```python
@dataclass
class ExtractedEvents:
    symptoms: list[str]
    diagnosis: list[str]
    medications: list[str]
    allergies: list[str]
    key_events: list[str]

class EventExtractor:
    MAX_RETRIES = 1
    TIMEOUT_SECONDS = 15

    async def extract(self, user_message: str, assistant_response: str,
                      previous_events: dict | None = None) -> ExtractedEvents:
        """LLM 从本轮对话中抽取关键医学事件，与历史事件合并去重"""
        ...

    def _merge_and_dedup(self, new_events: ExtractedEvents,
                         previous_events: dict) -> ExtractedEvents:
        """与历史事件合并，同名去重"""
        ...
```

### MemoryReader

```python
class MemoryReader:
    async def read(self, user_id: int, session_id: str, current_query: str) -> MemoryContext:
        """
        并行调用三层存储 → 融合为 MemoryContext：
        1. MySQL: patient_profiles WHERE user_id=?
        2. Redis: LRANGE session:{sid}:context 0 9
        3. ChromaDB: current_query embed → user_memory.query(top_k=5)
        """
        ...
```

### Conversation 模型 (新增)

```python
class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sources: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    token_count: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

## 四、数据流

### 写入路径（对话完成后）

```
SSE 流结束
  │
  ▼
[api/chat.py]  BackgroundTasks.add_task(memory_service.save_turn, ...)
  │
  ├─ [short_term.py] Redis LPUSH session:{sid}:context "{role, content, intent, ts}"
  │                   LTRIM 保留最近 20 条
  │                   EXPIRE 1800 秒
  │
  └─ [BackgroundTasks 子任务]
       ├─ [event_extractor.py] LLM 从对话中抽取关键事件 → ExtractedEvents
       ├─ [long_term.py] 事件文本 → Qwen3-Embedding → ChromaDB user_memory.upsert()
       └─ [conversation.py] MySQL INSERT conversation 记录
```

### 读取路径（对话开始前）

```
[orchestrator.py]  Step 0: ctx = await memory_service.get_context(user_id, session_id, message)
  │
  ├─ [short_term.py]  Redis LRANGE session:{sid}:context 0 9  → 最近 10 轮
  ├─ [long_term.py]   message → embed → ChromaDB user_memory.query(top_k=5)
  └─ [MySQL]          SELECT * FROM patient_profiles WHERE user_id=?
  │
  ▼ 融合 → MemoryContext.formatted_prompt:
  """
  [用户画像] 男, 45-55岁, 过敏:青霉素, 慢性病史:高血压
  [近期对话]
   用户: 头痛怎么办 → 回答: ...
   用户: 血压偏高 → 回答: ...
  [相关历史] 2026-03 就诊记录: 诊断为高血压... | 处方氨氯地平...
  """
```

### Orchestrator 集成

```python
# orchestrator.py — 在现有 Intent 分类前插入 Step 0

async def run(self, message, role, role_value, session_id, user_id):
    # Step 0: Memory context (NEW)
    memory_ctx = await self.memory_service.get_context(user_id, session_id, message)

    # Step 1: Intent classification (existing)
    intent_result = await self.intent_classifier.classify(message, role)

    # ... existing pipeline ...

    # Memory context injected into response generation
    async for chunk in self.response_gen.generate(
        message, intent, final_docs, role, sources_data,
        memory_context=memory_ctx.formatted_prompt  # NEW
    ):
        yield {"type": "chunk", "content": chunk}
```

## 五、错误处理与降级

### 读取降级（全链路不中断）

| 存储故障 | 降级行为 |
|---------|----------|
| Redis 不可用 | `recent_conversations` 返回空列表 |
| ChromaDB 不可用 | `relevant_history` 返回空列表 |
| MySQL 不可用 | `user_profile` 返回默认空值 |
| 全部不可用 | `formatted_prompt` = "暂无历史上下文" |

### 写入容错（非关键路径）

| 存储故障 | 容错行为 |
|---------|----------|
| Redis 写入失败 | log warning，不阻塞 |
| EventExtractor LLM 失败 | 重试 1 次 → 仍失败则跳过异步抽取 |
| ChromaDB upsert 失败 | log error，事件仅存 MySQL |
| MySQL insert 失败 | log error（最坏情况丢失单轮对话） |

## 六、Orchestrator 和 API 变更

### orchestrator.py

- `__init__` 新增 `self.memory_service = MemoryService()`
- `run()` 方法签名新增 `user_id: int` 参数
- 在 Step 1（Intent）之前插入 Step 0（get_context）
- Step 7（response_gen）传入 `memory_context` 参数

### api/chat.py

- 从 `RequestContext` 提取 `user_id` 传入 orchestrator
- 流式结束后：`BackgroundTasks.add_task(memory_service.save_turn, ...)`

### response_gen.py

- `generate()` 方法签名新增 `memory_context: str | None = None`
- 当 `memory_context` 非空时，注入到 system prompt 的用户画像区域

### identity_router.py

- 不再需要修改（`RequestContext` 已有 `user_id` 字段）

## 七、测试方案

沿袭现有 3 层测试结构（asyncio_mode = auto）：

### tests/unit/

| 文件 | 测试内容 |
|------|----------|
| `test_short_term.py` | mock Redis → LPUSH/LRANGE/LTRIM/EXPIRE 调用参数验证、空 session 返回空列表 |
| `test_event_extractor.py` | mock LLM → 正常 JSON 解析、非法 JSON fallback 空事件、事件去重合并 |
| `test_memory_reader.py` | mock 三层数据源 → 融合结果字段完整性、三层全空降级 |

### tests/async_unit/

| 文件 | 测试内容 |
|------|----------|
| `test_long_term.py` | mock ChromaDB + adapter embed → search/save 调用参数验证 |
| `test_memory_service.py` | mock 子组件 → get_context 端到端流程、save_turn 调用链验证 |

### tests/api/

| 文件 | 测试内容 |
|------|----------|
| `test_chat.py` (扩展) | SSE 流结束后验证 Redis 中有会话记录、BackgroundTasks 被调度 |
