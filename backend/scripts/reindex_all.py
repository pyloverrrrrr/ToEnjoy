# -*- coding: utf-8 -*-
"""Reindex all KB documents from data/kb/ folders into ChromaDB with correct doc_types."""
import asyncio
import os
import sys
sys.path.insert(0, ".")

from app.db.chroma import init_chroma, get_chroma
from app.core.kb.indexer import index_document, KB_BASE_DIR

# Map filenames to doc_type for proper frontend filtering
PROFESSIONAL_TYPES = {
    # Guidelines (10)
    "高血压合理用药指南2024.txt": "guideline",
    "高血压基层诊疗指南2024.txt": "guideline",
    "心房颤动抗凝治疗专家共识.txt": "guideline",
    "糖尿病肾病诊治指南2025.txt": "guideline",
    "儿童社区获得性肺炎诊疗指南.txt": "guideline",
    "慢性阻塞性肺疾病GOLD2025.txt": "guideline",
    "质子泵抑制剂临床应用指南.txt": "guideline",
    "稳定性冠心病诊断与治疗指南.txt": "guideline",
    "2型糖尿病防治指南2025.txt": "guideline",
    "血脂异常管理指南2024.txt": "guideline",
    # Literature (6)
    "SGLT2抑制剂心血管获益RCT汇总.txt": "literature",
    "PD-1抑制剂不良反应管理Meta分析.txt": "literature",
    "新型口服抗凝药疗效比较网络Meta分析.txt": "literature",
    "二甲双胍心血管保护作用机制研究.txt": "literature",
    "GLP-1受体激动剂临床应用循证综述.txt": "literature",
    "强化降压与标准降压的RCT荟萃分析.txt": "literature",
    # Drug (6)
    "阿托伐他汀说明书.txt": "drug",
    "沙库巴曲缬沙坦说明书.txt": "drug",
    "氨氯地平说明书.txt": "drug",
    "二甲双胍说明书.txt": "drug",
    "瑞舒伐他汀说明书.txt": "drug",
    "缬沙坦说明书.txt": "drug",
}

PATIENT_TYPES = {
    "高血压患者日常生活指南.txt": "education",
    "糖尿病饮食控制手册.txt": "education",
    "冠心病术后康复指导手册.txt": "education",
    "常见药物服用注意事项.txt": "education",
    "体检报告怎么看.txt": "education",
    "脑卒中早期识别与急救.txt": "education",
    "骨质疏松预防与补钙指南.txt": "education",
    "孕期营养与保健知识.txt": "education",
}


async def reindex():
    await init_chroma()
    chroma = get_chroma()

    for collection, type_map in [
        ("kb_professional", PROFESSIONAL_TYPES),
        ("kb_patient", PATIENT_TYPES),
    ]:
        # Drop old collection so new embeddings dimension is auto-detected
        try:
            chroma.delete_collection(collection)
            print(f"Dropped old collection '{collection}'")
        except Exception:
            print(f"Collection '{collection}' did not exist, will be auto-created")

        kb_dir = KB_BASE_DIR / collection
        print(f"\n{'='*60}")
        print(f"Reindexing collection: {collection} ({kb_dir})")
        print(f"{'='*60}")

        if not kb_dir.exists():
            print(f"  Directory not found: {kb_dir}, skipping")
            continue

        for file_path in sorted(kb_dir.iterdir()):
            if file_path.suffix.lower() not in {".txt", ".pdf", ".docx", ".md"}:
                continue
            fn = file_path.name
            doc_type = type_map.get(fn, "literature")
            try:
                result = await index_document(
                    str(file_path), collection, doc_type=doc_type
                )
                print(f"  OK: [{doc_type}] {result['title']} ({result['chunks']} chunks)")
            except Exception as e:
                print(f"  FAILED: {fn} — {e}")

    print("\nReindex complete!")


if __name__ == "__main__":
    asyncio.run(reindex())
