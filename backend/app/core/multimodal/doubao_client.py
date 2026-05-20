import asyncio
import base64
import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DASHSCOPE_TTS_URL = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer"
DASHSCOPE_FILES_URL = "https://dashscope.aliyuncs.com/api/v1/files"
DASHSCOPE_ASR_URL = "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription"
DASHSCOPE_TASKS_URL = "https://dashscope.aliyuncs.com/api/v1/tasks"

TTS_VOICE_MAP = {
    "zh_female_qingxin": "longxiaochun_v3",
    "zh_male_qingxin": "longanyang",
}


class DoubaoClient:
    """多模态客户端 — OCR 用火山 ARK，TTS/STT 用 DashScope (阿里百炼)。"""

    def __init__(
        self,
        api_key: str = "",
        app_id: str = "",
        base_url: str = ARK_BASE_URL,
        stt_model: str = "paraformer-v1",
        tts_model: str = "cosyvoice-v3-flash",
        vision_model: str = "",
        vision_endpoint: str = "",
    ):
        self.api_key = api_key or settings.doubao_api_key
        self.app_id = app_id or settings.doubao_app_id
        self.base_url = base_url
        self.stt_model = stt_model
        self.tts_model = tts_model
        self.vision_model = vision_model or settings.doubao_vision_model
        self.vision_endpoint = vision_endpoint or settings.doubao_vision_endpoint

    @property
    def _ark_headers(self) -> dict:
        h = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.app_id:
            h["x-app-id"] = self.app_id
        return h

    @property
    def _dashscope_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {settings.dashscope_api_key}",
        }

    async def speech_to_text(self, audio_bytes: bytes, audio_format: str = "wav") -> str:
        """DashScope Paraformer 文件转写。

        Args:
            audio_bytes: 音频数据
            audio_format: 音频格式

        Returns:
            转写后的文本
        """
        content_type = f"audio/{audio_format}" if audio_format == "wav" else "audio/mpeg"
        ext = audio_format if audio_format in ("wav", "mp3") else "wav"

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Step 1: 上传文件
            files = {"file": (f"recording.{ext}", audio_bytes, content_type)}
            upload_resp = await client.post(
                DASHSCOPE_FILES_URL,
                headers={"Authorization": self._dashscope_headers["Authorization"]},
                data={"purpose": "assistants"},
                files=files,
            )
            upload_resp.raise_for_status()
            upload_data = upload_resp.json()
            file_id = upload_data.get("id") or upload_data.get("output", {}).get("uploaded_files", [{}])[0].get("file_id")
            if not file_id:
                logger.error(f"DashScope file upload unexpected response: {upload_data}")
                raise RuntimeError("Failed to upload audio file for transcription")

            # Step 2: 获取文件 URL
            file_resp = await client.get(
                f"{DASHSCOPE_FILES_URL}/{file_id}",
                headers=self._dashscope_headers,
            )
            file_resp.raise_for_status()
            file_data = file_resp.json()
            file_url = file_data.get("url") or file_data.get("output", {}).get("url", "")
            if not file_url:
                raise RuntimeError("Failed to get file URL for transcription")

            # Step 3: 提交转写任务
            task_payload = {
                "model": self.stt_model,
                "input": {"file_urls": [file_url]},
                "parameters": {"language_hints": ["zh", "en"]},
            }
            task_resp = await client.post(
                DASHSCOPE_ASR_URL,
                headers={**self._dashscope_headers, "Content-Type": "application/json"},
                json=task_payload,
            )
            task_resp.raise_for_status()
            task_data = task_resp.json()
            task_id = task_data.get("output", {}).get("task_id", "")

            # Step 4: 轮询等待完成
            for _ in range(30):
                poll_resp = await client.get(
                    f"{DASHSCOPE_TASKS_URL}/{task_id}",
                    headers=self._dashscope_headers,
                )
                poll_resp.raise_for_status()
                poll_data = poll_resp.json()
                status = poll_data.get("output", {}).get("task_status", "")
                if status == "SUCCEEDED":
                    results = poll_data.get("output", {}).get("results", [])
                    if results:
                        transcription_url = results[0].get("transcription_url", "")
                        if transcription_url:
                            trans_resp = await client.get(transcription_url)
                            trans_resp.raise_for_status()
                            trans_data = trans_resp.json()
                            transcripts = trans_data.get("transcripts", [])
                            if transcripts:
                                return transcripts[0].get("text", "")
                    return ""
                elif status == "FAILED":
                    logger.error(f"ASR task failed: {poll_data}")
                    return ""
                await asyncio.sleep(1)

            logger.warning("ASR task timed out")
            return ""

    async def _tts_url(self, text: str, voice: str = "zh_female_qingxin", speed: float = 1.0) -> str:
        """Get the OSS audio URL from DashScope CosyVoice (without downloading)."""
        dashscope_voice = TTS_VOICE_MAP.get(voice, "longanyang")
        payload = {
            "model": self.tts_model,
            "input": {
                "text": text,
                "voice": dashscope_voice,
                "format": "mp3",
                "speech_rate": speed,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                DASHSCOPE_TTS_URL,
                headers={**self._dashscope_headers, "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            audio_url = data.get("output", {}).get("audio", {}).get("url", "")
            if not audio_url:
                logger.error(f"CosyVoice TTS: no audio URL in response: {data}")
                raise RuntimeError("TTS response missing audio URL")
            return audio_url

    async def text_to_speech(
        self, text: str, voice: str = "zh_female_qingxin", speed: float = 1.0
    ) -> bytes:
        """DashScope CosyVoice TTS — downloads audio via OSS URL.

        Prefer returning the URL directly (use _tts_url + frontend streaming)
        to avoid backend proxy latency. This method is kept for offline/batch use.
        """
        audio_url = await self._tts_url(text, voice, speed)
        async with httpx.AsyncClient(timeout=30.0) as client:
            audio_resp = await client.get(audio_url)
            audio_resp.raise_for_status()
            return audio_resp.content

    async def ocr_image(self, image_bytes: bytes) -> str:
        """ARK 视觉模型 OCR。使用推理接入点或直接模型名。"""
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:image/png;base64,{b64}"

        model = self.vision_endpoint or self.vision_model

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url},
                        },
                        {
                            "type": "text",
                            "text": (
                                "请仔细识别并提取这份医学报告中的所有文字内容，"
                                "包括检查项目、检测结果、参考范围、异常标记等。"
                                "不要总结或解释，只输出原文内容。"
                            ),
                        },
                    ],
                }
            ],
            "max_tokens": 4096,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._ark_headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


_doubao_client: Optional[DoubaoClient] = None


def get_doubao_client() -> DoubaoClient:
    global _doubao_client
    if _doubao_client is None:
        _doubao_client = DoubaoClient()
    return _doubao_client
