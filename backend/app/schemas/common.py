from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message_en: str
    message_zh: str
    details: dict | None = None


class Pagination(BaseModel):
    page: int = 1
    page_size: int = 20
    total: int = 0
