import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from backend.service import AgentService
from backend.storage import read_json

ROOT = Path(__file__).resolve().parents[1]


class SessionFeatureTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        p = Path(self.tmp.name)
        self.service = AgentService(ROOT, p / 'settings', p / 'data', p, AsyncMock())

    async def asyncTearDown(self):
        await self.service.close()
        self.tmp.cleanup()

    async def test_user_abort_is_stopped_and_does_not_leave_error_banner(self):
        sid = (await self.service.request('create_session', {}))['id']
        item = self.service.storage.session(sid)
        item['status'] = 'stopped'
        self.service.messages[sid] = [
            {'role': 'user', 'content': '检查设备'},
            {'role': 'assistant', 'content': [], 'stopReason': 'error', 'errorMessage': 'this operation was aborted'},
        ]
        await self.service.handle_event(sid, {'type': 'agent_settled'})
        self.assertEqual(item['status'], 'stopped')
        self.assertNotIn('error', item)
        self.assertFalse(any(call.args[0].get('type') == 'notice' for call in self.service.emit.call_args_list))
        snapshot = await self.service.snapshot(sid)
        message = snapshot['active']['messages'][-1]
        self.assertTrue(message['userInterrupted'])
        self.assertNotIn('errorMessage', message)
        self.assertEqual(self.service.messages[sid][-1]['errorMessage'], 'this operation was aborted')

    async def test_genuine_model_error_is_not_hidden_by_abort_handling(self):
        sid = (await self.service.request('create_session', {}))['id']
        self.service.messages[sid] = [{'role': 'assistant', 'content': [], 'stopReason': 'error', 'errorMessage': 'API request failed: 503'}]
        await self.service.handle_event(sid, {'type': 'agent_settled'})
        self.assertEqual(self.service.storage.session(sid)['status'], 'error')
        self.assertEqual((await self.service.snapshot(sid))['active']['messages'][-1]['errorMessage'], 'API request failed: 503')

    async def test_enabled_models_persist_filter_and_reject_disabled_switch(self):
        await self.service.save_provider({'id': 'test', 'model': 'one', 'enabledModels': ['one', 'two'], 'key': 'fixture', 'custom': True, 'baseUrl': 'http://localhost:9/v1'})
        provider = self.service.provider_view()[0]
        self.assertEqual(provider['enabledModels'], ['one', 'two'])
        native = read_json(self.service.storage.agent / 'models.json')['providers']['test']['models']
        self.assertEqual({m['id'] for m in native}, {'one', 'two'})
        sid = (await self.service.request('create_session', {}))['id']
        process = AsyncMock()
        process.config_revision = self.service.model_config_revision
        process.call.return_value = {'models': [{'provider': 'test', 'id': m} for m in ('one', 'two', 'disabled')]}
        self.service.ensure = AsyncMock(return_value=process)
        result = await self.service.request('models', {'sessionId': sid})
        self.assertEqual([m['id'] for m in result['models']], ['one', 'two'])
        with self.assertRaisesRegex(ValueError, '未在供应商'):
            await self.service.request('set_model', {'sessionId': sid, 'provider': 'test', 'model': 'disabled'})
        with self.assertRaises(ValueError):
            await self.service.save_provider({'id': 'test', 'model': 'one', 'enabledModels': []})
        self.assertEqual(self.service.provider_view()[0]['enabledModels'], ['one', 'two'])

    async def test_first_send_names_once_and_manual_name_stays(self):
        sid = (await self.service.request('create_session', {}))['id']
        item = self.service.storage.session(sid)
        item.update(provider='test', model='chat')
        process = AsyncMock()
        process.call.return_value = {'disposition': 'started'}
        self.service.ensure = AsyncMock(return_value=process)
        self.service.generate_title = AsyncMock()
        await self.service.request('send', {'sessionId': sid, 'text': '帮我整理游戏库\n给出建议'})
        await asyncio.sleep(0)
        self.assertEqual(item['name'], '帮我整理游戏库 给出建议')
        self.service.generate_title.assert_awaited_once_with(sid, '帮我整理游戏库\n给出建议')
        await self.service.request('session_meta', {'sessionId': sid, 'name': '我的标题'})
        await self.service.request('send', {'sessionId': sid, 'text': '继续'})
        self.assertEqual(item['name'], '我的标题')
        self.service.generate_title.assert_awaited_once()

    async def test_title_model_follows_session_override_and_rename_race(self):
        sid = (await self.service.request('create_session', {}))['id']
        item = self.service.storage.session(sid)
        item.update(provider='chat-provider', model='chat-model')
        self.service.node = lambda: 'node'
        for override in (None, {'provider': 'title-provider', 'model': 'small'}):
            self.service.storage.preferences['titleModel'] = override
            item['autoTitle'] = True
            process = AsyncMock()
            process.returncode = 0
            process.communicate.return_value = (json.dumps({'title': '  “设备状态检查”  '}).encode(), b'')
            with patch('asyncio.create_subprocess_exec', return_value=process):
                await self.service.generate_title(sid, '检查设备')
            sent = json.loads(process.communicate.call_args.args[0])
            self.assertEqual(sent['provider'], override['provider'] if override else 'chat-provider')
            self.assertEqual(sent['model'], override['model'] if override else 'chat-model')
            self.assertEqual(item['name'], '设备状态检查')
        item['autoTitle'] = True
        async def delayed(_):
            item['name'], item['autoTitle'] = '用户手动名称', False
            return b'{"title":"automatic"}', b''
        process.communicate.side_effect = delayed
        with patch('asyncio.create_subprocess_exec', return_value=process):
            await self.service.generate_title(sid, '检查设备')
        self.assertEqual(item['name'], '用户手动名称')

    async def test_title_failure_keeps_fallback_and_model_removal_resets_setting(self):
        await self.service.save_provider({'id': 'test', 'model': 'one', 'enabledModels': ['one', 'two'], 'key': 'fixture', 'custom': True, 'baseUrl': 'http://localhost:9/v1'})
        await self.service.request('preferences', {'titleModel': {'provider': 'test', 'model': 'two'}})
        await self.service.save_provider({'id': 'test', 'model': 'one', 'enabledModels': ['one'], 'custom': True, 'baseUrl': 'http://localhost:9/v1'})
        self.assertIsNone(self.service.storage.preferences['titleModel'])
        sid = (await self.service.request('create_session', {}))['id']
        item = self.service.storage.session(sid)
        item['name'] = '首条消息摘要'
        with patch('asyncio.create_subprocess_exec', side_effect=RuntimeError('network')):
            self.service.node = lambda: 'node'
            await self.service.generate_title(sid, '首条消息摘要')
        self.assertEqual(item['name'], '首条消息摘要')
