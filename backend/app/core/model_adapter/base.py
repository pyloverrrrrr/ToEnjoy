from abc import ABC, abstractmethod
from typing import AsyncGenerator


class BaseLLMAdapter(ABC):
    """Unified abstraction for LLM model adapters."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str: ...

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]: ...

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Default: raise if not implemented by subclass."""
        raise NotImplementedError(f"{self.name} does not support embedding")

    async def rerank(self, query: str, documents: list[str], top_n: int = 5) -> list[dict]:
        """Default: raise if not implemented by subclass."""
        raise NotImplementedError(f"{self.name} does not support reranking")
