from enum import Enum

from pydantic import BaseModel


class ToolStatus(str, Enum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"


class ToolDefinition(BaseModel):
    name: str
    description: str
    inputSchema: dict


class ToolCallRequest(BaseModel):
    tool: str
    params: dict = {}


class ToolCallResponse(BaseModel):
    tool: str
    status: ToolStatus
    data: dict | None = None
    error: str | None = None
