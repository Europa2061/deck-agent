import asyncio
import hashlib
import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from backend.voice import VoiceService, download_ssl_context, pipewire_environment

ROOT = Path(__file__).resolve().parents[1]


class DownloadResponse(io.BytesIO):
    status = 200
    headers = {}


class VoiceDownloadTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.voice = VoiceService(ROOT, Path(self.tmp.name), AsyncMock(), AsyncMock())
        self.voice.manifest = self.voice.legacy_manifest.copy()
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode="w:bz2") as tar:
            for name, value in (("model.int8.onnx", b"test-model-only"), ("tokens.txt", b"test-tokens")):
                member = tarfile.TarInfo("model/" + name)
                member.size = len(value)
                tar.addfile(member, io.BytesIO(value))
        self.content = archive.getvalue()
        self.voice.manifest.update(downloadBytes=len(self.content), requiredFreeBytes=0, sha256=hashlib.sha256(self.content).hexdigest())

    async def asyncTearDown(self):
        await self.voice.close()
        self.tmp.cleanup()

    async def test_verified_download_is_ready_and_failed_hash_is_not(self):
        with patch("urllib.request.urlopen", return_value=DownloadResponse(self.content)):
            await self.voice.download()
        self.assertEqual(self.voice.status, "ready")
        self.assertTrue(self.voice.ready())
        await self.voice.request("voice_delete", {}, {})
        self.voice.manifest["sha256"] = "0" * 64
        with patch("urllib.request.urlopen", return_value=DownloadResponse(self.content)):
            await self.voice.download()
        self.assertEqual(self.voice.status, "error")
        self.assertFalse(self.voice.ready())
        self.assertFalse((self.voice.data / "model.part").exists())

    async def test_server_without_range_support_restarts_instead_of_appending(self):
        (self.voice.data / "model.part").write_bytes(b"old-partial")
        with patch("urllib.request.urlopen", return_value=DownloadResponse(self.content)) as open_url:
            await self.voice.download()
        self.assertTrue(open_url.call_args.args[0].get_header("Range").startswith("bytes="))
        self.assertTrue(self.voice.ready())

    async def test_cancel_keeps_partial_and_does_not_claim_ready(self):
        voice = self.voice

        class CancelResponse(DownloadResponse):
            def read(self, size=-1):
                chunk = super().read(size)
                voice.cancel.set()
                return chunk

        with patch("urllib.request.urlopen", return_value=CancelResponse(self.content)):
            await voice.download()
        self.assertEqual(voice.status, "paused")
        self.assertTrue((voice.data / "model.part").exists())
        self.assertFalse(voice.ready())


class HuggingFaceVoiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.voice = VoiceService(ROOT, Path(self.tmp.name), AsyncMock(), AsyncMock())
        self.files = {'model.int8.onnx': b'fixture-model', 'tokens.txt': b'tokens'}
        self.voice.manifest.update(artifacts=[{'name': k, 'bytes': len(v), 'sha256': hashlib.sha256(v).hexdigest()} for k, v in self.files.items()], downloadBytes=sum(map(len, self.files.values())))

    async def asyncTearDown(self):
        await self.voice.close()
        self.tmp.cleanup()

    def response(self, request, **_):
        return DownloadResponse(self.files[request.full_url.rsplit('/', 1)[-1]])

    async def test_hf_and_mirror_same_pinned_files_verified_with_resume_fallback(self):
        self.voice.model.mkdir(parents=True)
        (self.voice.model / 'model.int8.onnx.part').write_bytes(b'old')
        self.voice.source = 'hf-mirror'
        with patch('urllib.request.urlopen', side_effect=self.response) as download:
            await self.voice.download()
        self.assertTrue(self.voice.ready())
        self.assertTrue(download.call_args_list[0].args[0].get_header('Range').startswith('bytes='))
        for call in download.call_args_list:
            self.assertIn('https://hf-mirror.com/', call.args[0].full_url)
            self.assertIn('/resolve/' + self.voice.manifest['revision'] + '/', call.args[0].full_url)
        await self.voice.request('voice_delete', {}, {})
        self.voice.source = 'huggingface'
        with patch('urllib.request.urlopen', side_effect=self.response) as download:
            await self.voice.download()
        self.assertTrue(self.voice.ready())
        self.assertTrue(download.call_args.args[0].full_url.startswith('https://huggingface.co/'))

    async def test_bad_file_never_ready_and_retry_reuses_verified_file(self):
        original = self.voice.manifest['artifacts'][1]['sha256']
        self.voice.manifest['artifacts'][1]['sha256'] = '0' * 64
        with patch('urllib.request.urlopen', side_effect=self.response):
            await self.voice.download()
        self.assertEqual(self.voice.status, 'error')
        self.assertFalse(self.voice.ready())
        self.assertTrue((self.voice.model / 'model.int8.onnx').exists())
        self.voice.manifest['artifacts'][1]['sha256'] = original
        with patch('urllib.request.urlopen', side_effect=self.response) as download:
            await self.voice.download()
        self.assertTrue(self.voice.ready())
        self.assertEqual(download.call_count, 1)

    async def test_selection_persists_and_whisper_uses_its_own_flags(self):
        await self.voice.request('voice_select', {'modelId': 'whisper-small-int8', 'source': 'hf-mirror'}, {})
        args = self.voice.recognizer_args('zh')
        self.assertIn('--whisper-language=zh', args)
        self.assertTrue(any('small-encoder.int8.onnx' in a for a in args))
        self.assertFalse(any('sense-voice' in a for a in args))
        restored = VoiceService(ROOT, self.voice.data, AsyncMock(), AsyncMock())
        self.assertEqual(restored.model_id, 'whisper-small-int8')
        self.assertEqual(restored.source, 'hf-mirror')
        await restored.close()
        self.voice.status = 'recording'
        with self.assertRaises(ValueError):
            await self.voice.request('voice_select', {'modelId': 'sensevoice-int8'}, {})
        self.voice.status = 'missing'
        with self.assertRaises(ValueError):
            await self.voice.request('voice_select', {'source': 'https://untrusted.example'}, {})

    async def test_paraformer_uses_multilingual_offline_model_arguments(self):
        await self.voice.request('voice_select', {'modelId': 'paraformer-zh-yue-en-int8'}, {})
        manifest = self.voice.manifest
        self.assertEqual(manifest['downloadBytes'], sum(item['bytes'] for item in manifest['artifacts']))
        for language in ('auto', 'zh', 'en'):
            args = self.voice.recognizer_args(language)
            self.assertEqual(args, [f'--paraformer={self.voice.model / "model.int8.onnx"}', f'--tokens={self.voice.model / "tokens.txt"}'])
        self.assertEqual(self.voice.status, 'missing')
        restored = VoiceService(ROOT, self.voice.data, AsyncMock(), AsyncMock())
        self.assertEqual(restored.model_id, 'paraformer-zh-yue-en-int8')
        await restored.close()

    async def test_tiny_selection_moves_to_small_without_deleting_old_files(self):
        import json
        old_model = self.voice.data / 'models' / 'whisper-tiny-int8'
        old_model.mkdir(parents=True)
        (old_model / 'old-model').write_text('keep')
        (self.voice.data / 'selection.json').write_text(json.dumps({'modelId': 'whisper-tiny-int8', 'source': 'hf-mirror'}))
        restored = VoiceService(ROOT, self.voice.data, AsyncMock(), AsyncMock())
        self.assertEqual(restored.model_id, 'whisper-small-int8')
        self.assertEqual(restored.source, 'hf-mirror')
        self.assertEqual(restored.status, 'missing')
        self.assertEqual((old_model / 'old-model').read_text(), 'keep')
        self.assertTrue(any('small-decoder.int8.onnx' in a for a in restored.recognizer_args('auto')))
        await restored.close()

    async def test_cancel_direct_download_keeps_partial_and_can_resume(self):
        voice = self.voice
        class CancelResponse(DownloadResponse):
            def read(self, size=-1):
                result = super().read(size)
                voice.cancel.set()
                return result
        with patch('urllib.request.urlopen', return_value=CancelResponse(self.files['model.int8.onnx'])):
            await voice.download()
        self.assertEqual(voice.status, 'paused')
        self.assertFalse(voice.ready())
        self.assertTrue((voice.model / 'model.int8.onnx.part').exists())
        voice.source = 'hf-mirror'
        with patch('urllib.request.urlopen', side_effect=self.response):
            await voice.download()
        self.assertTrue(voice.ready())


class MicrophoneDeviceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.voice = VoiceService(ROOT, Path(self.tmp.name), AsyncMock(), AsyncMock())

    async def asyncTearDown(self):
        self.voice.process = None
        await self.voice.close()
        self.tmp.cleanup()

    async def test_lists_input_nodes_with_stable_names_and_ignores_other_objects(self):
        import json
        nodes = [
            {'type': 'PipeWire:Interface:Node', 'info': {'props': {'media.class': 'Audio/Source', 'node.name': 'alsa_input.internal', 'node.description': '内置麦克风'}}},
            {'type': 'PipeWire:Interface:Node', 'info': {'props': {'media.class': 'Audio/Source', 'node.name': 'bluez_input.headset', 'node.nick': '耳机'}}},
            {'type': 'PipeWire:Interface:Node', 'info': {'props': {'media.class': 'Audio/Sink', 'node.name': 'speaker'}}},
            {'type': 'PipeWire:Interface:Node', 'info': {'props': {'media.class': 'Audio/Source'}}},
            {'type': 'PipeWire:Interface:Device', 'info': {'props': {'media.class': 'Audio/Source', 'node.name': 'not-a-node'}}},
        ]
        process = AsyncMock()
        process.returncode = 0
        process.communicate.return_value = (json.dumps(nodes).encode(), b'')
        with patch('backend.voice.shutil.which', return_value='/usr/bin/pw-dump'), patch('backend.voice.asyncio.create_subprocess_exec', new=AsyncMock(return_value=process)) as spawn, patch('backend.voice.pipewire_environment', return_value={'XDG_RUNTIME_DIR': '/run/user/1000'}):
            result = await self.voice.request('voice_devices', {}, {})
        self.assertEqual(spawn.call_args.kwargs['env'], {'XDG_RUNTIME_DIR': '/run/user/1000'})
        self.assertEqual(result, [{'id': 'alsa_input.internal', 'name': '内置麦克风'}, {'id': 'bluez_input.headset', 'name': '耳机'}])

    async def test_detection_error_is_reported(self):
        with patch('backend.voice.shutil.which', return_value=None):
            with self.assertRaisesRegex(RuntimeError, '无法读取麦克风列表'):
                await self.voice.request('voice_devices', {}, {})

    async def test_legacy_default_and_selected_device_are_passed_to_recording(self):
        for saved, expected in [('@DEFAULT_AUDIO_SOURCE@', 'auto'), ('alsa_input.internal', 'alsa_input.internal')]:
            process = AsyncMock()
            process.returncode = None
            with patch.object(self.voice, 'ready', return_value=True), patch('pathlib.Path.exists', return_value=True), patch('backend.voice.shutil.which', return_value='/usr/bin/pw-record'), patch('backend.voice.asyncio.create_subprocess_exec', new=AsyncMock(return_value=process)) as spawn, patch('backend.voice.asyncio.sleep', new=AsyncMock()), patch('backend.voice.pipewire_environment', return_value={'XDG_RUNTIME_DIR': '/run/user/1000'}):
                self.voice.status = 'ready'
                await self.voice.request('voice_start', {'sessionId': 'test'}, {'inputDevice': saved})
            self.assertIn('--target=' + expected, spawn.call_args.args)
            self.assertEqual(spawn.call_args.kwargs['env'], {'XDG_RUNTIME_DIR': '/run/user/1000'})
            self.voice.process = None


class DownloadCertificateTests(unittest.TestCase):
    def test_loads_system_trust_without_disabling_tls_verification(self):
        from unittest.mock import Mock
        import ssl
        context = Mock()
        with patch('backend.voice.ssl.create_default_context', return_value=context) as create, patch('backend.voice.Path.is_file', return_value=True):
            self.assertIs(download_ssl_context(), context)
        create.assert_called_once_with()
        context.load_verify_locations.assert_called_once_with(cafile='/etc/ssl/certs/ca-certificates.crt')
        with patch('backend.voice.Path.is_file', return_value=False):
            actual = download_ssl_context()
        self.assertEqual(actual.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(actual.check_hostname)


class PipeWireEnvironmentTests(unittest.TestCase):
    def test_system_service_uses_plugin_users_audio_session(self):
        with patch.dict('os.environ', {'XDG_RUNTIME_DIR': '/run/user/0', 'PIPEWIRE_RUNTIME_DIR': '/run/user/0', 'OTHER': 'keep'}, clear=True), patch('backend.voice.os.getuid', return_value=1000), patch('backend.voice.Path.is_socket', return_value=True):
            env = pipewire_environment()
            self.assertEqual(env['XDG_RUNTIME_DIR'], '/run/user/1000')
            self.assertEqual(env['PIPEWIRE_RUNTIME_DIR'], '/run/user/1000')
            self.assertEqual(env['OTHER'], 'keep')
            self.assertEqual(__import__('os').environ['XDG_RUNTIME_DIR'], '/run/user/0')

    def test_without_session_socket_keeps_original_environment(self):
        with patch.dict('os.environ', {'XDG_RUNTIME_DIR': '/custom/audio'}, clear=True), patch('backend.voice.Path.is_socket', return_value=False):
            self.assertEqual(pipewire_environment(), {'XDG_RUNTIME_DIR': '/custom/audio'})
