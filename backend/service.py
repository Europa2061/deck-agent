import asyncio
import copy
import json
import logging
import os
import platform
import re
import shutil
import sys
import tempfile
import time
import uuid
from pathlib import Path

from . import logging_setup
from .build_info import collect as build_metadata
from .rpc import PiProcess
from .storage import Storage, read_json, write_json
from .session_state import is_user_interruption, message_view, is_abort_error
from .workflows.common import Store as PlayerStore
from .workflows import plugins as player_plugins
from .voice import VoiceService
from .updates import check_release, UpdateDownload

PI_VERSION = "1.5.0"


class AgentService:
    def __init__(self, root: Path, settings: Path, data: Path, home: Path, emit):
        self.root = root
        self.storage = Storage(settings, data, home)
        self.emit = emit
        self.build = build_metadata(root)
        self.started_at = time.time()
        self.run_started = {}
        self.title_tasks = {}
        # 供应商密钥只用于日志脱敏，不写入日志本身。
        logging_setup.register_secret(*[
            entry.get("key") for entry in read_json(self.storage.agent / "auth.json").values()
            if isinstance(entry, dict) and isinstance(entry.get("key"), str)
        ])
        self.processes = {}
        self.starting = {}
        self.messages = {}
        self.ui_requests = {}
        self.extension_status = {}
        self.widgets = {}
        self.tools = {}
        self.catalog_cache = None
        self.model_config_revision = 0
        self.config_lock = asyncio.Lock()
        self.refresh_task = None
        self.tasks = set()
        self.closed = False
        self.player_store = PlayerStore(home=home, data=data)
        self.update_download = UpdateDownload(data / "updates")
        self.update_lock = asyncio.Lock()
        self.voice = VoiceService(root, data / "voice", self.changed, self.voice_draft)

    def spawn(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.tasks.add(task)
        task.add_done_callback(self._task_done)
        return task

    def _task_done(self, task):
        self.tasks.discard(task)
        if task.cancelled():
            return
        error = task.exception()
        if error is not None:
            # 后台任务（通知刷新、状态对齐、扩展超时）失败也要留下脱敏堆栈。
            logging_setup.logger_for().error("后台任务失败：%s", self.safe_error(error), exc_info=error)

    def safe_error(self, error):
        text = str(error) or type(error).__name__
        if "No API key found for the selected model" in text:
            return "当前模型尚未配置可用认证，请在「设置 → 供应商与模型」中检查配置。"
        # 错误来自子进程或供应商，回传前去除已保存的密钥原值。
        for entry in read_json(self.storage.agent / "auth.json").values():
            if isinstance(entry, dict) and entry.get("key"):
                text = text.replace(entry["key"], "[已隐藏]")
        return text[:1500]

    async def changed(self, notification=None):
        if notification:
            await self.emit({"type": "notice", **notification})
        if self.closed or (self.refresh_task and not self.refresh_task.done()):
            return

        async def later():
            await asyncio.sleep(0.1)
            if not self.closed:
                await self.emit({"type": "changed"})

        self.refresh_task = self.spawn(later())

    def environment(self, agent_dir=None):
        env = dict(os.environ)
        env["HOME"] = str(self.storage.home)
        env["PI_CODING_AGENT_DIR"] = str(agent_dir or self.storage.agent)
        env["DECK_AGENT_DATA_DIR"] = str(self.storage.data)
        env["DECK_AGENT_PLUGINS_DIR"] = str(self.root.parent)
        # Decky 为冻结程序时 sys.executable 是 PluginLoader，不是可执行脚本的 Python。
        embedded = bool(getattr(sys, "frozen", False)) or "python" not in Path(sys.executable).name.lower()
        env["DECK_AGENT_PYTHON"] = (shutil.which("python3") or "/usr/bin/python3") if embedded else sys.executable
        env["DECK_AGENT_EMBEDDED_PYTHON"] = "1" if embedded else "0"
        node_bin = Path(shutil.which("node")).parent if os.environ.get("DECK_AGENT_DEV") == "1" and sys.platform != "linux" and shutil.which("node") else self.root / "runtime/node/bin"
        env["PATH"] = str(node_bin) + os.pathsep + env.get("PATH", "/usr/local/bin:/usr/bin:/bin")
        # 向 Pi 传入产品提示，不剥离其工具或扩展能力。
        return env

    def node(self):
        if os.environ.get("DECK_AGENT_DEV") == "1" and sys.platform != "linux" and shutil.which("node"):
            return shutil.which("node")
        bundled = self.root / "runtime/node/bin/node"
        if bundled.is_file():
            return str(bundled)
        if os.environ.get("DECK_AGENT_DEV") == "1" and shutil.which("node"):
            return shutil.which("node")
        raise RuntimeError("安装包缺少 Node 运行环境，请重新安装完整的 Linux x64 插件包。")

    def pi_command(self):
        cli = self.root / "runtime/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js"
        if not cli.exists():
            raise RuntimeError("安装包缺少 Pi，请重新安装完整插件包。")
        return [self.node(), str(cli)]

    async def catalog(self, refresh=False):
        if self.catalog_cache is not None and not refresh:
            return self.catalog_cache
        process = await asyncio.create_subprocess_exec(
            self.node(), str(self.root / "runtime/catalog.mjs"), env=self.environment(),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), 60)
        except BaseException:
            process.kill()
            await process.wait()
            raise
        if process.returncode:
            raise RuntimeError("模型目录读取失败：" + stderr.decode(errors="replace")[-800:])
        self.catalog_cache = json.loads(stdout)
        return self.catalog_cache

    def provider_view(self):
        auth = read_json(self.storage.agent / "auth.json")
        models = read_json(self.storage.agent / "models.json").get("providers", {})
        pi_settings = read_json(self.storage.agent / "settings.json")
        preferences = self.storage.preferences.get("providers", {})
        configured = set(auth) | {key for key, value in models.items() if value.get("apiKey")}
        result = []
        for provider_id in sorted(configured):
            config = models.get(provider_id, {})
            pref = preferences.get(provider_id, {})
            is_default = pi_settings.get("defaultProvider") == provider_id
            model_id = pi_settings.get("defaultModel", pref.get("model", "")) if is_default else pref.get("model", "")
            selected_model = next((m for m in config.get("models", []) if m.get("id") == model_id), {})
            # 永远不把 auth.json 或包含 apiKey/headers 的原始模型对象送到 GUI。
            result.append({
                "id": provider_id, "name": pref.get("name", provider_id),
                "model": model_id, "enabledModels": pref.get("enabledModels", [model_id] if model_id else []),
                "thinking": pi_settings.get("defaultThinkingLevel", "off") if is_default else pref.get("thinking", "off"), "baseUrl": config.get("baseUrl", ""),
                "api": config.get("api", "openai-completions"),
                "configured": True, "default": is_default,
                "custom": bool(pref.get("custom")), "reasoning": bool(selected_model.get("reasoning")),
            })
        return result

    async def snapshot(self, session_id=None):
        runtime_error = None
        try:
            self.pi_command()
        except Exception as exc:
            runtime_error = str(exc)
        sessions = copy.deepcopy(self.storage.sessions)
        for item in sessions:
            item.pop("file", None)
            item["unread"] = item.get("replyVersion", 0) > item.get("readVersion", 0)
            item["pending"] = list(self.ui_requests.get(item["id"], {}).values())
        return {
            "pluginInstalls": player_plugins.pending(self.player_store),
            "newSessionDraft": self.storage.new_draft.get("draft", ""),
            "newSessionModel": {k: v for k, v in self.storage.new_draft.items() if k in ("provider", "model", "thinking")},
            "sessions": sessions, "preferences": self.storage.preferences,
            "providers": self.provider_view(),
            "runtime": {"ready": runtime_error is None, "error": runtime_error, "piVersion": PI_VERSION},
            "version": read_json(self.root / "package.json").get("version", "0.1.0"),
            "build": self.build,
            "voice": self.voice.snapshot(),
            "active": ({"id": session_id, "messages": [message_view(message) for message in self.messages.get(session_id, []) if message.get("role") in ("user", "assistant", "toolResult", "custom")],
                        "statusEntries": self.extension_status.get(session_id, {}),
                        "widgets": self.widgets.get(session_id, {}),
                        "tools": list(self.tools.get(session_id, {}).values())} if session_id else None),
        }

    async def ensure(self, session_id):
        if session_id in self.starting:
            return await self.starting[session_id]
        process = self.processes.get(session_id)
        if process is not None:
            if process.config_revision == self.model_config_revision or self.storage.session(session_id)["status"] in ("running", "waiting", "starting"):
                return process
        task = self.spawn(self._restart_config(session_id, process) if process else self._start(session_id))
        self.starting[session_id] = task
        try:
            return await task
        finally:
            self.starting.pop(session_id, None)

    async def _restart_config(self, session_id, process):
        # Pi 的可用模型是启动时的快照；空闲时从原会话文件重开，不重发任务。
        await process.close()
        return await self._start(session_id)

    def runtime_report(self):
        return {
            "piVersion": PI_VERSION,
            "node": str(self.root / "runtime/node/bin/node") if (self.root / "runtime/node/bin/node").is_file() else "",
            "piInstalled": (self.root / "runtime/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js").is_file(),
            "sttEngine": (self.root / "runtime/stt/bin/sherpa-onnx-offline").is_file(),
            "captureTool": shutil.which("pw-record") or "",
        }

    async def _start(self, session_id):
        log = logging_setup.logger_for(session_id)
        item = self.storage.session(session_id)
        cwd = self.storage.cwd(item["cwd"])
        command = self.pi_command() + ["--mode", "rpc", "--session", item["file"],
                                       "--append-system-prompt", str(self.root / "resources/system.md"),
                                       "--skill", str(self.root / "resources/skills"),
                                       "--extension", str(self.root / "resources/extensions/player-tools.ts"),
                                       "--prompt-template", str(self.root / "resources/prompts")]
        if not Path(item["file"]).exists():
            defaults = read_json(self.storage.agent / "settings.json")
            if item.get("provider") and item.get("model"):
                command += ["--provider", item["provider"], "--model", item["model"], "--thinking", item.get("thinking", "off")]
            elif defaults.get("defaultProvider") and defaults.get("defaultModel"):
                command += ["--provider", defaults["defaultProvider"], "--model", defaults["defaultModel"]]

        async def on_event(event):
            await self.handle_event(session_id, event)

        async def on_exit(expected):
            current = self.processes.get(session_id)
            if current is not None and current is not process:
                return
            self.processes.pop(session_id, None)
            self.ui_requests.pop(session_id, None)
            self.tools.pop(session_id, None)
            self.run_started.pop(session_id, None)
            if not expected:
                log.error("Pi 进程意外退出 pid=%s code=%s stderr=%s", process.pid,
                          process.process.returncode if process.process else None,
                          process.last_diagnostics(5))
                item["status"] = "interrupted"
                item["error"] = "Pi 进程退出，历史已保留。请检查结果后再继续。"
                self.storage.save_sessions()
                await self.changed()

        process = PiProcess(command, str(cwd), self.environment(), on_event, on_exit, session=session_id)
        process.config_revision = self.model_config_revision
        self.processes[session_id] = process
        try:
            state = await process.start()
            self.processes[session_id] = process
            item["file"] = state.get("sessionFile") or item["file"]
            model = state.get("model") or {}
            item["provider"] = model.get("provider", item.get("provider", ""))
            item["model"] = model.get("id", item.get("model", ""))
            item["thinking"] = state.get("thinkingLevel", "off")
            self.messages[session_id] = (await process.call("get_messages")).get("messages", [])
            # 启动或读取历史本身不把中断标记变成执行中，也不重发 prompt。
            self.storage.save_sessions()
            log.info("Pi 会话已就绪 pid=%s provider=%s model=%s", process.pid,
                     item.get("provider", ""), item.get("model", ""))
            return process
        except BaseException:
            self.processes.pop(session_id, None)
            await process.close()
            raise

    async def handle_event(self, session_id, event):
        item = self.storage.session(session_id)
        kind = event.get("type")
        log = logging_setup.logger_for(session_id)
        if kind in ("agent_start", "turn_start"):
            if kind == "agent_start":
                self.run_started[session_id] = time.monotonic()
                log.info("任务开始 provider=%s model=%s", item.get("provider", ""), item.get("model", ""))
            else:
                log.debug("新一轮开始")
            item["status"] = "running"
            item.pop("error", None)
        elif kind == "message_start":
            self.messages.setdefault(session_id, []).append(event["message"])
        elif kind in ("message_update", "message_end"):
            messages = self.messages.setdefault(session_id, [])
            if messages and messages[-1].get("role") == event.get("message", {}).get("role"):
                messages[-1] = event["message"]
            elif event.get("message"):
                messages.append(event["message"])
            message = event.get("message", {})
            content = message.get("content") or []
            has_text = bool(content.strip()) if isinstance(content, str) else any(
                part.get("type") == "text" and str(part.get("text", "")).strip() for part in content if isinstance(part, dict)
            )
            if kind == "message_end" and message.get("role") == "assistant" and has_text:
                item["replyVersion"] = item.get("replyVersion", 0) + 1
                self.storage.save_sessions()
        elif kind == "tool_execution_start":
            self.tools.setdefault(session_id, {})[event["toolCallId"]] = {
                "id": event["toolCallId"], "name": event.get("toolName", "tool"), "args": event.get("args", {}), "result": None,
                "started": time.monotonic(),
            }
            # 只记录工具名，不记录参数和输出。
            log.info("工具开始 name=%s", event.get("toolName", "tool"))
        elif kind == "tool_execution_update":
            tool = self.tools.get(session_id, {}).get(event.get("toolCallId"))
            if tool is not None:
                tool["result"] = event.get("partialResult")
        elif kind == "tool_execution_end":
            tool = self.tools.get(session_id, {}).pop(event.get("toolCallId"), None)
            name = (tool or {}).get("name") or event.get("toolName", "tool")
            started = (tool or {}).get("started")
            if started:
                log.info("工具结束 name=%s 耗时=%.0fms", name, (time.monotonic() - started) * 1000)
            else:
                log.info("工具结束 name=%s", name)
        elif kind == "extension_ui_request":
            method = event.get("method")
            if method in ("confirm", "select", "input", "editor"):
                log.info("等待用户输入 method=%s", method)
                request = {**event, "instanceId": str(id(self.processes.get(session_id))), "sessionId": session_id}
                self.ui_requests.setdefault(session_id, {})[event["id"]] = request
                item["status"] = "waiting"
                if event.get("timeout"):
                    self.spawn(self.expire_request(session_id, event["id"], event["timeout"]))
                await self.changed({"sessionId": session_id, "title": item["name"], "message": event.get("title", "需要你的输入")})
            elif method == "notify":
                await self.changed({"sessionId": session_id, "title": item["name"], "message": event.get("message", "")})
            elif method == "set_editor_text":
                item["draft"] = event.get("text", "")
            elif method == "setStatus":
                self.extension_status.setdefault(session_id, {})[event.get("statusKey", "")] = event.get("statusText", "")
            elif method == "setTitle":
                item["extensionTitle"] = event.get("title", "")
            elif method == "setWidget":
                self.widgets.setdefault(session_id, {})[event.get("widgetKey", "")] = event.get("widgetLines", [])
        elif kind == "agent_settled":
            self.ui_requests.pop(session_id, None)
            self.tools.pop(session_id, None)
            item["status"] = "idle" if item.get("status") != "stopped" else "stopped"
            messages = self.messages.get(session_id, [])
            last = next((m for m in reversed(messages) if m.get("role") == "assistant"), {})
            elapsed = time.monotonic() - self.run_started.pop(session_id, time.monotonic())
            if is_user_interruption(last):
                item["status"] = "stopped"
                item.pop("error", None)
                log.info("用户中断任务 耗时=%.1fs", elapsed)
            elif last.get("stopReason") == "error":
                item["status"] = "error"
                item["error"] = self.safe_error(last.get("errorMessage", "模型请求失败。"))
                log.error("任务出错 耗时=%.1fs 错误=%s", elapsed, item["error"])
            else:
                log.info("任务结束 status=%s 耗时=%.1fs", item["status"], elapsed)
            item["updated"] = time.time()
            self.storage.save_sessions()
            self.spawn(self.reconcile(session_id))
            if item["status"] != "stopped":
                await self.changed({"sessionId": session_id, "title": item["name"], "message": "任务出错" if item["status"] == "error" else "任务已结束"})
        await self.changed()

    async def reconcile(self, session_id):
        process = self.processes.get(session_id)
        if process:
            try:
                self.messages[session_id] = (await process.call("get_messages")).get("messages", [])
                await self.changed()
            except Exception:
                pass

    async def expire_request(self, session_id, request_id, milliseconds):
        await asyncio.sleep(max(0, milliseconds) / 1000)
        requests = self.ui_requests.get(session_id, {})
        if requests.pop(request_id, None):
            if not requests:
                self.storage.session(session_id)["status"] = "running"
            await self.changed()

    async def voice_draft(self, session_id, text):
        item = self.storage.new_draft if session_id == "__new__" else self.storage.session(session_id)
        item["draft"] = (item.get("draft", "") + " " + text).strip()
        if session_id == "__new__":
            self.storage.save_new_draft()
        else:
            self.storage.save_sessions()
        await self.changed({"sessionId": session_id, "title": item.get("name", "新会话"), "message": "语音已填入草稿"})

    def model_enabled(self, provider, model):
        pref = self.storage.preferences.get("providers", {}).get(provider)
        # 未经本插件管理的 Pi 原生供应商保持原有行为。
        return pref is None or model in pref.get("enabledModels", [pref.get("model")])

    async def generate_title(self, session_id, text):
        process = None
        try:
            item = self.storage.session(session_id)
            selected = self.storage.preferences.get("titleModel") or {"provider": item.get("provider"), "model": item.get("model")}
            process = await asyncio.create_subprocess_exec(
                self.node(), str(self.root / "runtime/title.mjs"), cwd=item["cwd"], env=self.environment(),
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(process.communicate(json.dumps({**selected, "text": text[:3000]}, ensure_ascii=False).encode()), 35)
            if process.returncode:
                raise RuntimeError("命名请求未完成")
            title = json.loads(stdout).get("title", "")
            if not isinstance(title, str):
                raise ValueError("命名结果格式不正确")
            title = re.sub(r"\s+", " ", str(title)).strip(' \"“”「」`')[:32]
            if not title:
                raise ValueError("命名结果为空")
            item = self.storage.session(session_id)
            if item.get("autoTitle"):
                item["name"] = title
                item["autoTitle"] = False
                self.storage.save_sessions()
                await self.changed()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # 命名失败保留首条消息摘要，不影响聊天，也不把供应商输出写到日志。
            logging_setup.logger_for(session_id).warning("自动命名未完成 type=%s", type(exc).__name__)
        finally:
            if process and process.returncode is None:
                process.kill()
                await process.wait()
            self.title_tasks.pop(session_id, None)

    async def save_provider(self, payload):
        provider_id = payload.get("id", "").strip()
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}", provider_id):
            raise ValueError("供应商 ID 只使用字母、数字、短横线和下划线。")
        model_id = payload.get("model", "").strip()
        if not model_id:
            raise ValueError("请填写模型 ID。")
        enabled = payload.get("enabledModels", [model_id])
        if not isinstance(enabled, list) or not enabled or len(enabled) > 200 or any(not isinstance(m, str) or not m.strip() or len(m) > 300 for m in enabled):
            raise ValueError("请至少启用一个模型，最多 200 个。")
        enabled = list(dict.fromkeys(m.strip() for m in enabled))
        if model_id not in enabled:
            raise ValueError("默认模型必须在已选模型中。")
        base_url = payload.get("baseUrl", "").strip()
        if payload.get("custom") and not base_url:
            raise ValueError("自定义供应商需要接口地址。")
        api = payload.get("api", "openai-completions")
        if payload.get("custom") and api not in ("openai-completions", "openai-responses", "anthropic-messages", "google-generative-ai"):
            raise ValueError("不支持这个接口协议。")
        if base_url:
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            if parsed.scheme not in ("https", "http") or not parsed.netloc or parsed.username or parsed.password:
                raise ValueError("请输入有效的 HTTP(S) 接口地址，不要在地址中包含密钥。")
        async with self.config_lock:
            auth_path = self.storage.agent / "auth.json"
            auth = read_json(auth_path)
            key = payload.get("key", "").strip()
            if not key and provider_id not in auth:
                raise ValueError("请填写 API Key；本地兼容接口可填写其要求的占位值。")
            if key:
                # Pi 原生凭据，不使用 models.json 的 !command 解释规则保存输入值。
                auth[provider_id] = {"type": "api_key", "key": key}
                write_json(auth_path, auth)
                logging_setup.register_secret(key)
                logging_setup.logger_for().info("保存供应商凭据 id=%s", provider_id)
            models_path = self.storage.agent / "models.json"
            models = read_json(models_path)
            providers = models.setdefault("providers", {})
            catalog_models = (self.catalog_cache or {}).get("models", [])
            manual_model = bool(catalog_models) and any(not any(m["provider"] == provider_id and m["id"] == selected_id for m in catalog_models) for selected_id in enabled)
            if payload.get("custom") or base_url or manual_model:
                config = providers.setdefault(provider_id, {})
                if base_url:
                    config["baseUrl"] = base_url
                if payload.get("custom") or manual_model:
                    config["api"] = api if payload.get("custom") else next((m["api"] for m in catalog_models if m["provider"] == provider_id), api)
                    existing = config.setdefault("models", [])
                    for selected_id in enabled:
                        if not any(m.get("id") == selected_id for m in existing) and not any(m["provider"] == provider_id and m["id"] == selected_id for m in catalog_models):
                            existing.append({"id": selected_id, "name": selected_id, "reasoning": bool(payload.get("reasoning", False))})
                    selected = next((m for m in existing if m.get("id") == model_id), None)
                    if selected is None:
                        existing.append({"id": model_id, "name": model_id, "reasoning": bool(payload.get("reasoning", False))})
                    elif "reasoning" in payload:
                        selected["reasoning"] = bool(payload["reasoning"])
                write_json(models_path, models)
            elif "baseUrl" in payload and provider_id in providers:
                providers[provider_id].pop("baseUrl", None)
                write_json(models_path, models)
            preferences = self.storage.preferences.setdefault("providers", {})
            preferences[provider_id] = {k: payload.get(k, "") for k in ("name", "model", "thinking", "custom")}
            preferences[provider_id]["enabledModels"] = enabled
            title_model = self.storage.preferences.get("titleModel")
            if title_model and title_model.get("provider") == provider_id and title_model.get("model") not in enabled:
                self.storage.preferences["titleModel"] = None
            settings_path = self.storage.agent / "settings.json"
            settings = read_json(settings_path)
            if not settings.get("defaultProvider") or settings.get("defaultProvider") == provider_id or payload.get("default"):
                settings.update(defaultProvider=provider_id, defaultModel=model_id, defaultThinkingLevel=payload.get("thinking", "off"))
                write_json(settings_path, settings)
            self.storage.save_preferences()
            self.catalog_cache = None
            self.model_config_revision += 1
        await self.changed()

    async def request(self, action, payload):
        payload = payload if isinstance(payload, dict) else {}
        log = logging_setup.logger_for(payload.get("sessionId"))
        started = time.monotonic()
        try:
            result = await self._dispatch(action, payload)
        except Exception as error:
            elapsed = (time.monotonic() - started) * 1000
            message = self.safe_error(error)
            if isinstance(error, ValueError):
                log.warning("请求被拒绝 action=%s 耗时=%.0fms 原因=%s", action, elapsed, message)
            else:
                log.error("请求失败 action=%s 耗时=%.0fms 错误=%s", action, elapsed, message, exc_info=True)
            raise
        else:
            log.debug("请求完成 action=%s 耗时=%.0fms", action, (time.monotonic() - started) * 1000)
            return result

    async def _dispatch(self, action, payload):
        if self.closed:
            raise RuntimeError("插件正在退出。")
        if action == "snapshot":
            return await self.snapshot(payload.get("sessionId"))
        if action == "catalog":
            return await self.catalog(bool(payload.get("refresh")))
        if action == "create_session":
            default = str(self.storage.home / "DeckAgent")
            cwd = self.storage.cwd(payload.get("cwd") or self.storage.preferences.get("defaultCwd", default), create=not payload.get("cwd") or payload.get("cwd") == default)
            session_id = str(uuid.uuid4())
            item = {"id": session_id, "name": payload.get("name", "").strip() or "新会话", "cwd": str(cwd),
                    "file": str(self.storage.sessions_dir / (session_id + ".jsonl")), "status": "idle",
                    "archived": False, "draft": "", "updated": time.time(), "autoTitle": not bool(payload.get("name", "").strip())}
            if payload.get("fromDraft"):
                item["draft"] = str(payload.get("text", ""))
                item.update({k: v for k, v in self.storage.new_draft.items() if k in ("provider", "model", "thinking")})
            self.storage.sessions.insert(0, item)
            self.storage.save_sessions()
            logging_setup.logger_for(session_id).info("新建会话 cwd=%s", cwd)
            await self.changed()
            return {"id": session_id}
        if action == "open_session":
            await self.ensure(payload["sessionId"])
            return await self.snapshot(payload["sessionId"])
        if action == "mark_read":
            item = self.storage.session(payload["sessionId"])
            revision = payload.get("replyVersion", 0)
            if not isinstance(revision, int) or revision < 0:
                raise ValueError("已读版本不正确。")
            read = max(item.get("readVersion", 0), min(revision, item.get("replyVersion", 0)))
            if read != item.get("readVersion", 0):
                item["readVersion"] = read
                self.storage.save_sessions()
                await self.changed()
            return None
        if action == "draft":
            if payload["sessionId"] == "__new__":
                self.storage.new_draft["draft"] = str(payload["text"])
                self.storage.save_new_draft()
                return None
            self.storage.session(payload["sessionId"])["draft"] = str(payload["text"])
            self.storage.save_sessions()
            return None
        if action == "send":
            item = self.storage.session(payload["sessionId"])
            text = str(payload.get("text", "")).strip()
            if not text:
                raise ValueError("请输入任务内容。")
            log = logging_setup.logger_for(item["id"])
            log.info("发送任务 chars=%d behavior=%s", len(text), payload.get("behavior") or "prompt")
            process = await self.ensure(item["id"])
            if item.get("autoTitle", item["name"] == "新会话") and not item.get("titleStarted"):
                item["titleStarted"] = True
                item["name"] = re.sub(r"\s+", " ", text)[:24] or "新会话"
                item["autoTitle"] = True
                self.storage.save_sessions()
                self.title_tasks[item["id"]] = self.spawn(self.generate_title(item["id"], text))
            values = {"message": text}
            if payload.get("behavior") in ("steer", "followUp"):
                values["streamingBehavior"] = payload["behavior"]
            response = await process.call("prompt", **values)
            if item.get("draft", "").strip() == text:
                item["draft"] = ""
            if response.get("disposition") == "handled":
                state = await process.call("get_state")
                if not state.get("isStreaming") and not self.ui_requests.get(item["id"]):
                    item["status"] = "idle"
            self.storage.save_sessions()
            await self.changed()
            return response
        if action == "stop":
            session_id = payload["sessionId"]
            process = self.processes.get(session_id)
            if not process:
                raise ValueError("当前会话没有运行中的任务。")
            logging_setup.logger_for(session_id).info("用户停止任务 pid=%s", process.pid)
            item = self.storage.session(session_id)
            item["status"] = "stopped"
            if is_abort_error(item.get("error")):
                item.pop("error", None)
            for request_id in self.ui_requests.get(session_id, {}):
                await process.send({"type": "extension_ui_response", "id": request_id, "cancelled": True})
            result = await process.stop()
            self.ui_requests.pop(session_id, None)
            self.storage.save_sessions()
            await self.changed()
            return result
        if action == "session_meta":
            item = self.storage.session(payload["sessionId"])
            if item.get("status") in ("running", "waiting") and ("archived" in payload or payload.get("delete")):
                raise ValueError("先停止任务，再归档或删除会话。")
            if payload.get("delete"):
                process = self.processes.pop(item["id"], None)
                if process:
                    await process.close()
                logging_setup.logger_for(item["id"]).info("删除会话记录")
                Path(item["file"]).unlink(missing_ok=True)
                self.storage.sessions.remove(item)
                self.messages.pop(item["id"], None)
            else:
                if "name" in payload:
                    name = payload["name"].strip()
                    if not name:
                        raise ValueError("会话名称不能为空。")
                    logging_setup.logger_for(item["id"]).info("重命名会话 chars=%d", len(name))
                    item["name"] = name
                    item["autoTitle"] = False
                    if item["id"] in self.processes:
                        await self.processes[item["id"]].call("set_session_name", name=name)
                if "archived" in payload:
                    logging_setup.logger_for(item["id"]).info("会话归档 archived=%s", bool(payload["archived"]))
                    item["archived"] = bool(payload["archived"])
            self.storage.save_sessions()
            await self.changed()
            return None
        if action == "set_model" and payload["sessionId"] == "__new__":
            if not self.model_enabled(payload["provider"], payload["model"]):
                raise ValueError("这个模型未在供应商中启用，请先到设置添加。")
            self.storage.new_draft.update({k: payload[k] for k in ("provider", "model", "thinking") if k in payload})
            self.storage.save_new_draft()
            await self.changed()
            return None
        if action == "set_model":
            process = await self.ensure(payload["sessionId"])
            if process.config_revision != self.model_config_revision:
                raise ValueError("供应商配置已更新，请先等待当前任务结束或停止任务，再切换模型。")
            if not self.model_enabled(payload["provider"], payload["model"]):
                raise ValueError("这个模型未在供应商中启用，请先到设置添加。")
            await process.call("set_model", provider=payload["provider"], modelId=payload["model"])
            if payload.get("thinking"):
                await process.call("set_thinking_level", level=payload["thinking"])
            item = self.storage.session(payload["sessionId"])
            item.update(provider=payload["provider"], model=payload["model"])
            self.storage.save_sessions()
            await self.changed()
            return None
        if action == "commands" and payload["sessionId"] == "__new__":
            return {"commands": []}
        if action == "commands":
            return await (await self.ensure(payload["sessionId"])).call("get_commands")
        if action == "configured_models":
            catalog = await self.catalog()
            configured = {p["id"] for p in self.provider_view()}
            return {"models": [m for m in catalog.get("models", []) if m["provider"] in configured and self.model_enabled(m["provider"], m["id"])]}
        if action == "models":
            process = await self.ensure(payload["sessionId"])
            if process.config_revision != self.model_config_revision:
                raise ValueError("供应商配置已更新，请先等待当前任务结束或停止任务，再刷新模型列表。")
            result = await process.call("get_available_models")
            return {"models": [{key: model.get(key) for key in ("provider", "id", "name", "reasoning", "api")} for model in result.get("models", []) if self.model_enabled(model.get("provider"), model.get("id"))]}
        if action == "ui_response":
            session_id, request_id = payload["sessionId"], payload["requestId"]
            pending = self.ui_requests.get(session_id, {})
            request = pending.get(request_id)
            process = self.processes.get(session_id)
            if not request or not process or request["instanceId"] != str(id(process)):
                raise ValueError("这个请求已过期，请刷新当前会话。")
            record = {"type": "extension_ui_response", "id": request_id}
            if payload.get("cancelled"):
                record["cancelled"] = True
            elif request["method"] == "confirm":
                record["confirmed"] = bool(payload.get("value"))
            else:
                record["value"] = str(payload.get("value", ""))
                if request["method"] == "select" and record["value"] not in request.get("options", []):
                    raise ValueError("请选择请求中的一个选项。")
            await process.send(record)
            pending.pop(request_id, None)
            self.storage.session(session_id)["status"] = "waiting" if pending else "running"
            await self.changed()
            return None
        if action == "save_provider":
            return await self.save_provider(payload)
        if action == "default_provider":
            provider = next((p for p in self.provider_view() if p["id"] == payload["id"]), None)
            if not provider or not provider["model"]:
                raise ValueError("请先配置供应商的默认模型。")
            async with self.config_lock:
                path = self.storage.agent / "settings.json"
                settings = read_json(path)
                settings.update(defaultProvider=provider["id"], defaultModel=provider["model"], defaultThinkingLevel=provider["thinking"])
                write_json(path, settings)
            await self.changed()
            return None
        if action == "remove_provider":
            async with self.config_lock:
                provider_id = payload["id"]
                path = self.storage.agent / "auth.json"
                auth = read_json(path)
                auth.pop(provider_id, None)
                write_json(path, auth)
                path = self.storage.agent / "models.json"
                models = read_json(path)
                config = models.get("providers", {}).get(provider_id, {})
                owned = self.storage.preferences.get("providers", {}).get(provider_id, {}).get("custom")
                if owned:
                    models.get("providers", {}).pop(provider_id, None)
                else:
                    config.pop("apiKey", None)
                write_json(path, models)
                self.storage.preferences.get("providers", {}).pop(provider_id, None)
                if (self.storage.preferences.get("titleModel") or {}).get("provider") == provider_id:
                    self.storage.preferences["titleModel"] = None
                self.storage.save_preferences()
                path = self.storage.agent / "settings.json"
                settings = read_json(path)
                if settings.get("defaultProvider") == provider_id:
                    for key in ("defaultProvider", "defaultModel", "defaultThinkingLevel"):
                        settings.pop(key, None)
                    write_json(path, settings)
                self.catalog_cache = None
                self.model_config_revision += 1
            await self.changed()
            return None
        if action == "test_provider":
            # 使用临时的原生配置和 Pi 的模型适配器；不启动 Agent 或加载扩展。
            log = logging_setup.logger_for()
            started = time.monotonic()
            log.info("开始供应商连接测试 id=%s model=%s", payload.get("id"), payload.get("model"))
            with tempfile.TemporaryDirectory(prefix="deck-agent-test-") as directory:
                target = Path(directory)
                for name in ("auth.json", "models.json"):
                    write_json(target / name, read_json(self.storage.agent / name))
                key = payload.get("key", "").strip()
                if key:
                    auth = read_json(target / "auth.json")
                    auth[payload["id"]] = {"type": "api_key", "key": key}
                    write_json(target / "auth.json", auth)
                if payload.get("baseUrl"):
                    models = read_json(target / "models.json")
                    config = models.setdefault("providers", {}).setdefault(payload["id"], {})
                    config["baseUrl"] = payload["baseUrl"]
                    if payload.get("custom"):
                        config.update(api=payload.get("api", "openai-completions"), models=[{"id": payload["model"]}])
                    write_json(target / "models.json", models)
                process = await asyncio.create_subprocess_exec(self.node(), str(self.root / "runtime/test-provider.mjs"),
                    payload["id"], payload["model"], env=self.environment(target), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                try:
                    stdout, _ = await asyncio.wait_for(process.communicate(), 45)
                except BaseException:
                    process.kill()
                    await process.wait()
                    raise
                result = json.loads(stdout)
                if not result.get("ok"):
                    error = str(result.get("error", "连接测试失败。"))
                    if key:
                        error = error.replace(key, "[已隐藏]")
                    log.warning("供应商连接测试失败 id=%s 耗时=%.0fs", payload.get("id"), time.monotonic() - started)
                    raise RuntimeError(error)
                log.info("供应商连接测试通过 id=%s 耗时=%.0fs", payload.get("id"), time.monotonic() - started)
                return {"ok": True}
        if action == "preferences":
            for key in ("defaultCwd", "notifications", "updateAuto", "releaseRepo", "language", "inputDevice", "titleModel"):
                if key in payload:
                    if key == "defaultCwd":
                        self.storage.cwd(payload[key])
                    if key == "titleModel" and payload[key] is not None:
                        value = payload[key]
                        if not isinstance(value, dict) or not all(isinstance(value.get(k), str) and value[k] for k in ("provider", "model")) or value.get("provider") not in {p["id"] for p in self.provider_view()} or not self.model_enabled(value.get("provider"), value.get("model")):
                            raise ValueError("请选择已启用的命名模型。")
                    self.storage.preferences[key] = payload[key]
            self.storage.save_preferences()
            await self.changed()
            return None
        if action == "player_plugin_claim":
            def claim():
                with self.player_store.lock():
                    return player_plugins.claim(self.player_store, payload["ticket"])
            return await asyncio.to_thread(claim)
        if action in ("player_plugin_failed", "player_plugin_dismiss"):
            with self.player_store.lock():
                record = self.player_store.get(payload["ticket"])
                if record.get("kind") != "plugin-install":
                    raise ValueError("这不是插件安装请求。")
                if action == "player_plugin_failed" and record["status"] == "prompted":
                    record.update(status="failed", error=str(payload.get("error", "安装接口调用失败。"))[:500])
                elif action == "player_plugin_dismiss" and record["status"] in ("queued", "failed"):
                    record["status"] = "dismissed"
                self.player_store.save(record)
            await self.changed()
            return None
        if action == "updates":
            return await asyncio.to_thread(check_release, self.storage.preferences.get("releaseRepo", ""), read_json(self.root / "package.json")["version"])
        if action == "update_status":
            return self.update_download.snapshot()
        if action == "update_download":
            async with self.update_lock:
                release = await asyncio.to_thread(check_release, self.storage.preferences.get("releaseRepo", ""), read_json(self.root / "package.json")["version"])
                if payload.get("version") != release["latest"]:
                    raise ValueError("发布版本已变化，请重新检查更新。")
                self.update_download.start(release)
            return self.update_download.snapshot()
        if action == "update_cancel":
            self.update_download.cancel()
            return self.update_download.snapshot()
        if action == "update_prepare":
            def ensure_idle():
                if self.starting or any(s.get("status") in ("starting", "running", "waiting") for s in self.storage.sessions) or any(self.ui_requests.values()) or self.title_tasks or self.voice.status in ("recording", "transcribing", "downloading"):
                    raise ValueError("当前有任务、待确认请求或语音操作，请结束后再安装更新。")
            ensure_idle()
            prepared = await self.update_download.prepare()
            ensure_idle()
            return prepared
        if action.startswith("voice_"):
            if action == "voice_start" and payload.get("sessionId") != "__new__":
                self.storage.session(payload["sessionId"])
            return await self.voice.request(action, payload, self.storage.preferences)
        if action == "diagnostics":
            return await self.diagnostics()
        raise ValueError("未知操作：" + str(action))

    async def diagnostics(self):
        """给设置页和 SSH 联调用的运行状态；不包含配置内容或密钥。"""
        report = self.runtime_report()
        node_version = ""
        try:
            process = await asyncio.create_subprocess_exec(
                self.node(), "--version", env=self.environment(),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(process.communicate(), 10)
            node_version = stdout.decode(errors="replace").strip()
        except Exception as error:
            node_version = "不可用：" + self.safe_error(error)
        usage = shutil.disk_usage(self.storage.data)
        now = time.monotonic()
        return {
            "build": self.build,
            "version": self.build["version"],
            "piVersion": report["piVersion"],
            "activeProcesses": sum(1 for item in self.processes.values() if item.alive()),
            "platform": {
                "system": platform.system(), "release": platform.release(), "machine": platform.machine(),
                "python": platform.python_version(), "uid": os.geteuid(),
            },
            "paths": {
                "plugin": str(self.root), "settings": str(self.storage.settings), "data": str(self.storage.data),
                "piConfig": str(self.storage.agent), "logs": str(logging_setup.log_directory() or ""),
            },
            "runtime": {**report, "nodeVersion": node_version},
            "processes": [
                {
                    "pid": process.pid, "session": logging_setup.short_session(session_id),
                    "uptimeSeconds": round(now - process.started_at) if process.started_at else None,
                    "alive": process.alive(),
                }
                for session_id, process in list(self.processes.items())
            ],
            "disk": {"freeBytes": usage.free, "totalBytes": usage.total},
            "logs": {"files": logging_setup.log_files(), "recentErrors": logging_setup.recent_errors(20)},
            "voice": self.voice.snapshot(),
        }

    async def close(self):
        self.closed = True
        logging_setup.logger_for().info("插件退出：清理进程与语音任务")
        await self.update_download.close()
        await self.voice.close()
        for item in self.storage.sessions:
            if item.get("status") in ("running", "waiting"):
                item["status"] = "interrupted"
        await asyncio.gather(*(process.close() for process in list(self.processes.values())), return_exceptions=True)
        for task in list(self.tasks):
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.storage.save_sessions()
