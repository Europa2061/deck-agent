"""真实 Pi 命名请求连本机模拟服务；不调用外部模型，不产生费用。"""
import asyncio
import http.server
import json
import os
import shutil
import tempfile
import threading
import unittest
from pathlib import Path

from backend.storage import write_json

ROOT = Path(__file__).resolve().parents[1]
PI = ROOT / 'runtime/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js'


@unittest.skipUnless(PI.exists() and shutil.which('node'), '需要项目固定版本 Pi 运行时')
class TitleRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_title_request_uses_selected_model_without_tools(self):
        seen = []
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                seen.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.end_headers()
                for delta, finish in (({'role': 'assistant', 'content': '整理游戏库'}, None), ({}, 'stop')):
                    payload = {'id': 'fixture', 'object': 'chat.completion.chunk', 'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}
                    self.wfile.write(('data: ' + json.dumps(payload) + '\n\n').encode())
                self.wfile.write(b'data: [DONE]\n\n')
                self.wfile.flush()
            def log_message(self, *_):
                pass
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                p = Path(directory)
                write_json(p / 'models.json', {'providers': {'title-fixture': {'api': 'openai-completions', 'baseUrl': f'http://127.0.0.1:{server.server_port}/v1', 'models': [{'id': 'title-small', 'contextWindow': 4096, 'maxTokens': 128, 'reasoning': False}]}}})
                write_json(p / 'auth.json', {'title-fixture': {'type': 'api_key', 'key': 'test-fixture'}})
                process = await asyncio.create_subprocess_exec(shutil.which('node'), str(ROOT / 'runtime/title.mjs'), stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env={**os.environ, 'PI_CODING_AGENT_DIR': directory})
                try:
                    stdout, stderr = await asyncio.wait_for(process.communicate(json.dumps({'provider': 'title-fixture', 'model': 'title-small', 'text': '请帮我整理游戏库'}).encode()), 30)
                finally:
                    if process.returncode is None:
                        process.kill()
                        await process.wait()
                self.assertEqual(process.returncode, 0, stderr.decode())
                self.assertEqual(json.loads(stdout)['title'], '整理游戏库')
                self.assertEqual(seen[0]['model'], 'title-small')
                self.assertFalse(seen[0].get('tools'))
                self.assertEqual(len(seen[0]['messages']), 2)
        finally:
            await asyncio.to_thread(server.shutdown)
            server.server_close()
            thread.join(2)
