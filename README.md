# Remediant — 医患双端服务平台

基于 **ReAct Agent** + **RAG 混合检索** 的智能医疗问答系统，面向医生和患者双端提供服务。

## 系统架构

```
Browser → Nginx(:80) → FastAPI(:8000)
                          │
                          ├─ /api/chat/stream  ←→ Agent 编排引擎 (ReAct)
                          ├─ /api/search       ←→ RAG 检索管线
                          ├─ /api/voice/*      ←→ 语音 STT/TTS
                          ├─ /api/report/*     ←→ OCR 报告解读
                          ├─ /api/patient/*    ←→ 患者端接口
                          ├─ /api/doctor/*     ←→ 医生端接口
                          └─ /api/kb/*         ←→ 知识库管理
                          │
                          ├─ MySQL    — 用户/病历/对话
                          ├─ Redis    — 会话缓存/短期记忆
                          ├─ ChromaDB — 向量检索/长期记忆
                          └─ MinIO    — 文件存储
```

### Agent 工作流

```
用户输入 → 记忆加载(三层并行) → ReAct 循环(LLM自主决策工具调用) → SSE 流式输出
                                  │
                                  ├─ rag.search          → 知识库检索
                                  ├─ patient_record.*    → 病历查询
                                  ├─ identity.*          → 身份验证
                                  └─ memory.get_context  → 记忆补充
```

## 技术栈

| 层次 | 技术 |
|------|------|
| 后端框架 | FastAPI + SQLAlchemy 2.0 async |
| 数据库 | MySQL 8.0 + Redis 7 + ChromaDB 0.5 |
| LLM | DashScope qwen-max / text-embedding-v3 / gte-rerank-v2 |
| 语音 | DashScope Paraformer (STT) + CosyVoice (TTS) |
| OCR | 火山引擎 Doubao Vision Pro |
| 前端 | React 18 + TypeScript + Vite + Zustand |
| 部署 | Docker Compose (6 容器) |

## 功能

### 患者端
- **智能问诊** — RAG + ReAct 多轮对话，流式 SSE 输出，推理链可视化
- **挂号系统** — 科室选择 + 状态追踪（已挂号→问诊中→康复中→已康复）
- **病历查看** — 按就诊分集折叠面板，康复后自动解锁
- **康复计划** — 与挂号状态联动
- **报告解读** — 上传医学报告 → OCR 识别 → LLM 结构化解读
- **语音输入** — 浏览器语音识别

### 医生端
- **智能问诊** — 分屏设计（检索面板 + 对话区），ReAct 推理步骤透明展示
- **患者管理** — 科室范围患者列表 + 状态流转操作
- **病历 CRUD** — 诊断/就诊/处方内联编辑
- **知识库管理** — 文档上传/解析/删除/重索引
- **医学检索** — RAG 全文检索 + 文档类型筛选

## 快速开始

```bash
# 1. 启动服务（需要 Docker）
cd docker
# 编辑 backend/.env 配置 DASHSCOPE_API_KEY
docker compose up -d

# 2. 初始化知识库
cd ../backend && python -X utf8 scripts/reindex_all.py

# 3. 访问
# 前端: http://localhost
# API 文档: http://localhost:8000/docs
```

## 项目结构

```
backend/
├── app/
│   ├── api/            # FastAPI 路由层
│   ├── core/
│   │   ├── agent/      # ReAct 推理引擎
│   │   ├── rag/        # RAG 检索管线 (BM25 + 向量 + Reranker)
│   │   ├── memory/     # 三层记忆系统 (Redis + ChromaDB + MySQL)
│   │   ├── kb/         # 知识库文档管线 (解析/分块/索引)
│   │   ├── model_adapter/ # LLM 适配器抽象层 (DashScope)
│   │   └── multimodal/ # 多模态 (STT/TTS/OCR)
│   ├── models/         # SQLAlchemy ORM 模型
│   ├── schemas/        # Pydantic 校验 Schema
│   └── db/             # 数据库连接管理
└── tests/
    ├── unit/           # 纯同步单元测试
    ├── async_unit/     # 异步单元测试 (mock LLM)
    └── api/            # API 集成测试

frontend/
└── src/
    ├── api/            # HTTP 调用层
    ├── components/     # 共享组件
    ├── pages/          # 页面 (Login + patient/ + doctor/)
    ├── stores/         # Zustand 状态管理
    └── types/          # TypeScript 类型定义
```

## 测试

```bash
cd backend && python -m pytest -v
# 分层运行:
# python -m pytest tests/unit/ -v
# python -m pytest tests/async_unit/ -v
# python -m pytest tests/api/ -v
```

## 环境要求

- Python 3.11–3.12
- Node.js 18+
- Docker Desktop
