"""Decky 加载入口；不请求 root，不运行独立 HTTP 服务。"""

import asyncio
import os
import sys
from pathlib import Path

import decky

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import logging_setup
from backend.build_info import collect as collect_build
from backend.service import AgentService


class Plugin:
    async def _migration(self):
        # ZipFile.extractall 不恢复符号链接，重建随包清单中的运行时内部链接。
        import json
        manifest = ROOT / "runtime/symlinks.json"
        runtime = (ROOT / "runtime").resolve()
        if manifest.exists():
            for relative, target in json.loads(manifest.read_text()).items():
                link = runtime / relative
                resolved = (link.parent / target).resolve()
                if not link.parent.resolve().is_relative_to(runtime) or not resolved.is_relative_to(runtime):
                    raise RuntimeError("运行时链接清单包含无效路径。")
                if not link.exists() and not link.is_symlink():
                    link.parent.mkdir(parents=True, exist_ok=True)
                    link.symlink_to(target)
        executable_manifest = runtime / "executables.json"
        executables = json.loads(executable_manifest.read_text()) if executable_manifest.exists() else ["node/bin/node", "node/bin/pi", "node/bin/npm", "node/bin/npx", "stt/bin/sherpa-onnx-offline"]
        for relative in executables:
            path = runtime / relative
            if not path.resolve().is_relative_to(runtime):
                raise RuntimeError("运行时可执行文件清单包含无效路径。")
            if path.exists():
                path.chmod(path.stat().st_mode | 0o111)

    async def _main(self):
        self.ready = asyncio.Event()
        self.init_error = None
        settings = Path(decky.DECKY_PLUGIN_SETTINGS_DIR)
        log_dir = Path(decky.DECKY_PLUGIN_LOG_DIR or (Path(decky.DECKY_PLUGIN_RUNTIME_DIR) / "logs"))
        debug = logging_setup.debug_enabled(settings)
        log = logging_setup.setup_logging(log_dir, debug=debug, extra_logger=getattr(decky, "logger", None))
        build = collect_build(ROOT)
        try:
            self.service = AgentService(
                ROOT, settings,
                Path(decky.DECKY_PLUGIN_RUNTIME_DIR), Path(decky.DECKY_USER_HOME or os.environ["HOME"]),
                self._emit,
            )
            report = self.service.runtime_report()
            log.info("插件启动 build=%s commit=%s builtAt=%s source=%s uid=%s python=%s decky=%s debug=%s",
                     build["id"], build["commit"], build["builtAt"], build["source"], os.geteuid(),
                     sys.version.split()[0], getattr(decky, "DECKY_VERSION", "") or "未知", debug)
            log.info("运行环境 pi=%s node=%s stt=%s capture=%s logDir=%s",
                     report["piVersion"], report["node"] or "缺失",
                     "已就绪" if report["sttEngine"] else "缺失",
                     report["captureTool"] or "缺失", logging_setup.log_directory())
        except Exception:
            self.init_error = "后端启动失败，请查看 Decky 插件日志，检查配置和数据文件。"
            log.exception("Deck Agent 后端启动失败 build=%s", build["id"])
        finally:
            self.ready.set()

    async def _emit(self, event):
        await decky.emit("deck_agent_event", event)

    async def request(self, action: str, payload: dict):
        if not hasattr(self, "ready"):
            return {"ok": False, "error": "插件正在启动，请稍后重试。"}
        await self.ready.wait()
        if self.init_error:
            return {"ok": False, "error": self.init_error}
        try:
            return {"ok": True, "value": await self.service.request(action, payload)}
        except Exception as exc:
            error = self.service.safe_error(exc)
            decky.logger.error("Deck Agent request(%s) 失败：%s", action, error)
            return {"ok": False, "error": error}

    async def _unload(self):
        logging_setup.logger_for().info("插件卸载")
        if hasattr(self, "service"):
            await self.service.close()

    async def _uninstall(self):
        # 用户配置、会话、语音模型保留在 Decky 的独立持久目录。
        pass
