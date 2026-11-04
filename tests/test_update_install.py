"""更新包下载、校验与安装交接；不接触真实安装器。"""
import asyncio
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from backend.service import AgentService
from backend.updates import UpdateDownload

ROOT = Path(__file__).resolve().parents[1]


def package(version="0.6.0", extra=None):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, body in {
            "package.json": json.dumps({"name": "deck-agent", "version": version}),
            "plugin.json": json.dumps({"name": "Deck Agent"}),
            "build-info.json": json.dumps({"version": version}),
            "main.py": "", "dist/index.js": "", **(extra or {}),
        }.items():
            archive.writestr("deck-agent/" + name, body)
    return buffer.getvalue()


def release(**changes):
    return {"latest": "v0.6.0", "available": True,
            "zipUrl": "https://github.com/owner/repo/releases/download/v0.6.0/deck-agent-0.6.0.zip",
            "checksumUrl": "https://github.com/owner/repo/releases/download/v0.6.0/deck-agent-0.6.0.zip.sha256", **changes}


class Response(io.BytesIO):
    def __init__(self, body):
        super().__init__(body)
        self.headers = {"Content-Length": str(len(body))}


class DownloadTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.download = UpdateDownload(Path(self.tmp.name) / "updates")

    async def asyncTearDown(self):
        await self.download.close()
        self.tmp.cleanup()

    async def run_download(self, blob=None, checksum=None):
        blob = blob if blob is not None else package()
        sha = checksum or hashlib.sha256(blob).hexdigest()
        with patch.object(self.download, "_open", side_effect=[Response((sha + "  deck-agent-0.6.0.zip\n").encode()), Response(blob)]):
            self.download.start(release())
            await self.download.task

    async def test_download_verify_and_prepare_local_artifact(self):
        await self.run_download()
        self.assertEqual(self.download.snapshot()["status"], "ready")
        result = await self.download.prepare()
        self.assertTrue(result["artifact"].startswith("file:///"))
        path = Path(result["artifact"][7:])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), result["hash"])
        path.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "已变化"):
            await self.download.prepare()

    async def test_checksum_mismatch_removes_partial_and_prevents_install(self):
        await self.run_download(checksum="0" * 64)
        self.assertEqual(self.download.snapshot()["status"], "error")
        self.assertIn("SHA-256", self.download.snapshot()["error"])
        self.assertFalse(list(self.download.directory.glob("*.part")))
        with self.assertRaises(ValueError):
            await self.download.prepare()
        await self.run_download()
        self.assertEqual(self.download.snapshot()["status"], "ready")

    async def test_wrong_version_and_path_traversal_rejected(self):
        for blob in (package("0.7.0"), package(extra={"../escape": "bad"}), b"not a zip"):
            await self.run_download(blob)
            self.assertEqual(self.download.snapshot()["status"], "error")
            self.assertIsNone(self.download.prepared)

    async def test_missing_checksum_and_untrusted_url_rejected(self):
        with self.assertRaisesRegex(ValueError, "校验文件"):
            self.download.start(release(checksumUrl=None))
        for url in ("http://github.com/x/releases/download/a/b", "file:///tmp/x", "https://evil.example/releases/download/a/b"):
            with self.assertRaises(ValueError):
                self.download._open(url)

    async def test_duplicate_download_and_cancellation(self):
        self.download.start(release())
        with self.assertRaisesRegex(ValueError, "已有更新"):
            self.download.start(release())
        self.download.cancel()
        with patch.object(self.download, "_open", side_effect=[Response(("0" * 64).encode()), Response(b"x")]):
            await self.download.task
        self.assertEqual(self.download.snapshot()["status"], "cancelled")
        self.assertFalse(list(self.download.directory.glob("*.part")))


class InstallGuardTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.service = AgentService(ROOT, base / "settings", base / "data", base, AsyncMock())
        self.service.update_download.prepare = AsyncMock(return_value={"artifact": "file:///tmp/update.zip", "hash": "0" * 64, "version": "0.6.0"})

    async def asyncTearDown(self):
        await self.service.close()
        self.tmp.cleanup()

    async def test_idle_hands_off_but_busy_sessions_and_voice_block(self):
        self.assertEqual((await self.service.request("update_prepare", {}))["version"], "0.6.0")
        for status in ("running", "waiting", "starting"):
            self.service.storage.sessions = [{"id": "test", "status": status}]
            with self.assertRaisesRegex(ValueError, "请结束"):
                await self.service.request("update_prepare", {})
        self.service.storage.sessions = []
        self.service.ui_requests = {"test": {"id": {}}}
        with self.assertRaises(ValueError):
            await self.service.request("update_prepare", {})
        self.service.ui_requests.clear()
        for status in ("recording", "transcribing", "downloading"):
            self.service.voice.status = status
            with self.assertRaises(ValueError):
                await self.service.request("update_prepare", {})

    async def test_version_changed_since_check_requires_recheck(self):
        with patch("backend.service.check_release", return_value=release(latest="v0.7.0")):
            with self.assertRaisesRegex(ValueError, "已变化"):
                await self.service.request("update_download", {"version": "v0.6.0"})
