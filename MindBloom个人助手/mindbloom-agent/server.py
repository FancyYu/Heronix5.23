"""MindBloom Agent · FastAPI 服务"""
import asyncio
import datetime
import httpx
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import BACKEND_URL, XIAOZHI_BRIDGE_URL
from intent import classify_intent
from agents.explore import handle_explore
from agents.initiate import handle_initiate
from agents.focus import handle_focus


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = asyncio.create_task(_reminder_scheduler())
    yield
    scheduler.cancel()


app = FastAPI(title="MindBloom Agent", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


# ── 数据模型 ──
class ChatRequest(BaseModel):
    user_id: str
    message: str
    task: str = ""


class ChatResponse(BaseModel):
    reply: str
    intent: str
    agent: str


class RemindRequest(BaseModel):
    user_id: str
    text: str
    remind_type: str = "system"


class ReminderCreate(BaseModel):
    user_id: str = "demo_user_001"
    text: str
    remind_at: str  # ISO 格式时间，如 "2026-05-24T10:00:00"
    remind_type: str = "task"


class XiaozhiInput(BaseModel):
    user_id: str
    text: str


# ── 定时提醒调度器 ──
reminders: list[dict] = []


async def _push_reminder(user_id: str, text: str, remind_type: str = "task"):
    """推送提醒到小智硬件。"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"{XIAOZHI_BRIDGE_URL}/xiaozhi/remind", json={
                "text": text,
                "user_id": user_id,
                "remind_type": remind_type,
            })
    except Exception:
        pass


async def _reminder_scheduler():
    """后台调度器：每 15 秒检查一次到期的提醒。"""
    while True:
        now = datetime.datetime.now()
        due = []
        for i, r in enumerate(reminders):
            if not r.get("fired"):
                remind_time = datetime.datetime.fromisoformat(r["remind_at"])
                if remind_time <= now:
                    due.append(i)
        for i in reversed(due):
            r = reminders[i]
            await _push_reminder(r["user_id"], r["text"], r.get("remind_type", "task"))
            r["fired"] = True
        await asyncio.sleep(15)


# ── 辅助函数 ──
async def _load_user(user_id: str) -> dict:
    """从后端加载用户画像。"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{BACKEND_URL}/users/{user_id}")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return {}


async def _load_latest_status(user_id: str) -> dict:
    """从后端加载最新状态。"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{BACKEND_URL}/status/{user_id}/latest")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return {}


async def _record_action(user_id: str, agent_type: str, action_type: str, content: str):
    """记录行为到后端。"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"{BACKEND_URL}/actions", json={
                "user_id": user_id,
                "agent_type": agent_type,
                "action_type": action_type,
                "content": content,
                "status": "active",
            })
    except Exception:
        pass


async def _record_status(user_id: str, energy: int = 5, mood: str = "calm",
                          focus: int = 5, sensory: str = "comfortable", ctx: str = "alone"):
    """更新用户状态到后端。"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"{BACKEND_URL}/status", json={
                "user_id": user_id,
                "energy_level": energy,
                "mood": mood,
                "focus_level": focus,
                "sensory_load": sensory,
                "context": ctx,
            })
    except Exception:
        pass


def _parse_status(s: dict) -> tuple:
    energy = s.get("energy_level", 5)
    mood = s.get("mood", "calm")
    focus = s.get("focus_level", 5)
    return energy, mood, focus


# ── Agent 路由 ──
AGENT_MAP = {
    "explore": ("探索伙伴", handle_explore, "exploration"),
    "initiate": ("启动伙伴", handle_initiate, "task_breakdown"),
    "focus": ("专注伙伴", handle_focus, "focus_session"),
}


async def _route_to_agent(intent: str, user_message: str, energy: int, mood: int, focus: int):
    """路由到对应 Agent 处理。"""
    if intent == "crisis":
        return (
            "我感受到了你现在很难受。你不需要一个人面对这些。\n\n"
            "以下资源可能对你有帮助：\n"
            "• 全国24小时心理援助热线：010-82951332\n"
            "• 希望24热线（北京）：400-161-9995\n\n"
            "你愿意让我帮你记下来，等你状态好一些再聊别的吗？"
        ), "crisis"

    agent_name, handler, action_type = AGENT_MAP.get(intent, AGENT_MAP["explore"])
    if intent == "focus":
        reply = await handler(user_message, energy=energy, focus=focus)
    else:
        reply = await handler(user_message, energy=energy, mood=mood)
    return reply, intent


# ── API 路由 ──
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """主聊天入口。用户发消息 → 意图识别 → Agent 处理 → 回复。"""
    user = await _load_user(req.user_id)
    status = await _load_latest_status(req.user_id)
    energy, mood, focus = _parse_status(status)

    intent = await classify_intent(req.message)
    reply, agent_used = await _route_to_agent(intent, req.message, energy, mood, focus)

    await _record_action(req.user_id, agent_used, intent, req.message[:100])
    await _record_status(req.user_id, energy=energy, mood=mood, focus=focus)

    return ChatResponse(reply=reply, intent=intent, agent=agent_used)


@app.post("/remind")
async def remind(req: RemindRequest):
    """主动提醒（供小智或其他定时任务调用）。"""
    from config import XIAOZHI_BRIDGE_URL
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.post(f"{XIAOZHI_BRIDGE_URL}/xiaozhi/remind", json={
                "text": req.text,
                "user_id": req.user_id,
                "remind_type": req.remind_type,
            })
            return {"ok": r.status_code == 200}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/xiaozhi/input")
async def xiaozhi_input(req: XiaozhiInput):
    """从小智收到语音输入 → 走 Agent 处理 → 让小智说出回复。"""
    chat_req = ChatRequest(user_id=req.user_id, message=req.text)
    result = await chat(chat_req)
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"{XIAOZHI_BRIDGE_URL}/xiaozhi/speak", json={
                "text": result.reply,
            })
    except Exception:
        pass
    return {"reply": result.reply, "intent": result.intent}


@app.get("/health")
def health():
    return {"status": "ok", "app": "MindBloom Agent", "version": "0.1.0"}


# ── 提醒管理 API ──
@app.post("/reminders")
async def create_reminder(req: ReminderCreate):
    """创建一条定时提醒（到时间后推送到小智）。"""
    reminder = {
        "id": str(uuid.uuid4())[:8],
        "user_id": req.user_id,
        "text": req.text,
        "remind_at": req.remind_at,
        "remind_type": req.remind_type,
        "fired": False,
    }
    reminders.append(reminder)
    return {"ok": True, "id": reminder["id"], "remind_at": req.remind_at}


@app.get("/reminders")
async def list_reminders(user_id: str = "demo_user_001"):
    """查看所有提醒。"""
    user_reminders = [r for r in reminders if r["user_id"] == user_id]
    return {"reminders": user_reminders}


@app.delete("/reminders/{reminder_id}")
async def delete_reminder(reminder_id: str):
    """删除一条提醒。"""
    for i, r in enumerate(reminders):
        if r["id"] == reminder_id:
            reminders.pop(i)
            return {"ok": True}
    raise HTTPException(status_code=404, detail="提醒不存在")