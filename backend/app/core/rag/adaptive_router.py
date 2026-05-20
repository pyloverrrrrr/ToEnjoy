from dataclasses import dataclass
from enum import Enum


class SearchStrategy(str, Enum):
    DIRECT = "direct"
    SELF_RAG = "self_rag"


@dataclass
class RouteDecision:
    kb_collection: str
    strategy: SearchStrategy


class AdaptiveRouter:
    """Identity-aware routing: selects KB collection and search strategy."""

    def route(self, role: str, sub_queries: list[str]) -> RouteDecision:
        kb = "kb_professional" if role == "doctor" else "kb_patient"
        strategy = SearchStrategy.SELF_RAG if len(sub_queries) >= 2 else SearchStrategy.DIRECT
        return RouteDecision(kb_collection=kb, strategy=strategy)
