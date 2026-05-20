from fastapi import APIRouter, Depends

from app.middleware.identity_router import get_request_context, RequestContext
from app.core.rag.query_processor import QueryProcessor
from app.core.rag.adaptive_router import AdaptiveRouter
from app.core.rag.hybrid_retriever import HybridRetriever
from app.core.rag.post_processor import PostProcessor
from app.core.rag.citation import annotate_citations
from app.schemas.search import SearchRequest, SearchResponse, SearchResultItem

router = APIRouter(prefix="/api/search", tags=["search"])

query_processor = QueryProcessor()
adaptive_router = AdaptiveRouter()
hybrid_retriever = HybridRetriever()
post_processor = PostProcessor()


@router.post("", response_model=SearchResponse)
async def search(req: SearchRequest, ctx: RequestContext = Depends(get_request_context)):
    processed = await query_processor.process(req.query, ctx.role)

    route = adaptive_router.route(ctx.role.value, processed.sub_queries)

    bm25_docs, vector_docs = await hybrid_retriever.search(
        query=processed.rewritten, collection=route.kb_collection, top_k=10
    )

    final_docs = await post_processor.process(bm25_docs, vector_docs, processed.rewritten, top_k=5)

    sources = annotate_citations(final_docs)

    results = [
        SearchResultItem(
            id=d.get("id", f"result_{i}"),
            title=d.get("metadata", {}).get("title", d.get("id", "Untitled")),
            content=d.get("content", ""),
            source_type=d.get("metadata", {}).get("type", "unknown"),
            score=d.get("rerank_score") or d.get("rrf_score", 0),
            source={
                "title": s.title,
                "type": s.source_type,
                "url": s.url,
                "evidence_level": s.evidence_level,
            },
        )
        for i, (d, s) in enumerate(zip(final_docs, sources))
    ]

    return SearchResponse(
        query=req.query,
        results=results,
        sources=[s.__dict__ for s in sources],
        total=len(results),
    )
