"""仅做 Pi JSONL 传输、请求关联和进程清理，不重写 Agent 循环。"""

import asyncio
import json
import os
import signal
import time
import uuid
from collections import deque

from .logging_setup import logger_for


class PiProcess:
    def __init__(self, command, cwd, env, on_event, on_exit, *, session=None):
        self.command = command
        self.cwd = cwd
        self.env = env
        self.on_event = on_event
        self.on_exit = on_exit
        self.process = None
        self.pending = {}
        # 进程 stderr 留在内存里给诊断用，同时按行写日志，重载后仍能回看。
        self.diagnostics = deque(maxlen=30)
        self.write_lock = asyncio.Lock()
        self.reader = None
        self.stderr_reader = None
        self.closing = False
        self.started_at = None
        self.log = logger_for(session)

    @property
    def pid(self):
        return self.process.pid if self.process else None

    def alive(self):
        return bool(self.process and self.process.returncode is None)

    def last_diagnostics(self, limit=10):
        return list(self.diagnostics)[-limit:]

    async def start(self):
        self.process = await asyncio.create_subprocess_exec(
            *self.command, cwd=self.cwd, env=self.env,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE, start_new_session=True,
            limit=32 * 1024 * 1024,
        )
        self.started_at = time.monotonic()
        self.log.debug("Pi 进程已创建 pid=%s cwd=%s", self.pid, self.cwd)
        self.reader = asyncio.create_task(self._read())
        self.stderr_reader = asyncio.create_task(self._stderr())
        return await self.call("get_state", timeout=90)

    async def _read(self):
        error = "Pi 进程已退出。"
        try:
            # asyncio 的二进制 readline 只按 LF 分帧，不拆 U+2028/U+2029。
            while line := await self.process.stdout.readline():
                try:
                    record = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    self.diagnostics.append("Pi 返回了无效的 JSONL 记录。")
                    self.log.warning("收到无效 JSONL 记录 length=%d", len(line))
                    continue
                if record.get("type") == "response":
                    future = self.pending.pop(record.get("id"), None)
                    if future is None:
                        self.log.debug("收到无对应请求的响应 id=%s", record.get("id"))
                    elif not future.done():
                        if record.get("success"):
                            future.set_result(record.get("data", {}))
                        else:
                            future.set_exception(RuntimeError(record.get("error", "Pi 请求失败。")))
                else:
                    await self.on_event(record)
        except Exception as exc:
            error = f"Pi 输出中断：{exc}"
            self.log.error("Pi 输出中断：%s", exc, exc_info=True)
        finally:
            for future in self.pending.values():
                if not future.done():
                    future.set_exception(RuntimeError(error))
            self.pending.clear()
            await self.on_exit(self.closing)

    async def _stderr(self):
        while line := await self.process.stderr.readline():
            text = line.decode("utf-8", errors="replace").strip()[-1000:]
            if text:
                self.diagnostics.append(text)
                self.log.debug("Pi stderr: %s", text)

    async def send(self, record):
        if not self.process or self.process.returncode is not None or self.closing:
            raise RuntimeError("Pi 进程未运行。")
        async with self.write_lock:
            self.process.stdin.write(json.dumps(record, ensure_ascii=False).encode() + b"\n")
            await self.process.stdin.drain()

    async def call(self, kind, timeout=30, **values):
        request_id = str(uuid.uuid4())
        future = asyncio.get_running_loop().create_future()
        self.pending[request_id] = future
        started = time.monotonic()
        try:
            await self.send({"id": request_id, "type": kind, **values})
            result = await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            self.log.warning("Pi 请求超时 type=%s timeout=%ss", kind, timeout)
            raise
        except Exception as error:
            self.log.warning("Pi 请求失败 type=%s 耗时=%.0fms 错误=%s",
                             kind, (time.monotonic() - started) * 1000, error)
            raise
        else:
            self.log.debug("Pi 请求完成 type=%s 耗时=%.0fms", kind, (time.monotonic() - started) * 1000)
            return result
        finally:
            self.pending.pop(request_id, None)

    async def stop(self):
        queued = await self.call("clear_queue")
        await self.call("abort", timeout=60)
        return queued

    async def close(self):
        if not self.process:
            return
        self.closing = True
        if self.process.returncode is None:
            self.process.stdin.close()
            try:
                await asyncio.wait_for(self.process.wait(), 5)
            except asyncio.TimeoutError:
                # 独立进程组只包含本插件启动的 Pi 和其子进程。
                try:
                    os.killpg(self.process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    await asyncio.wait_for(self.process.wait(), 3)
                except asyncio.TimeoutError:
                    try:
                        os.killpg(self.process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    await self.process.wait()
        self.log.debug("Pi 进程已退出 pid=%s code=%s", self.pid, self.process.returncode)
        for task in (self.reader, self.stderr_reader):
            if task and task is not asyncio.current_task():
                task.cancel()
        await asyncio.gather(*(t for t in (self.reader, self.stderr_reader) if t), return_exceptions=True)
