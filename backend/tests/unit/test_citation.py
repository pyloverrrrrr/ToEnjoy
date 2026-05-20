from app.core.rag.citation import annotate_citations, SourceCitation


class TestAnnotateCitations:
    def test_extracts_all_fields(self):
        docs = [{
            "id": "doc1",
            "metadata": {
                "title": "NCCN 2025 NSCLC指南",
                "type": "guideline",
                "evidence_level": "A",
                "version": "2025.v3",
                "pmid": "12345678",
            },
        }]
        result = annotate_citations(docs)
        assert len(result) == 1
        assert result[0].title == "NCCN 2025 NSCLC指南"
        assert result[0].source_type == "guideline"
        assert result[0].evidence_level == "A"
        assert result[0].version == "2025.v3"
        assert result[0].pmid == "12345678"

    def test_deduplicates_by_title(self):
        docs = [
            {"id": "doc1", "metadata": {"title": "Same Title"}},
            {"id": "doc2", "metadata": {"title": "Same Title"}},
            {"id": "doc3", "metadata": {"title": "Different Title"}},
        ]
        result = annotate_citations(docs)
        assert len(result) == 2

    def test_missing_metadata_uses_defaults(self):
        docs = [{"id": "doc1", "metadata": {}}]
        result = annotate_citations(docs)
        assert result[0].source_type == "unknown"
        assert result[0].evidence_level is None
        assert result[0].url is None

    def test_missing_title_falls_back_to_id(self):
        docs = [{"id": "fallback_id", "metadata": {}}]
        result = annotate_citations(docs)
        assert result[0].title == "fallback_id"

    def test_source_type_from_metadata_type_key(self):
        docs = [{"id": "d", "metadata": {"type": "literature"}}]
        result = annotate_citations(docs)
        assert result[0].source_type == "literature"

    def test_source_type_from_source_type_key(self):
        docs = [{"id": "d", "metadata": {"source_type": "education"}}]
        result = annotate_citations(docs)
        assert result[0].source_type == "education"
