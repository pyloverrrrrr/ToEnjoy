from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = "default"


class ChatHistoryItem(BaseModel):
    session_id: str
    first_message: str
    message_count: int
    last_message_at: str


class ChatHistoryResponse(BaseModel):
    items: list[ChatHistoryItem]
    page: int = 1
    page_size: int = 20
    total: int = 0


class ChatDetailMessage(BaseModel):
    id: int
    role: str
    content: str
    intent: str | None = None
    sources: dict | None = None
    created_at: str


class ChatDetailResponse(BaseModel):
    session_id: str
    messages: list[ChatDetailMessage]
