import json
import logging
from typing import AsyncGenerator

import httpx
from app.config import settings
from app.core.model_adapter.base import BaseLLMAdapter

logger = logging.getLogger(__name__)

DASHSCOPE_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class DashScopeAdapter(BaseLLMAdapter):
    """阿里百炼 DashScope adapter for Qwen-Max (OpenAI-compatible API)."""

    @property
    def name(self) -> str:
        return "dashscope"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {settings.dashscope_api_key}",
            "Content-Type": "application/json",
        }

    def _build_body(self, messages: list[dict], temperature: float, max_tokens: int, stream: bool) -> dict:
        return {
            "model": "qwen-max",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

    async def generate(self, messages: list[dict[str, str]], temperature: float = 0.7, max_tokens: int = 2048) -> str:
        if not settings.dashscope_api_key:
            raise ConnectionError("DASHSCOPE_API_KEY not configured")
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{DASHSCOPE_BASE}/chat/completions",
                headers=self._headers(),
                json=self._build_body(messages, temperature, max_tokens, stream=False),
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def generate_stream(
        self, messages: list[dict[str, str]], temperature: float = 0.7, max_tokens: int = 2048
    ) -> AsyncGenerator[str, None]:
        if not settings.dashscope_api_key:
            raise ConnectionError("DASHSCOPE_API_KEY not configured")
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{DASHSCOPE_BASE}/chat/completions",
                headers=self._headers(),
                json=self._build_body(messages, temperature, max_tokens, stream=True),
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Use DashScope text-embedding-v3 (OpenAI-compatible endpoint)."""
        if not settings.dashscope_api_key:
            raise ConnectionError("DASHSCOPE_API_KEY not configured")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{DASHSCOPE_BASE}/embeddings",
                headers=self._headers(),
                json={
                    "model": "text-embedding-v3",
                    "input": texts,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]

    async def rerank(self, query: str, documents: list[str], top_n: int = 5) -> list[dict]:
        """Use DashScope Rerank API."""
        if not settings.dashscope_api_key:
            raise ConnectionError("DASHSCOPE_API_KEY not configured")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank",
                headers=self._headers(),
                json={
                    "model": "gte-rerank-v2",
                    "input": {
                        "query": query,
                        "documents": documents,
                    },
                    "parameters": {
                        "top_n": top_n,
                        "return_documents": False,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("output", {}).get("results", [])
            return [
                {"index": r["index"], "relevance_score": r["relevance_score"], "document": documents[r["index"]]}
                for r in sorted(results, key=lambda x: x["relevance_score"], reverse=True)[:top_n]
            ]
