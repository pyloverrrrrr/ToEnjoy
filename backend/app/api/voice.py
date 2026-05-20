import logging
import time

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.config import settings
from app.middleware.identity_router import get_request_context, RequestContext
from app.schemas.voice import VoiceTranscribeResponse, VoiceSynthesizeRequest, VoiceSynthesizeResponse
from app.core.multimodal.doubao_client import get_doubao_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])

MAX_AUDIO_SIZE = settings.max_upload_size_mb * 1024 * 1024


@router.post("/transcribe", response_model=VoiceTranscribeResponse)
async def transcribe(
    file: UploadFile = File(...),
    ctx: RequestContext = Depends(get_request_context),
):
    """上传音频文件，返回转写文本。"""
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="请上传音频文件")

    audio_bytes = await file.read()
    if len(audio_bytes) > MAX_AUDIO_SIZE:
        raise HTTPException(status_code=413, detail=f"文件超过 {settings.max_upload_size_mb}MB 限制")

    start = time.perf_counter()
    text = await get_doubao_client().speech_to_text(audio_bytes)
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    return VoiceTranscribeResponse(text=text, duration_ms=elapsed_ms)


@router.post("/synthesize", response_model=VoiceSynthesizeResponse)
async def synthesize(
    req: VoiceSynthesizeRequest,
    ctx: RequestContext = Depends(get_request_context),
):
    """文本合成语音，返回 DashScope OSS 音频 URL，前端直接拉取播放。"""
    audio_url = await get_doubao_client()._tts_url(
        text=req.text, voice=req.voice, speed=req.speed,
    )
    return VoiceSynthesizeResponse(audio_url=audio_url)
