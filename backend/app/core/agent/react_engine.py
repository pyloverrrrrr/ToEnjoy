import json
import logging
import re

from app.core.model_adapter.adapter_registry import get_adapter_registry
from app.core.agent.tool_router import ToolRouter
from app.schemas.agent import ReActStep, ReActResult

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 5

REACT_SYSTEM = """你是一个医疗AI助手，使用工具收集信息后回答用户问题。

## 回复格式（必须严格遵循）

思考: <分析当前情况，决定下一步需要什么信息>
行动: <工具名称>
行动输入: <JSON参数>

系统会返回"观察"结果。你可以重复 思考→行动→行动输入→观察 多轮。

当你收集到足够信息能够回答用户时，最后一轮使用 finish：

思考: <总结你收集到的信息>
行动: finish
行动输入: {{"summary": "<信息摘要>"}}

## 规则
1. 每轮只执行一个行动
2. 行动输入必须是单行JSON（不要换行）
3. 最多进行{max_iterations}轮
4. 简单问题1-2轮即可，先思考是否真的需要调用工具
5. 工具返回错误时，尝试其他方式或直接告知用户

{available_tools}"""


def _extract_section(text: str, tag: str) -> str:
    m = re.search(rf'^{tag}\s*[：:]\s*(.+)$', text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _parse_action_input(raw: str) -> dict:
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        return {}


class ReActEngine:
    """ReAct loop: Thought → Action → Observation → Thought ... → finish."""

    def __init__(self):
        self.tool_router = ToolRouter()

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    async def run(self, message: str, *, role: str = "patient",
                  user_id: int = 0, session_id: str = "",
                  memory_context: str | None = None) -> ReActResult:
        steps: list[ReActStep] = []
        adapter = get_adapter_registry()
        tools_text = self._build_tool_descriptions()
        system = REACT_SYSTEM.format(max_iterations=MAX_ITERATIONS, available_tools=tools_text)

        conversation = [{"role": "system", "content": system}]
        user_content = f"用户角色: {role}\n用户问题: {message}"
        if memory_context:
            user_content = f"{memory_context}\n\n{user_content}"
        conversation.append({"role": "user", "content": user_content})

        for i in range(MAX_ITERATIONS):
            raw = await adapter.generate(
                messages=conversation,
                temperature=0.3,
                max_tokens=1024,
            )
            raw = raw.strip()

            thought = _extract_section(raw, "思考")
            action = _extract_section(raw, "行动")
            action_input = _parse_action_input(_extract_section(raw, "行动输入"))

            if not action:
                logger.warning("ReAct iteration %d: no action found in LLM output", i + 1)
                steps.append(ReActStep(thought="无法解析LLM输出", action="finish",
                                        action_input={}, observation=raw))
                break

            if action == "finish":
                steps.append(ReActStep(thought=thought, action="finish",
                                        action_input=action_input, observation=""))
                break

            observation = await self.tool_router.execute(
                action, action_input,
                user_id=user_id, session_id=session_id,
                message=message, role=role,
            )

            steps.append(ReActStep(thought=thought, action=action,
                                    action_input=action_input, observation=observation))

            # Append assistant turn + observation for next iteration
            conversation.append({"role": "assistant", "content": raw})
            conversation.append({"role": "user", "content": f"观察: {observation}"})

        return ReActResult(steps=steps, iterations=len(steps))

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _build_tool_descriptions(self) -> str:
        from app.core.mcp.registry import get_mcp_registry

        lines = []

        registry = get_mcp_registry()
        for tool in registry.get_all_tools():
            lines.append(f"### {tool.name}")
            lines.append(tool.description)
            schema = tool.inputSchema.get("properties", {})
            required = tool.inputSchema.get("required", [])
            param_desc = {}
            for k, v in schema.items():
                desc = v.get("description", "")
                req = "必填" if k in required else "可选"
                param_desc[k] = f"{desc}({req})"
            lines.append(f"参数: {json.dumps(param_desc, ensure_ascii=False)}")
            lines.append("")

        lines.append("### memory.get_context")
        lines.append("读取用户的记忆上下文，包含历史对话和关键医疗事件。")
        lines.append("参数: {}")
        lines.append("")

        lines.append("### finish")
        lines.append("收集到足够信息后调用，结束信息收集阶段。")
        lines.append('参数: {"summary": "收集到的关键信息摘要"}')
        lines.append("")

        return "\n".join(lines)
