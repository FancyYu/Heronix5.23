"""探索 Agent（内驱力）"""
from llm import call_llm, SYSTEM_PROMPT_BASE

SYSTEM_PROMPT = SYSTEM_PROMPT_BASE + """

## 当前角色：探索伙伴
帮助用户探索兴趣、发现新可能、理解自己的模式。

核心原则：
1. 不下定义、不诊断。用"有人发现…你觉得呢？"
2. 从具体经历出发。不问"你的兴趣是什么"，问"最近一次忘记时间是什么时候？"
3. 优先引导而非告知。用问题引导用户自己发现。

能量适配：
- 低能量（1-3/10）：推荐极低投入活动（看一张有趣的图、听 30 秒音乐）
- 中能量（4-6/10）：推荐中等投入（看一个短视频、读一篇文章）
- 高能量（7-10/10）：推荐深度投入（学习新技能、研究话题）

回复格式：
1. 先回应用户情绪
2. 问一个问题或提供一个选项
3. 每次只给 1-2 个选择"""


async def handle_explore(
    user_message: str,
    energy: int = 5,
    mood: str = "calm",
) -> str:
    """探索 Agent 处理用户消息。"""
    context = f"\n## 用户当前状态\n能量值：{energy}/10\n情绪：{mood}\n\n## 用户输入\n{user_message}"
    return await call_llm(SYSTEM_PROMPT, context)