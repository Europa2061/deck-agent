"""仅供本机开发：令牌保护的 HTTP 适配器，生产插件不启动它。"""
import asyncio
import json
import os
import secrets
import sys
from collections import deque
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["DECK_AGENT_DEV"] = "1"
from backend import logging_setup
from backend.service import AgentService


async def main():
    token = secrets.token_urlsafe(24)
    events = deque(maxlen=1000)
    sequence = 0

    async def emit(event):
        nonlocal sequence
        sequence += 1
        events.append({"sequence": sequence, "event": event})

    data = ROOT / ".dev-data"
    home = data / "home"
    home.mkdir(parents=True, exist_ok=True)
    # 开发时默认记录细节日志，路径与插件日志目录一致（.dev-data/logs）。
    log = logging_setup.setup_logging(data / "logs", debug=True)
    log.info("开发后端启动，数据目录 %s", data)
    service = AgentService(ROOT, data / "settings", data / "data", home, emit)

    async def handle(reader, writer):
        status = 200
        try:
            header = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 10)
            lines = header.decode("latin1").split("\r\n")
            method, url, _ = lines[0].split(" ")
            headers = {key.strip().lower(): value.strip() for key, value in (line.split(":", 1) for line in lines[1:] if ":" in line)}
            if not secrets.compare_digest(headers.get("x-deck-agent-token", ""), token):
                status, result = 403, {"ok": False, "error": "开发令牌不正确。"}
            elif headers.get("origin") and headers["origin"] != "http://127.0.0.1:4313":
                status, result = 403, {"ok": False, "error": "来源不正确。"}
            elif method == "GET" and urlparse(url).path == "/api/events":
                after = int(parse_qs(urlparse(url).query).get("after", ["0"])[0])
                result = [event for event in events if event["sequence"] > after]
            elif method == "POST" and url == "/api/request":
                length = int(headers.get("content-length", "0"))
                if not 0 < length <= 1024 * 1024:
                    raise ValueError("请求大小不正确。")
                body = json.loads(await asyncio.wait_for(reader.readexactly(length), 10))
                try:
                    result = {"ok": True, "value": await service.request(body["action"], body.get("payload", {}))}
                except Exception as error:
                    result = {"ok": False, "error": service.safe_error(error)}
            else:
                status, result = 404, {"ok": False, "error": "未知路径。"}
        except Exception as error:
            status, result = 400, {"ok": False, "error": str(error)}
        try:
            response = json.dumps(result, ensure_ascii=False).encode()
            writer.write(f"HTTP/1.1 {status} OK\r\nContent-Type: application/json; charset=utf-8\r\nContent-Length: {len(response)}\r\nConnection: close\r\nCache-Control: no-store\r\n\r\n".encode() + response)
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(handle, "127.0.0.1", 4314)
    print(f"开发预览：http://127.0.0.1:4313/#token={token}", flush=True)
    print(f"日志：{logging_setup.log_directory()}", flush=True)
    print("数据仅写入项目 .dev-data/；这是真实 Pi 后端，不是原型模拟。", flush=True)
    try:
        async with server:
            await server.serve_forever()
    finally:
        await service.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
