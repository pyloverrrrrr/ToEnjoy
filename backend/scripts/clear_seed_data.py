# -*- coding: utf-8 -*-
"""Clear seed data from ChromaDB collections."""
import asyncio
import sys
sys.path.insert(0, ".")

from app.db.chroma import init_chroma, get_chroma

SEED_IDS = [
    "patient_001", "patient_002", "patient_003", "patient_004", "patient_005",
    "pro_001", "pro_002", "pro_003", "pro_004", "pro_005",
]


async def clear():
    await init_chroma()
    chroma = get_chroma()

    for collection_name in ["kb_patient", "kb_professional"]:
        col = chroma.get_collection(collection_name)
        existing = col.get()
        ids_to_delete = [doc_id for doc_id in existing["ids"] if doc_id in SEED_IDS]
        if ids_to_delete:
            col.delete(ids=ids_to_delete)
            print(f"Deleted {len(ids_to_delete)} seed docs from {collection_name}: {ids_to_delete}")
        else:
            print(f"No seed docs found in {collection_name}")

    print("Clear complete!")


if __name__ == "__main__":
    asyncio.run(clear())
