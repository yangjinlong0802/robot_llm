"""指令分类服务 — 使用 LLM 判断用户输入是否为机器人可执行指令。

返回格式: {"Instruction": str, "is_Instruction": bool}
"""

import json
import logging

logger = logging.getLogger(__name__)

_CLASSIFY_PROMPT = """\
判断用户输入是机器人动作指令还是普通对话，只输出纯JSON，不要任何其他内容。

判断规则：
- is_Instruction=true：移动、抓取、放置、转向、停止等可由机器人执行的动作
- is_Instruction=false：问候、闲聊、询问信息等无法由机器人执行的内容

输出格式（仅此格式，无其他内容）：
{"Instruction": "<用户指令>", "is_Instruction": true或false}

## 核心规则

输出的用户指令必须精确仅包含动作指令，避免包含额外的描述或解释。

示例：
用户：帮我抓瓶子 → {"Instruction": "抓瓶子", "is_Instruction": true}
用户：正在执行抓瓶子 → {"Instruction": "抓瓶子", "is_Instruction": true}
用户：前进两米 → {"Instruction": "前进两米", "is_Instruction": true}
用户：你好 → {"Instruction": "你好", "is_Instruction": false}
用户：今天天气怎么样 → {"Instruction": "今天天气怎么样", "is_Instruction": false}"""


async def classify_instruction(
    user_input: str,
    api_key: str = "",
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o-mini",
    enabled: bool = True,
) -> dict:
    """对用户输入进行指令分类。

    Args:
        user_input: 待分类的文本
        api_key: OpenAI 兼容 API Key（空则跳过分类，默认执行）
        base_url: API 基础 URL
        model: 使用的模型
        enabled: 是否启用分类；False 时直接返回 is_Instruction=True

    Returns:
        {"Instruction": str, "is_Instruction": bool}
        出错时 fallback 为 is_Instruction=True，避免指令被静默丢弃。
    """
    if not enabled or not api_key:
        return {"Instruction": user_input, "is_Instruction": True}

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        completion = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _CLASSIFY_PROMPT},
                {"role": "user", "content": user_input},
            ],
            temperature=0.1,
            max_tokens=100,
            response_format={"type": "json_object"},
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as exc:
        logger.warning("Ask 分类失败 (%s)，默认执行", exc)
        return {"Instruction": user_input, "is_Instruction": True}
