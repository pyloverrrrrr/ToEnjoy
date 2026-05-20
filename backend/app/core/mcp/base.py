from abc import ABC, abstractmethod

from app.schemas.mcp import ToolDefinition, ToolCallResponse
from app.config import settings


class BaseMCPModule(ABC):
    @property
    @abstractmethod
    def module_name(self) -> str:
        ...

    @property
    def timeout(self) -> float:
        return settings.mcp_default_timeout

    @abstractmethod
    def get_tools(self) -> list[ToolDefinition]:
        ...

    @abstractmethod
    async def execute(self, tool_name: str, params: dict) -> ToolCallResponse:
        ...

    def validate_params(self, tool_name: str, params: dict) -> None:
        pass
