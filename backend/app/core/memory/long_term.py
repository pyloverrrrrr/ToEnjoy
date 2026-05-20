import logging
import uuid

from app.db.chroma import get_chroma
from app.core.model_adapter.adapter_registry import get_adapter_registry
from app.core.memory.event_extractor import ExtractedEvents

logger = logging.getLogger(__name__)


class LongTermMemory:
    COLLECTION = "user_memory"

    async def search(self, query: str, user_id: int, top_k: int = 5) -> list[str]:
        try:
            adapter = get_adapter_registry()
            embeddings = await adapter.embed([query])
            chroma = get_chroma()
            if chroma is None:
                logger.warning("Long-term memory: ChromaDB not initialized")
                return []
            col = chroma.get_collection(self.COLLECTION)
            result = col.query(
                query_embeddings=embeddings,
                n_results=top_k,
                where={"user_id": user_id},
            )
            return result.get("documents", [[]])[0]
        except Exception as e:
            logger.warning(f"Long-term memory search failed: {e}")
            return []

    async def delete_by_user(self, user_id: int) -> None:
        try:
            chroma = get_chroma()
            if chroma is None:
                return
            col = chroma.get_collection(self.COLLECTION)
            try:
                col.delete(where={"user_id": user_id})
            except Exception:
                logger.warning("Long-term memory delete by user_id not supported by this ChromaDB version")
        except Exception as e:
            logger.warning(f"Long-term memory delete failed: {e}")

    async def save(self, user_id: int, events: ExtractedEvents) -> None:
        texts = events.key_events + events.symptoms + events.diagnosis + events.medications + events.allergies
        texts = [t for t in texts if t.strip()]
        if not texts:
            return

        try:
            adapter = get_adapter_registry()
            embeddings = await adapter.embed(texts)
            chroma = get_chroma()
            if chroma is None:
                logger.warning("Long-term memory: ChromaDB not initialized")
                return
            col = chroma.get_collection(self.COLLECTION)
            ids = [f"mem_{user_id}_{uuid.uuid4().hex[:12]}" for _ in texts]
            metadatas = [{"user_id": user_id, "type": "event"} for _ in texts]
            col.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)
        except Exception as e:
            logger.warning(f"Long-term memory save failed: {e}")
