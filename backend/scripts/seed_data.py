# -*- coding: utf-8 -*-
"""Seed ChromaDB with test medical knowledge for MVP verification."""

import asyncio
import sys
sys.path.insert(0, ".")

from app.db.chroma import init_chroma, get_chroma

PATIENT_KB = [
    {
        "id": "patient_001",
        "content": "头痛是常见的临床症状，可能由多种原因引起。持续性头痛伴有恶心、呕吐时，建议前往神经内科就诊。常见的头痛类型包括偏头痛、紧张型头痛和丛集性头痛。就诊前请准备好既往病史记录，告知医生头痛的起止时间、疼痛性质（搏动性/钝痛/刺痛）、伴随症状等信息。",
        "metadata": {"title": "头痛症状与就诊指引", "type": "education", "source_type": "education"},
    },
    {
        "id": "patient_002",
        "content": "血常规是最常用的临床检验项目之一。白细胞（WBC）正常参考范围：4.0-10.0x10^9/L，升高常见于感染、炎症；红细胞（RBC）正常范围：男性4.0-5.5x10^12/L，女性3.5-5.0x10^12/L，降低常见于贫血；血小板（PLT）正常范围：100-300x10^9/L，减少可能导致出血倾向。本解读仅供参考，具体诊断请以医生意见为准。",
        "metadata": {"title": "血常规指标通俗解读", "type": "education", "source_type": "education"},
    },
    {
        "id": "patient_003",
        "content": "高血压是一种常见的慢性疾病，定义为收缩压>=140mmHg和/或舒张压>=90mmHg。确诊后应遵医嘱规律服药、定期监测血压、低盐饮食（每日食盐<6g）、适度运动（每周至少150分钟中等强度运动）。常用降压药包括：钙通道阻滞剂（如氨氯地平）、ACEI（如依那普利）、ARB（如缬沙坦）等。切忌自行停药或换药。",
        "metadata": {"title": "高血压日常管理指南", "type": "education", "source_type": "education"},
    },
    {
        "id": "patient_004",
        "content": "糖尿病是一种以高血糖为特征的代谢性疾病。2型糖尿病患者应遵循五驾马车治疗原则：饮食控制、运动疗法、药物治疗、血糖监测和健康教育。空腹血糖正常值：3.9-6.1mmol/L；餐后2小时血糖正常值：<7.8mmol/L。常见的口服降糖药包括二甲双胍、磺脲类、DPP-4抑制剂等。",
        "metadata": {"title": "糖尿病基础知识与日常管理", "type": "education", "source_type": "education"},
    },
    {
        "id": "patient_005",
        "content": "感冒（上呼吸道感染）的常见症状包括：鼻塞、流涕、咽喉疼痛、咳嗽、发热、头痛、全身酸痛等。普通感冒多为自限性疾病，一般7-10天可自愈。建议多休息、多饮水、保持室内通风。若发热超过38.5度可持续使用退烧药（如对乙酰氨基酚），但若高热持续3天以上不退或出现呼吸困难，应立即就医。",
        "metadata": {"title": "感冒症状与家庭护理", "type": "education", "source_type": "education"},
    },
]

PROFESSIONAL_KB = [
    {
        "id": "pro_001",
        "content": "2025年NCCN非小细胞肺癌（NSCLC）临床实践指南推荐：对于EGFR突变阳性的晚期NSCLC患者，一线治疗首选奥希替尼（Osimertinib），证据等级1类。对于PD-L1表达>=50%且无驱动基因突变的患者，帕博利珠单抗（Pembrolizumab）单药治疗为1类推荐。免疫联合化疗适用于PD-L1表达1-49%的患者。所有晚期NSCLC患者推荐进行全面的分子检测，包括EGFR、ALK、ROS1、BRAF、NTRK、MET、RET和PD-L1。",
        "metadata": {"title": "NCCN 2025 NSCLC免疫治疗推荐", "type": "guideline", "evidence_level": "A", "version": "2025.v3"},
    },
    {
        "id": "pro_002",
        "content": "二甲双胍在慢性肾脏病（CKD）患者中的剂量调整指南：eGFR>=45 mL/min/1.73m2时可使用常规剂量（最大2550mg/日）；eGFR 30-44 mL/min/1.73m2时减量至最大1000mg/日；eGFR<30 mL/min/1.73m2时禁用二甲双胍。老年患者（>=65岁）应定期监测肾功能（至少每年一次），若eGFR下降应及时调整剂量。二甲双胍不推荐用于eGFR<45的初治患者。",
        "metadata": {"title": "二甲双胍CKD剂量调整临床指南", "type": "guideline", "evidence_level": "A", "version": "2024"},
    },
    {
        "id": "pro_003",
        "content": "一项关于SGLT2抑制剂在射血分数保留的心力衰竭（HFpEF）患者中应用的Meta分析（纳入5项RCT，n=21,947）显示：SGLT2抑制剂可显著降低心血管死亡或心衰住院的复合终点（HR 0.80, 95%CI 0.74-0.87, P<0.001）。达格列净和恩格列净均表现出获益。亚组分析显示，无论基线是否使用ARNI或MRA，获益一致。",
        "metadata": {"title": "SGLT2抑制剂HFpEF应用Meta分析", "type": "literature", "evidence_level": "B", "pmid": "37632456"},
    },
    {
        "id": "pro_004",
        "content": "2024年ESC高血压管理指南更新要点：1）启动药物治疗的血压阈值降低至>=140/90mmHg（一般人群）；2）推荐目标血压<130/80mmHg（大多数患者）；3）首选联合治疗（单片复方制剂），包括ACEI/ARB+CCB+利尿剂的三联方案；4）推荐家庭血压监测和远程医疗辅助管理（I类推荐，A级证据）；5）对于顽固性高血压，可考虑去肾交感神经术（RDN）作为辅助治疗（IIb类推荐）。",
        "metadata": {"title": "ESC 2024高血压管理指南", "type": "guideline", "evidence_level": "A", "version": "2024"},
    },
    {
        "id": "pro_005",
        "content": "阿莫西林克拉维酸钾药品说明：适用于敏感菌引起的下呼吸道感染、中耳炎、鼻窦炎、尿路感染等。成人常规剂量：625mg（阿莫西林500mg+克拉维酸125mg），每8小时一次。严重感染可增至1g（阿莫西林875mg+克拉维酸125mg），每12小时一次。肾功能不全调整：CrCl 10-30mL/min时，给药间隔延长至12小时；CrCl<10mL/min时，间隔24小时。禁忌症：青霉素过敏史、传染性单核细胞增多症、肝功能异常史。常见不良反应：腹泻、恶心、皮疹。",
        "metadata": {"title": "阿莫西林克拉维酸钾说明书", "type": "drug", "version": "2024.12"},
    },
]


async def seed():
    await init_chroma()
    chroma = get_chroma()

    for collection_name, docs in [("kb_patient", PATIENT_KB), ("kb_professional", PROFESSIONAL_KB)]:
        col = chroma.get_collection(collection_name)
        existing = col.get()
        if existing["ids"]:
            print(f"Collection {collection_name} already has {len(existing['ids'])} docs, skipping seed.")
            continue

        col.add(
            ids=[d["id"] for d in docs],
            documents=[d["content"] for d in docs],
            metadatas=[d["metadata"] for d in docs],
        )
        print(f"Seeded {len(docs)} documents into {collection_name}")

    print("Seed complete!")


if __name__ == "__main__":
    asyncio.run(seed())
