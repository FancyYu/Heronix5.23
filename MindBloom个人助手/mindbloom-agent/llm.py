"""LLM 调用封装"""
import httpx
from config import (
    LLM_API_KEY, LLM_BASE_URL, LLM_MODEL,
    LLM_MAX_TOKENS, LLM_TEMPERATURE, LLM_INTENT_TEMPERATURE,
)

SYSTEM_PROMPT_BASE = """你是 MindBloom，一位专为神经多样性人士设计的温暖 AI 伙伴。

沟通风格：
- 语气温和、不评判、不催促
- 语言简洁清晰，避免过长段落
- 使用适当的表情符号增加友好感
- 主动提供具体可操作的建议
- 对用户感受给予充分确认
- 将复杂信息拆解为小步骤
- 永远不说"你应该/必须"，改用"你可以/试试看"

回复格式：优先换行分段，用 • 列表代替长段文字。"""


async def call_llm(
    system_prompt: str,
    user_message: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """调用 LLM API，自动降级本地回复。"""
    if not LLM_API_KEY or not LLM_API_KEY.strip():
        return _get_fallback(user_message)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{LLM_BASE_URL}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {LLM_API_KEY}",
                },
                json={
                    "model": LLM_MODEL,
                    "messages": messages,
                    "max_tokens": max_tokens or LLM_MAX_TOKENS,
                    "temperature": temperature if temperature is not None else LLM_TEMPERATURE,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            return _get_fallback(user_message)
    except Exception as e:
        print(f"[LLM] API call failed: {e}")
        return _get_fallback(user_message)


async def call_intent_llm(system_prompt: str, user_message: str) -> str:
    """调用 LLM 做意图识别（低温度，短回复）。"""
    return await call_llm(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=LLM_INTENT_TEMPERATURE,
        max_tokens=64,
    )


def _get_fallback(user_message: str) -> str:
    """本地兜底回复。"""
    msg = user_message.lower()
    if any(k in msg for k in ["无聊", "不知道做什么", "好奇"]):
        return "听起来你现在可能有点不知道做什么好 🌿\n\n要不要试试这几件小事？\n• 听一首你很久没听的歌\n• 画一张随手涂鸦（不需要好看）\n• 看一个 3 分钟的趣味科普视频\n\n选一个最没压力的试试看？"
    if any(k in msg for k in ["动不了", "拖延", "卡住", "做不下去"]):
        return "启动确实是最难的一步 💪\n\n试试这个：\n1. 倒数 5-4-3-2-1\n2. 然后只做 2 分钟\n3. 2 分钟后可以停\n\n你现在能做的第一个最小动作是什么？"
    if any(k in msg for k in ["分心", "走神", "专注", "学习", "集中"]):
        return "注意力被拉走很正常的 🌿\n\n先试试：\n• 设置 5 分钟倒计时\n• 这 5 分钟只做一件事\n• 时间到了就站起来活动一下\n\n要不要先设定一个 5 分钟的番茄钟？"
    if any(k in msg for k in ["崩溃", "活不下去", "绝望"]):
        return "我感受到了你现在很难受。你不需要一个人面对这些。\n\n以下资源可能对你有帮助：\n• 全国 24 小时心理援助热线：010-82951332\n• 希望 24 热线：400-161-9995\n\n你愿意让我帮你记下来，等你状态好一些再聊别的吗？"
    return "谢谢你愿意跟我说这些 💚\n\n你的感受是有效的。有什么想聊聊的吗？"