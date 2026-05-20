from app.core.rag.bm25_index import BM25Index


class TestBM25IndexTokenize:
    def test_chinese_tokenization(self):
        idx = BM25Index()
        tokens = idx.tokenize("头痛三天挂什么科")
        assert "头痛" in tokens or "头" in tokens
        assert len(tokens) > 1

    def test_empty_text(self):
        idx = BM25Index()
        tokens = idx.tokenize("")
        assert tokens == []

    def test_whitespace_filtering(self):
        idx = BM25Index()
        tokens = idx.tokenize("  发热  ")
        assert all(t == "发热" for t in tokens)


class TestBM25IndexBuildAndSearch:
    def test_build_and_search(self):
        idx = BM25Index()
        docs = [
            {"id": "1", "content": "头痛是常见的临床症状"},
            {"id": "2", "content": "高血压需要定期监测血压"},
            {"id": "3", "content": "糖尿病患者应控制饮食"},
        ]
        idx.build_index(docs)

        results = idx.search("头痛症状", top_k=2)
        assert len(results) > 0
        assert results[0]["id"] == "1"
        assert "bm25_score" in results[0]

    def test_empty_docs(self):
        idx = BM25Index()
        idx.build_index([])
        assert idx.search("头痛") == []

    def test_search_before_build(self):
        idx = BM25Index()
        assert idx.search("头痛") == []

    def test_bm25_scores_are_descending(self):
        idx = BM25Index()
        docs = [
            {"id": "1", "content": "头痛是常见的临床症状"},
            {"id": "2", "content": "头痛可能由多种原因引起"},
            {"id": "3", "content": "糖尿病患者应控制饮食"},
        ]
        idx.build_index(docs)
        results = idx.search("头痛", top_k=3)
        scores = [r["bm25_score"] for r in results]
        assert scores == sorted(scores, reverse=True)
