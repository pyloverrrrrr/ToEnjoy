import logging

from fastapi import APIRouter, Depends

from app.middleware.identity_router import get_request_context, RequestContext
from app.core.mcp.registry import get_mcp_registry
from app.schemas.mcp import ToolDefinition, ToolCallRequest, ToolCallResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


@router.get("/tools", response_model=list[ToolDefinition])
async def list_tools(ctx: RequestContext = Depends(get_request_context)):
    return get_mcp_registry().get_all_tools()


@router.post("/invoke", response_model=ToolCallResponse)
async def invoke_tool(
    req: ToolCallRequest,
    ctx: RequestContext = Depends(get_request_context),
):
    return await get_mcp_registry().invoke(req.tool, req.params)
