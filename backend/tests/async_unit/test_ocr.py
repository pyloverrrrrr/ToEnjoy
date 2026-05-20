import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.core.multimodal.ocr import extract_text, interpret_report, OCR_SYSTEM_PROMPT


class TestExtractText:
    @pytest.mark.asyncio
    async def test_extract_text_calls_doubao_ocr(self):
        mock_client = MagicMock()
        mock_client.ocr_image = AsyncMock(return_value="血常规报告\n白细胞: 5.2")

        with patch("app.core.multimodal.doubao_client.get_doubao_client", return_value=mock_client):
            result = await extract_text(b"\xff\xd8", mime_type="image/jpeg")

        assert result == "血常规报告\n白细胞: 5.2"
        mock_client.ocr_image.assert_awaited_once_with(b"\xff\xd8")


class TestInterpretReport:
    @pytest.mark.asyncio
    async def test_interpret_report_parses_json_output(self):
        mock_registry = MagicMock()
        json_output = json.dumps({
            "summary": "血常规结果基本正常",
            "sections": [
                {"title": "白细胞", "content": "白细胞计数在正常范围内"}
            ],
            "abnormal_flags": [],
        })
        mock_registry.generate = AsyncMock(return_value=json_output)

        with patch("app.core.model_adapter.adapter_registry.get_adapter_registry", return_value=mock_registry):
            result = await interpret_report("白细胞: 5.2×10⁹/L")

        assert result["summary"] == "血常规结果基本正常"
        assert len(result["sections"]) == 1
        assert result["abnormal_flags"] == []

    @pytest.mark.asyncio
    async def test_interpret_report_passes_system_prompt(self):
        mock_registry = MagicMock()
        mock_registry.generate = AsyncMock(return_value='{"summary": "ok", "sections": [], "abnormal_flags": []}')

        with patch("app.core.model_adapter.adapter_registry.get_adapter_registry", return_value=mock_registry):
            await interpret_report("化验单内容")

        call_args = mock_registry.generate.call_args[0][0]
        assert call_args[0]["role"] == "system"
        assert call_args[0]["content"] == OCR_SYSTEM_PROMPT
        assert call_args[1]["role"] == "user"
        assert "化验单内容" in call_args[1]["content"]

    @pytest.mark.asyncio
    async def test_interpret_report_fallback_on_bad_json(self):
        mock_registry = MagicMock()
        mock_registry.generate = AsyncMock(return_value="这不是合法的 JSON 格式")

        with patch("app.core.model_adapter.adapter_registry.get_adapter_registry", return_value=mock_registry):
            result = await interpret_report("一些文字")

        assert result["summary"] == "一些文字"
        assert "raw" in result

    @pytest.mark.asyncio
    async def test_interpret_report_strips_markdown_code_block(self):
        mock_registry = MagicMock()
        json_output = '```json\n{"summary": "正常", "sections": [], "abnormal_flags": []}\n```'
        mock_registry.generate = AsyncMock(return_value=json_output)

        with patch("app.core.model_adapter.adapter_registry.get_adapter_registry", return_value=mock_registry):
            result = await interpret_report("正常报告")

        assert result["summary"] == "正常"
