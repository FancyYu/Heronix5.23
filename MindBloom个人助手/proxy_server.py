"""
MindBloom 一站式代理服务器
同时提供静态文件服务和 API 转发。
可替代 python -m http.server，通过同一个 localtunnel 暴露前端+API。
"""
import asyncio
import httpx
import mimetypes
import os
import posixpath
import urllib.parse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AGENT_API = "http://localhost:8080"
BACKEND_API = "http://localhost:8000"
BRIDGE_API = "http://localhost:8001"

API_ROUTES = {
    "/chat": AGENT_API,
    "/remind": AGENT_API,
    "/reminders": AGENT_API,
    "/reminders/": AGENT_API,
    "/status": BACKEND_API,
    "/users": BACKEND_API,
    "/actions": BACKEND_API,
    "/interests": BACKEND_API,
    "/focus": BACKEND_API,
    "/internal/": BRIDGE_API,
    "/alarm_clock/": BRIDGE_API,
    "/xiaozhi/": BRIDGE_API,
    "/mcp/": BRIDGE_API,
}


def _is_api_path(path: str) -> str | None:
    for prefix, target in API_ROUTES.items():
        if path.startswith(prefix):
            return target
    return None


async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        request_line = await asyncio.wait_for(reader.readline(), timeout=10)
        if not request_line:
            writer.close()
            return
        request_line = request_line.decode("utf-8", errors="replace").strip()
        parts = request_line.split(" ")
        if len(parts) < 2:
            writer.close()
            return
        method = parts[0]
        path = parts[1]
        url = urllib.parse.urlparse(path)
        clean_path = url.path

        headers = {}
        content_length = 0
        while True:
            header_line = await asyncio.wait_for(reader.readline(), timeout=5)
            header_line = header_line.decode("utf-8", errors="replace").strip()
            if not header_line:
                break
            if ":" in header_line:
                key, val = header_line.split(":", 1)
                headers[key.strip().lower()] = val.strip()
                if key.lower() == "content-length":
                    content_length = int(val.strip())

        body = b""
        if content_length > 0:
            body = await asyncio.wait_for(reader.readexactly(content_length), timeout=10)

        target_base = _is_api_path(clean_path)
        if target_base:
            target_url = f"{target_base}{clean_path}"
            if url.query:
                target_url += f"?{url.query}"
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.request(
                        method=method,
                        url=target_url,
                        headers={k: v for k, v in headers.items() if k not in ("host", "content-length", "accept-encoding")},
                        content=body,
                        follow_redirects=True,
                    )
                response_body = resp.content
                response_headers = (
                    f"HTTP/1.1 {resp.status_code} {resp.reason_phrase}\r\n"
                    f"Content-Type: {resp.headers.get('content-type', 'application/json')}\r\n"
                    f"Content-Length: {len(response_body)}\r\n"
                    f"Access-Control-Allow-Origin: *\r\n"
                    f"Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS\r\n"
                    f"Access-Control-Allow-Headers: Content-Type\r\n"
                    f"Cache-Control: no-cache\r\n"
                    f"\r\n"
                ).encode()
                writer.write(response_headers + response_body)
            except Exception as e:
                error_body = f'{{"error":"proxy error: {str(e)}"}}'.encode()
                writer.write(
                    f"HTTP/1.1 502 Bad Gateway\r\nContent-Type: application/json\r\nContent-Length: {len(error_body)}\r\nAccess-Control-Allow-Origin: *\r\n\r\n".encode()
                    + error_body
                )
        else:
            file_path = clean_path.lstrip("/")
            if not file_path or file_path.endswith("/"):
                file_path = "index.html"
            full_path = os.path.normpath(os.path.join(SCRIPT_DIR, file_path))
            if not full_path.startswith(SCRIPT_DIR):
                writer.write(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
                writer.close()
                return
            if os.path.isfile(full_path):
                with open(full_path, "rb") as f:
                    data = f.read()
                content_type, _ = mimetypes.guess_type(full_path)
                if not content_type:
                    content_type = "application/octet-stream"
                writer.write(
                    f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {len(data)}\r\nAccess-Control-Allow-Origin: *\r\n\r\n".encode()
                    + data
                )
            else:
                writer.write(b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n")
    except Exception as e:
        print(f"[Proxy] Error: {e}")
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def main():
    server = await asyncio.start_server(handle, "0.0.0.0", 3000)
    print(f"MindBloom Proxy Server → http://localhost:3000")
    print(f"  静态文件: {SCRIPT_DIR}")
    print(f"  API 转发: /chat, /reminders... → Agent (8080) / Backend (8000) / Bridge (8001)")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())