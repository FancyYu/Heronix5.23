"""
小智 MCP Server
以 MCP Server 身份连接小智云端 Broker。
云端是 Client，我们是 Server——云端发现我们的工具并在用户说话时调用。
"""

import asyncio
import json
import logging
import ssl
import uuid
from typing import Any, Callable, Optional

import websockets

logger = logging.getLogger("xiaozhi_mcp")


def _gen_id() -> int:
    return int(uuid.uuid4().int % 1000000)


def _make_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


class XiaozhiMCPServer:
    """以小智 MCP Server 身份连接云端 Broker。

    协议流程：
      云端 → initialize → 我们回复 capabilities + serverInfo
      云端 → notifications/initialized
      云端 → tools/list     → 我们回复注册的工具列表
      云端 → tools/call     → 我们处理（调用 Agent）并回复结果
    """

    def __init__(
        self,
        ws_url: str = "ws://localhost:8002",
        reconnect_interval: int = 5,
    ):
        self.ws_url = ws_url
        self.reconnect_interval = reconnect_interval
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._connected = False
        self._listener_task: Optional[asyncio.Task] = None
        self._ready = asyncio.Event()
        self._tool_handlers: dict[str, Callable] = {}

    def register_tool(self, name: str, handler: Callable):
        """注册一个工具，云端可以通过 tools/call 调用。"""
        self._tool_handlers[name] = handler
        logger.info(f"注册工具: {name}")

    @property
    def connected(self) -> bool:
        return self._connected and self.ws is not None

    async def connect(self):
        """连接到小智云端，自动重连。"""
        ssl_ctx = _make_ssl_context() if self.ws_url.startswith("wss://") else None
        while True:
            try:
                logger.info(f"连接小智云端: {self.ws_url[:60]}...")
                self.ws = await websockets.connect(
                    self.ws_url,
                    ssl=ssl_ctx,
                    ping_interval=None,
                )
                self._connected = True
                self._ready.clear()
                logger.info("小智云端已连接，等待 MCP 握手...")

                self._listener_task = asyncio.create_task(self._listen())
                await self._ready.wait()
                logger.info("MCP Server 就绪，等待云端调用")

                await self._listener_task
            except Exception as e:
                logger.warning(f"连接断开: {e}, {self.reconnect_interval}s 后重连")
                self._connected = False
                self._ready.clear()
                await asyncio.sleep(self.reconnect_interval)

    async def _send_response(self, req_id: int, result: dict):
        """发送 JSON-RPC 响应。"""
        msg = {"jsonrpc": "2.0", "id": req_id, "result": result}
        await self.ws.send(json.dumps(msg, ensure_ascii=False))

    async def _send_error(self, req_id: int, code: int, message: str):
        """发送 JSON-RPC 错误。"""
        msg = {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": code, "message": message},
        }
        await self.ws.send(json.dumps(msg, ensure_ascii=False))

    async def _send_notification(self, method: str, params: dict | None = None):
        """发送 JSON-RPC 通知（无 id，无需回复）。"""
        msg = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        await self.ws.send(json.dumps(msg, ensure_ascii=False))

    async def send_speak(self, text: str):
        """主动让小智说话（通过 notification 方式推送）。"""
        await self._send_notification("notifications/speak", {"text": text})
        logger.info(f"已推送说话通知: {text[:30]}...")

    async def send_remind(self, text: str):
        """主动推送提醒到小智。"""
        await self._send_notification("notifications/remind", {"text": text})
        logger.info(f"已推送提醒: {text[:30]}...")

    async def send_led(self, r: int = 0, g: int = 0, b: int = 0):
        """推送 LED 颜色设置。"""
        await self._send_notification("notifications/led", {"r": r, "g": g, "b": b})

    def _get_tools_list(self) -> list[dict]:
        """生成注册的工具列表（符合 MCP 格式）。"""
        tool_schemas = {
            "get_user_status": {
                "description": "获取用户当前状态（能量/情绪/专注值）",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "用户标识，默认 demo_user_001"},
                    },
                },
            },
            "get_user_profile": {
                "description": "获取用户档案信息",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "用户标识"},
                    },
                },
            },
            "get_recent_actions": {
                "description": "获取用户的近期行为记录",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "用户标识"},
                        "limit": {"type": "integer", "description": "返回条数，默认5"},
                    },
                },
            },
            "get_interests": {
                "description": "获取用户的兴趣/驱动模式",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "用户标识"},
                    },
                },
            },
            "get_focus_history": {
                "description": "获取用户的专注历史记录",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "用户标识"},
                        "limit": {"type": "integer", "description": "返回条数，默认5"},
                    },
                },
            },
            "get_context": {
                "description": "获取用户完整上下文（状态+档案+近期行为+待提醒事项），用于对话连续性。注意：如果有 pending_reminders 字段，请主动告知用户这些待办提醒",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "用户标识"},
                    },
                },
            },
            "create_reminder": {
                "description": "创建一条定时提醒",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "提醒内容"},
                        "user_id": {"type": "string", "description": "用户标识"},
                        "remind_type": {"type": "string", "description": "提醒类型: task/break/medication/water/custom"},
                        "remind_at": {"type": "string", "description": "提醒时间 ISO 格式，如 2026-05-24T10:00:00"},
                    },
                    "required": ["text"],
                },
            },
            "get_pending_speech": {
                "description": "获取待播报的提醒或消息，适合在用户开始对话时调用，让用户不会错过重要提醒",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "用户标识"},
                    },
                },
            },
        }
        tools = []
        for name in self._tool_handlers:
            schema = tool_schemas.get(name, {
                "description": f"工具 {name}",
                "inputSchema": {"type": "object", "properties": {}},
            })
            tools.append({"name": name, **schema})
        return tools

    async def _handle_initialize(self, req_id: int, params: dict):
        """处理 initialize 请求。"""
        logger.info(f"收到 initialize")
        await self._send_response(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "mindbloom-agent", "version": "0.1.0"},
        })
        logger.info("已回复 initialize")

    async def _handle_tools_list(self, req_id: int):
        """处理 tools/list 请求——返回注册的工具。"""
        tools = self._get_tools_list()
        logger.info(f"收到 tools/list，回复 {len(tools)} 个工具")
        await self._send_response(req_id, {"tools": tools})

    async def _handle_tools_call(self, req_id: int, params: dict):
        """处理 tools/call 请求——调用对应的处理函数。"""
        name = params.get("name", "")
        arguments = params.get("arguments", {})
        logger.info(f"收到 tools/call: {name}")

        handler = self._tool_handlers.get(name)
        if not handler:
            await self._send_error(req_id, -32601, f"工具不存在: {name}")
            return

        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**arguments)
            else:
                result = handler(**arguments)
            await self._send_response(req_id, {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]})
            logger.info(f"{name} 执行成功")
        except Exception as e:
            logger.error(f"{name} 执行失败: {e}")
            await self._send_error(req_id, -32603, str(e))

    async def _listen(self):
        """持续监听 WebSocket 消息。"""
        try:
            async for raw in self.ws:
                try:
                    data = json.loads(raw)
                    method = data.get("method", "")
                    req_id = data.get("id")
                    is_notification = method.startswith("notifications/")

                    if method == "initialize" and req_id is not None:
                        await self._handle_initialize(req_id, data.get("params", {}))
                    elif method == "tools/list" and req_id is not None:
                        await self._handle_tools_list(req_id)
                    elif method == "tools/call" and req_id is not None:
                        await self._handle_tools_call(req_id, data.get("params", {}))
                    elif is_notification:
                        if method == "notifications/initialized":
                            logger.info("收到 initialized，注册完成")
                            self._ready.set()
                        else:
                            logger.debug(f"通知: {method}")
                    elif "result" in data or "error" in data:
                        logger.debug(f"响应: id={req_id}")
                    else:
                        logger.debug(f"未处理消息: method={method}")
                except json.JSONDecodeError:
                    logger.warning(f"非 JSON 消息: {raw[:100]}")
        except websockets.ConnectionClosed:
            logger.warning("WebSocket 连接关闭")
            self._connected = False
            self._ready.clear()

    async def disconnect(self):
        """断开连接。"""
        self._connected = False
        self._ready.clear()
        if self._listener_task:
            self._listener_task.cancel()
        if self.ws:
            await self.ws.close()