# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

For full version (413 lines) see `CLAUDE.full.md`. This file is a trimmed version for daily use — read CLAUDE.full.md when you need details on API routes, state machines, frontend components, or test patterns.

## Project overview

Remediant is a unified medical service platform serving both patients and doctors through identity-based routing. It combines a RAG retrieval pipeline with a hand-written ReAct Agent orchestration engine under a monorepo structure (`backend/` + `frontend/` + `docker/`).

## Commands

```bash
# Start all services
cd docker && docker compose up -d

# Restart backend after code changes (Docker mode)
cd docker && docker compose restart backend

# Backend dev (without Docker)
cd backend && uvicorn app.main:app --reload --port 8000

# Frontend dev
cd frontend && npm install && npm run dev

# Reindex KB documents into ChromaDB (after adding/editing files in data/kb/)
docker exec remediant-backend python -X utf8 //app/scripts/reindex_all.py

# Verify KB indexing status
docker exec remediant-backend python -X utf8 //app/scripts/verify_kb.py

# Run all backend tests (asyncio_mode=auto configured in pyproject.toml)
# NOTE: Python 3.12 required (3.13 incompatible with numpy 1.x / chromadb-client)
cd backend && python -m pytest -v

# Run a specific test tier
cd backend && python -m pytest tests/unit/ -v
cd backend && python -m pytest tests/async_unit/ -v
cd backend && python -m pytest tests/api/ -v
```

Docker Compose is the canonical dev environment (6 containers: MySQL, Redis, ChromaDB, MinIO, backend, Nginx). Backend hot-reloads via `--reload` volume mount.

## Architecture overview

### Request flow
Browser → Nginx(:80) → FastAPI(:8000). Identity routing via JWT middleware: `doctor` → `kb_professional` + professional template, `patient` → `kb_patient` + layperson template.

### Agent pipeline (手写 ReAct)
`Orchestrator.run()` in `backend/app/core/agent/orchestrator.py`:
1. Memory context load (3-layer parallel)
2. **手写 ReAct loop** — LLM decides tools (rag.search / memory.get_context / finish), max 5 iterations, regex-parsed Chinese tags (思考/行动/行动输入)
3. SSE streaming: reasoning_steps → chunks → sources → done
4. BackgroundTasks saves turn to memory + MySQL after stream completes

### Model adapter (backend/app/core/model_adapter/)
All LLM calls → DashScope (阿里百炼) via `get_adapter_registry()`, never directly:
- Inference: `qwen-max` — `/compatible-mode/v1/chat/completions`
- Embedding: `text-embedding-v3` — `/compatible-mode/v1/embeddings`
- Reranker: `gte-rerank-v2` — native `/api/v1/services/rerank/text-rerank/text-rerank`

### Memory system (3 layers, independent degradation)
- **Short-term**: Redis lists, 20-turn cap, 30-min TTL
- **Long-term**: ChromaDB `user_memory` collection
- **Profile**: MySQL user profile fields
- Fused in parallel via `asyncio.gather(return_exceptions=True)`

### Tool framework (backend/app/core/agent/tool_router.py)
Tool routing is handled by `ToolRouter.execute()` which dispatches actions: `rag.search` → RAG pipeline, `memory.get_context` → memory service, `patient_record.*` / `identity.*` → direct DB queries, `finish` → empty string. All use `async_session()` directly (not FastAPI DI).

### RAG pipeline
LLM rewrite + decomposition → role-based collection routing → parallel BM25 + vector search → RRF fusion + reranker → citation annotation.

### KB document pipeline
Upload → parse (.txt/.pdf/.docx/.md) → chunk (800 chars, 150 overlap) → embed (Qwen3-Embedding-8B) → ChromaDB upsert.

### Multimodal
- OCR: 火山引擎 ARK (`doubao-1.5-vision-pro-250328`)
- STT/TTS: DashScope (Paraformer / CosyVoice)
- File storage: MinIO

## Key conventions

- All LLM calls → `get_adapter_registry().generate()` / `.embed()`, never to specific adapters
- `RequestContext` injected via FastAPI `Depends(get_request_context)`
- For non-DI contexts (background tasks, memory reader), use `import app.db.session` and `app.db.session.async_session()` — NOT `from ... import` (blocks test patching)
- Same `import module` pattern applies to `get_adapter_registry` and any singletons tests need to mock
- Memory services (`get_redis()`, `get_chroma()`) can return `None` — always guard with `if x is None: return []`
- Soft-delete queries must always include `User.deleted_at.is_(None)` to avoid matching deleted accounts
- Zustand stores are global singletons — `authStore.logout()` must clear chatStore + searchStore to prevent cross-role data leakage
- Python 3.11–3.12 required (3.13 segfaults with numpy 1.x)
- All pages use 100% inline styles (no CSS modules)

## Common pitfalls

- **SQLAlchemy `create_all` does NOT migrate existing tables.** Adding a column requires manual `ALTER TABLE`.
- **Docker mode**: changes need `docker compose restart backend` (uvicorn `--reload` only works outside Docker).
- **Git Bash on Windows**: `docker exec` paths with `/app/` get converted. Use `//app/` prefix to bypass.
- **DashScope embedding**: uses OpenAI-compatible endpoint `/compatible-mode/v1/embeddings`, NOT the native `/api/v1/services/embeddings/` endpoint.

## Spec and plan docs

See `CLAUDE.full.md` or `docs/superpowers/` for full details.
