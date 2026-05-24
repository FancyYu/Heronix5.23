"""小智 MCP 硬件集成（Agent ↔ 小智双向通信）"""
import httpx
from config import XIAOZHI_BRIDGE_URL


async def speak(text: str) -> bool:
    """让小智说话（文本转语音）。"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                f"{XIAOZHI_BRIDGE_URL}/xiaozhi/speak",
                json={"text": text},
            )
            return resp.status_code == 200
    except Exception:
        return False


async def remind(user_id: str, text: str, remind_type: str = "system") -> bool:
    """主动推送提醒到小智硬件。"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                f"{XIAOZHI_BRIDGE_URL}/xiaozhi/remind",
                json={"text": text, "user_id": user_id, "remind_type": remind_type},
            )
            return resp.status_code == 200
    except Exception:
        return False


async def set_led(r: int = 0, g: int = 0, b: int = 0) -> bool:
    """设置小智 LED 颜色。"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                f"{XIAOZHI_BRIDGE_URL}/xiaozhi/led?r={r}&g={g}&b={b}",
            )
            return resp.status_code == 200
    except Exception:
        return False


async def get_status() -> dict:
    """获取小智设备状态。"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{XIAOZHI_BRIDGE_URL}/xiaozhi/status")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return {"connected": False}


async def test_connection() -> dict:
    """测试与小智 Bridge 的连接。"""
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{XIAOZHI_BRIDGE_URL}/health")
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "connected": data.get("xiaozhi_connected", False),
                    "bridge_ok": True,
                }
    except Exception:
        pass
    return {"connected": False, "bridge_ok": False}