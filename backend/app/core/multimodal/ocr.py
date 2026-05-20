import logging
from typing import AsyncGenerator

import app.core.multimodal.doubao_client
import app.core.model_adapter.adapter_registry

logger = logging.getLogger(__name__)

OCR_SYSTEM_PROMPT = (
    "你是一位资深的医学报告解读专家。请根据以下从患者报告中提取的原始文字，"
    "完成结构化的医学报告解读。\n\n"
    "请按以下格式输出 JSON：\n"
    '{{"summary": "报告概要（2-3句话）", '
    '"sections": [{{"title": "段落标题", "content": "该段落的解读或关键发现"}}], '
    '"abnormal_flags": ["异常指标1", "异常指标2"]}}\n\n'
    "注意：\n"
    "1. summary 用通俗易懂的语言概括报告核心结论\n"
    "2. sections 中保留原文的关键信息，同时给出临床解读\n"
    '3. abnormal_flags 列出所有标注为异常或超出参考范围的指标\n'
    "4. 只输出 JSON，不要有其他内容"
)


async def extract_text(file_bytes: bytes, mime_type: str = "image/png") -> str:
    """从医学报告图片/PDF中提取文字。

    Args:
        file_bytes: 文件字节流
        mime_type: MIME 类型

    Returns:
        提取的原始文本
    """
    client = app.core.multimodal.doubao_client.get_doubao_client()
    return await client.ocr_image(file_bytes)


async def interpret_report(extracted_text: str) -> dict:
    """对提取的报告文字进行结构化解读。

    Args:
        extracted_text: OCR提取的原始文字

    Returns:
        {"summary": str, "sections": [...], "abnormal_flags": [...]}
    """
    import json

    registry = app.core.model_adapter.adapter_registry.get_adapter_registry()
    prompt = f"以下是需要解读的医学报告内容：\n\n{extracted_text}"

    response = await registry.generate([
        {"role": "system", "content": OCR_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ])

    # 尝试清理 LLM 输出中可能的 markdown 代码块包装
    text = response.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse LLM JSON output, returning raw. Raw: {text[:200]}")
        return {
            "summary": extracted_text[:200],
            "sections": [],
            "abnormal_flags": [],
            "raw": text,
        }


async def interpret_report_stream(extracted_text: str) -> AsyncGenerator[dict, None]:
    """Stream LLM interpretation with progress events and token chunks.

    Yields:
        {"type": "progress", "phase": "llm", "message": "..."}
        {"type": "chunk", "content": "..."}
        {"type": "done", "result": {...}}
    """
    import json

    registry = app.core.model_adapter.adapter_registry.get_adapter_registry()
    prompt = f"以下是需要解读的医学报告内容：\n\n{extracted_text}"

    yield {"type": "progress", "phase": "llm", "message": "正在进行AI智能分析..."}

    full_text = ""
    async for token in registry.generate_stream([
        {"role": "system", "content": OCR_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]):
        full_text += token
        yield {"type": "chunk", "content": token}

    text = full_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(lines)

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse LLM JSON output. Raw: {text[:200]}")
        result = {
            "summary": extracted_text[:200],
            "sections": [],
            "abnormal_flags": [],
            "raw": text,
        }

    yield {"type": "done", "result": result}
