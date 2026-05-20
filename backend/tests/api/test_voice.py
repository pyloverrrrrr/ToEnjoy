import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_doubao():
    mock = MagicMock()
    mock.speech_to_text = AsyncMock(return_value="患者头痛三天，来院就诊。")
    mock._tts_url = AsyncMock(return_value="https://example.com/audio.mp3")
    return mock


class TestVoiceTranscribe:
    async def test_transcribe_returns_text(self, async_client, auth_token, mock_doubao):
        with patch("app.api.voice.get_doubao_client", return_value=mock_doubao):
            resp = await async_client.post(
                "/api/voice/transcribe",
                files={"file": ("test.wav", b"fake-audio-data", "audio/wav")},
                headers={"Authorization": f"Bearer {auth_token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["text"] == "患者头痛三天，来院就诊。"
        assert "duration_ms" in data

    async def test_transcribe_rejects_non_audio(self, async_client, auth_token):
        resp = await async_client.post(
            "/api/voice/transcribe",
            files={"file": ("test.txt", b"not audio", "text/plain")},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 400

    async def test_transcribe_requires_auth(self, async_client, mock_doubao):
        with patch("app.api.voice.get_doubao_client", return_value=mock_doubao):
            resp = await async_client.post(
                "/api/voice/transcribe",
                files={"file": ("test.wav", b"data", "audio/wav")},
            )
        assert resp.status_code == 403


class TestVoiceSynthesize:
    async def test_synthesize_returns_audio_url(self, async_client, auth_token, mock_doubao):
        with patch("app.api.voice.get_doubao_client", return_value=mock_doubao):
            resp = await async_client.post(
                "/api/voice/synthesize",
                json={"text": "您好，请按时服药。"},
                headers={"Authorization": f"Bearer {auth_token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["audio_url"] == "https://example.com/audio.mp3"

    async def test_synthesize_validates_text_length(self, async_client, auth_token, mock_doubao):
        with patch("app.api.voice.get_doubao_client", return_value=mock_doubao):
            resp = await async_client.post(
                "/api/voice/synthesize",
                json={"text": "a" * 2001},
                headers={"Authorization": f"Bearer {auth_token}"},
            )
        assert resp.status_code == 422

    async def test_synthesize_validates_speed_range(self, async_client, auth_token, mock_doubao):
        with patch("app.api.voice.get_doubao_client", return_value=mock_doubao):
            resp = await async_client.post(
                "/api/voice/synthesize",
                json={"text": "test", "speed": 3.0},
                headers={"Authorization": f"Bearer {auth_token}"},
            )
        assert resp.status_code == 422
