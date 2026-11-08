"""在干净 Linux 目录模拟 Decky 解压与首次加载，不使用源码中的运行依赖。"""
import asyncio
import importlib.util
import json
import logging
import os
import subprocess
import sys
import tempfile
import types
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.release_version import package_path


async def main():
    if sys.platform != "linux":
        raise SystemExit("安装包启动检查需要 Linux x64。")
    with tempfile.TemporaryDirectory(prefix="deck-agent-package-") as directory:
        temporary = Path(directory)
        with zipfile.ZipFile(package_path(ROOT)) as archive:
            assert not any(".dev-data" in name or name.endswith("auth.json") or name.startswith("deck-agent/references/") for name in archive.namelist())
            archive.extractall(temporary)
        plugin_root = temporary / "deck-agent"
        stamp = json.loads((plugin_root / "build-info.json").read_text())
        assert stamp.get("version") and stamp.get("id") and stamp.get("builtAt"), "安装包缺少构建标识。"
        print("安装包构建标识：" + stamp["id"] + " " + stamp["builtAt"], flush=True)
        stub = types.ModuleType("decky")
        for name, path in (("DECKY_PLUGIN_SETTINGS_DIR", temporary / "settings"), ("DECKY_PLUGIN_RUNTIME_DIR", temporary / "data"), ("DECKY_PLUGIN_LOG_DIR", temporary / "logs"), ("DECKY_USER_HOME", temporary / "home")):
            setattr(stub, name, str(path))
        stub.DECKY_VERSION = "test"

        async def emit(*args):
            pass

        stub.emit = emit
        stub.logger = logging.getLogger("deck-agent-smoke")
        sys.modules["decky"] = stub
        spec = importlib.util.spec_from_file_location("installed_deck_agent", plugin_root / "main.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        plugin = module.Plugin()
        await plugin._migration()
        env = dict(os.environ)
        env["PATH"] = str(plugin_root / "runtime/node/bin") + ":" + env.get("PATH", "")
        env["LD_LIBRARY_PATH"] = str(plugin_root / "runtime/stt/lib")
        for command in ([str(plugin_root / "runtime/node/bin/node"), "--version"], [str(plugin_root / "runtime/node/bin/npm"), "--version"], [str(plugin_root / "runtime/node/bin/pi"), "--version"]):
            subprocess.run(command, env=env, check=True)
        subprocess.run([str(plugin_root / "runtime/stt/bin/sherpa-onnx-offline"), "--help"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        await plugin._main()
        service = plugin.service
        log_file = temporary / "logs/deck-agent.log"
        assert log_file.is_file() and "插件启动 build=" in log_file.read_text(encoding="utf-8")
        diagnostics = await plugin.request("diagnostics", {})
        assert diagnostics["ok"] and diagnostics["value"]["build"]["builtAt"], diagnostics
        ai = (plugin_root / "runtime/node_modules/@earendil-works/pi-ai/dist/index.js").as_uri()
        extensions = service.storage.agent / "extensions"
        extensions.mkdir()
        (extensions / "test.js").write_text("export default async function(pi){const {fauxProvider,fauxAssistantMessage,fauxToolCall}=await import(" + json.dumps(ai) + ");const fake=fauxProvider({provider:'package-test',models:[{id:'test'}],tokensPerSecond:10000});fake.setResponses([fauxAssistantMessage(fauxToolCall('deck_games',{action:'list'}),{stopReason:'toolUse'}),fauxAssistantMessage(fauxToolCall('write',{path:'proof.txt',content:'package-ok'}),{stopReason:'toolUse'}),fauxAssistantMessage('done')]);pi.registerProvider(fake.provider);}")
        (service.storage.agent / "settings.json").write_text(json.dumps({"defaultProvider": "package-test", "defaultModel": "test"}))
        try:
            created = await plugin.request("create_session", {})
            assert created["ok"], created
            session_id = created["value"]["id"]
            sent = await plugin.request("send", {"sessionId": session_id, "text": "测试安装包"})
            assert sent["ok"], sent
            proof = temporary / "home/DeckAgent/proof.txt"
            async with asyncio.timeout(30):
                while not (proof.exists() and service.storage.session(session_id)["status"] == "idle"):
                    state = service.storage.session(session_id)
                    if state["status"] in ("error", "interrupted"):
                        raise RuntimeError(state.get("error", state["status"]))
                    await asyncio.sleep(0.05)
            assert proof.read_text() == "package-ok"
            await service.reconcile(session_id)
            result = next(message for message in service.messages[session_id] if message.get("role") == "toolResult" and message.get("toolName") == "deck_games")
            assert not result.get("isError"), result
            commands = await plugin.request("commands", {"sessionId": session_id})
            names = {command["name"] for command in commands["value"]["commands"]}
            assert {"skill:game-care", "skill:save-care", "skill:mod-care", "skill:decky-plugins"}.issubset(names), names
            print("干净安装包检查通过：Node、npm、Pi、STT、原生/玩家工具执行、四个 Skills 与退出清理。", flush=True)
        finally:
            await plugin._unload()


if __name__ == "__main__":
    asyncio.run(main())
