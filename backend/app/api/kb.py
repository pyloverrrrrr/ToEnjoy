import logging
import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.middleware.identity_router import get_request_context, RequestContext
from app.models.user import UserRole
from app.core.kb.indexer import index_document, delete_document, list_documents, reindex_collection, KB_BASE_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/kb", tags=["kb"])

SUPPORTED_MIMES = {
    "text/plain",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

COLLECTIONS = ["kb_professional", "kb_patient"]


class DocumentItem(BaseModel):
    filename: str
    title: str
    type: str
    chunks: int
    indexed_at: str


class IndexResult(BaseModel):
    filename: str
    title: str
    type: str
    collection: str
    chunks: int
    chunk_ids: list[str] = []


def _require_doctor(ctx: RequestContext):
    if ctx.role != UserRole.doctor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can manage knowledge base")


@router.post("/documents", status_code=status.HTTP_201_CREATED, response_model=IndexResult)
async def upload_document(
    file: UploadFile = File(...),
    collection: str = "kb_professional",
    doc_type: str | None = None,
    ctx: RequestContext = Depends(get_request_context),
):
    """Upload and index a document into the knowledge base. Document type is auto-detected if not provided."""
    _require_doctor(ctx)

    if collection not in COLLECTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid collection. Choose: {', '.join(COLLECTIONS)}")

    filename = file.filename or "document.bin"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {".txt", ".pdf", ".docx", ".md"}:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    # Save to local KB folder
    kb_dir = KB_BASE_DIR / collection
    kb_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex[:8]}_{filename}"
    file_path = kb_dir / safe_name

    file_bytes = await file.read()
    if len(file_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # Index into ChromaDB
    try:
        title = os.path.splitext(filename)[0]
        result = await index_document(str(file_path), collection, title=title, doc_type=doc_type)
        return IndexResult(**result)
    except Exception as e:
        # Clean up file on failure
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")


@router.get("/documents", response_model=list[DocumentItem])
async def list_kb_documents(
    collection: str = "kb_professional",
    ctx: RequestContext = Depends(get_request_context),
):
    """List indexed documents in a knowledge base collection."""
    doc_type_val = ctx.role.value if ctx.role else "patient"
    if collection not in COLLECTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid collection. Choose: {', '.join(COLLECTIONS)}")
    return list_documents(collection)


@router.delete("/documents/{filename:path}")
async def delete_kb_document(
    filename: str,
    collection: str = "kb_professional",
    ctx: RequestContext = Depends(get_request_context),
):
    """Delete a document from the knowledge base and its ChromaDB index."""
    _require_doctor(ctx)

    if collection not in COLLECTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid collection. Choose: {', '.join(COLLECTIONS)}")

    # Remove from ChromaDB
    deleted = await delete_document(filename, collection)

    # Remove from file system
    kb_dir = KB_BASE_DIR / collection
    for f in kb_dir.iterdir():
        if f.name.endswith(f"_{filename}") or f.name == filename:
            f.unlink()

    return {"deleted_chunks": deleted, "filename": filename}


@router.post("/reindex")
async def reindex(
    collection: str = "kb_professional",
    ctx: RequestContext = Depends(get_request_context),
):
    """Reindex all documents in a KB folder."""
    _require_doctor(ctx)

    if collection not in COLLECTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid collection. Choose: {', '.join(COLLECTIONS)}")

    results = await reindex_collection(collection)
    return {"collection": collection, "indexed": len([r for r in results if "error" not in r]), "results": results}
