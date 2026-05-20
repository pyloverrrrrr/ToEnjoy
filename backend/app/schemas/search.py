from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    filters: dict | None = None


class SearchResultItem(BaseModel):
    id: str
    title: str
    content: str
    source_type: str
    score: float
    source: dict


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
    sources: list[dict]
    total: int
