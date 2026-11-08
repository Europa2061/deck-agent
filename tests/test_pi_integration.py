"""使用真实 Pi 进程、原生工具与原生会话；模型由 Pi 自带 faux provider 提供。"""
import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path

from backend.service import AgentService
from backend.storage import write_json

ROOT = Path(__file__).resolve().parents[1]
PI = ROOT / "runtime/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js"


@unittest.skipUnless(PI.exists(), "先执行 npm ci --prefix runtime 安装固定版本 Pi")
class PiIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name)
        self.previous_dev = os.environ.get("DECK_AGENT_DEV")
        os.environ["DECK_AGENT_DEV"] = "1"
        self.events = []

        async def emit(event):
            self.events.append(event)

        self.service = AgentService(ROOT, self.directory / "settings", self.directory / "data", self.directory, emit)
        extension = self.service.storage.agent / "extensions/test.js"
        extension.parent.mkdir()
        ai = (ROOT / "runtime/node_modules/@earendil-works/pi-ai/dist/index.js").as_uri()
        extension.write_text('''
export default async function(pi) {
  const {fauxProvider,fauxAssistantMessage,fauxToolCall}=await import(AI_URL);
  const fake=fauxProvider({provider:'deck-test',models:[{id:'test',name:'Local test'}],tokensPerSecond:10000});
  fake.setResponses([
    fauxAssistantMessage(fauxToolCall('write',{path:'proof.txt',content:'真实 Pi 工具已执行'}),{stopReason:'toolUse'}),
    fauxAssistantMessage(fauxToolCall('bash',{command:"printf '真实 shell 命令已执行' > shell-proof.txt"}),{stopReason:'toolUse'}),
    fauxAssistantMessage('测试任务已完成')
  ]);
  pi.registerProvider(fake.provider);
  pi.registerCommand('deck-test-confirm',{
    description:'测试原生 GUI 请求',
    handler:async(args,ctx)=>{const confirmed=await ctx.ui.confirm('测试确认','是否继续？');ctx.ui.notify(confirmed?'confirmed':'cancelled','info');}
  });
}
'''.replace("AI_URL", json.dumps(ai)))
        write_json(self.service.storage.agent / "settings.json", {"defaultProvider": "deck-test", "defaultModel": "test"})

    async def asyncTearDown(self):
        await self.service.close()
        self.tmp.cleanup()
        if self.previous_dev is None:
            os.environ.pop("DECK_AGENT_DEV", None)
        else:
            os.environ["DECK_AGENT_DEV"] = self.previous_dev

    async def wait_for(self, predicate):
        async with asyncio.timeout(15):
            while not predicate():
                await asyncio.sleep(0.025)

    async def test_new_draft_model_is_applied_on_first_real_session_start(self):
        extension = self.service.storage.agent / "extensions/test.js"
        extension.write_text(extension.read_text().replace("name:'Local test'", "name:'Local test',reasoning:true"))
        await self.service.request("set_model", {"sessionId": "__new__", "provider": "deck-test", "model": "test", "thinking": "low"})
        self.assertFalse(self.service.processes)
        item = await self.service.request("create_session", {"fromDraft": True, "text": "首条提交"})
        self.assertEqual(self.service.storage.session(item["id"])["draft"], "首条提交")
        process = await self.service.ensure(item["id"])
        state = await process.call("get_state")
        self.assertEqual(state["model"]["provider"], "deck-test")
        self.assertEqual(state["model"]["id"], "test")
        self.assertEqual(state["thinkingLevel"], "low")

    async def test_real_abort_is_an_inline_user_interruption(self):
        extension = self.service.storage.agent / 'extensions/test.js'
        source = extension.read_text().replace('tokensPerSecond:10000', 'tokensPerSecond:1')
        start = source.index('  fake.setResponses([')
        end = source.index('  pi.registerProvider', start)
        source = source[:start] + "  fake.setResponses([fauxAssistantMessage('等待用户中断的慢速回复，请停止这个任务。')]);\n" + source[end:]
        extension.write_text(source)
        sid = (await self.service.request('create_session', {}))['id']
        await self.service.request('send', {'sessionId': sid, 'text': '取消测试'})
        await self.wait_for(lambda: self.service.storage.session(sid)['status'] == 'running')
        await self.service.request('stop', {'sessionId': sid})
        await self.wait_for(lambda: sid not in self.service.run_started)
        snapshot = await self.service.snapshot(sid)
        self.assertEqual(snapshot['sessions'][0]['status'], 'stopped')
        self.assertNotIn('error', snapshot['sessions'][0])
        self.assertTrue(any(message.get('userInterrupted') for message in snapshot['active']['messages']))

    async def test_real_tool_execution_and_history_resume_without_replay(self):
        session = await self.service.request("create_session", {})
        session_id = session["id"]
        await self.service.request("open_session", {"sessionId": session_id})
        response = await self.service.request("send", {"sessionId": session_id, "text": "写入测试文件"})
        self.assertEqual(response["disposition"], "started")
        target = self.directory / "DeckAgent/proof.txt"
        await self.wait_for(lambda: target.exists() and self.service.storage.session(session_id)["status"] == "idle")
        self.assertEqual(target.read_text(), "真实 Pi 工具已执行")
        self.assertEqual((target.parent / "shell-proof.txt").read_text(), "真实 shell 命令已执行")
        await self.service.reconcile(session_id)
        messages = self.service.messages[session_id]
        self.assertTrue(any(m.get("role") == "toolResult" and m.get("toolName") == "write" for m in messages))
        saved_file = Path(self.service.storage.session(session_id)["file"])
        self.assertTrue(saved_file.is_file())
        old_mtime = target.stat().st_mtime_ns
        await self.service.save_provider({"id": "local-history", "model": "history-model", "key": "test-placeholder", "custom": True, "baseUrl": "http://127.0.0.1:9/v1"})
        await self.service.request("models", {"sessionId": session_id})
        self.assertEqual(target.stat().st_mtime_ns, old_mtime)
        self.assertTrue(self.service.messages[session_id])
        process = self.service.processes.pop(session_id)
        await process.close()
        self.service.messages.pop(session_id, None)
        snapshot = await self.service.request("open_session", {"sessionId": session_id})
        self.assertTrue(snapshot["active"]["messages"])
        self.assertEqual(target.stat().st_mtime_ns, old_mtime)

    async def test_provider_change_does_not_restart_busy_session(self):
        session = await self.service.request("create_session", {})
        sid = session["id"]
        process = await self.service.ensure(sid)
        self.service.storage.session(sid)["status"] = "running"
        await self.service.save_provider({"id": "local-busy", "model": "busy-model", "key": "test-placeholder", "custom": True, "baseUrl": "http://127.0.0.1:9/v1"})
        self.assertIs(await self.service.ensure(sid), process)
        self.assertTrue(process.alive())
        with self.assertRaisesRegex(ValueError, "等待当前任务"):
            await self.service.request("models", {"sessionId": sid})
        self.service.storage.session(sid)["status"] = "idle"
        models = await self.service.request("models", {"sessionId": sid})
        self.assertTrue(any(m["provider"] == "local-busy" for m in models["models"]))

    async def test_saved_provider_appears_in_existing_session_and_can_be_selected(self):
        session = await self.service.request("create_session", {})
        sid = session["id"]
        await self.service.request("open_session", {"sessionId": sid})
        await self.service.save_provider({"id": "local-added", "name": "Local added", "model": "local-model", "key": "test-placeholder", "custom": True, "baseUrl": "http://127.0.0.1:9/v1", "api": "openai-completions"})
        catalog = await self.service.catalog(refresh=True)
        self.assertTrue(any(m["provider"] == "local-added" for m in catalog["models"]))
        models = await self.service.request("models", {"sessionId": sid})
        self.assertTrue(any(m["provider"] == "local-added" for m in models["models"]), "配置目录有模型，但已有对话的模型列表为空/缺失")
        await self.service.request("set_model", {"sessionId": sid, "provider": "local-added", "model": "local-model"})
        self.assertEqual(self.service.storage.session(sid)["model"], "local-model")

    async def test_two_native_instances_execute_independently(self):
        first = await self.service.request("create_session", {})
        other_cwd = self.directory / "other"
        other_cwd.mkdir()
        second = await self.service.request("create_session", {"cwd": str(other_cwd)})
        await asyncio.gather(*(self.service.request("send", {"sessionId": s["id"], "text": "执行测试"}) for s in (first, second)))
        await self.wait_for(lambda: all(self.service.storage.session(s["id"])["status"] == "idle" for s in (first, second)))
        self.assertTrue((self.directory / "DeckAgent/proof.txt").exists())
        self.assertTrue((other_cwd / "proof.txt").exists())
        self.assertNotEqual(self.service.processes[first["id"]].process.pid, self.service.processes[second["id"]].process.pid)

    async def test_native_extension_confirm_and_cancel_roundtrip(self):
        session = await self.service.request("create_session", {})
        session_id = session["id"]
        pending_send = asyncio.create_task(self.service.request("send", {"sessionId": session_id, "text": "/deck-test-confirm"}))
        await self.wait_for(lambda: bool(self.service.ui_requests.get(session_id)))
        request_id = next(iter(self.service.ui_requests[session_id]))
        self.assertEqual(self.service.storage.session(session_id)["status"], "waiting")
        await self.service.request("ui_response", {"sessionId": session_id, "requestId": request_id, "cancelled": True})
        response = await pending_send
        self.assertEqual(response["disposition"], "handled")
        self.assertTrue(any(e.get("message") == "cancelled" for e in self.events))
        self.assertEqual(self.service.storage.session(session_id)["status"], "idle")

    async def test_player_tools_use_real_cli_and_builtin_skills_are_discoverable(self):
        environment = self.service.environment
        self.service.environment = lambda agent_dir=None: {
            **environment(agent_dir), 'DECK_AGENT_EMBEDDED_PYTHON': '1',
            'PYTHONHOME': str(self.directory / 'missing-python-home'),
            '_PYI_APPLICATION_HOME_DIR': str(self.directory / 'missing-pyinstaller-home'),
        }
        target = self.directory / 'player-save.sav'
        target.write_text('test progress')
        import zipfile
        archive = self.directory / 'sample-plugin.zip'
        with zipfile.ZipFile(archive, 'w') as stream:
            stream.writestr('sample/plugin.json', json.dumps({'name': 'Test Sample', 'author': 'Test'}))
            stream.writestr('sample/package.json', json.dumps({'version': '1.0.0'}))
            stream.writestr('sample/dist/index.js', '')
        extension = self.service.storage.agent / 'extensions/test.js'
        source = extension.read_text()
        start = source.index('  fake.setResponses([')
        end = source.index('  pi.registerProvider', start)
        calls = [
            ('deck_games', {'action': 'list'}),
            ('deck_saves', {'action': 'path_backup', 'paths': [str(target)], 'label': 'integration'}),
            ('deck_mods', {'action': 'inspect', 'archive': str(archive)}),
            ('deck_plugins', {'action': 'prepare', 'archive': str(archive)}),
        ]
        source = source[:start] + '  fake.setResponses([\n' + ',\n'.join(
            '    fauxAssistantMessage(fauxToolCall(' + json.dumps(name) + ',' + json.dumps(params) + "),{stopReason:'toolUse'})" for name, params in calls
        ) + ",\n    fauxAssistantMessage('玩家工具验证结束')\n  ]);\n" + source[end:]
        extension.write_text(source)
        sid = (await self.service.request('create_session', {}))['id']
        await self.service.request('send', {'sessionId': sid, 'text': '测试内置玩家工具'})
        await self.wait_for(lambda: sid not in self.service.run_started and self.service.storage.session(sid)['status'] == 'idle')
        await self.service.reconcile(sid)
        results = [m for m in self.service.messages[sid] if m.get('role') == 'toolResult']
        self.assertEqual([r['toolName'] for r in results], [name for name, _ in calls])
        self.assertFalse(any(r.get('isError') for r in results), results)
        self.assertTrue(self.service.player_store.list('backup'))
        self.assertEqual(self.service.player_store.list('plugin-install')[0]['manifest']['name'], 'Test Sample')
        commands = await self.service.request('commands', {'sessionId': sid})
        names = {c['name'] for c in commands['commands']}
        for skill in ('game-care', 'save-care', 'mod-care', 'decky-plugins'):
            self.assertIn('skill:' + skill, names)

    async def test_builtin_config_tool_waits_for_gui_and_respects_cancel(self):
        target = self.directory / 'game.ini'
        target.write_text('quality=high\n')
        extension = self.service.storage.agent / 'extensions/test.js'
        source = extension.read_text()
        start = source.index('  fake.setResponses([')
        end = source.index('  pi.registerProvider', start)
        params = {'action': 'config_apply', 'file': str(target), 'old': 'quality=high', 'new': 'quality=medium'}
        source = source[:start] + "  fake.setResponses([fauxAssistantMessage(fauxToolCall('deck_games'," + json.dumps(params) + "),{stopReason:'toolUse'}),fauxAssistantMessage('已按用户选择处理')]);\n" + source[end:]
        extension.write_text(source)
        sid = (await self.service.request('create_session', {}))['id']
        await self.service.request('send', {'sessionId': sid, 'text': '测试取消配置修改'})
        await self.wait_for(lambda: bool(self.service.ui_requests.get(sid)))
        self.assertEqual(target.read_text(), 'quality=high\n')
        request = next(iter(self.service.ui_requests[sid].values()))
        self.assertEqual(request['method'], 'confirm')
        await self.service.request('ui_response', {'sessionId': sid, 'requestId': request['id'], 'value': False})
        await self.wait_for(lambda: sid not in self.service.run_started)
        self.assertEqual(target.read_text(), 'quality=high\n')
        self.assertFalse(self.service.player_store.list('config-backup'))

    async def test_mod_install_confirmation_and_plugin_queue_use_real_tools(self):
        import zipfile
        game = self.directory / 'game'
        game.mkdir()
        archive = self.directory / 'mod.zip'
        with zipfile.ZipFile(archive, 'w') as stream:
            stream.writestr('Mods/demo.txt', 'installed by actual Pi tool')
        extension = self.service.storage.agent / 'extensions/test.js'
        source = extension.read_text()
        start = source.index('  fake.setResponses([')
        end = source.index('  pi.registerProvider', start)
        params = {'action': 'install', 'archive': str(archive), 'target': str(game), 'name': 'integration-mod'}
        source = source[:start] + "  fake.setResponses([fauxAssistantMessage(fauxToolCall('deck_mods'," + json.dumps(params) + "),{stopReason:'toolUse'}),fauxAssistantMessage('文件已部署，等待实际游戏验证')]);\n" + source[end:]
        extension.write_text(source)
        sid = (await self.service.request('create_session', {}))['id']
        await self.service.request('send', {'sessionId': sid, 'text': '测试确认 Mod 部署'})
        await self.wait_for(lambda: bool(self.service.ui_requests.get(sid)))
        self.assertFalse((game / 'Mods/demo.txt').exists())
        pending = next(iter(self.service.ui_requests[sid].values()))
        await self.service.request('ui_response', {'sessionId': sid, 'requestId': pending['id'], 'value': True})
        await self.wait_for(lambda: sid not in self.service.run_started)
        self.assertEqual((game / 'Mods/demo.txt').read_text(), 'installed by actual Pi tool')
        self.assertEqual(self.service.player_store.list('mod')[0]['status'], 'enabled')
        from backend.workflows import plugins
        plugin = self.directory / 'plugin.zip'
        with zipfile.ZipFile(plugin, 'w') as stream:
            stream.writestr('sample/plugin.json', json.dumps({'name': 'Player Tools Test'}))
            stream.writestr('sample/package.json', json.dumps({'version': '1.0.0'}))
            stream.writestr('sample/dist/index.js', '')
        record = plugins.prepare(self.service.player_store, {'archive': str(plugin)})
        plugins.queue(self.service.player_store, record['id'])
        self.assertEqual((await self.service.snapshot())['pluginInstalls'][0]['name'], 'Player Tools Test')
        claimed = await self.service.request('player_plugin_claim', {'ticket': record['id']})
        self.assertEqual(claimed['name'], 'Player Tools Test')
        self.assertFalse((await self.service.snapshot())['pluginInstalls'])
        await self.service.request('player_plugin_failed', {'ticket': record['id'], 'error': 'native test failure'})
        self.assertEqual((await self.service.snapshot())['pluginInstalls'][0]['error'], 'native test failure')
