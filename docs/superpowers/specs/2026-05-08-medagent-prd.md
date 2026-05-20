# Remediant 项目需求文档 (PRD)

> 版本：V1.0 | 日期：2026-05-08 | 状态：开发期

---

## 一、项目概述

### 1.1 项目名称

**Remediant** — 医患双端服务平台

### 1.2 项目背景

当前医疗场景存在两大核心矛盾：

- **患者端：** 诊前咨询响应慢、医学报告看不懂、诊后康复疑问难以及时解答。大量基础性、重复性问题占用医生宝贵时间。
- **医生端：** 海量医学知识分散在指南、文献、药品库中，检索低效；临床决策缺乏即时、可溯源的证据支撑；医教研工作缺少智能辅助。

Remediant 融合两个已验证的技术方案——"患者智能辅助 Agent"（强交互、多模态、工具调度）与"基于 RAG 的智能医学助手"（强检索、混合召回、引用溯源），构建一个统一平台，通过身份路由同时服务患者与医生两端。

### 1.3 核心目标

| 目标 | 指标 | 来源 |
|------|------|------|
| 降低医生重复性咨询耗时 | 减少 40% | 项目一 |
| 患者咨询首响应时间 | < 3秒 | 新增 |
| 医学知识检索准确率 | 引用溯源覆盖率 > 95% | 项目二 |
| 语音交互可及性 | 支持老年/低文化水平患者无障碍使用 | 项目一 |
| 跨院区部署灵活性 | 用户数据 & 配置可跨院迁移 | 项目一 |

### 1.4 目标用户 (V1)

| 角色 | 核心诉求 | 优先级 |
|------|----------|--------|
| **患者** | 诊前咨询、报告解读、诊后康复指导 | P0 |
| **医生** | 临床决策支持、精准知识检索、病例查阅 | P0 |
| ~~医学生~~ | V2 迭代 | — |
| ~~科研人员~~ | V2 迭代 | — |

---

## 二、用户场景与用户故事

### 2.1 患者端场景

#### S1 — 诊前智能咨询

> "我头痛三天了，伴有恶心，该挂什么科？"

- 系统识别症状关键词，启动 ReAct 推理链
- 检索相关医学知识（患者版通俗库），结合 Adaptive-RAG 多轮交互追问关键信息（持续时间、伴随症状、既往史等）
- 给出科室建议、就诊准备指引（需带什么材料、注意事项）
- 以通俗语言呈现，支持语音播报

#### S2 — 医学报告解读

> 患者上传血常规 / CT报告 / 出院小结（图片/PDF）

- 调用 Doubao 多模态能力对报告进行 OCR + 结构化提取
- RAG 检索对应的指标参考范围、通俗解释
- 生成"逐项解读 + 综合小结 + 就医建议"三段式回答
- 明确标注"本解读仅供参考，请以医生诊断为准"

#### S3 — 诊后康复管理

> "出院后我的药怎么吃？什么情况需要复诊？"

- Agent 结合 MCP Server 调取该患者的出院医嘱、处方信息
- 记忆系统读取用户画像（年龄、病史等）
- 生成个性化用药提醒计划、康复阶段指引、复诊触发条件
- 关键节点可设置推送提醒

#### S4 — 语音交互（可及性）

> 老年患者通过语音提问，系统语音播报回答

- 前端 Web Speech API 收音 → 后端 Doubao STT 转写
- 文本进入标准 Agent 流程
- 回答经 Doubao TTS 合成为语音流，前端播放
- 回答风格自动适配长者模式（更慢语速、更通俗用词、更大字号）

### 2.2 医生端场景

#### S5 — 临床决策支持

> "对于 II 型糖尿病合并肾功能不全的患者，二甲双胍如何调整剂量？"

- 身份路由识别为医生 → 切换专业知识库（临床指南、药品说明书、最新文献）
- Adaptive-RAG：问题分解为"二甲双胍剂量指南 + 肾功能不全禁忌 + 药物相互作用"三个子查询
- 混合检索：BM25 关键词匹配 + Qwen3 向量语义检索
- RRF 多源融合 + Qwen3-Reranker 语义重排序
- Agent 综合推理生成结构化回答（推荐方案、证据等级、注意事项）
- 每条关键结论附带 Citation 引用溯源（来源文献/指南条目）

#### S6 — 精准知识检索

> "查一下 NCCN 2025 非小细胞肺癌免疫治疗的最新推荐"

- 问题重写 + 逻辑分解：实体识别、时间过滤、主题聚焦
- 多轮 Self-RAG 检索：首轮粗排 → 判断信息充分性 → 必要时追加检索
- 结果按证据等级（指南 > Meta分析 > RCT > 病例报告）分层展示
- 支持按来源类型、年份、证据等级筛选

#### S7 — 患者记录查阅

> "查一下张三的最近一次住院记录和过敏史"

- Agent 调度 MCP Server → 病例查询模块 → 对接医院 HIS 系统
- 返回结构化患者信息摘要
- 结合记忆系统中的历史对话上下文，提供患者全景视图

#### S8 — 推理过程透明化

> 医生可展开查看 Agent 每一步推理过程

- CoT 推理步骤以折叠面板展示：意图识别 → 子问题分解 → 检索策略选择 → 各检索结果 → 综合推理 → 生成回答
- 便于医生审核 AI 结论的可靠性，满足临床安全要求

---

## 三、功能需求与技术栈

### 3.1 患者端功能

| 编号 | 功能 | 描述 | 优先级 | 前端技术 | 后端技术 | AI/模型 | 存储 |
|------|------|------|--------|----------|----------|---------|------|
| F-P01 | 文本对话 | 流式输出，多轮对话，上下文保持 | P0 | React · EventSource (SSE) · StreamingText | FastAPI · LangChain Agent · SSE endpoint | Qwen-Max (阿里百炼) / Qwen3 (Ollama本地) · ReAct · CoT | Redis(上下文缓存) · MySQL(对话记录) |
| F-P02 | 语音输入 | 浏览器端录音，后端 STT 转写 | P1 | Web Speech API · MediaRecorder · VoiceInput | FastAPI · WebSocket / HTTP 音频上传 | Doubao STT (火山引擎) | 文件存储(临时音频) |
| F-P03 | 语音播报 | 回答文本经 TTS 合成语音播放 | P1 | AudioPlayer · MediaSource API | FastAPI · TTS endpoint · 音频流返回 | Doubao TTS (火山引擎) | — |
| F-P04 | 报告上传与解读 | 图片/PDF上传，OCR结构化，通俗化解读 | P0 | ReportUploader · 拖拽/预览 · react-dropzone | FastAPI · 文件上传 · 多模态管道 | Doubao (OCR+视觉) · Qwen3-Embedding · Qwen-Max | 文件存储(MinIO) · ChromaDB(指标向量) |
| F-P05 | 科室导诊 | 症状→科室推荐→就诊准备清单 | P0 | ChatBubble · MarkdownRenderer | FastAPI · Agent 编排 (工具链: RAG→规则引擎) | Qwen-Max / Qwen3 (Ollama) · ReAct | ChromaDB(导诊知识库) · MySQL(科室表) |
| F-P06 | 用药与康复计划 | 结合医嘱生成个性化康复指引 | P1 | CareTimeline · 时间轴视图 | FastAPI · MCP Server (病例查询) · Agent | Qwen-Max / Qwen3 (Ollama) · Instruction Template | MySQL(care_plans) · Redis(用药提醒缓存) |
| F-P07 | 对话历史 | 查看历史咨询记录 | P1 | 历史列表组件 · react-markdown | FastAPI · REST API (分页查询) | — | MySQL(conversations) |

### 3.2 医生端功能

| 编号 | 功能 | 描述 | 优先级 | 前端技术 | 后端技术 | AI/模型 | 存储 |
|------|------|------|--------|----------|----------|---------|------|
| F-D01 | 知识检索 | 自然语言查询，精准返回医学知识 | P0 | SearchPanel · MarkdownRenderer | FastAPI · RAG 检索管道 (查询处理+混合检索+后处理) | Qwen-Max (查询重写/分解) · Qwen3-Embedding · Qwen3-Reranker (Ollama本地重排) | ChromaDB(专业库) · rank_bm25 (BM25关键词) |
| F-D02 | 临床决策支持 | 基于病例信息+知识库给出循证建议 | P0 | ChatBubble · ReasoningChain · CitationCard | FastAPI · Agent 编排 (RAG+MCP 组合调度) | Qwen-Max / Qwen3 (Ollama) · ReAct · CoT · Self-Consistency | ChromaDB(指南/文献库) · MySQL(患者数据·经MCP) |
| F-D03 | 引用溯源 | 每条关键结论附带可点击的来源引用 | P0 | CitationCard · 可点击跳转 · SourceLink | FastAPI · RAG Citation 管道 | Qwen-Max / Qwen3 (Ollama) · RAG Citation机制 | MySQL(knowledge_sources) · ChromaDB(来源元数据) |
| F-D04 | 病例查询 | 通过MCP调取HIS中的患者记录 | P1 | PatientRecordView · 结构化数据展示 | FastAPI · MCP Server (patient-record模块) · 适配HIS接口 | — (工具调用，非模型) | — (数据来自HIS，不持久化) |
| F-D05 | 推理链展示 | 展开查看CoT推理过程 | P1 | ReasoningChain · 折叠面板 · 步骤可视化 | FastAPI · Agent 响应附加 reasoning_steps[] | Qwen-Max / Qwen3 (Ollama) · CoT (记录中间步骤) | MySQL(conversations.tool_calls JSON) |
| F-D06 | 检索过滤 | 按来源类型、证据等级、年份筛选 | P2 | SearchPanel · 筛选器组件 (Select/DatePicker) | FastAPI · 查询参数 → RAG 过滤管道 | — | MySQL(knowledge_sources) · ChromaDB metadata filter |
| F-D07 | 搜索历史 | 记录检索历史，支持回溯 | P2 | 历史列表 · 一键回填搜索词 | FastAPI · REST API (分页查询) | — | MySQL(conversations · 按intent过滤) |

### 3.3 系统通用功能

| 编号 | 功能 | 描述 | 优先级 | 前端技术 | 后端技术 | AI/模型 | 存储 |
|------|------|------|--------|----------|----------|---------|------|
| F-S01 | 身份认证 | JWT 登录，角色鉴权 | P0 | 登录页 · authStore(Zustand) · axios拦截器 | FastAPI · python-jose(JWT) · bcrypt · 中间件鉴权 | — | MySQL(users) · Redis(Token黑名单) |
| F-S02 | 身份路由 | 根据角色加载对应界面与知识库策略 | P0 | React Router(路由守卫) · 角色→redirect | FastAPI · 中间件注入 role → Agent策略选择 | — | — |
| F-S03 | 流式响应 | SSE协议，逐字返回生成内容 | P0 | EventSource · ReadableStream · StreamingText | FastAPI · StreamingResponse · SSE | Qwen-Max / Qwen3 (Ollama) (stream=true) | — |
| F-S04 | 记忆管理 | 短期对话缓存 + 长期用户画像 | P0 | — (纯后端能力) | FastAPI · 记忆读写API · 定时刷新任务 | Qwen3-Embedding (长期向量化) · Qwen-Max / Qwen3 (事件抽取) | Redis(短期) · ChromaDB(长期) · MySQL(持久) |
| F-S05 | 个性化配置 | 回答风格、语音偏好、专业等级可配置 | P2 | 设置面板 · Switch/Select表单 | FastAPI · REST API (读/写配置JSON) | — | MySQL(patient_profiles.personalization_config) |

---

## 四、技术架构详述

### 4.1 整体架构图

（详见第4.1节上文细化的系统架构图，此处以文字描述核心分层）

```
接入层:   React SPA (患者端 / 医生端)
  ↓
网关层:   FastAPI (认证 · 限流 · 身份路由)
  ↓
编排层:   Agent 编排引擎 (意图识别 → 规划推理 → 工具调度 → 响应生成)
  ↓         ↓              ↓              ↓
RAG管道   MCP Server    记忆系统      多模态能力
  ↓         ↓              ↓              ↓
数据层: MySQL + Redis + ChromaDB + 文件存储
```

### 4.2 核心组件来源追溯

| 组件 | 来源 | 说明 |
|------|------|------|
| Agent 编排引擎 (ReAct + CoT + Self-Consistency) | 项目一 | 意图识别、多轮推理、工具调度 |
| MCP Server (模块化工具) | 项目一 | 病例查询、就诊记录、身份验证等封装 |
| 记忆系统 (短期+长期) | 项目一 | Redis会话缓存 + ChromaDB画像 + MySQL持久化 |
| 多模态交互 (Doubao) | 项目一 | 语音STT/TTS + 医学图像理解 (火山引擎) |
| Adaptive-RAG 检索路由 | 项目二 | 身份感知 + 逻辑路由 + 动态调度 |
| 查询处理管道 (重写/分解) | 项目二 | 上下文压缩 + 问题重写 + 逻辑分解 |
| 混合检索 (BM25 + 向量) | 项目二 | 关键词匹配 + Qwen3语义检索 |
| RRF 融合 + Qwen3-Reranker 重排序 | 项目二改造 | 多源结果融合去重 + 语义精排 (替换Cohere，支持Ollama本地部署) |
| 引用溯源 (Citation) | 项目二 | 关键结论来源标注 |
| 层级向量索引 (ChromaDB) | 项目二 | Qwen3-Embedding-8B + Multi-representation |
| 模型适配器 (Model Adapter) | 新增 | 统一抽象层，支持阿里百炼 API / Ollama 本地模型透明切换 |

---

## 五、各模块详细设计

### 5.1 RAG 检索管道（继承项目二）

```
用户问题
  ↓
[1] 查询处理
  ├─ 上下文压缩：从记忆系统读取历史，压缩关键上下文
  ├─ 问题重写：模糊提问 → 精准检索语句 (Qwen-Max / Qwen3)
  └─ 逻辑分解：复杂问题 → 原子化子查询
  ↓
[2] 检索路由 (Adaptive-RAG)
  ├─ 身份感知：患者 → 通俗知识库 / 医生 → 专业知识库
  └─ 策略选择：简单问题直接检索 / 复杂问题多轮Self-RAG
  ↓
[3] 混合检索
  ├─ BM25：关键词精确匹配 (rank_bm25 Python库)
  └─ 向量检索：Qwen3-Embedding-8B 语义相似度 (ChromaDB)
  ↓
[4] 后处理
  ├─ RRF (Reciprocal Rank Fusion)：多源结果融合 & 去重
  └─ Qwen3-Reranker：语义精细化重排序 (本地Ollama / 阿里百炼Rerank API)
  ↓
[5] 引用溯源
  └─ 检索结果附带来源元数据 (文献PMID、指南条目、药品说明书版本)
```

**知识库设计：**

| 知识库 | 内容 | 更新频率 | 面向用户 |
|--------|------|----------|----------|
| 患者知识库 | 通俗疾病科普、用药说明、检查指标解读 | 月度 | 患者 |
| 临床指南库 | 国内外临床指南 (NCCN, ESC, 中华医学会等) | 季度 | 医生 |
| 医学文献库 | PubMed 文献摘要与全文 | 月度 | 医生 |
| 药品数据库 | 药品说明书、相互作用、禁忌症 | 月度 | 医生/患者 |

### 5.2 MCP Server（继承项目一）

按业务域拆分的模块化 MCP Server：

| 模块 | 工具 | 对接系统 | 说明 |
|------|------|----------|------|
| patient-record | `query_case` `query_visit` `query_prescription` | HIS | 病例、就诊、处方查询 |
| identity | `verify_patient` `verify_doctor` `get_permissions` | 统一认证 | 身份验证 |
| report | `parse_lab_report` `parse_imaging_report` | LIS / PACS | 检查报告结构化 |
| appointment | `query_schedule` `book_appointment` | HIS | 排班查询与预约 |
| knowledge | `sync_guideline` `index_document` | 知识管理系统 | 知识库管理 |

**设计原则：** 配置化 + 插拔式设计，新增院区只需配置对应的 HIS/LIS 接口地址，MCP Server 模块可复用。

### 5.3 记忆系统（继承项目一）

```
┌─────────────────────────────────────────┐
│              记忆系统架构                 │
│                                          │
│  写入路径:                               │
│  对话事件 → 事件抽取 → 短期缓存(Redis)    │
│                  ↓                       │
│            定时刷新任务                   │
│                  ↓                       │
│          关键事件 → 用户画像(MySQL)        │
│          对话摘要 → 长期向量(ChromaDB)    │
│                                          │
│  读取路径:                               │
│  Agent请求 → 短期上下文(Redis)            │
│          → 长期语义(ChromaDB 相似度)      │
│          → 结构化画像(MySQL)              │
│          → 融合 → 格式化注入Prompt        │
└─────────────────────────────────────────┘
```

| 层级 | 存储 | TTL | 内容 |
|------|------|-----|------|
| 短期 | Redis | 会话期间 + 30min | 对话上下文、当前意图、临时状态 |
| 长期 | ChromaDB | 永久 (可归档) | 对话摘要向量、关键事件向量 |
| 持久 | MySQL | 永久 | 用户画像结构化字段、个性化配置 |

**跨院迁移：** 用户画像与配置以标准化格式存储，支持导出→导入实现跨院区个人数据无缝迁移。

### 5.4 Agent 编排引擎（融合项目一+项目二）

```
输入: 用户消息 + 身份标签 + 上下文
  │
  ▼
[意图识别] Qwen-Max / Qwen3 (Ollama)
  ├─ 分类: 诊前咨询 / 报告解读 / 康复指导 / 知识检索 / 决策支持 / 闲聊
  └─ 输出: intent + confidence + 推荐工具链
  │
  ▼
[规划推理] ReAct + CoT + Self-Consistency
  ├─ 生成3条推理路径 (Self-Consistency抽样)
  ├─ 投票选出最优路径
  └─ 输出: 行动计划 (tool_chain[ ])
  │
  ▼
[工具调度] Tool Router
  ├─ 患者场景: RAG(通俗库) → MCP(病历) → 记忆(画像)
  ├─ 医生场景: RAG(专业库) → MCP(病例) → 记忆(历史检索)
  └─ 并行/串行执行，结果汇总
  │
  ▼
[响应生成] Instruction Template + CoT
  ├─ 患者: 通俗模板 + 三段式 (解读→小结→建议) + 免责声明
  ├─ 医生: 专业模板 + 证据分级 + Citation + 推理链可展开
  └─ 可选: TTS 语音合成
  │
  ▼
输出: 流式文本 + sources[ ] + metadata
```

### 5.5 多模态能力（继承项目一）

| 能力 | 模型/方案 | 应用场景 |
|------|----------|----------|
| 语音识别 (STT) | Doubao STT | 患者语音输入 |
| 语音合成 (TTS) | Doubao TTS | 回答语音播报 |
| 医学图像理解 | Doubao 多模态 | 影像报告辅助分析 |
| 文档OCR | Doubao / 专用OCR | 报告图片/PDF文字提取 |

---

## 六、数据模型

### 6.1 MySQL 表结构

```sql
-- 用户表
users (
  id, username, password_hash, role(patient|doctor|admin),
  name, phone, email, hospital_id, created_at, updated_at
)

-- 患者档案
patient_profiles (
  id, user_id, gender, birthday, blood_type, allergies,
  medical_history(JSON), personalization_config(JSON), created_at, updated_at
)

-- 医生档案
doctor_profiles (
  id, user_id, department, title, specialty, license_no, created_at, updated_at
)

-- 对话记录
conversations (
  id, user_id, session_id, role(user|assistant), content,
  intent, sources(JSON), tool_calls(JSON), token_count,
  created_at
)

-- 患者康复计划
care_plans (
  id, user_id, conversation_id, medication_schedule(JSON),
  follow_up_date, status, created_at, updated_at
)

-- 知识库元数据
knowledge_sources (
  id, title, type(guideline|literature|drug|education),
  source_url, version, evidence_level, indexed_at
)
```

### 6.2 Redis 缓存结构

| Key Pattern | 类型 | 用途 | TTL |
|-------------|------|------|-----|
| `session:{id}:context` | List | 当前会话对话上下文字符串 | 30min |
| `session:{id}:state` | Hash | 意图、当前工具链执行状态 | 30min |
| `user:{id}:profile` | Hash | 用户画像热缓存 | 1h |
| `rate:{user_id}:{endpoint}` | String | 限流计数器 | 1min |
| `rag:hot:{query_hash}` | String | RAG热点答案缓存 | 1h |
| `task:queue` | List | 异步任务队列 (索引更新等) | — |

### 6.3 ChromaDB 集合

| Collection | 嵌入模型 | 用途 |
|------------|----------|------|
| `kb_patient` | Qwen3-Embedding-8B | 患者知识库向量 |
| `kb_professional` | Qwen3-Embedding-8B | 专业指南/文献向量 |
| `user_memory` | Qwen3-Embedding-8B | 用户对话摘要 & 关键事件向量 |
| `drug_db` | Qwen3-Embedding-8B | 药品知识向量 |

---

## 七、前端设计

### 7.1 路由设计

```
/login                    →  登录页
/patient/chat             →  患者对话主页
/patient/report/:id       →  报告解读详情
/patient/care-plan        →  康复计划页
/patient/history          →  历史咨询记录
/doctor/search            →  医生知识检索主页
/doctor/patient/:id       →  患者病历查阅
/doctor/search-history    →  检索历史
/admin                    →  管理后台 (V2)
```

### 7.2 技术选型

| 项 | 选型 |
|----|------|
| 框架 | React 18 + TypeScript |
| 构建 | Vite |
| 路由 | React Router v6 |
| 状态管理 | Zustand |
| UI组件 | Ant Design / Shadcn UI |
| HTTP | axios |
| 流式 | EventSource (SSE) |
| 语音 | Web Speech API + MediaSource |
| Markdown渲染 | react-markdown + rehype |

### 7.3 核心组件

**共享组件：**
- `ChatBubble` — 聊天气泡（支持文本/Markdown/语音/图片）
- `StreamingText` — 流式文字逐字渲染
- `MarkdownRenderer` — Markdown 渲染（表格、公式、代码块）
- `CitationCard` — 引用来源卡片（可点击跳转）
- `ErrorBoundary` — 错误边界
- `LoadingSkeleton` — 加载骨架屏

**患者端专属：**
- `VoiceInput` — 语音录入按钮（按住说话）
- `AudioPlayer` — TTS 播放器
- `ReportUploader` — 报告上传拖拽区 + OCR 预览
- `CareTimeline` — 康复计划时间轴

**医生端专属：**
- `SearchPanel` — 高级检索面板（过滤条件、结果列表）
- `ReasoningChain` — CoT 推理步骤折叠展示
- `PatientRecordView` — 患者病历结构化视图

---

## 八、接口设计（API 清单）

### 8.1 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录，返回 JWT |
| POST | `/api/auth/register` | 患者注册 |
| GET | `/api/auth/me` | 获取当前用户信息与角色 |

### 8.2 对话

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/chat/stream` | 流式对话 (SSE)，传入身份+消息 |
| GET | `/api/chat/history` | 获取历史对话列表 |
| GET | `/api/chat/history/:id` | 获取单条对话详情 |

### 8.3 检索

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/search` | 知识检索（非流式，返回结果+sources） |
| POST | `/api/search/stream` | 检索+生成流式回答 |

### 8.4 报告

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/report/upload` | 上传报告图片/PDF |
| POST | `/api/report/interpret` | 解读指定报告 |

### 8.5 患者 & 医生

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/patient/profile` | 获取患者档案 |
| PUT | `/api/patient/profile` | 更新患者档案 |
| GET | `/api/patient/care-plan` | 获取康复计划 |
| GET | `/api/doctor/patient/:id` | 医生查看患者记录 (MCP) |

### 8.6 语音

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/voice/stt` | 语音→文本 (WebSocket 流式或 HTTP) |
| POST | `/api/voice/tts` | 文本→语音流 |

---

## 九、非功能需求

### 9.1 性能

| 指标 | 目标 | 备注 |
|------|------|------|
| 首响应时间 (TTFR) | < 3s | 流式首个token |
| 检索延迟 | < 1.5s | BM25+向量混合检索 |
| 并发对话 | 支持 50+ 并发 | 开发期单机 |
| 语音端到端延迟 | < 5s | 说话→听到回答 |

### 9.2 安全

- 所有 API 需 JWT 鉴权
- 患者医疗数据脱敏传输（姓名、身份证号部分掩码）
- 医生权限分级（住院医师/主治/主任，数据访问范围不同）
- API 限流：患者 30req/min，医生 60req/min
- 日志不记录明文敏感信息

### 9.3 可维护性

- MCP Server 模块化：新增医院对接只需配置+新增 MCP 模块
- 知识库独立管理：增量索引，无需重建全库
- 配置化设计：用户画像字段、回答模板、知识库路由策略均可配置
- Docker Compose 一键部署，开发/测试环境一致

### 9.4 可靠性

- LLM 调用失败自动重试（最多3次，指数退避）
- MCP Server 超时熔断（10s），降级返回提示信息
- Redis 不可用时降级为仅使用 MySQL 持久层
- 关键操作日志记录，支持问题回溯

---

## 十、V1.0 详细实施步骤规划

> 总工期参考：约 10-12 周（单人全职），下述步骤按依赖关系排序。

---

### 第0步：基础设施搭建 (预计 2天)

**目标：** 本地可一键启动完整开发环境，所有服务可用。

| 子步骤 | 具体操作 | 产出物 | 关键技术点 |
|--------|---------|--------|-----------|
| 0.1 | 创建项目目录结构（monorepo: `backend/` + `frontend/` + `docker/`） | 项目骨架 | — |
| 0.2 | 编写 `docker-compose.yml`：MySQL 8.0 + Redis 7 + ChromaDB + MinIO | Docker Compose 环境 | Docker Compose |
| 0.3 | 初始化 FastAPI 项目（poetry / pip + requirements.txt），编写 `/api/health` 探活端点 | FastAPI 骨架 | FastAPI · Uvicorn · Gunicorn |
| 0.4 | 初始化 React 项目（Vite + TypeScript + React Router + Zustand），首页渲染 | React 骨架 | Vite · React 18 · TypeScript |
| 0.5 | 配置 Nginx 反向代理（`/api` → FastAPI，`/` → React 开发服务器） | Nginx 配置 | Nginx |
| **验收** | `docker compose up` 后浏览器访问 `localhost` 看到 React 首页，`localhost/api/health` 返回 `{"status":"ok"}` | | |

---

### 第1步：数据层 — MySQL 表结构 + Redis + ChromaDB (预计 3天)

**目标：** 所有数据存储就绪，ORM 模型可用，向量库可写入/查询。

| 子步骤 | 具体操作 | 产出物 | 关键技术点 |
|--------|---------|--------|-----------|
| 1.1 | 创建 MySQL 6张表（users, patient_profiles, doctor_profiles, conversations, care_plans, knowledge_sources），编写 SQLAlchemy ORM 模型 | ORM 模型 + 建表脚本 | SQLAlchemy 2.0 · Alembic(迁移) |
| 1.2 | 创建 `knowledge_sources` 种子数据脚本（测试用指南/文献/药品示例数据） | 种子数据脚本 | — |
| 1.3 | 配置 Redis 连接池，封装缓存读写工具类（`RedisClient`） | Redis 工具类 | redis-py · 连接池 |
| 1.4 | 配置 ChromaDB 连接，创建4个 Collection（kb_patient, kb_professional, user_memory, drug_db），配置 Qwen3-Embedding-8B | ChromaDB Collection | ChromaDB Client · Qwen3-Embedding-8B |
| 1.5 | 编写测试用数据向量化脚本，向 kb_patient / kb_professional 灌入示例数据 | 示例向量数据 | Qwen3-Embedding-8B · Multi-representation |
| **验收** | MySQL 表创建成功、Redis 读写正常、ChromaDB 可写入向量并返回相似查询结果 | | |

---

### 第2步：认证系统 + 身份路由 (预计 2天)

**目标：** 用户可注册/登录，后端可识别角色并注入对应策略。

| 子步骤 | 具体操作 | 产出物 | 关键技术点 |
|--------|---------|--------|-----------|
| 2.1 | 实现 JWT 签发与验证工具（`create_access_token` / `decode_token`） | JWT 工具函数 | python-jose · bcrypt · datetime.timedelta |
| 2.2 | 实现注册接口（`POST /api/auth/register` — 仅患者） + 登录接口（`POST /api/auth/login`） | 认证 API | FastAPI Router · Pydantic Schema |
| 2.3 | 实现 JWT 鉴权中间件（`get_current_user` Depends），注入 `RequestContext`（user_id, role） | 鉴权中间件 | FastAPI Depends · HTTPBearer |
| 2.4 | 实现身份路由策略：角色 → RAG知识库选择 + 回答模板选择 + 界面路由 | 身份路由配置 | Python Enum · 策略映射 |
| 2.5 | 前端：登录页 UI + authStore（Zustand）+ axios 拦截器自动附加 Token + 路由守卫 | 登录页 | React Hook Form · Zustand · axios interceptors |
| **验收** | 患者/医生登录后返回不同 role，前端自动跳转对应主页，未登录访问受保护路由被拦截 | | |

---

### 第3步：RAG 检索管道 — 离线索引 (预计 3天)

**目标：** 完成知识库离线索引建立，检索管道可对外查询。

| 子步骤 | 具体操作 | 产出物 | 关键技术点 |
|--------|---------|--------|-----------|
| 3.1 | 实现数据预处理管道：临床指南/文献/药品数据清洗 → 分段（chunking）→ Qwen3-Embedding-8B 向量化 | 数据预处理脚本 | LangChain TextSplitter · Qwen3-Embedding-8B |
| 3.2 | 实现层级向量索引构建，Multi-representation 多表征写入 ChromaDB | 索引构建管道 | ChromaDB · 层级索引 |
| 3.3 | 实现 BM25 索引构建（基于 rank_bm25 或 Elasticsearch），关键词索引 | BM25 索引 | rank_bm25 · Elasticsearch(可选) |
| 3.4 | 实现离线索引任务管理（支持增量更新、重建），通过 Redis 任务队列调度 | 索引任务管理 | Redis List · Celery / BackgroundTasks |
| **验收** | 知识库向量化完成，手动调用 ChromaDB 查询能返回语义相关结果，BM25 能返回关键词匹配结果 | | |

---

### 第4步：RAG 检索管道 — 在线检索 (预计 4天)

**目标：** 完整的 RAG 在线检索管道，从查询到精排结果全链路跑通。

| 子步骤 | 具体操作 | 产出物 | 关键技术点 |
|--------|---------|--------|-----------|
| 4.1 | 实现查询处理管道：上下文压缩（从记忆系统读取 → Qwen-Max 摘要压缩）→ 问题重写（模糊→精准）→ 逻辑分解（复杂→原子化子查询） | QueryProcessor 模块 | Qwen-Max / Qwen3 · LangChain Prompt Template |
| 4.2 | 实现 Adaptive-RAG 检索路由：身份感知（读 role）→ 策略选择（简单→直接检索 / 复杂→Self-RAG多轮）→ 知识库选择 | AdaptiveRouter 模块 | LangChain Router · 策略模式 |
| 4.3 | 实现混合检索：BM25 关键词 + 向量语义，并行检索 → 结果合并 | HybridRetriever 模块 | ChromaDB .query() · BM25 · asyncio.gather |
| 4.4 | 实现后处理管道：RRF 多源融合 & 去重 → Qwen3-Reranker 语义精排 (Ollama本地 / 阿里百炼API) | PostProcessor 模块 | RRF 算法 · Qwen3-Reranker · Ollama |
| 4.5 | 实现 Citation 引用溯源：检索结果附带源元数据（PMID、指南条目、版本号），注入 Prompt 要求模型标注引用 | Citation 管道 | Prompt Template · 源数据透传 |
| 4.6 | 实现 `POST /api/search` 接口（非流式检索），返回结果 + sources[] | 检索 API | FastAPI · Pydantic Response Schema |
| **验收** | 发送"二甲双胍肾功能不全剂量调整" → 返回排序后的指南/文献结果，每条有来源标注，患者查询自动路由到通俗库 | | |

---

### 第5步：记忆系统 (预计 3天)

**目标：** 三层层记忆读写全链路可用，跨会话上下文保持。

| 子步骤 | 具体操作 | 产出物 | 关键技术点 |
|--------|---------|--------|-----------|
| 5.1 | 实现短期记忆层：对话事件 → Redis 缓存（session:{id}:context List + state Hash），TTL 30min | ShortTermMemory 模块 | Redis List · Hash · expire |
| 5.2 | 实现事件抽取：Qwen-Max / Qwen3 从对话中抽取关键事件（症状、诊断、用药、过敏等） | EventExtractor 模块 | Qwen-Max / Qwen3 · Few-shot Prompt |
| 5.3 | 实现长期记忆层：对话摘要向量化 → ChromaDB user_memory Collection，关键事件 → MySQL patient_profiles.medical_history | LongTermMemory 模块 | Qwen3-Embedding-8B · ChromaDB · SQLAlchemy |
| 5.4 | 实现记忆读取 API：Agent 请求 → 短期(Redis) + 长期(ChromaDB 相似度) + 画像(MySQL) → 融合 → 注入 Prompt 上下文 | MemoryReader 模块 | asyncio.gather · Prompt Template |
| 5.5 | 实现定时刷新任务：Redis → ChromaDB/MySQL 异步写入，Celery Beat / APScheduler | 定时刷新 | Celery Beat · APScheduler |
| 5.6 | 实现 `GET /api/memory/context` 接口（供 Agent 调用） | 记忆 API | FastAPI |
| **验收** | 用户对话后刷新页面再提问，系统记住之前提到的症状/病史，回答体现个性化上下文 | | |

---

### 第6步：MCP Server 框架 (预计 3天)

**目标：** MCP Server 框架可扩展，至少2个模块可用。

| 子步骤 | 具体操作 | 产出物 | 关键技术点 |
|--------|---------|--------|-----------|
| 6.1 | 设计 MCP Server 框架：BaseMCPModule 抽象类，定义 `tool_schema` / `execute` 接口，支持配置化注册 | MCP 框架核心 | ABC 抽象类 · Pydantic Schema · 动态注册 |
| 6.2 | 实现 `patient-record` 模块：`query_case` / `query_visit` / `query_prescription` 工具（对接模拟 HIS 接口） | patient-record MCP 模块 | MCP Protocol / REST to HIS |
| 6.3 | 实现 `identity` 模块：`verify_patient` / `verify_doctor` / `get_permissions` 工具 | identity MCP 模块 | MCP Protocol · JWT 校验 |
| 6.4 | 实现 MCP Tool Registry：所有模块注册 → 生成工具清单 → Agent 可读取可用工具列表 | MCP Tool Registry | Registry 模式 · 工具元数据 |
| 6.5 | 实现 MCP 超时熔断：10s 超时 → 返回降级信息，错误日志记录 | 熔断降级 | asyncio.wait_for · 熔断器模式 |
| **验收** | Agent 调用 `query_case("张三")` → 返回结构化病例数据（含过敏史、就诊记录），10s 内无响应则降级提示 | | |

---

### 第7步：Agent 编排引擎 (预计 5天)

**目标：** 完整 Agent 编排链路跑通——意图识别 → 推理规划 → 工具调度 → 响应生成。

| 子步骤 | 具体操作 | 产出物 | 关键技术点 |
|--------|---------|--------|-----------|
| 7.1 | 实现意图识别：Qwen-Max / Qwen3 分类（诊前咨询/报告解读/康复/知识检索/决策支持/闲聊），输出 intent + confidence | IntentClassifier 模块 | Qwen-Max / Qwen3 · Few-shot Prompt · Pydantic Enum |
| 7.2 | 实现 ReAct 推理循环：Thought → Action → Observation → Thought 迭代，最大迭代次数限制 | ReActEngine 模块 | LangChain Agent · ReAct Prompt |
| 7.3 | 实现 Self-Consistency 多路径推理：同问题3条推理路径采样 → 投票选出最优 Action Plan | SelfConsistency 模块 | Qwen-Max / Qwen3 (temperature=0.7) · 投票策略 |
| 7.4 | 实现 CoT 链式推理：引导模型展示中间推理步骤，Step-by-step 记录每步结果 | CoTEngine 模块 | Chain-of-Thought Prompt · 步骤记录 |
| 7.5 | 实现 Tool Router 工具调度器：根据 Action Plan 自动路由到 RAG/MCP/Memory，并行/串行执行，汇总结果 | ToolRouter 模块 | LangChain Tool · asyncio.gather · 依赖图 |
| 7.6 | 实现响应生成：Instruction Template（患者通俗版/医生专业版），CoT 推理，Citation 注入，免责声明 | ResponseGenerator 模块 | Prompt Template · Qwen-Max / Qwen3 stream |
| 7.7 | 实现 `POST /api/chat/stream` 流式对话接口（SSE），完整编排链路串联 | 流式对话 API | FastAPI StreamingResponse · SSE · asyncio |
| **验收** | 患者问"头痛挂什么科"→ 意图识别→RAG检索→返回科室建议；医生问临床问题 → 意图识别→专业库RAG→MCP→Citation→结构化回答 | | |

---

### 第8步：多模态能力 (预计 3天)

**目标：** 语音输入/播报端到端可用，报告图片可OCR提取文字。

| 子步骤 | 具体操作 | 产出物 | 关键技术点 |
|--------|---------|--------|-----------|
| 8.1 | 实现 `POST /api/voice/stt`：接收音频流 → Doubao STT → 返回文本（支持 WebSocket 流式） | STT API | Doubao STT API · FastAPI WebSocket |
| 8.2 | 实现 `POST /api/voice/tts`：接收文本 → Doubao TTS → 返回音频流（SSE 或直接返回音频文件） | TTS API | Doubao TTS API · StreamingResponse |
| 8.3 | 实现 `POST /api/report/upload` + `POST /api/report/interpret`：图片/PDF → Doubao OCR → 结构化提取 → 送入 RAG 管道解读 | 报告解读 API | Doubao 多模态 · FastAPI UploadFile · python-multipart |
| 8.4 | 前端：VoiceInput 组件（Web Speech API / MediaRecorder → 后端 STT） + AudioPlayer 组件（TTS 音频播放） | 语音交互组件 | Web Speech API · MediaSource · AudioContext |
| 8.5 | 前端：ReportUploader 组件（拖拽上传 + 缩略图预览 + 解读结果流式展示） | 报告上传组件 | react-dropzone · FileReader · SSE |
| **验收** | 浏览器点击"语音输入"按钮说话 → 文本出现在输入框 → 发送 → 回答以语音播放；上传血常规报告图片 → 逐项解读展示 | | |

---

### 第9步：前端页面整合 (预计 5天)

**目标：** 患者端和医生端全部页面完成，与后端 API 联调通过。

| 子步骤 | 具体操作 | 产出物 | 关键技术点 |
|--------|---------|--------|-----------|
| 9.1 | 实现共享组件（ChatBubble, StreamingText, MarkdownRenderer, CitationCard, ErrorBoundary, LoadingSkeleton） | 共享组件库 | React · react-markdown · rehype · CSS Modules |
| 9.2 | 实现患者端页面：`/patient/chat`（对话主页，流式）、`/patient/report/:id`（报告解读）、`/patient/care-plan`（康复计划时间轴）、`/patient/history`（历史记录） | 患者端4个页面 | React Router · Zustand chatStore · EventSource |
| 9.3 | 实现患者端 VoiceInput + AudioPlayer 集成到对话页 | 语音交互集成 | Web Speech API · MediaSource |
| 9.4 | 实现医生端页面：`/doctor/search`（知识检索主页含筛选器）、`/doctor/patient/:id`（病例查阅）、`/doctor/search-history`（检索历史） | 医生端3个页面 | React Router · Zustand searchStore |
| 9.5 | 实现医生端 SearchPanel（筛选条件面板）+ ReasoningChain（CoT步骤折叠）+ CitationCard（可点击来源） | 医生端专属组件 | Ant Design · react-markdown |
| 9.6 | 前端与后端 API 全量联调，处理错误状态（网络异常、Token过期、超时） | 联调完毕 | axios · ErrorBoundary |
| **验收** | 患者端：登录→提问→流式回答→语音播报→上传报告→解读；医生端：登录→知识检索→查看结果+引用→展开推理链→查询患者记录 | | |

---

### 第10步：集成测试与文档 (预计 3天)

**目标：** 核心链路通过测试，关键文档齐全。

| 子步骤 | 具体操作 | 产出物 | 关键技术点 |
|--------|---------|--------|-----------|
| 10.1 | 编写后端单元测试（RAG管道各模块、MCP模块、Agent编排核心逻辑），覆盖率 > 60% | 单元测试 | pytest · pytest-asyncio |
| 10.2 | 编写集成测试（注册→登录→对话→检索 全链路），端到端覆盖 P0 场景 | 集成测试 | pytest · httpx · testcontainers |
| 10.3 | 编写前端组件测试（ChatBubble, StreamingText, CitationCard 等核心组件） | 前端测试 | Vitest · React Testing Library |
| 10.4 | 编写 README.md（项目说明 + 快速开始 + 目录结构 + 环境变量说明） | README | — |
| 10.5 | 编写 API 文档（FastAPI 自动生成 Swagger / OpenAPI） | API 文档 | FastAPI swagger_ui |
| **验收** | `pytest` 全部通过，Swagger 页面可交互测试所有 API，README 按步骤可复现开发环境 | | |

---

## V1.1 — 试点优化 (规划中，待V1.0完成)

- 多院区 MCP Server 扩展（新增医院 HIS/LIS 适配器）
- 知识库增量更新管道（定时拉取最新指南/文献 → 增量索引）
- 用户画像自动更新优化（事件抽取准确率调优 + 刷新频率优化）
- 性能压测与调优（并发50+对话压测，识别瓶颈并优化）

## V2.0 — 扩展 (规划中，待V1.1完成)

- 医学生端：学习模式、测验评估
- 科研人员端：文献综述辅助、数据分析
- 管理后台完善（用户管理、知识库管理、监控面板）
- K8s 部署支持（Helm Chart + 水平扩展）

---

## 十一、附录：融合前后对照

| 原项目能力 | 融合后归属 |
|-----------|-----------|
| 项目一：记忆架构（短期+长期） | 记忆系统 (5.3) |
| 项目一：模块化 MCP Server | MCP Server (5.2) |
| 项目一：Doubao 多模态（语音+图像） | 多模态能力 (5.5) |
| 项目一：ReAct + CoT 推理规划 | Agent 编排引擎 (5.4) |
| 项目一：配置化插拔式架构 | 系统架构 (4.1) + MCP Server (5.2) |
| 项目二：Qwen3-Embedding 离线索引 | RAG 检索管道 (5.1) + 数据模型 (6.3) |
| 项目二：查询处理（压缩/重写/分解） | RAG 检索管道 第[1]步 (5.1) |
| 项目二：Adaptive-RAG + BM25 + 向量混合检索 | RAG 检索管道 第[2][3]步 (5.1) |
| 项目二：RRF 融合 + Qwen3-Reranker 重排序 | RAG 检索管道 第[4]步 (5.1) |
| 项目二：Instruction Template + CoT + Citation | Agent 编排引擎 (5.4) + RAG 第[5]步 (5.1) |

---

## 十二、代码目录结构

```
remediant/
│
├── docker/                              # 容器化配置
│   ├── docker-compose.yml               # 一键启动所有服务
│   ├── nginx/
│   │   └── default.conf                 # 反向代理 /api→FastAPI, /→React
│   └── Dockerfile.backend               # FastAPI 镜像 (生产用)
│
├── backend/                             # Python 后端
│   ├── app/
│   │   ├── main.py                      # FastAPI 入口，挂载所有路由
│   │   ├── config.py                    # 环境变量 & 配置 (pydantic-settings)
│   │   │
│   │   ├── api/                         # REST API 路由层 (薄层，参数校验→调用core)
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                  # /api/auth/* (login, register, me)
│   │   │   ├── chat.py                  # /api/chat/stream (SSE 流式对话)
│   │   │   ├── search.py                # /api/search (知识检索)
│   │   │   ├── report.py                # /api/report/* (上传+解读)
│   │   │   ├── patient.py               # /api/patient/* (档案+康复计划)
│   │   │   ├── doctor.py                # /api/doctor/* (患者查阅)
│   │   │   └── voice.py                 # /api/voice/* (STT+TTS)
│   │   │
│   │   ├── core/                        # 核心业务逻辑 (与HTTP协议无关)
│   │   │   ├── __init__.py
│   │   │   │
│   │   │   ├── agent/                   # Agent 编排引擎
│   │   │   │   ├── __init__.py
│   │   │   │   ├── orchestrator.py      # 主编排器：意图→规划→调度→生成
│   │   │   │   ├── intent.py            # 意图分类器 (Qwen-Max / Qwen3)
│   │   │   │   ├── react_engine.py      # ReAct Thought→Action→Observe 循环
│   │   │   │   ├── cot_engine.py        # CoT 推理步骤记录
│   │   │   │   ├── self_consistency.py  # Self-Consistency 多路径投票
│   │   │   │   ├── tool_router.py       # 工具调度：Action→RAG/MCP/Memory
│   │   │   │   └── response_gen.py      # 响应生成 (模板+Citation+免责声明)
│   │   │   │
│   │   │   ├── model_adapter/              # 模型适配器 (云API / Ollama本地切换)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py                 # BaseLLMAdapter 抽象接口
│   │   │   │   ├── dashscope_adapter.py    # 阿里百炼 (Qwen-Max) 适配器
│   │   │   │   ├── ollama_adapter.py       # Ollama 本地模型适配器
│   │   │   │   └── adapter_registry.py     # 适配器注册与路由
│   │   │   │
│   │   │   ├── rag/                     # RAG 检索管道
│   │   │   │   ├── __init__.py
│   │   │   │   ├── query_processor.py   # 上下文压缩 + 问题重写 + 逻辑分解
│   │   │   │   ├── adaptive_router.py   # 身份感知路由 + 检索策略选择
│   │   │   │   ├── hybrid_retriever.py  # BM25 + 向量 并行混合检索
│   │   │   │   ├── bm25_index.py        # BM25 关键词索引 (rank_bm25)
│   │   │   │   ├── post_processor.py    # RRF 多源融合 + Qwen3-Reranker 语义重排
│   │   │   │   └── citation.py          # 引用溯源 & 来源元数据注入
│   │   │   │
│   │   │   ├── memory/                  # 记忆系统 (三层架构)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── short_term.py        # Redis 短期会话缓存
│   │   │   │   ├── long_term.py         # ChromaDB 长期向量记忆
│   │   │   │   ├── event_extractor.py   # Qwen-Max / Qwen3 关键事件抽取
│   │   │   │   └── memory_reader.py     # 三层融合读取 → Prompt上下文
│   │   │   │
│   │   │   ├── mcp/                     # MCP Server (模块化工具封装)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py              # BaseMCPModule 抽象类
│   │   │   │   ├── registry.py          # Tool Registry 注册中心
│   │   │   │   ├── patient_record.py    # 病例/就诊/处方查询 (对接HIS)
│   │   │   │   └── identity.py          # 身份验证
│   │   │   │
│   │   │   └── multimodal/              # 多模态能力
│   │   │       ├── __init__.py
│   │   │       ├── stt.py               # Doubao 语音识别
│   │   │       ├── tts.py               # Doubao 语音合成
│   │   │       └── ocr.py               # Doubao 报告OCR & 医学图像理解
│   │   │
│   │   ├── models/                      # SQLAlchemy ORM 模型
│   │   │   ├── __init__.py
│   │   │   ├── user.py                  # User
│   │   │   ├── patient.py               # PatientProfile
│   │   │   ├── doctor.py                # DoctorProfile
│   │   │   ├── conversation.py          # Conversation
│   │   │   ├── care_plan.py             # CarePlan
│   │   │   └── knowledge_source.py      # KnowledgeSource
│   │   │
│   │   ├── schemas/                     # Pydantic 请求/响应 Schema
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                  # LoginRequest, TokenResponse
│   │   │   ├── chat.py                  # ChatRequest, SSEChunk
│   │   │   ├── search.py                # SearchRequest, SearchResponse
│   │   │   └── common.py                # ErrorResponse, Pagination
│   │   │
│   │   ├── db/                          # 数据库连接管理
│   │   │   ├── __init__.py
│   │   │   ├── session.py               # SQLAlchemy async session
│   │   │   ├── redis.py                 # Redis client (aioredis)
│   │   │   └── chroma.py                # ChromaDB client
│   │   │
│   │   └── middleware/                   # FastAPI 中间件
│   │       ├── __init__.py
│   │       ├── auth.py                   # JWT 鉴权 (get_current_user)
│   │       └── identity_router.py        # 身份路由 → RequestContext
│   │
│   ├── scripts/                         # 运维脚本
│   │   ├── seed_data.py                 # MySQL + ChromaDB 种子数据
│   │   ├── index_kb.py                  # 知识库离线索引构建
│   │   └── migrate.py                   # Alembic 数据库迁移
│   │
│   ├── tests/                           # 测试
│   │   ├── conftest.py                  # pytest fixtures
│   │   ├── test_rag/                    # RAG 管道测试
│   │   ├── test_agent/                  # Agent 编排测试
│   │   ├── test_mcp/                    # MCP 模块测试
│   │   └── test_api/                    # API 集成测试
│   │
│   ├── requirements.txt                 # Python 依赖
│   └── pyproject.toml                   # 项目元数据
│
├── frontend/                            # React 前端
│   ├── src/
│   │   ├── main.tsx                     # 入口
│   │   ├── App.tsx                      # 根组件 (路由挂载)
│   │   │
│   │   ├── routes/
│   │   │   └── index.tsx                # 路由配置 + 身份路由守卫
│   │   │
│   │   ├── pages/                       # 页面组件
│   │   │   ├── Login.tsx
│   │   │   ├── patient/
│   │   │   │   ├── Chat.tsx             # /patient/chat 对话主页
│   │   │   │   ├── ReportDetail.tsx     # /patient/report/:id
│   │   │   │   ├── CarePlan.tsx         # /patient/care-plan
│   │   │   │   └── History.tsx          # /patient/history
│   │   │   └── doctor/
│   │   │       ├── Search.tsx           # /doctor/search 知识检索
│   │   │       ├── PatientRecord.tsx    # /doctor/patient/:id
│   │   │       └── SearchHistory.tsx    # /doctor/search-history
│   │   │
│   │   ├── components/                  # 组件
│   │   │   ├── shared/                  # 医患共享组件
│   │   │   │   ├── ChatBubble.tsx       # 聊天气泡 (文本/语音/图片)
│   │   │   │   ├── StreamingText.tsx    # SSE 流式文字逐字渲染
│   │   │   │   ├── MarkdownRenderer.tsx # Markdown 渲染 (表格/公式)
│   │   │   │   ├── CitationCard.tsx     # 引用来源卡片 (可点击跳转)
│   │   │   │   ├── ErrorBoundary.tsx    # React 错误边界
│   │   │   │   └── LoadingSkeleton.tsx  # 加载骨架屏
│   │   │   ├── patient/                 # 患者端专属组件
│   │   │   │   ├── VoiceInput.tsx       # 语音录入按钮
│   │   │   │   ├── AudioPlayer.tsx      # TTS 语音播报器
│   │   │   │   ├── ReportUploader.tsx   # 报告拖拽上传+预览
│   │   │   │   └── CareTimeline.tsx     # 康复计划时间轴
│   │   │   └── doctor/                  # 医生端专属组件
│   │   │       ├── SearchPanel.tsx      # 高级检索面板 (筛选器)
│   │   │       ├── ReasoningChain.tsx   # CoT 推理步骤折叠面板
│   │   │       └── PatientRecordView.tsx # 患者病历结构化视图
│   │   │
│   │   ├── stores/                      # Zustand 状态管理
│   │   │   ├── authStore.ts             # 认证状态 (token, role, user)
│   │   │   ├── chatStore.ts             # 对话/流式消息状态
│   │   │   ├── voiceStore.ts            # 语音录制/播放状态
│   │   │   └── searchStore.ts           # 检索/过滤/分页状态
│   │   │
│   │   ├── api/                         # API 调用封装
│   │   │   ├── client.ts                # axios 实例 + JWT拦截器
│   │   │   ├── auth.ts                  # login() / register() / getMe()
│   │   │   ├── chat.ts                  # streamChat() (SSE ReadableStream)
│   │   │   ├── search.ts                # search() / streamSearch()
│   │   │   ├── report.ts                # uploadReport() / interpretReport()
│   │   │   └── voice.ts                 # stt() / tts()
│   │   │
│   │   └── types/
│   │       └── index.ts                 # 全局 TypeScript 类型定义
│   │
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
│
└── README.md
```

---

## 十三、模块间数据流

### 13.1 主链路：用户消息 → Agent 编排 → 流式响应

```
[前端] 用户输入消息
  │
  │  POST /api/chat/stream
  │  Header: Authorization: Bearer <JWT>
  │  Body: { "message": "头痛三天挂什么科", "session_id": "sess_abc" }
  │
  ▼
[api/chat.py]  chat_stream()
  ├─ 鉴权中间件 → RequestContext(user_id, role)
  ├─ 创建/复用 session_id
  └─ 调用 AgentOrchestrator.run()
       │
       ▼
[core/agent/orchestrator.py]  Orchestrator.run(message, role, session_id)
  │
  │  ┌──────────────────────────────────────────────────┐
  │  │ Step 1: intent.classify(message, role)            │
  │  │   → IntentResult(intent=CONSULT, confidence=0.93) │
  │  │                                                   │
  │  │ Step 2: react_engine.reason(message, intent)      │
  │  │   → ActionPlan(steps=[RAG_SEARCH, MCP_QUERY])     │
  │  │                                                   │
  │  │ Step 3: tool_router.execute(action_plan)          │
  │  │   ├─ RAG  : hybrid_retriever.search(query)        │
  │  │   ├─ MCP  : patient_record.query_case(uid)        │
  │  │   └─ Mem  : memory_reader.get_context(uid, sid)   │
  │  │   → ToolResults(rag=[...], mcp={...}, mem={...})  │
  │  │                                                   │
  │  │ Step 4: response_gen.generate(                    │
  │  │   message, intent, tool_results, role             │
  │  │ ) → SSE stream chunks                             │
  │  └──────────────────────────────────────────────────┘
  │
  ▼
[前端] EventSource 接收 SSE 流
  data: {"type":"chunk","content":"根据您的"}
  data: {"type":"chunk","content":"症状描述..."}
  data: {"type":"sources","sources":[{...}]}
  data: {"type":"done"}

  StreamingText 逐字渲染 → MarkdownRenderer 格式化 → CitationCard 来源展示
```

### 13.2 RAG 检索管道数据流

```
用户查询: "二甲双胍肾功能不全剂量调整"
  │
  ▼
[query_processor.py] process(raw_query, role, context)
  │
  ├─ ① 上下文压缩: memory_reader.get_context() → Qwen-Max 摘要 → compressed (≤500 tokens)
  │
  ├─ ② 问题重写: Qwen-Max / Qwen3: "二甲双胍肾功能不全剂量调整"
  │       → "二甲双胍在CKD 3-4期患者中的剂量调整临床指南"
  │
  └─ ③ 逻辑分解: Qwen-Max / Qwen3 → sub_queries:
         ["二甲双胍 CKD 剂量指南",
          "二甲双胍 肾功能不全 禁忌症",
          "二甲双胍 降糖药 相互作用"]
  │
  ▼
[adaptive_router.py] route(rewritten_query, role, sub_queries)
  │
  ├─ 身份感知: role=doctor → kb_professional (指南+文献)
  │            role=patient → kb_patient (通俗科普)
  │
  └─ 策略选择: sub_queries ≥ 2 → Self-RAG 多轮 (逐个子查询检索)
              sub_queries = 0  → 直接检索
  │
  ▼
[hybrid_retriever.py] search(query, kb_collection)
  │
  ├─ BM25 分支 (关键词匹配)
  │    bm25_index.search(query) → [Doc(score=8.2), Doc(score=7.1), ...]
  │
  └─ 向量分支 (Qwen3-Embedding-8B 语义相似度)
       query_embedding = qwen3.embed(query)
       chroma.query(query_embedding, n=20) → [Doc(dist=0.12), Doc(dist=0.18), ...]
  │
  ▼ (两路结果合并)
[post_processor.py] process(bm25_docs, vector_docs)
  │
  ├─ ① RRF 融合去重: 对每篇文档计算 RRF_score = Σ(1 / (60 + rank_i))
  │       → 按 RRF_score 降序排列 (Top-20)
  │
  └─ ② Qwen3-Reranker (Ollama本地 / 阿里百炼API): POST rerank(query, top20_docs)
         → 语义精排 Top-5
  │
  ▼
[citation.py] annotate(final_docs)
  │
  └─ 注入来源元数据: { pmid, guideline_title, version, evidence_level, url }
  │
  ▼
输出: SearchResult(docs=[Doc x5], sources=[Source x5])
```

### 13.3 MCP 工具调用数据流

```
ToolRouter 收到 ActionPlan { steps: [MCP_PATIENT, RAG_SEARCH] }
  │
  ▼
[core/mcp/registry.py] invoke("patient_record.query_case", {"patient_name": "张三"})
  │
  ├─ 查找模块: tool_name → patient_record 模块
  │
  ├─ 执行: patient_record.query_case(patient_name="张三")
  │    ├─ 1. 查 MySQL users → user_id
  │    ├─ 2. 调 HIS 接口 (mock 或真实 REST API)
  │    │     GET /his/patients/{id}/cases → { cases[], visits[], prescriptions[] }
  │    │
  │    └─ 3. 超时 10s → CircuitBreaker → 降级返回: { error: "系统繁忙，请稍后再试" }
  │
  └─ 返回: ToolResult(tool="patient_record.query_case", status=SUCCESS, data={...})
  │
  ▼
ToolRouter 汇总所有 ToolResult →
  tool_results = {
    "mcp": [{tool: "patient_record.query_case", data: {cases: [...], allergies: [...]}}],
    "rag": [{tool: "search", data: SearchResult}],
    "memory": {profile: {...}, recent: [...], long_term: [...]}
  }
  │
  ▼
→ response_gen.generate(message, intent, tool_results, role)
```

### 13.4 记忆系统写入/读取数据流

```
═══ 写入路径 (对话完成后触发) ═══

api/chat.py (流式结束后)
  │
  ├─→ [short_term.py] save(session_id, turn_event)
  │     turn_event = {role, content, intent, timestamp}
  │     Redis: RPUSH session:{sid}:context "{json}"
  │            EXPIRE session:{sid}:context 1800  (30min TTL)
  │
  └─→ [BackgroundTasks] 异步执行:
       │
       ├─→ [event_extractor.py] extract(conversation_text)
       │     Qwen-Max / Qwen3 抽取: {symptoms[], diagnosis[], medications[], allergies[], key_events[]}
       │
       ├─→ [long_term.py] save(user_id, summary_embedding)
       │     ChromaDB: user_memory.add(embedding, metadata={user_id, event_type, ts})
       │
       └─→ MySQL: UPDATE patient_profiles SET medical_history=JSON_MERGE(...)
            MySQL: INSERT INTO conversations (...)

═══ 读取路径 (Agent 编排 Step 3 调用) ═══

[memory_reader.py] get_context(user_id, session_id, current_query)
  │
  ├─ [1] 短期层 Redis:
  │     LRANGE session:{sid}:context 0 -1 → 最近 N 轮对话
  │
  ├─ [2] 长期层 ChromaDB:
  │     embedding = qwen3.embed(current_query)
  │     user_memory.query(embedding, n=5) → 语义相似的历史关键事件
  │
  └─ [3] 持久层 MySQL:
        SELECT * FROM patient_profiles WHERE user_id=? → 结构化画像
  │
  ▼ 融合 → 注入 Agent Prompt:
  """
  [用户画像] 男, 45岁, 过敏:青霉素, 慢性病史:高血压
  [近期对话] Q1: 头痛怎么办 → A1: ...
  [相关历史] 2026-03 就诊记录: 诊断为高血压，处方氨氯地平...
  ---
  当前问题: 我的头痛和血压有关吗？
  """
```

### 13.5 各模块输入/输出速查表

| 模块 | 输入 | 输出 | 格式 |
|------|------|------|------|
| **api/chat** | `ChatRequest { message, session_id }` | `StreamingResponse` (SSE) | JSON → text/event-stream |
| **api/search** | `SearchRequest { query, filters }` | `SearchResponse { docs, sources }` | JSON → JSON |
| **agent/orchestrator** | `(message, role, session_id)` | `AsyncGenerator[SSEChunk]` | Python → SSE stream |
| **agent/intent** | `(message, role)` | `IntentResult(intent, confidence)` | str → Pydantic |
| **agent/react_engine** | `(message, intent, tools_schema)` | `ActionPlan { steps[] }` | Pydantic → Pydantic |
| **agent/tool_router** | `ActionPlan` | `ToolResults { rag[], mcp[], mem{} }` | Pydantic → dict |
| **agent/response_gen** | `(msg, intent, results, role)` | `AsyncGenerator[SSEChunk]` | Python → SSE stream |
| **rag/query_processor** | `(query, role, context)` | `ProcessedQuery { rewritten, sub_queries[] }` | str → Pydantic |
| **rag/adaptive_router** | `(query, role, sub_queries)` | `RouteDecision { kb, strategy }` | Pydantic → Pydantic |
| **rag/hybrid_retriever** | `(query, collection)` | `List[DocResult]` | str → list[Pydantic] |
| **rag/post_processor** | `(bm25_docs, vec_docs)` | `List[DocResult]` (精排Top5) | list → list |
| **rag/citation** | `List[DocResult]` | `List[SourceCitation]` | list → list |
| **memory/memory_reader** | `(user_id, session_id, query)` | `MemoryContext { profile, recent, long }` | IDs → Pydantic |
| **memory/short_term** | `(session_id, turn_event)` | — | Pydantic → Redis |
| **memory/event_extractor** | `(conversation_text)` | `ExtractedEvents { symptoms[], ... }` | str → Pydantic |
| **mcp/registry** | `(tool_name, args)` | `ToolResult { data, error }` | str+dict → Pydantic |
| **multimodal/stt** | `audio_bytes` | `str` (转写文本) | bytes → str |
| **multimodal/tts** | `text` | `bytes` (音频流) | str → bytes |
| **multimodal/ocr** | `image_bytes` | `str` (提取文本) | bytes → str |

---

## 十四、所需素材清单

### 14.1 API 密钥与服务账号 (全部国内可用)

| 服务 | 用途 | 优先级 | 获取方式 | 备注 |
|------|------|--------|----------|------|
| **阿里百炼 (DashScope) API Key** | Qwen-Max 推理 (意图/规划/生成/事件抽取) + Rerank API | **P0 必须** | dashscope.aliyun.com | 国内注册即用，按量计费；替代 OpenAI |
| **火山引擎 Doubao API Key** | 语音 STT/TTS + 医学图像 OCR/视觉 | P1 | console.volcengine.com | 国内服务，需企业/个人实名认证 |
| **Qwen3-Embedding-8B** | 文本向量化 (知识库+记忆) | **P0 必须** | HuggingFace / ModelScope 下载 | 本地 Ollama 部署或 HuggingFace Inference API |
| **Qwen3-Reranker** | RAG 语义重排序 | P1 | HuggingFace / ModelScope 下载 | 本地 Ollama 部署，替代 Cohere；也可使用阿里百炼 Rerank API |
| **DeepSeek API Key** (可选) | 备选推理模型 | P2 | platform.deepseek.com | 国内服务，作为 Qwen-Max 的备选方案 |

### 14.2 Ollama 本地环境

| 组件 | 用途 | 安装方式 | 最低配置 |
|------|------|----------|----------|
| **Ollama** | 本地模型运行时 | ollama.com 下载 (Windows/Mac/Linux) | — |
| **Qwen3:14b** (约8GB) | 本地推理模型 (开发/降级) | `ollama pull qwen3:14b` | GPU 8GB+ VRAM 或 16GB+ RAM |
| **Qwen3-Embedding** (约1GB) | 本地文本向量化 | `ollama pull qwen3-embedding` | CPU 即可 |
| **Qwen3-Reranker** (约2GB) | 本地语义重排序 | `ollama pull qwen3-reranker` | GPU 4GB+ VRAM 或 8GB+ RAM |

> **云+端策略：** 生产环境使用阿里百炼 API (Qwen-Max) 保证效果，开发调试使用 Ollama 本地模型降低费用。模型适配器层 (`core/model_adapter/`) 支持通过配置开关一键切换。

### 14.3 知识库素材 (MVP最低量)

| 素材 | 用途 | 最低数量 | 来源建议 | 我可帮生成？ |
|------|------|----------|----------|-------------|
| **临床指南摘要** | 医生端专业知识库 | ≥ 30 条 | 中华医学会、NCCN、ESC 公开摘要 | 否，需权威来源 |
| **药品说明书** | 药品查询 | ≥ 50 种常用药 | 国家药监局公开数据 | 否，需官方数据 |
| **通俗医学科普** | 患者端通俗知识库 | ≥ 30 篇 | 默沙东诊疗手册、丁香园 | 可协助格式化入库 |
| **检查指标参考** | 报告解读 | 血/尿常规+肝肾功 各1份 | 临床检验标准手册 | 可，公开标准值 |
| **科室导诊规则表** | 症状→科室映射 | ≥ 50 条规则 | 医院导诊规范 | 可，标准化规则 |

### 14.4 测试账号与数据

| 素材 | 用途 | 数量 | 备注 |
|------|------|------|------|
| **患者测试账号** | 患者端功能验证 | 2-3个 | 不同年龄/病史画像 |
| **医生测试账号** | 医生端功能验证 | 2-3个 | 不同科室/职称 |
| **化验单样本图片** | 报告上传解读测试 | 3-5张 | 脱敏处理 |
| **典型测试问题** | 检索/对话质量验证 | 患者10条+医生10条 | 覆盖8个场景 |

### 14.5 降级替代方案

| 原方案 | 降级方案 | 影响 |
|--------|----------|------|
| 阿里百炼 Qwen-Max | Ollama 本地 Qwen3:14b | 推理质量略降，完全离线可用 |
| Qwen3-Reranker (Ollama) | RRF 分数直接排序 | 重排精度下降约 10-15% |
| Doubao STT/TTS | 浏览器 Web Speech API | 仅 Chrome 支持，准确率略低 |
| Qwen3-Embedding (Ollama) | HuggingFace Inference API | 增加网络延迟 ~200ms |
| 真实 HIS 对接 | JSON mock 文件 | 数据为假，不影响架构验证 |
| 阿里百炼 API 不可用 | 全部切 Ollama 本地模型 | 完全离线运行，无需外部网络依赖 |
