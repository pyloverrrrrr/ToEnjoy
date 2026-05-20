import json
from typing import AsyncGenerator

from app.config import settings
from app.core.agent.react_engine import ReActEngine
from app.core.agent.response_gen import ResponseGenerator
from app.core.rag.citation import annotate_citations
from app.core.memory.memory_service import MemoryService


class Orchestrator:
    """ReAct-based orchestrator: ReAct loop (RAG/MCP/Memory) → Generate."""

    def __init__(self):
        self.react_engine = ReActEngine()
        self.response_gen = ResponseGenerator()
        self.memory_service = MemoryService()

    async def run(self, message: str, role: str, role_value: str,
                  session_id: str, user_id: int = 0) -> AsyncGenerator[dict, None]:
        # Step 0: Load memory context
        memory_ctx = None
        if user_id > 0:
            memory_ctx = await self.memory_service.get_context(user_id, session_id, message)

        # Step 1: ReAct loop — LLM decides which tools to call
        react_result = await self.react_engine.run(
            message, role=role, user_id=user_id, session_id=session_id,
            memory_context=memory_ctx.formatted_prompt if memory_ctx else None,
        )

        # Step 2: Emit reasoning steps (for doctor-facing transparency)
        yield {
            "type": "reasoning_steps",
            "steps": [s.to_dict() for s in react_result.steps],
        }

        # Step 3: Build context from ReAct observations
        search_context = self._extract_search_results(react_result)

        # Step 4: Annotate citations if we have search results
        sources_data: list[dict] = []
        if search_context:
            sources = annotate_citations(search_context)
            sources_data = [{"title": s.title, "type": s.source_type, "url": s.url,
                             "evidence_level": s.evidence_level, "version": s.version}
                            for s in sources]

        # Step 5: Stream response with CoT context
        memory_prompt = memory_ctx.formatted_prompt if memory_ctx else None
        async for chunk in self.response_gen.generate(
            message, search_context, role, sources_data,
            memory_context=memory_prompt,
            react_steps=react_result.steps,
        ):
            yield {"type": "chunk", "content": chunk}

        # Final: sources + done
        yield {"type": "sources", "sources": sources_data}
        yield {"type": "done"}

    def _extract_search_results(self, react_result) -> list[dict]:
        """Pull RAG search results from ReAct observations for citation annotation."""
        docs: list[dict] = []
        for step in react_result.steps:
            if step.action == "rag.search" and step.observation:
                try:
                    data = json.loads(step.observation)
                    for r in data.get("results", []):
                        docs.append({
                            "content": r.get("content", ""),
                            "metadata": {"title": r.get("title", "知识库结果")},
                        })
                except (json.JSONDecodeError, TypeError):
                    docs.append({
                        "content": step.observation,
                        "metadata": {"title": f"ReAct检索-{step.action_input.get('query', '')[:50]}"},
                    })
        return docs
