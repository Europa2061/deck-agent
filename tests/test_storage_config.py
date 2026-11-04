import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from backend.service import AgentService
from backend.storage import Storage, read_json, write_json
from backend.updates import version_key

ROOT = Path(__file__).resolve().parents[1]


class StorageTests(unittest.TestCase):
    def test_restart_marks_busy_sessions_interrupted_without_replaying(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            store = Storage(p / "settings", p / "data", p)
            store.sessions = [{"id": "test", "status": "running", "draft": "未发送", "file": "x"}]
            store.save_sessions()
            restored = Storage(p / "settings", p / "data", p)
            self.assertEqual(restored.sessions[0]["status"], "interrupted")
            self.assertEqual(restored.sessions[0]["draft"], "未发送")

    def test_legacy_abort_banner_is_migrated_without_hiding_other_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            store = Storage(p / 'settings', p / 'data', p)
            store.sessions = [{'id': 'cancel', 'status': 'error', 'error': 'This operation was aborted'},
                              {'id': 'network', 'status': 'error', 'error': 'HTTP 503'}]
            store.save_sessions()
            restored = Storage(store.settings, store.data, p)
            self.assertEqual(restored.sessions[0]['status'], 'stopped')
            self.assertNotIn('error', restored.sessions[0])
            self.assertEqual(restored.sessions[1]['error'], 'HTTP 503')

    def test_secret_files_are_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "auth.json"
            write_json(path, {"key": "test"})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_semver_numeric_order_and_prerelease(self):
        self.assertGreater(version_key("v0.10.0"), version_key("v0.9.0"))
        self.assertGreater(version_key("1.0.0"), version_key("1.0.0-beta.1"))
        with self.assertRaises(ValueError):
            version_key("latest")


class ConfigTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        p = Path(self.tmp.name)
        self.service = AgentService(ROOT, p / "settings", p / "data", p, AsyncMock())

    async def asyncTearDown(self):
        await self.service.close()
        self.tmp.cleanup()

    async def test_reply_unread_acknowledges_only_seen_revision_and_persists(self):
        sid = (await self.service.request("create_session", {}))["id"]
        message = {"role": "assistant", "content": [{"type": "text", "text": "回复"}]}
        await self.service.handle_event(sid, {"type": "message_update", "message": message})
        self.assertFalse((await self.service.snapshot())["sessions"][0]["unread"])
        await self.service.handle_event(sid, {"type": "message_end", "message": message})
        first = (await self.service.snapshot())["sessions"][0]
        self.assertTrue(first["unread"])
        await self.service.handle_event(sid, {"type": "message_end", "message": message})
        await self.service.request("mark_read", {"sessionId": sid, "replyVersion": first["replyVersion"]})
        current = (await self.service.snapshot())["sessions"][0]
        self.assertTrue(current["unread"], "旧页面的已读请求不能清除较新的回复")
        await self.service.request("mark_read", {"sessionId": sid, "replyVersion": current["replyVersion"]})
        self.assertFalse((await self.service.snapshot())["sessions"][0]["unread"])
        saved = read_json(self.service.storage.metadata_path)[0]
        self.assertEqual(saved["readVersion"], saved["replyVersion"])

    async def test_tool_output_does_not_create_unread_reply(self):
        sid = (await self.service.request("create_session", {}))["id"]
        for message in ({"role": "toolResult", "content": "工具输出"}, {"role": "assistant", "content": [{"type": "toolCall", "name": "bash"}]}):
            await self.service.handle_event(sid, {"type": "message_end", "message": message})
        self.assertFalse((await self.service.snapshot())["sessions"][0]["unread"])

    async def test_diagnostics_reports_build_paths_and_logs_without_secrets(self):
        write_json(self.service.storage.agent / "auth.json", {"test": {"type": "api_key", "key": "diagnostics-secret"}})
        info = await self.service.request("diagnostics", {})
        self.assertEqual(info["build"], self.service.build)
        self.assertEqual(info["version"], self.service.build["version"])
        self.assertIn("logs", info["paths"])
        self.assertIn("nodeVersion", info["runtime"])
        self.assertIsInstance(info["logs"]["recentErrors"], list)
        self.assertEqual(info["activeProcesses"], 0)
        self.assertNotIn("diagnostics-secret", json.dumps(info))

    async def test_provider_save_preserves_native_fields_and_hides_key(self):
        agent = self.service.storage.agent
        write_json(agent / "auth.json", {"other": {"type": "api_key", "key": "other-secret"}})
        write_json(agent / "settings.json", {"extensions": ["./my-extension.ts"], "customField": True})
        await self.service.save_provider({"id": "test", "key": "test-secret", "model": "test-model", "thinking": "low"})
        self.assertIn("other", read_json(agent / "auth.json"))
        self.assertTrue(read_json(agent / "settings.json")["customField"])
        view = json.dumps(await self.service.snapshot())
        self.assertNotIn("test-secret", view)
        self.assertNotIn("other-secret", view)
        self.assertEqual(self.service.safe_error("failed with test-secret"), "failed with [已隐藏]")

    async def test_invalid_custom_provider_does_not_write_partial_credentials(self):
        with self.assertRaises(ValueError):
            await self.service.save_provider({"id": "test", "key": "secret", "model": "test", "custom": True})
        self.assertEqual(read_json(self.service.storage.agent / "auth.json"), {})

    async def test_new_session_draft_survives_restart_without_session_or_process(self):
        await self.service.request("draft", {"sessionId": "__new__", "text": "尚未发送"})
        await self.service.voice_draft("__new__", "语音补充")
        await self.service.request("set_model", {"sessionId": "__new__", "provider": "test", "model": "m", "thinking": "low"})
        self.assertEqual(await self.service.request("commands", {"sessionId": "__new__"}), {"commands": []})
        restored = Storage(self.service.storage.settings, self.service.storage.data, self.service.storage.home)
        self.assertEqual(restored.new_draft["draft"], "尚未发送 语音补充")
        self.assertEqual(restored.sessions, [])
        self.assertFalse(self.service.processes)
        snapshot = await self.service.snapshot()
        self.assertEqual(snapshot["newSessionDraft"], "尚未发送 语音补充")
        self.assertEqual(snapshot["newSessionModel"]["model"], "m")
        created = await self.service.request("create_session", {"fromDraft": True})
        self.assertEqual(self.service.storage.session(created["id"])["model"], "m")
        self.assertEqual(len(self.service.storage.sessions), 1)

    async def test_voice_draft_returns_to_origin_session_without_sending(self):
        one = await self.service.request("create_session", {})
        two = await self.service.request("create_session", {})
        self.service.storage.session(one["id"])["draft"] = "原草稿"
        await self.service.voice_draft(one["id"], "语音文字")
        self.assertEqual(self.service.storage.session(one["id"])["draft"], "原草稿 语音文字")
        self.assertEqual(self.service.storage.session(two["id"])["draft"], "")
        self.assertFalse(self.service.processes)

    async def test_extension_response_checks_origin_instance_and_cancellation(self):
        item = await self.service.request("create_session", {})
        process = AsyncMock()
        self.service.processes[item["id"]] = process
        request = {"type": "extension_ui_request", "id": "req", "method": "confirm", "title": "确认"}
        await self.service.handle_event(item["id"], request)
        with self.assertRaises(ValueError):
            await self.service.request("ui_response", {"sessionId": item["id"], "requestId": "wrong", "value": True})
        await self.service.request("ui_response", {"sessionId": item["id"], "requestId": "req", "cancelled": True})
        process.send.assert_awaited_once_with({"type": "extension_ui_response", "id": "req", "cancelled": True})
        self.assertFalse(self.service.ui_requests[item["id"]])

    async def test_model_data_sent_to_frontend_excludes_system_context(self):
        item = await self.service.request("create_session", {})
        self.service.messages[item["id"]] = [{"role": "system", "content": "internal"}, {"role": "user", "content": "hello"}]
        snap = await self.service.snapshot(item["id"])
        self.assertEqual(snap["active"]["messages"], [{"role": "user", "content": "hello"}])
