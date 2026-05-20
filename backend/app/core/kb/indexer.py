import logging
import re
import uuid
import os
from datetime import datetime
from pathlib import Path

from app.db.chroma import get_chroma
from app.core.kb.document_parser import parse_file
from app.core.kb.document_chunker import chunk_text
from app.core.model_adapter.adapter_registry import get_adapter_registry

logger = logging.getLogger(__name__)

KB_BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "kb"

# Keyword rules for auto-detecting document type from content
_TYPE_RULES: list[tuple[str, list[str]]] = [
    ("guideline", [
        "指南", "推荐意见", "证据等级", "证据级别", "专家共识", "临床路径",
        "guideline", "recommendation", "consensus", "clinical practice",
    ]),
    ("drug", [
        "用法用量", "适应症", "禁忌", "不良反应", "药品", "说明书", "处方",
        "dosage", "contraindication", "drug", "pharmacokinetics",
    ]),
    ("education", [
        "预防", "保健", "养生", "科普", "健康教育", "生活方式", "自我管理",
        "patient education", "health tips", "prevention",
    ]),
]

_TYPE_LABELS = {
    "guideline": "guideline",
    "drug": "drug",
    "education": "education",
    "literature": "literature",
}


def _classify_document_type(text: str) -> str:
    """Auto-detect document type from content using keyword rules."""
    text_lower = text.lower()
    scores: dict[str, int] = {}

    for doc_type, keywords in _TYPE_RULES:
        score = 0
        for kw in keywords:
            score += len(re.findall(re.escape(kw), text_lower))
        scores[doc_type] = score

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "literature"
    logger.info(f"Auto-detected document type: {_TYPE_LABELS[best]} (scores: {scores})")
    return _TYPE_LABELS[best]


def _build_document_id(filename: str, chunk_idx: int) -> str:
    safe = filename.replace("/", "_").replace("\\", "_")
    return f"{safe}_chunk_{chunk_idx}"


async def index_document(
    file_path: str,
    collection: str,
    title: str | None = None,
    doc_type: str | None = None,
) -> dict:
    """Index a document: parse → chunk → classify → embed → store in ChromaDB.

    If doc_type is not provided, it is auto-detected from the document content.
    Returns a summary dict with document metadata and chunk count.
    """
    filename = os.path.basename(file_path)
    display_title = title or os.path.splitext(filename)[0]

    # Step 1: Parse
    raw_text = parse_file(file_path)

    # Step 2: Chunk
    chunks = chunk_text(raw_text)
    if not chunks:
        raise ValueError(f"No text extracted from {filename}")

    # Step 3: Auto-detect document type if not specified
    resolved_type = doc_type or _classify_document_type(raw_text)

    # Step 4: Embed
    adapter = get_adapter_registry()
    embeddings = await adapter.embed(chunks)

    # Step 4: Store in ChromaDB
    chroma = get_chroma()
    if chroma is None:
        raise RuntimeError("ChromaDB not initialized")

    col = chroma.get_or_create_collection(collection)
    chunk_ids = [_build_document_id(filename, i) for i in range(len(chunks))]
    metadatas = [
        {
            "title": display_title,
            "type": resolved_type,
            "filename": filename,
            "chunk_index": i,
            "total_chunks": len(chunks),
            "indexed_at": datetime.utcnow().isoformat(),
        }
        for i in range(len(chunks))
    ]

    col.upsert(ids=chunk_ids, documents=chunks, embeddings=embeddings, metadatas=metadatas)

    logger.info(f"Indexed {filename}: {len(chunks)} chunks into collection '{collection}'")

    return {
        "filename": filename,
        "title": display_title,
        "type": resolved_type,
        "collection": collection,
        "chunks": len(chunks),
        "chunk_ids": chunk_ids,
    }


async def delete_document(filename: str, collection: str) -> int:
    """Delete all chunks for a document from ChromaDB. Returns count of deleted chunks."""
    chroma = get_chroma()
    if chroma is None:
        raise RuntimeError("ChromaDB not initialized")

    col = chroma.get_or_create_collection(collection)
    # Find all chunk IDs for this document
    existing = col.get()
    ids_to_delete = [
        doc_id for doc_id, meta in zip(existing["ids"], existing["metadatas"])
        if meta and meta.get("filename") == filename
    ]
    if ids_to_delete:
        col.delete(ids=ids_to_delete)
    return len(ids_to_delete)


def list_documents(collection: str) -> list[dict]:
    """List indexed documents in a collection (deduplicated by filename)."""
    chroma = get_chroma()
    if chroma is None:
        return []

    col = chroma.get_or_create_collection(collection)
    existing = col.get()

    seen = {}
    for doc_id, meta in zip(existing["ids"], existing["metadatas"]):
        if not meta:
            continue
        fn = meta.get("filename", "")
        if fn not in seen:
            seen[fn] = {
                "filename": fn,
                "title": meta.get("title", fn),
                "type": meta.get("type", ""),
                "chunks": 1,
                "indexed_at": meta.get("indexed_at", ""),
            }
        else:
            seen[fn]["chunks"] += 1

    return sorted(seen.values(), key=lambda x: x["indexed_at"], reverse=True)


async def reindex_collection(collection: str, kb_dir: str | None = None) -> list[dict]:
    """Scan a KB folder and re-index all files. Returns list of indexing results."""
    base = Path(kb_dir) if kb_dir else KB_BASE_DIR / collection
    if not base.exists():
        return []

    results = []
    for file_path in base.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in {".txt", ".pdf", ".docx", ".md"}:
            try:
                result = await index_document(str(file_path), collection)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to index {file_path.name}: {e}")
                results.append({"filename": file_path.name, "error": str(e)})

    return results
