import logging

from app.core.model_adapter.adapter_registry import get_adapter_registry

logger = logging.getLogger(__name__)

RRF_K = 60


class PostProcessor:
    """RRF fusion + Qwen3-Reranker semantic reranking."""

    async def process(self, bm25_docs: list[dict], vector_docs: list[dict], query: str, top_k: int = 5) -> list[dict]:
        merged = self._rrf_fusion(bm25_docs, vector_docs)
        if not merged:
            return []

        # Use reranker if available, otherwise fall back to RRF scores
        try:
            return await self._rerank(query, merged, top_k)
        except Exception as e:
            logger.warning(f"Reranking failed, using RRF scores: {e}")
            return merged[:top_k]

    def _rrf_fusion(self, bm25_docs: list[dict], vector_docs: list[dict]) -> list[dict]:
        """Reciprocal Rank Fusion: merge and deduplicate results from both sources."""
        scores: dict[str, float] = {}
        docs_map: dict[str, dict] = {}

        for rank, doc in enumerate(bm25_docs, start=1):
            doc_id = doc.get("id", f"bm25_{rank}")
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (RRF_K + rank)
            docs_map[doc_id] = doc

        for rank, doc in enumerate(vector_docs, start=1):
            doc_id = doc.get("id", f"vec_{rank}")
            scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (RRF_K + rank)
            docs_map[doc_id] = doc

        merged = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [{**docs_map.get(doc_id, {}), "rrf_score": score, "id": doc_id} for doc_id, score in merged]

    async def _rerank(self, query: str, docs: list[dict], top_k: int) -> list[dict]:
        adapter = get_adapter_registry()
        contents = [d.get("content", "") for d in docs]
        results = await adapter.rerank(query, contents, top_k)
        reranked = []
        for r in results:
            idx = r["index"]
            if idx < len(docs):
                doc = {**docs[idx], "rerank_score": r["relevance_score"]}
                reranked.append(doc)
        return reranked
