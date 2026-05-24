"""
MindBloom · 小智 MCP Bridge (纯 HTTP API)
本地闹钟 + 查询工具的后端服务。
xiaozhi-client 通过 stdio MCP 加载工具后统一注册到云端。
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from alarm_clock import AlarmClockManager

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mindbloom_bridge")

alarm_clock: Optional[AlarmClockManager] = None
AGENT_API = "http://localhost:8080"
BACKEND_API = "http://localhost:8000"
XIAOZHI_CLIENT_API = "http://localhost:9999"

_pending_speech: list[str] = []


# ---------- 模型 ----------
class SpeakRequest(BaseModel):
    text: str


class RemindRequest(BaseModel):
    text: str
    user_id: str = "demo_user_001"
    remind_type: str = "task"


class InputWebhook(BaseModel):
    text: str
    user_id: str = "demo_user_001"
    source: str = "xiaozhi"


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict = {}


# ---------- MCP 工具处理函数 ----------


async def tool_get_user_status(user_id: str = "demo_user_001") -> dict:
    """获取用户的当前状态（能量/情绪/专注值）。"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{BACKEND_API}/status/{user_id}/latest")
            return resp.json() if resp.status_code == 200 else {"status": "unknown"}
    except Exception as e:
        return {"error": str(e)}


async def tool_get_user_profile(user_id: str = "demo_user_001") -> dict:
    """获取用户档案信息。"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{BACKEND_API}/users/{user_id}")
            return resp.json() if resp.status_code == 200 else {"status": "unknown"}
    except Exception as e:
        return {"error": str(e)}


async def tool_get_recent_actions(user_id: str = "demo_user_001", limit: int = 5) -> dict:
    """获取用户的近期行为记录。"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{BACKEND_API}/actions/{user_id}/recent?limit={limit}")
            return {"actions": resp.json()} if resp.status_code == 200 else {"actions": []}
    except Exception as e:
        return {"error": str(e)}


async def tool_get_interests(user_id: str = "demo_user_001") -> dict:
    """获取用户的兴趣模式。"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{BACKEND_API}/interests/{user_id}")
            return {"interests": resp.json()} if resp.status_code == 200 else {"interests": []}
    except Exception as e:
        return {"error": str(e)}


async def tool_get_focus_history(user_id: str = "demo_user_001", limit: int = 5) -> dict:
    """获取用户的专注历史。"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{BACKEND_API}/focus_sessions/{user_id}/recent?limit={limit}")
            return {"sessions": resp.json()} if resp.status_code == 200 else {"sessions": []}
    except Exception as e:
        return {"error": str(e)}


async def tool_get_context(user_id: str = "demo_user_001") -> dict:
    """获取用户完整上下文（状态+档案+近期行为+待提醒事项），用于对话连续性。注意：如果有 pending_reminders 字段，请主动告知用户。"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            status_resp = await client.get(f"{BACKEND_API}/status/{user_id}/latest")
            user_resp = await client.get(f"{BACKEND_API}/users/{user_id}")
            actions_resp = await client.get(f"{BACKEND_API}/actions/{user_id}/recent?limit=3")
            reminders_resp = await client.get(f"{AGENT_API}/reminders?user_id={user_id}")
        result = {
            "status": status_resp.json() if status_resp.status_code == 200 else None,
            "user": user_resp.json() if user_resp.status_code == 200 else None,
            "recent_actions": actions_resp.json() if actions_resp.status_code == 200 else [],
        }
        if reminders_resp.status_code == 200:
            reminders_data = reminders_resp.json()
            pending = [r for r in reminders_data.get("reminders", []) if not r.get("fired")]
            if pending:
                result["pending_reminders"] = [
                    {"text": r["text"], "time": r["remind_at"]} for r in pending
                ]
        return result
    except Exception as e:
        return {"error": str(e)}


async def tool_create_reminder(text: str, user_id: str = "demo_user_001", remind_type: str = "task", remind_at: str = "") -> dict:
    """创建一条定时提醒（同时同步到本地闹钟）。"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(f"{AGENT_API}/reminders", json={
                "user_id": user_id,
                "text": text,
                "remind_at": remind_at,
                "remind_type": remind_type,
            })
            if resp.status_code == 200 and alarm_clock:
                if remind_at:
                    asyncio.create_task(alarm_clock.create_alarm(
                        name=text,
                        time=remind_at,
                        reminder_type="sound" if remind_type == "break" else "manual",
                    ))
                else:
                    logger.warning(f"create_reminder 未收到时间参数，跳过本地闹钟创建: {text}")
            return resp.json() if resp.status_code == 200 else {"error": "创建失败"}
    except Exception as e:
        return {"error": str(e)}


async def tool_get_pending_speech(user_id: str = "demo_user_001") -> dict:
    """获取待播报的提醒/消息。"""
    global _pending_speech
    if _pending_speech:
        text = _pending_speech.pop(0)
        return {"text": text, "remaining": len(_pending_speech)}
    return {"text": "", "remaining": 0}


# ---------- 生命周期 ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global alarm_clock

    alarm_clock = AlarmClockManager(agent_api=AGENT_API)
    await alarm_clock.start()
    logger.info("Bridge HTTP API 就绪（xiaozhi-client 负责云端连接）")
    yield

    await alarm_clock.stop()
    logger.info("Bridge 已停止")


app = FastAPI(
    title="MindBloom · 小智 Bridge",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- API 路由 ----------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "local_alarm_clock": alarm_clock is not None,
        "note": "xiaozhi-client 负责云端连接，见 http://localhost:9999",
    }


async def _xiaozhi_speak(text: str) -> bool:
    """通过 xiaozhi-client 的 API 让小智说话。"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                f"{XIAOZHI_CLIENT_API}/api/tts/speak",
                json={"text": text},
            )
            return resp.status_code == 200
    except Exception:
        pass
    return False


async def _xiaozhi_send_tts(text: str) -> bool:
    """尝试多种方式让小智说话。"""
    if await _xiaozhi_speak(text):
        return True
    logger.warning("xiaozhi-client 未就绪，消息加入待播报队列")
    _pending_speech.append(text)
    return False


@app.post("/xiaozhi/speak")
async def xiaozhi_speak(req: SpeakRequest):
    ok = await _xiaozhi_send_tts(req.text)
    return {"success": ok, "queued": not ok}


@app.post("/xiaozhi/remind")
async def xiaozhi_remind(req: RemindRequest):
    _pending_speech.append(req.text)
    ok = await _xiaozhi_send_tts(req.text)
    logger.info(f"提醒已处理: {req.text[:30]}...")
    return {"success": ok, "queued": True}


@app.post("/xiaozhi/input")
async def xiaozhi_input(req: InputWebhook):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{AGENT_API}/chat",
                json={"user_id": req.user_id, "message": req.text},
            )
            if resp.status_code == 200:
                result = resp.json()
                reply = result.get("reply", "")
                if reply:
                    await _xiaozhi_send_tts(reply)
                return {"success": True, "reply": reply, "intent": result.get("intent")}
            return {"success": False, "error": f"Agent error: {resp.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/alarm_clock/status")
async def alarm_clock_status():
    """查看本地闹钟状态。"""
    if not alarm_clock:
        return {"running": False}
    try:
        alarms = await alarm_clock.list_alarms()
        return {"running": True, "alarms_count": len(alarms), "alarms": alarms}
    except Exception as e:
        return {"running": True, "error": str(e)}


# ---------- 内部分发端点（由 local_cloud_mcp.py 调用）----------
@app.post("/internal/tool/call")
async def internal_tool_call(req: ToolCallRequest):
    """统一工具调用分发——由 local_cloud_mcp.py 通过 HTTP 调用。"""
    name = req.name
    args = req.arguments

    handler_map = {
        "get_user_status": tool_get_user_status,
        "get_user_profile": tool_get_user_profile,
        "get_recent_actions": tool_get_recent_actions,
        "get_interests": tool_get_interests,
        "get_focus_history": tool_get_focus_history,
        "get_context": tool_get_context,
        "create_reminder": tool_create_reminder,
        "get_pending_speech": tool_get_pending_speech,
    }

    handler = handler_map.get(name)
    if not handler:
        raise HTTPException(status_code=404, detail=f"未知工具: {name}")

    try:
        if asyncio.iscoroutinefunction(handler):
            result = await handler(**args)
        else:
            result = handler(**args)
        return result
    except Exception as e:
        logger.error(f"工具 {name} 调用失败: {e}")
        return {"error": str(e)}


# ---------- 本地 MCP 转发端点（由 local_stdio_mcp.py 调用）----------
@app.post("/mcp/create_alarm")
async def mcp_create_alarm(params: dict):
    if not alarm_clock:
        return {"error": "闹钟服务未就绪"}
    name = params.get("name", "提醒")
    alarm_time = params.get("time", "")
    reminder_type = params.get("reminderType", "sound")
    try:
        result = await alarm_clock.create_alarm(
            name=name,
            time=alarm_time,
            reminder_type=reminder_type,
        )
        asyncio.create_task(_save_reminder_to_db(
            text=name,
            remind_at=alarm_time,
            remind_type="break" if reminder_type == "sound" else "task",
        ))
        return {"success": True, "alarm": result}
    except Exception as e:
        return {"error": str(e)}


async def _save_reminder_to_db(text: str, remind_at: str, remind_type: str = "task", user_id: str = "demo_user_001"):
    """保存提醒到 Agent 数据库（静默执行，不阻塞调用方）。"""
    if not remind_at:
        logger.warning(f"提醒缺少时间，跳过存库: {text}")
        return
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"{AGENT_API}/reminders", json={
                "user_id": user_id,
                "text": text,
                "remind_at": remind_at,
                "remind_type": remind_type,
            })
            logger.info(f"提醒已存库: {text} @ {remind_at}")
    except Exception as e:
        logger.warning(f"提醒存库失败: {e}")


@app.get("/mcp/list_alarms")
async def mcp_list_alarms():
    if not alarm_clock:
        return {"error": "闹钟服务未就绪", "alarms": []}
    try:
        alarms = await alarm_clock.list_alarms()
        return {"alarms": alarms}
    except Exception as e:
        return {"error": str(e), "alarms": []}


@app.post("/mcp/delete_alarm")
async def mcp_delete_alarm(params: dict):
    if not alarm_clock:
        return {"error": "闹钟服务未就绪"}
    try:
        await alarm_clock.delete_alarm(params.get("deleteId", ""))
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@app.post("/mcp/toggle_alarm")
async def mcp_toggle_alarm(params: dict):
    if not alarm_clock:
        return {"error": "闹钟服务未就绪"}
    try:
        await alarm_clock.toggle_alarm(
            params.get("toggleId", ""),
            params.get("enabled", True),
        )
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


@app.post("/mcp/speak")
async def mcp_speak(params: dict):
    """让本地 MCP 触发说话——优先推送到小智，兜底 macOS 语音。"""
    text = params.get("text", "")
    if not text:
        return {"error": "缺少 text"}
    ok = await _xiaozhi_send_tts(text)
    if not ok:
        try:
            import subprocess
            subprocess.Popen(["say", text])
            return {"success": True, "via": "macos_say"}
        except Exception:
            pass
    return {"success": ok, "via": "xiaozhi_client" if ok else "macos_say"}


@app.get("/mcp/health")
async def mcp_health():
    return {
        "status": "ok",
        "alarm_clock_running": alarm_clock is not None,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)