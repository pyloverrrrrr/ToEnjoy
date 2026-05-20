import jieba

from rank_bm25 import BM25Okapi


class BM25Index:
    """BM25 keyword index with jieba Chinese tokenization."""

    def __init__(self):
        self.documents: list[dict] = []
        self.bm25: BM25Okapi | None = None
        self._tokenized_docs: list[list[str]] = []

    def tokenize(self, text: str) -> list[str]:
        tokens = jieba.cut(text)
        return [t.strip() for t in tokens if t.strip()]

    def build_index(self, documents: list[dict]):
        """Build BM25 index from documents with 'content' field."""
        self.documents = documents
        self._tokenized_docs = [self.tokenize(doc.get("content", "")) for doc in documents]
        if self._tokenized_docs:
            self.bm25 = BM25Okapi(self._tokenized_docs)

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        if not self.bm25:
            return []
        tokenized = self.tokenize(query)
        scores = self.bm25.get_scores(tokenized)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
        return [
            {**self.documents[idx], "bm25_score": float(score)}
            for idx, score in ranked if score > 0
        ]
