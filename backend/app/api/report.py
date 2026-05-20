import json
import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, BackgroundTasks, Query
from fastapi.responses import JSONResponse, StreamingResponse

from app.config import settings
from app.middleware.identity_router import get_request_context, RequestContext
from app.schemas.report import ReportUploadResponse, ReportInterpretResponse, ReportSection
from app.core.multimodal.file_storage import upload_to_minio, get_from_minio
from app.core.multimodal.ocr import extract_text, interpret_report, interpret_report_stream
from app.models.conversation import Conversation
import app.db.session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/report", tags=["report"])

ALLOWED_MIMES = {
    "image/png", "image/jpeg", "image/jpg", "image/gif",
    "application/pdf",
}

MAX_FILE_SIZE = settings.max_upload_size_mb * 1024 * 1024


@router.post("/upload", response_model=ReportUploadResponse)
async def upload(
    file: UploadFile = File(...),
    ctx: RequestContext = Depends(get_request_context),
):
    """上传医学报告（图片或PDF），返回报告ID。"""
    if file.content_type not in ALLOWED_MIMES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file.content_type}。支持: {', '.join(sorted(ALLOWED_MIMES))}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"文件超过 {settings.max_upload_size_mb}MB 限制")

    object_path = await upload_to_minio(
        file_bytes,
        file.filename or "report.bin",
        prefix=f"user_{ctx.user_id}/",
    )
    report_id = object_path

    return ReportUploadResponse(
        report_id=report_id,
        filename=file.filename or "unknown",
        status="uploaded",
    )


@router.post("/interpret/{report_id:path}/stream")
async def interpret_stream(
    report_id: str,
    session_id: str | None = Query(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    ctx: RequestContext = Depends(get_request_context),
):
    """Stream report interpretation: OCR → LLM analysis with progress events."""
    if not report_id.startswith(f"user_{ctx.user_id}/"):
        raise HTTPException(status_code=403, detail="无权访问此报告")

    try:
        file_bytes = await get_from_minio(report_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"报告不存在: {report_id}") from e

    async def event_generator():
        yield f"data: {json.dumps({'type': 'progress', 'phase': 'ocr', 'message': '正在进行OCR文字识别...'}, ensure_ascii=False)}\n\n"
        try:
            raw_text = await extract_text(file_bytes)
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'OCR 识别失败: {e}'}, ensure_ascii=False)}\n\n"
            return

        full_result = None
        try:
            async for event in interpret_report_stream(raw_text):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event.get("type") == "done":
                    full_result = event.get("result")
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'报告解读失败: {e}'}, ensure_ascii=False)}\n\n"

        # Save report result to conversation history for persistence
        if full_result and session_id:
            try:
                async with app.db.session.async_session() as db:
                    content = json.dumps(full_result, ensure_ascii=False)
                    db.add(Conversation(
                        user_id=ctx.user_id,
                        session_id=session_id,
                        role="assistant",
                        content=content,
                        intent="report_interpretation",
                    ))
                    await db.commit()
            except Exception as e:
                logger.warning(f"Failed to save report result to conversation: {e}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/interpret/{report_id:path}", response_model=ReportInterpretResponse)
async def interpret(
    report_id: str,
    ctx: RequestContext = Depends(get_request_context),
):
    """解读指定报告：从 MinIO 取出 → OCR 提取文字 → LLM 结构化解读。"""
    if not report_id.startswith(f"user_{ctx.user_id}/"):
        raise HTTPException(status_code=403, detail="无权访问此报告")
    try:
        file_bytes = await get_from_minio(report_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"报告不存在或无法读取: {report_id}") from e

    try:
        raw_text = await extract_text(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OCR 识别失败: {e}") from e

    try:
        result = await interpret_report(raw_text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"报告解读失败: {e}") from e

    sections = [
        ReportSection(title=s.get("title", ""), content=s.get("content", ""))
        for s in result.get("sections", [])
    ]

    return ReportInterpretResponse(
        report_id=report_id,
        summary=result.get("summary", ""),
        sections=sections,
    )
