"""
本地 stdio MCP Server
由 xiaozhi-client 通过 xiaozhi.config.json 启动。
通过 stdin/stdout JSON-RPC 通信，HTTP 转发到 Bridge 实际执行。
"""

import asyncio
import json
import logging
import os
import sys
import uuid

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - local_mcp - %(levelname)s - %(message)s",
)
logger = logging.getLogger("local_mcp")

BRIDGE_URL = os.getenv("MINDBLOOM_BRIDGE_URL", "http://localhost:8001")
_server_info = {"name": "mindbloom-local", "version": "0.1.0"}


def _gen_id() -> int:
    return int(uuid.uuid4().int % 1000000)


def _respond(msg: dict):
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


async def _forward(method: str, params: dict) -> dict:
    """通过 HTTP 转发到 Bridge 实际执行。"""
    url = f"{BRIDGE_URL}/mcp/{method}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            if method in ("list_alarms",):
                resp = await client.get(url, params=params)
            else:
                resp = await client.post(url, json=params)
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"Bridge error: {resp.status_code}"}
    except Exception as e:
        logger.error(f"Bridge 转发失败: {e}")
        return {"error": str(e)}


async def handle_request(request: dict) -> dict:
    """处理一条 JSON-RPC 请求。"""
    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": _server_info,
            },
        }

    if method == "notifications/initialized":
        return {}

    if method == "tools/list":
        tools = [
            {
                "name": "create_alarm",
                "description": "创建本地闹钟，到时间会触发提醒音",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "闹钟名称"},
                        "time": {"type": "string", "description": "触发时间 (ISO 8601)"},
                        "reminderType": {"type": "string", "description": "提醒类型: sound(音乐)/manual(人工)"},
                    },
                    "required": ["name", "time"],
                },
            },
            {
                "name": "list_alarms",
                "description": "列出所有本地闹钟",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "delete_alarm",
                "description": "删除指定的闹钟",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "deleteId": {"type": "string", "description": "闹钟ID"},
                    },
                    "required": ["deleteId"],
                },
            },
            {
                "name": "toggle_alarm",
                "description": "启用或禁用闹钟",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "toggleId": {"type": "string", "description": "闹钟ID"},
                        "enabled": {"type": "boolean", "description": "true启用/false禁用"},
                    },
                    "required": ["toggleId", "enabled"],
                },
            },
            {
                "name": "speak",
                "description": "让小智立即说一句话",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "要说的文本"},
                    },
                    "required": ["text"],
                },
            },
        ]
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": tools},
        }

    if method == "tools/call":
        name = params.get("name", "")
        arguments = params.get("arguments", {})

        if name == "create_alarm":
            result = await _forward("create_alarm", arguments)
        elif name == "list_alarms":
            result = await _forward("list_alarms", arguments)
        elif name == "delete_alarm":
            result = await _forward("delete_alarm", arguments)
        elif name == "toggle_alarm":
            result = await _forward("toggle_alarm", arguments)
        elif name == "speak":
            result = await _forward("speak", arguments)
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"未知工具: {name}"},
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]},
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"未知方法: {method}"},
    }


async def main():
    """stdio 事件循环。"""
    logger.info("本地 MCP Server 启动 (stdin/stdout)")
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    buffer = ""
    while True:
        try:
            chunk = await reader.read(4096)
            if not chunk:
                break
            buffer += chunk.decode()

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    request = json.loads(line)
                    response = await handle_request(request)
                    if response:
                        _respond(response)
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON 解析失败: {e}")
                    _respond({"jsonrpc": "2.0", "error": {"code": -32700, "message": f"Parse error: {e}"}})
        except Exception as e:
            logger.error(f"读取 stdin 失败: {e}")
            break

    logger.info("本地 MCP Server 停止")


if __name__ == "__main__":
    asyncio.run(main())