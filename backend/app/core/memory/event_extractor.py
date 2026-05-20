import asyncio
import json
import logging
from dataclasses import dataclass, field

from app.core.model_adapter.adapter_registry import get_adapter_registry

logger = logging.getLogger(__name__)

EXTRACT_PROMPT = """You are a medical event extraction expert. Extract key medical events from the conversation.

Output JSON format:
{
  "symptoms": ["symptom1", "symptom2"],
  "diagnosis": ["diagnosis1"],
  "medications": ["med1", "med2"],
  "allergies": ["allergy1"],
  "key_events": ["event summary 1", "event summary 2"]
}

Rules:
- Only extract events explicitly mentioned by the user
- symptoms: reported symptoms (headache, nausea, etc.)
- diagnosis: confirmed diagnoses only, not speculation
- medications: prescribed or mentioned medications
- allergies: known allergies
- key_events: 1-2 sentence summaries of important medical events in this conversation"""


@dataclass
class ExtractedEvents:
    symptoms: list[str] = field(default_factory=list)
    diagnosis: list[str] = field(default_factory=list)
    medications: list[str] = field(default_factory=list)
    allergies: list[str] = field(default_factory=list)
    key_events: list[str] = field(default_factory=list)


class EventExtractor:
    MAX_RETRIES = 1

    @staticmethod
    def _ensure_list(value, default=None) -> list[str]:
        if isinstance(value, list):
            return [str(v) for v in value]
        logger.warning(f"Unexpected type for extracted field: {type(value).__name__}")
        return default or []

    async def extract(
        self,
        user_message: str,
        assistant_response: str,
        previous_events: dict | None = None,
    ) -> ExtractedEvents:
        adapter = get_adapter_registry()
        conversation = f"User: {user_message}\nAssistant: {assistant_response}"

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                result = await adapter.generate(
                    messages=[
                        {"role": "system", "content": EXTRACT_PROMPT},
                        {"role": "user", "content": conversation},
                    ],
                    temperature=0.1,
                    max_tokens=256,
                )
                data = json.loads(result.strip().removeprefix("```json").removesuffix("```"))
                new_events = ExtractedEvents(
                    symptoms=self._ensure_list(data.get("symptoms", [])),
                    diagnosis=self._ensure_list(data.get("diagnosis", [])),
                    medications=self._ensure_list(data.get("medications", [])),
                    allergies=self._ensure_list(data.get("allergies", [])),
                    key_events=self._ensure_list(data.get("key_events", [])),
                )
                if previous_events:
                    return self._merge(new_events, previous_events)
                return new_events
            except Exception as e:
                logger.warning(f"Event extraction attempt {attempt + 1} failed: {e}")
                if attempt >= self.MAX_RETRIES:
                    break
                await asyncio.sleep(1 * attempt)
        return ExtractedEvents()

    def _merge(self, new_events: ExtractedEvents, previous_events: dict) -> ExtractedEvents:
        prev = ExtractedEvents(
            symptoms=previous_events.get("symptoms", []),
            diagnosis=previous_events.get("diagnosis", []),
            medications=previous_events.get("medications", []),
            allergies=previous_events.get("allergies", []),
            key_events=previous_events.get("key_events", []),
        )
        return ExtractedEvents(
            symptoms=list(set(prev.symptoms + new_events.symptoms)),
            diagnosis=list(set(prev.diagnosis + new_events.diagnosis)),
            medications=list(set(prev.medications + new_events.medications)),
            allergies=list(set(prev.allergies + new_events.allergies)),
            key_events=list(set(prev.key_events + new_events.key_events)),
        )
