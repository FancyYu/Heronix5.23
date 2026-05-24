"""
本地闹钟管理器
包装 mcp-alarm-clock (Node.js stdio MCP)，与网页提醒双向同步。
"""

import asyncio
import json
import logging
import os
import subprocess
from typing import Any, Optional

import httpx

logger = logging.getLogger("alarm_clock")

ALARM_CLOCK_DIR = os.path.join(os.path.dirname(__file__), "node_modules", "mcp-alarm-clock")
ALARMS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "alarms.json")


class AlarmClockManager:
    """管理 mcp-alarm-clock 进程，同步网页提醒到本地闹钟。"""

    def __init__(self, agent_api: str = "http://localhost:8080"):
        self.agent_api = agent_api
        self._process: Optional[subprocess.Popen] = None
        self._running = False
        self._pending_responses: dict[int, asyncio.Future] = {}
        self._req_id = 0
        self._bg_tasks: list[asyncio.Task] = []

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    async def start(self):
        """启动 mcp-alarm-clock 子进程。"""
        cli_path = os.path.join(ALARM_CLOCK_DIR, "bin", "cli.js")
        if not os.path.exists(cli_path):
            logger.error(f"mcp-alarm-clock 未找到: {cli_path}")
            return

        self._process = await asyncio.create_subprocess_exec(
            "node", cli_path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._running = True
        logger.info("mcp-alarm-clock 进程已启动")

        self._bg_tasks.append(asyncio.create_task(self._read_stdout()))
        self._bg_tasks.append(asyncio.create_task(self._read_stderr()))
        self._bg_tasks.append(asyncio.create_task(self._sync_loop()))

        await asyncio.sleep(1)

    async def _send_request(self, method: str, params: dict | None = None) -> Any:
        """通过 stdin 发送 JSON-RPC 请求，等待响应。"""
        if not self._process or not self._process.stdin:
            raise ConnectionError("mcp-alarm-clock 未运行")

        req_id = self._next_id()
        msg = {"method": method, "params": params or {}}
        msg_str = json.dumps(msg, ensure_ascii=False) + "\n"

        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_responses[req_id] = future

        try:
            self._process.stdin.write(msg_str.encode())
            await self._process.stdin.drain()
            result = await asyncio.wait_for(future, timeout=10)
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"{method} 响应超时")
        finally:
            self._pending_responses.pop(req_id, None)

    async def _read_stdout(self):
        """读取 stdout，解析 JSON 响应和闹钟触发消息。"""
        while self._running and self._process and self._process.stdout:
            try:
                line = await asyncio.wait_for(
                    self._process.stdout.readline(), timeout=30
                )
                if not line:
                    break
                text = line.decode().strip()
                if not text:
                    continue

                if text.startswith("{"):
                    try:
                        data = json.loads(text)
                        if "result" in data or "error" in data:
                            for fut in self._pending_responses.values():
                                if not fut.done():
                                    if "result" in data:
                                        fut.set_result(data["result"])
                                    else:
                                        fut.set_exception(
                                            Exception(f"Alarm error: {data['error']}")
                                        )
                                    break
                    except json.JSONDecodeError:
                        pass

                if "⏰" in text:
                    alarm_name = text.split(":")[-1].strip() if ":" in text else text
                    logger.info(f"🎯 本地闹钟触发: {alarm_name}")
                    asyncio.create_task(self._on_alarm_fired(alarm_name))

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"读取 stdout 失败: {e}")
                break

    async def _read_stderr(self):
        """读取 stderr 日志。"""
        while self._running and self._process and self._process.stderr:
            try:
                line = await asyncio.wait_for(
                    self._process.stderr.readline(), timeout=30
                )
                if not line:
                    break
                text = line.decode().strip()
                if text:
                    logger.debug(f"[mcp-alarm] {text}")
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

    async def create_alarm(self, name: str, time: str, reminder_type: str = "sound") -> dict:
        """创建本地闹钟。"""
        result = await self._send_request("createAlarm", {
            "name": name,
            "time": time,
            "reminderType": reminder_type,
        })
        logger.info(f"本地闹钟已创建: {name} @ {time}")
        return result

    async def list_alarms(self) -> list:
        """列出所有闹钟。"""
        return await self._send_request("listAlarms")

    async def delete_alarm(self, alarm_id: str) -> bool:
        """删除闹钟。"""
        return await self._send_request("deleteAlarm", {"deleteId": alarm_id})

    async def toggle_alarm(self, alarm_id: str, enabled: bool) -> bool:
        """启用/禁用闹钟。"""
        return await self._send_request("toggleAlarm", {
            "toggleId": alarm_id,
            "enabled": enabled,
        })

    async def _on_alarm_fired(self, alarm_name: str):
        """本地闹钟触发时的回调——推送提醒到小智 + macOS 语音播报。"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(
                    "http://localhost:8001/xiaozhi/speak",
                    json={"text": f"🌿 MindBloom 提醒：{alarm_name}"},
                )
        except Exception:
            pass
        try:
            import subprocess
            subprocess.Popen(["say", f"Mind Bloom 提醒：{alarm_name}"])
        except Exception:
            pass
        logger.info(f"闹钟触发已推送: {alarm_name}")

    async def _sync_loop(self):
        """定期同步网页提醒到本地闹钟（每 30 秒）。"""
        await asyncio.sleep(5)
        while self._running:
            try:
                await self._sync_from_web()
            except Exception as e:
                logger.warning(f"同步失败: {e}")
            await asyncio.sleep(30)

    async def _sync_from_web(self):
        """从 Agent 拉取未触发的提醒，同步到本地闹钟。"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    f"{self.agent_api}/reminders?user_id=demo_user_001"
                )
                if resp.status_code != 200:
                    return
                data = resp.json()
                web_reminders = [r for r in data.get("reminders", []) if not r.get("fired")]
        except Exception:
            return

        if not web_reminders:
            return

        try:
            local_alarms = await self.list_alarms()
        except Exception:
            local_alarms = []
        local_times = {a.get("time", "") for a in local_alarms}

        for reminder in web_reminders:
            remind_time = reminder.get("remind_at", "")
            if remind_time not in local_times:
                await self.create_alarm(
                    name=reminder.get("text", "提醒"),
                    time=remind_time,
                    reminder_type="sound",
                )
                local_times.add(remind_time)
                logger.info(f"网页提醒已同步到本地闹钟: {reminder.get('text', '')[:30]}")

    async def stop(self):
        """停止进程。"""
        self._running = False
        for task in self._bg_tasks:
            task.cancel()
        if self._process:
            try:
                self._process.terminate()
                await asyncio.sleep(1)
                self._process.kill()
            except Exception:
                pass
        logger.info("mcp-alarm-clock 已停止")