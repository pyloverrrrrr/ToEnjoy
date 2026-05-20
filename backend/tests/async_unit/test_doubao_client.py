import base64
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.multimodal.doubao_client import DoubaoClient, get_doubao_client


class TestDoubaoClientInit:
    def test_uses_settings_by_default(self):
        client = DoubaoClient(api_key="sk-test", app_id="app-1")
        assert client.api_key == "sk-test"
        assert client.app_id == "app-1"

    def test_default_models(self):
        client = DoubaoClient(api_key="sk-test")
        assert client.stt_model == "paraformer-v1"
        assert client.tts_model == "cosyvoice-v3-flash"
        assert client.vision_model == "doubao-1.5-vision-pro-250328"

    def test_vision_model_can_override(self):
        client = DoubaoClient(api_key="sk-test", vision_model="custom-model")
        assert client.vision_model == "custom-model"

    def test_vision_endpoint_defaults_empty(self):
        client = DoubaoClient(api_key="sk-test")
        assert client.vision_endpoint == ""

    def test_auth_headers_without_app_id(self):
        client = DoubaoClient(api_key="sk-test")
        headers = client._ark_headers
        assert headers["Authorization"] == "Bearer sk-test"
        assert "x-app-id" not in headers

    def test_auth_headers_with_app_id(self):
        client = DoubaoClient(api_key="sk-test", app_id="app-1")
        headers = client._ark_headers
        assert headers["x-app-id"] == "app-1"


class TestDoubaoClientSTT:
    @pytest.mark.asyncio
    async def test_speech_to_text_sends_b64_audio(self):
        audio = b"\x00\x01\x02\x03"

        # Mock responses for the multi-step STT flow:
        # Step 1: file upload
        upload_resp = MagicMock()
        upload_resp.raise_for_status.return_value = None
        upload_resp.json.return_value = {"id": "file-abc123"}

        # Step 2: get file URL
        file_resp = MagicMock()
        file_resp.raise_for_status.return_value = None
        file_resp.json.return_value = {"url": "https://example.com/audio.wav"}

        # Step 3: submit transcription task
        task_resp = MagicMock()
        task_resp.raise_for_status.return_value = None
        task_resp.json.return_value = {"output": {"task_id": "task-xyz"}}

        # Step 4: poll — first SUCCEEDED
        poll_resp = MagicMock()
        poll_resp.raise_for_status.return_value = None
        poll_resp.json.return_value = {
            "output": {
                "task_status": "SUCCEEDED",
                "results": [{"transcription_url": "https://example.com/result.json"}],
            }
        }

        # Step 5: download transcription
        trans_resp = MagicMock()
        trans_resp.raise_for_status.return_value = None
        trans_resp.json.return_value = {
            "transcripts": [{"text": "患者头痛三天"}]
        }

        async def post_side_effect(*args, **kwargs):
            url = args[0] if args else kwargs.get("url", "")
            if "files" in url:
                return upload_resp
            if "asr/transcription" in url:
                return task_resp
            return MagicMock()

        client = DoubaoClient(api_key="sk-test")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(side_effect=post_side_effect)
            mock_client.get = AsyncMock(side_effect=lambda *a, **kw: {
                "https://dashscope.aliyuncs.com/api/v1/files/file-abc123": file_resp,
                "https://dashscope.aliyuncs.com/api/v1/tasks/task-xyz": poll_resp,
                "https://example.com/result.json": trans_resp,
            }.get(a[0], MagicMock()))
            mock_client_cls.return_value = mock_client

            result = await client.speech_to_text(audio, audio_format="wav")

        assert result == "患者头痛三天"


class TestDoubaoClientTTS:
    @pytest.mark.asyncio
    async def test_text_to_speech_returns_audio_bytes(self):
        audio_data = b"mp3-audio-bytes"
        # First response: JSON with audio URL (CosyVoice returns metadata, not audio directly)
        tts_json_resp = MagicMock()
        tts_json_resp.raise_for_status.return_value = None
        tts_json_resp.json.return_value = {
            "output": {"audio": {"url": "https://example.com/audio.mp3"}}
        }
        # Second response: actual audio download
        audio_resp = MagicMock()
        audio_resp.raise_for_status.return_value = None
        audio_resp.content = audio_data

        client = DoubaoClient(api_key="sk-test")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client

            mock_client.post.return_value = tts_json_resp
            mock_client.get.return_value = audio_resp
            mock_client_cls.return_value = mock_client

            result = await client.text_to_speech("你好", voice="zh_female_qingxin", speed=1.0)

        assert result == audio_data
        # Verify TTS request payload
        post_call = mock_client.post.call_args
        payload = post_call.kwargs["json"]
        assert payload["model"] == "cosyvoice-v3-flash"
        assert payload["input"]["text"] == "你好"
        assert payload["input"]["voice"] == "longxiaochun_v3"
        assert payload["input"]["format"] == "mp3"
        # Verify audio download
        mock_client.get.assert_called_once_with("https://example.com/audio.mp3")


class TestDoubaoClientOCR:
    @pytest.mark.asyncio
    async def test_ocr_image_sends_b64_image(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "血常规 白细胞: 5.2×10⁹/L"}}]
        }

        client = DoubaoClient(api_key="sk-test")
        img = b"\xff\xd8\xff\xe0"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            result = await client.ocr_image(img)

        assert "血常规" in result
        call_args = mock_client.post.call_args
        payload = call_args.kwargs["json"]
        assert payload["model"] == "doubao-1.5-vision-pro-250328"
        messages = payload["messages"]
        user_content = messages[0]["content"]
        assert user_content[0]["type"] == "image_url"
        assert "base64" in user_content[0]["image_url"]["url"]

    @pytest.mark.asyncio
    async def test_ocr_image_uses_endpoint_when_configured(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "血常规 白细胞: 5.2×10⁹/L"}}]
        }

        client = DoubaoClient(api_key="sk-test", vision_endpoint="ep-test123")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_resp
            mock_client_cls.return_value = mock_client

            await client.ocr_image(b"\xff\xd8\xff\xe0")

        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["model"] == "ep-test123"


class TestGetDoubaoClient:
    def test_returns_singleton(self):
        from app.core.multimodal import doubao_client as mod
        original = mod._doubao_client
        mod._doubao_client = None
        try:
            c1 = get_doubao_client()
            c2 = get_doubao_client()
            assert c1 is c2
        finally:
            mod._doubao_client = original
