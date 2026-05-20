from typing import AsyncGenerator

from app.core.model_adapter.adapter_registry import get_adapter_registry
from app.schemas.agent import ReActStep

PATIENT_SYSTEM = """你是医患双端服务平台智能医学助手，为患者提供通俗易懂的医学信息。

## 回答要求
1. 使用通俗语言，避免专业术语。若必须使用，请附带解释
2. 回答结构：逐项解读 → 综合小结 → 就医建议
3. 必须附加免责声明："本解读仅供参考，请以医生诊断为准"
4. 根据提供的知识库内容回答，不要编造医学信息
5. 每条关键建议标注引用来源编号，如 [1]、[2]
6. 当患者描述症状并询问应该就诊的科室时，使用 memory.get_context 获取患者画像和历史对话，
   结合症状信息推荐合适的科室，并提醒患者前往挂号页面挂号
7. 科室推荐参考：
   头痛/头晕→神经内科；胸闷/胸痛/心悸→心内科；咳嗽/发热/呼吸困难→呼吸内科；
   腹痛/胃痛/消化不良→消化内科；皮肤瘙痒/皮疹→皮肤科；关节痛/腰背痛→骨科；
   眼部不适→眼科；耳鼻喉症状→耳鼻喉科；妇科症状→妇产科；儿童疾病→儿科；
   泌尿症状→泌尿外科；血糖异常→内分泌科。
   推荐时简要说明理由（基于患者描述的症状）"""

DOCTOR_SYSTEM = """你是医患双端服务平台智能医学助手，为临床医生提供循证医学决策支持。

## 回答要求
1. 使用专业医学语言，简洁精准
2. 回答结构：推荐方案 → 证据等级 → 注意事项
3. 每条关键结论附带引用来源（文献PMID、指南条目编号、药品说明书版本）
4. 标注证据等级（指南推荐/Meta分析/RCT/专家共识等）
5. 仅根据提供的知识库内容回答，不确定处明确指出"""


class ResponseGenerator:
    async def generate(
        self,
        message: str,
        search_results: list[dict],
        role: str,
        sources: list[dict] | None = None,
        memory_context: str | None = None,
        react_steps: list[ReActStep] | None = None,
    ) -> AsyncGenerator[str, None]:
        adapter = get_adapter_registry()
        system = PATIENT_SYSTEM if role != "doctor" else DOCTOR_SYSTEM

        if memory_context:
            system = f"{system}\n\n## 用户历史上下文\n{memory_context}"

        # Build tool observation context from ReAct steps
        tool_context = self._build_tool_context(react_steps or [])

        context_parts = []
        if tool_context:
            context_parts.append(tool_context)

        for i, doc in enumerate(search_results[:5]):
            content = doc.get("content", "")
            meta = doc.get("metadata", {})
            src_title = meta.get("title", f"来源{i + 1}")
            context_parts.append(f"[{i + 1}] {src_title}\n{content}")

        context_text = "\n\n".join(context_parts) if context_parts else "暂无相关知识库结果"

        user_prompt = f"""## 知识库检索结果
{context_text}

## 用户问题
{message}

请根据上述信息回答用户问题："""

        async for chunk in adapter.generate_stream(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=2048,
        ):
            yield chunk

    def _build_tool_context(self, steps: list[ReActStep]) -> str:
        if not steps:
            return ""
        parts = ["## 工具调用结果"]
        for i, step in enumerate(steps):
            if step.action == "finish":
                continue
            parts.append(f"### {step.action}")
            parts.append(f"参数: {step.action_input}")
            parts.append(f"结果: {step.observation}")
            parts.append("")
        return "\n".join(parts) if len(parts) > 1 else ""
