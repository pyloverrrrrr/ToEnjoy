from dataclasses import dataclass, field


@dataclass
class SourceCitation:
    title: str
    source_type: str
    url: str | None = None
    evidence_level: str | None = None
    version: str | None = None
    pmid: str | None = None


def annotate_citations(docs: list[dict]) -> list[SourceCitation]:
    """Extract source metadata from retrieved documents into structured citations."""
    citations = []
    seen = set()
    for doc in docs:
        meta = doc.get("metadata", {})
        title = meta.get("title") or meta.get("source") or doc.get("id", "Unknown")
        if title in seen:
            continue
        seen.add(title)
        citations.append(SourceCitation(
            title=title,
            source_type=meta.get("type", meta.get("source_type", "unknown")),
            url=meta.get("url") or meta.get("source_url"),
            evidence_level=meta.get("evidence_level"),
            version=meta.get("version"),
            pmid=meta.get("pmid"),
        ))
    return citations
