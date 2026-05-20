import json
import pytest
from unittest.mock import AsyncMock, patch
from app.core.memory.event_extractor import EventExtractor, ExtractedEvents


class TestEventExtractor:
    def test_extract_valid_json_parses_events(self):
        mock_adapter = AsyncMock()
        mock_adapter.generate.return_value = json.dumps({
            "symptoms": ["headache", "nausea"],
            "diagnosis": [],
            "medications": [],
            "allergies": [],
            "key_events": ["patient reports 3-day headache"],
        })

        with patch("app.core.memory.event_extractor.get_adapter_registry", return_value=mock_adapter):
            import asyncio
            extractor = EventExtractor()
            result = asyncio.run(extractor.extract("I have a headache", "You should rest"))

        assert result.symptoms == ["headache", "nausea"]
        assert result.diagnosis == []
        assert result.key_events == ["patient reports 3-day headache"]

    def test_extract_invalid_json_falls_back_to_empty(self):
        mock_adapter = AsyncMock()
        mock_adapter.generate.return_value = "not json at all {{{"

        with patch("app.core.memory.event_extractor.get_adapter_registry", return_value=mock_adapter):
            import asyncio
            extractor = EventExtractor()
            result = asyncio.run(extractor.extract("hello", "hi"))

        assert result.symptoms == []
        assert result.key_events == []

    def test_extract_merges_with_previous_events(self):
        mock_adapter = AsyncMock()
        mock_adapter.generate.return_value = json.dumps({
            "symptoms": ["cough"],
            "diagnosis": [],
            "medications": ["amoxicillin"],
            "allergies": [],
            "key_events": ["prescribed amoxicillin"],
        })

        previous = {
            "symptoms": ["fever"],
            "diagnosis": ["flu"],
            "medications": [],
            "allergies": ["penicillin"],
            "key_events": ["diagnosed with flu"],
        }

        with patch("app.core.memory.event_extractor.get_adapter_registry", return_value=mock_adapter):
            import asyncio
            extractor = EventExtractor()
            result = asyncio.run(extractor.extract("coughing", "take amoxicillin", previous))

        assert "fever" in result.symptoms
        assert "cough" in result.symptoms
        assert "penicillin" in result.allergies
        assert "flu" in result.diagnosis

    def test_extract_llm_failure_retries_once_then_empty(self):
        mock_adapter = AsyncMock()
        mock_adapter.generate.side_effect = Exception("API timeout")

        with patch("app.core.memory.event_extractor.get_adapter_registry", return_value=mock_adapter):
            import asyncio
            extractor = EventExtractor()
            result = asyncio.run(extractor.extract("test", "response"))

        assert result.symptoms == []
        assert mock_adapter.generate.call_count == 2

    def test_extract_json_in_code_fences_parses_correctly(self):
        mock_adapter = AsyncMock()
        mock_adapter.generate.return_value = "```json\n" + json.dumps({
            "symptoms": ["fever"],
            "diagnosis": [],
            "medications": [],
            "allergies": [],
            "key_events": ["temperature 38.5"],
        }) + "\n```"

        with patch("app.core.memory.event_extractor.get_adapter_registry", return_value=mock_adapter):
            import asyncio
            extractor = EventExtractor()
            result = asyncio.run(extractor.extract("fever", "take rest"))

        assert result.symptoms == ["fever"]

    def test_extract_type_corrupted_json_uses_defaults(self):
        mock_adapter = AsyncMock()
        mock_adapter.generate.return_value = json.dumps({
            "symptoms": "not_a_list",
            "diagnosis": None,
            "medications": 123,
            "allergies": [],
            "key_events": ["valid event"],
        })

        with patch("app.core.memory.event_extractor.get_adapter_registry", return_value=mock_adapter):
            import asyncio
            extractor = EventExtractor()
            result = asyncio.run(extractor.extract("test", "response"))

        assert result.symptoms == []  # string -> default
        assert result.diagnosis == []  # None -> default
        assert result.medications == []  # int -> default
        assert result.allergies == []  # valid empty list preserved
        assert result.key_events == ["valid event"]  # valid list preserved
