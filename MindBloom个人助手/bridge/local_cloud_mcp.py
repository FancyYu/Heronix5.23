"""
本地 stdio MCP Server — 云端查询工具
由 xiaozhi-client 通过 xiaozhi.config.json 启动。
通过 stdin/stdout JSON-RPC 通信，HTTP 转发到 Bridge 实际执行（port 8001）。
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
    format="%(asctime)s - cloud_mcp - %(levelname)s - %(message)s",
)
logger = logging.getLogger("cloud_mcp")

BRIDGE_URL = os.getenv("MINDBLOOM_BRIDGE_URL", "http://localhost:8001")


def _respond(msg: dict):
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


async def _forward(name: str, arguments: dict) -> dict:
    """通过 HTTP 转发到 Bridge 的通用工具调用端点。"""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{BRIDGE_URL}/internal/tool/call",
                json={"name": name, "arguments": arguments},
            )
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"Bridge error: {resp.status_code}"}
    except Exception as e:
        logger.error(f"Bridge 转发失败: {e}")
        return {"error": str(e)}


async def handle_request(request: dict) -> dict:
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
                "serverInfo": {"name": "mindbloom-cloud", "version": "0.1.0"},
            },
        }

    if method == "notifications/initialized":
        return {}

    if method == "tools/list":
        tools = [
            {
                "name": "get_user_status",
                "description": "获取用户当前状态（能量/情绪/专注值）",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "用户标识，默认 demo_user_001"},
                    },
                },
            },
            {
                "name": "get_user_profile",
                "description": "获取用户档案信息",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "用户标识"},
                    },
                },
            },
            {
                "name": "get_recent_actions",
                "description": "获取用户的近期行为记录",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "用户标识"},
                        "limit": {"type": "integer", "description": "返回条数，默认5"},
                    },
                },
            },
            {
                "name": "get_interests",
                "description": "获取用户的兴趣/驱动模式",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "用户标识"},
                    },
                },
            },
            {
                "name": "get_focus_history",
                "description": "获取用户的专注历史记录",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "用户标识"},
                        "limit": {"type": "integer", "description": "返回条数，默认5"},
                    },
                },
            },
            {
                "name": "get_context",
                "description": "获取用户完整上下文（状态+档案+近期行为+待提醒事项），注意：如果有 pending_reminders 字段，请主动告知用户这些待办提醒",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "用户标识"},
                    },
                },
            },
            {
                "name": "create_reminder",
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
            {
                "name": "get_pending_speech",
                "description": "获取待播报的提醒或消息，适合在用户开始对话时调用",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "用户标识"},
                    },
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
        result = await _forward(name, arguments)
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
    logger.info("云端查询 MCP Server 启动 (stdin/stdout)")
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
    logger.info("云端查询 MCP Server 停止")


if __name__ == "__main__":
    asyncio.run(main())