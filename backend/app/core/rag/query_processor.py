from dataclasses import dataclass

from app.core.model_adapter.adapter_registry import get_adapter_registry


@dataclass
class ProcessedQuery:
    original: str
    rewritten: str
    sub_queries: list[str]


class QueryProcessor:
    """Query processing: context compression + query rewrite + decomposition."""

    async def process(self, query: str, role: str, context: str = "") -> ProcessedQuery:
        adapter = get_adapter_registry()
        rewritten = await self._rewrite(query, role, context)
        sub_queries = await self._decompose(rewritten, role)
        return ProcessedQuery(original=query, rewritten=rewritten, sub_queries=sub_queries)

    async def _rewrite(self, query: str, role: str, context: str) -> str:
        adapter = get_adapter_registry()
        system = "你是医学查询改写专家。将模糊的口语化提问改写为精准的医学检索语句。保留所有关键症状、药品、疾病名称。仅输出改写后的查询语句，无需解释。"
        user = f"原始问题: {query}"
        if context:
            user = f"对话上下文: {context}\n\n原始问题: {query}"

        result = await adapter.generate(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.3,
            max_tokens=256,
        )
        return result.strip()

    async def _decompose(self, query: str, role: str) -> list[str]:
        """Decompose complex medical queries into atomic sub-queries."""
        # Heuristic: short queries don't need decomposition
        if len(query) < 40:
            return []

        adapter = get_adapter_registry()
        system = "你是医学问题分解专家。将复杂医学问题拆分为2-4个独立的原子化子查询，每个子查询关注一个单独的概念。以JSON数组输出，若问题简单则输出空数组[]。"
        user = f"复杂问题: {query}"

        result = await adapter.generate(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.3,
            max_tokens=512,
        )
        try:
            import json
            sub_queries = json.loads(result.strip().removeprefix("```json").removesuffix("```"))
            return sub_queries if isinstance(sub_queries, list) else []
        except Exception:
            return []
