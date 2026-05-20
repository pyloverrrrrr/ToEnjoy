import logging

from app.schemas.mcp import ToolDefinition, ToolCallResponse, ToolStatus
from app.core.mcp.base import BaseMCPModule
from app.core.rag.hybrid_retriever import HybridRetriever
from app.core.rag.post_processor import PostProcessor

logger = logging.getLogger(__name__)

_RAG_COLLECTION = {"doctor": "kb_professional", "patient": "kb_patient"}


class RagSearchModule(BaseMCPModule):

    def __init__(self):
        self.hybrid_retriever = HybridRetriever()
        self.post_processor = PostProcessor()

    @property
    def module_name(self) -> str:
        return "rag_search"

    def get_tools(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name="rag.search",
                description="搜索医学知识库，返回相关专业文献或科普内容",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索查询字符串"},
                    },
                    "required": ["query"],
                },
            ),
        ]

    async def execute(self, tool_name: str, params: dict) -> ToolCallResponse:
        query = params.get("query", "")
        if not query:
            return ToolCallResponse(
                tool=tool_name, status=ToolStatus.ERROR,
                error="参数错误: query 不能为空",
            )

        role = params.get("role", "patient")
        collection = _RAG_COLLECTION.get(role, "kb_professional")

        try:
            bm25_docs, vector_docs = await self.hybrid_retriever.search(
                query=query, collection=collection, top_k=10,
            )
            final_docs = await self.post_processor.process(
                bm25_docs, vector_docs, query, top_k=5,
            )

            if not final_docs:
                return ToolCallResponse(
                    tool=tool_name, status=ToolStatus.SUCCESS,
                    data={"query": query, "total": 0, "results": []},
                )

            results = []
            for doc in final_docs[:5]:
                content = doc.get("content", "")[:300]
                meta = doc.get("metadata", {})
                title = meta.get("title", "未命名文档")
                results.append({
                    "title": title,
                    "content": content,
                    "score": doc.get("score", 0),
                })

            return ToolCallResponse(
                tool=tool_name, status=ToolStatus.SUCCESS,
                data={"query": query, "total": len(results), "results": results},
            )

        except Exception as e:
            logger.error(f"RAG search failed: {e}", exc_info=True)
            return ToolCallResponse(
                tool=tool_name, status=ToolStatus.ERROR,
                error=f"知识库检索异常: {str(e)}",
            )
