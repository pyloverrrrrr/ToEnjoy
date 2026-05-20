import asyncio
import logging

from app.db.chroma import get_chroma
from app.core.model_adapter.adapter_registry import get_adapter_registry
from app.core.rag.bm25_index import BM25Index

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Parallel BM25 + vector hybrid retrieval."""

    def __init__(self):
        self._bm25_indexes: dict[str, BM25Index] = {}

    async def _load_docs_for_bm25(self, collection: str) -> list[dict]:
        """Load all documents from ChromaDB for BM25 indexing."""
        chroma = get_chroma()
        try:
            col = chroma.get_collection(collection)
            result = col.get()
            docs = []
            if result["ids"]:
                for i, doc_id in enumerate(result["ids"]):
                    docs.append({
                        "id": doc_id,
                        "content": result["documents"][i] if result["documents"] else "",
                        "metadata": result["metadatas"][i] if result["metadatas"] else {},
                    })
            return docs
        except Exception as e:
            logger.warning(f"Failed to load docs from ChromaDB collection {collection}: {e}")
            return []

    async def _get_bm25_index(self, collection: str) -> BM25Index:
        if collection not in self._bm25_indexes:
            idx = BM25Index()
            docs = await self._load_docs_for_bm25(collection)
            idx.build_index(docs)
            self._bm25_indexes[collection] = idx
        return self._bm25_indexes[collection]

    async def search(self, query: str, collection: str, top_k: int = 10) -> list[dict]:
        bm25_task = self._bm25_search(query, collection, top_k)
        vector_task = self._vector_search(query, collection, top_k)

        bm25_docs, vector_docs = await asyncio.gather(bm25_task, vector_task, return_exceptions=True)

        if isinstance(bm25_docs, Exception):
            logger.warning(f"BM25 search failed: {bm25_docs}")
            bm25_docs = []
        if isinstance(vector_docs, Exception):
            logger.warning(f"Vector search failed: {vector_docs}")
            vector_docs = []

        return bm25_docs, vector_docs

    async def _bm25_search(self, query: str, collection: str, top_k: int) -> list[dict]:
        try:
            idx = await self._get_bm25_index(collection)
            return idx.search(query, top_k)
        except Exception:
            return []

    async def _vector_search(self, query: str, collection: str, top_k: int) -> list[dict]:
        try:
            adapter = get_adapter_registry()
            embeddings = await adapter.embed([query])
            chroma = get_chroma()
            col = chroma.get_collection(collection)
            result = col.query(query_embeddings=embeddings, n_results=top_k)
            docs = []
            if result["ids"] and result["ids"][0]:
                for i, doc_id in enumerate(result["ids"][0]):
                    docs.append({
                        "id": doc_id,
                        "content": result["documents"][0][i] if result["documents"] else "",
                        "vector_score": float(result["distances"][0][i]) if result["distances"] else 0.0,
                        "metadata": result["metadatas"][0][i] if result["metadatas"] else {},
                    })
            return docs
        except Exception:
            return []
