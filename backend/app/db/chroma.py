from typing import Optional
import chromadb
from app.config import settings

chroma_client: Optional[chromadb.HttpClient] = None
EMBEDDING_DIM = 4096  # Qwen3-Embedding-8B dimension

COLLECTIONS = ["kb_patient", "kb_professional", "user_memory", "drug_db"]


async def init_chroma():
    global chroma_client
    chroma_client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
    existing = {c.name for c in chroma_client.list_collections()}
    for name in COLLECTIONS:
        if name not in existing:
            chroma_client.create_collection(name=name, metadata={"hnsw:space": "cosine"})


def get_chroma() -> chromadb.HttpClient:
    return chroma_client
