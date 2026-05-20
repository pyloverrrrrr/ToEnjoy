# -*- coding: utf-8 -*-
"""Verify KB indexing — check document counts and sample queries."""
import asyncio
import sys
sys.path.insert(0, ".")

from app.db.chroma import init_chroma, get_chroma
from app.core.kb.indexer import list_documents
from app.core.model_adapter.adapter_registry import get_adapter_registry


async def verify():
    await init_chroma()
    chroma = get_chroma()
    adapter = get_adapter_registry()

    for collection in ["kb_professional", "kb_patient"]:
        docs = list_documents(collection)
        print(f"\n{'='*60}")
        print(f"Collection: {collection} ({len(docs)} documents)")
        print(f"{'='*60}")
        type_counts = {}
        for d in docs:
            t = d.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
            print(f"  [{d.get('type', '?')}] {d['title']} ({d['chunks']} chunks)")
        print(f"  Type breakdown: {type_counts}")

        # Test a sample query
        col = chroma.get_collection(collection)
        print(f"  Total chunks in collection: {col.count()}")

        # Test search
        query = "高血压用药" if collection == "kb_professional" else "高血压饮食"
        embeddings = await adapter.embed([query])
        result = col.query(query_embeddings=embeddings, n_results=3)
        print(f"  Sample query '{query}': top 3 =>")
        for i, (doc_id, meta) in enumerate(zip(result["ids"][0], result["metadatas"][0])):
            dist = result["distances"][0][i] if result["distances"] else "?"
            title = meta.get("title", "?") if meta else "?"
            print(f"    #{i+1}: [{title}] (distance: {dist})")

    # Verify seed data is gone
    print(f"\n{'='*60}")
    print("Seed data cleanup verification")
    print(f"{'='*60}")
    for collection in ["kb_professional", "kb_patient"]:
        col = chroma.get_collection(collection)
        all_ids = col.get()["ids"]
        seed_ids = [i for i in all_ids if i.startswith("patient_") or i.startswith("pro_")]
        status = "CLEAN" if not seed_ids else f"STILL HAS {len(seed_ids)} SEED IDS: {seed_ids}"
        print(f"  {collection}: {status}")

    print("\nVerification complete!")


if __name__ == "__main__":
    asyncio.run(verify())
