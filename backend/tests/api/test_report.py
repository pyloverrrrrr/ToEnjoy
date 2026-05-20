import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_doubao():
    mock = MagicMock()
    mock.ocr_image = AsyncMock(return_value="血常规 白细胞: 5.2×10⁹/L 参考范围: 3.5-9.5")
    return mock


@pytest.fixture
def mock_minio():
    with patch("app.api.report.upload_to_minio", new_callable=AsyncMock) as upload, \
         patch("app.api.report.get_from_minio", new_callable=AsyncMock) as download:
        upload.return_value = "2026/05/09/abc123_report.png"
        download.return_value = b"fake-png-data"
        yield upload, download


class TestReportUpload:
    async def test_upload_png(self, async_client, auth_token, mock_minio):
        resp = await async_client.post(
            "/api/report/upload",
            files={"file": ("blood_test.png", b"fake-png", "image/png")},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "blood_test.png"
        assert data["status"] == "uploaded"
        assert "report_id" in data

    async def test_upload_rejects_text_files(self, async_client, auth_token):
        resp = await async_client.post(
            "/api/report/upload",
            files={"file": ("doc.txt", b"text", "text/plain")},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 400
        assert "不支持" in resp.json()["detail"]

    async def test_upload_requires_auth(self, async_client):
        resp = await async_client.post(
            "/api/report/upload",
            files={"file": ("test.png", b"data", "image/png")},
        )
        assert resp.status_code == 403


class TestReportInterpret:
    async def test_interpret_returns_structured_result(self, async_client, auth_token, mock_minio, mock_doubao):
        mock_registry = MagicMock()
        import json
        mock_registry.generate = AsyncMock(return_value=json.dumps({
            "summary": "血常规结果正常",
            "sections": [{"title": "白细胞", "content": "白细胞计数正常"}],
            "abnormal_flags": [],
        }))

        with patch("app.core.multimodal.doubao_client.get_doubao_client", return_value=mock_doubao), \
             patch("app.core.model_adapter.adapter_registry.get_adapter_registry", return_value=mock_registry):
            resp = await async_client.post(
                "/api/report/interpret/user_1/2026/05/09/abc123_report.png",
                headers={"Authorization": f"Bearer {auth_token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"] == "血常规结果正常"
        assert len(data["sections"]) == 1
        assert "本解读由 AI 生成" in data["disclaimer"]

    async def test_interpret_nonexistent_report(self, async_client, auth_token, mock_doubao):
        with patch("app.core.multimodal.doubao_client.get_doubao_client", return_value=mock_doubao), \
             patch("app.api.report.get_from_minio", side_effect=Exception("not found")):
            resp = await async_client.post(
                "/api/report/interpret/user_1/nonexistent/report.pdf",
                headers={"Authorization": f"Bearer {auth_token}"},
            )

        assert resp.status_code == 404
