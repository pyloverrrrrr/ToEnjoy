from app.core.rag.post_processor import PostProcessor, RRF_K


class TestRRFFusion:
    def test_rrf_fusion_merges_sources(self):
        pp = PostProcessor()
        bm25_docs = [{"id": "doc1", "content": "BM25 result"}]
        vector_docs = [{"id": "doc2", "content": "Vector result"}]

        result = pp._rrf_fusion(bm25_docs, vector_docs)
        assert len(result) == 2

    def test_rrf_deduplicates_by_id(self):
        pp = PostProcessor()
        bm25_docs = [{"id": "shared", "content": "from BM25"}]
        vector_docs = [{"id": "shared", "content": "from vector"}]

        result = pp._rrf_fusion(bm25_docs, vector_docs)
        assert len(result) == 1
        assert result[0]["rrf_score"] > 0

    def test_rrf_formula(self):
        pp = PostProcessor()
        bm25_docs = [{"id": "doc1", "content": "first"}]
        vector_docs = []

        result = pp._rrf_fusion(bm25_docs, vector_docs)
        expected_score = 1.0 / (RRF_K + 1)
        assert result[0]["rrf_score"] == expected_score

    def test_rrf_score_accumulates_both_sources(self):
        pp = PostProcessor()
        bm25_docs = [{"id": "shared", "content": "result"}]
        vector_docs = [{"id": "shared", "content": "result"}]

        result = pp._rrf_fusion(bm25_docs, vector_docs)
        expected = 1.0 / (RRF_K + 1) + 1.0 / (RRF_K + 1)
        assert len(result) == 1
        assert result[0]["rrf_score"] == expected

    def test_empty_inputs(self):
        pp = PostProcessor()
        result = pp._rrf_fusion([], [])
        assert result == []

    def test_order_is_by_rrf_score_descending(self):
        pp = PostProcessor()
        bm25_docs = [
            {"id": "low", "content": "third"},
            {"id": "high", "content": "first"},
        ]
        vector_docs = []

        result = pp._rrf_fusion(bm25_docs, vector_docs)
        scores = [r["rrf_score"] for r in result]
        assert scores == sorted(scores, reverse=True)


class TestProcessFallback:
    """When reranker is unavailable, RRF scores should be used."""

    async def test_empty_merged_falls_back_to_rrf(self):
        pp = PostProcessor()
        result = await pp.process([], [], "test query", top_k=3)
        assert result == []
