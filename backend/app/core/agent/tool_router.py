import json
import logging

from app.core.mcp.registry import get_mcp_registry
from app.core.memory.memory_service import MemoryService

logger = logging.getLogger(__name__)


class ToolRouter:
    """Dispatches tool calls from the ReAct engine to MCP / Memory."""

    def __init__(self):
        self.memory_service = MemoryService()

    async def execute(self, action: str, action_input: dict, *,
                      user_id: int = 0, session_id: str = "",
                      message: str = "", role: str = "patient") -> str:
        try:
            if action == "memory.get_context":
                return await self._memory_context(user_id, session_id, message)
            elif action == "finish":
                return ""
            else:
                return await self._mcp_invoke(action, {**action_input, "role": role})
        except Exception as e:
            logger.exception(f"Tool execution failed: {action}")
            return f"工具执行异常: {str(e)}"

    async def _mcp_invoke(self, action: str, params: dict) -> str:
        response = await get_mcp_registry().invoke(action, params)
        if response.status.value == "success":
            return json.dumps(response.data, ensure_ascii=False, indent=2)
        return f"MCP工具 '{action}' 返回错误: {response.error}"

    async def _memory_context(self, user_id: int, session_id: str, message: str) -> str:
        if user_id <= 0:
            return "用户未认证，无法读取记忆上下文"
        ctx = await self.memory_service.get_context(user_id, session_id, message)
        if ctx and ctx.formatted_prompt:
            return ctx.formatted_prompt
        return "暂无相关记忆上下文"
