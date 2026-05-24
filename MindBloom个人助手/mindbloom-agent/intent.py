"""意图识别 Agent（LLM 路由）"""
from llm import call_intent_llm, SYSTEM_PROMPT_BASE


INTENT_SYSTEM_PROMPT = SYSTEM_PROMPT_BASE + """

## 当前任务：意图识别
根据用户输入，判断用户最需要的 Agent 类型。只输出标签本身，不要其他内容。

可选标签：
- **explore**：用户需要探索兴趣、推荐活动、寻找方向
- **initiate**：用户需要启动任务、克服拖延、拆解步骤
- **focus**：用户需要专注支持、管理注意力
- **crisis**：用户处于高风险状态（严重情绪崩溃、绝望、自伤暗示）

判断原则（按优先级）：
1. **crisis 仅限于明确的自伤/自杀/严重失控信号**，如明确提到想死、自伤、活不下去。单纯的累、疲惫、情绪低落不算 crisis
2. **initiate 优先于 explore**：用户提到动不了、拖延、卡住、不想动、有任务做不下去时，归为 initiate
3. **focus 仅在明确提到注意力/分心/学习/工作时**
4. 不确定时默认 explore"""

def _keyword_intent(msg: str) -> str:
    """无 API Key 时用关键词兜底判断意图。"""
    msg = msg.lower()
    if any(k in msg for k in ["崩溃", "活不下去", "绝望", "想死", "自伤", "自杀", "失控"]):
        return "crisis"
    if any(k in msg for k in ["无聊", "不知道做什么", "好奇", "想尝试", "迷茫", "兴趣", "探索"]):
        return "explore"
    if any(k in msg for k in ["动不了", "拖延", "卡住", "做不下去", "不想动", "怎么开始", "拆任务", "启动", "写不出来", "做不出来", "怎么办", "好累", "累了"]):
        return "initiate"
    if any(k in msg for k in ["分心", "走神", "专注", "学习", "集中", "番茄", "工作", "注意力"]):
        return "focus"
    return "explore"


async def classify_intent(user_message: str) -> str:
    """识别用户意图。LLM 优先，无 Key 时关键词兜底。"""
    from config import LLM_API_KEY
    if not LLM_API_KEY or not LLM_API_KEY.strip():
        return _keyword_intent(user_message)

    try:
        result = await call_intent_llm(INTENT_SYSTEM_PROMPT, user_message)
        result = result.strip().lower()
        for intent in ["explore", "initiate", "focus", "crisis"]:
            if intent in result:
                return intent
    except Exception:
        pass
    return _keyword_intent(user_message)