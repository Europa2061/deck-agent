import asyncio
import hashlib
import json
import os
import threading
import time
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
import re
import urllib.error
import urllib.request


def version_key(value):
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?", value)
    if not match:
        raise ValueError("发布版本号需要使用 v0.1.0 这样的格式。")
    return (*map(int, match.group(1, 2, 3)), match.group(4) is None, match.group(4) or "")


def check_release(repo, current):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("请先填写 GitHub 发布仓库，格式为 owner/repo。")
    def fetch(path):
        request = urllib.request.Request(f"https://api.github.com/repos/{repo}/{path}", headers={
            "Accept": "application/vnd.github+json", "User-Agent": "Deck-Agent",
        })
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)

    try:
        try:
            release = fetch("releases/latest")
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
            # 首发测试阶段可能只有预发布；已有正式版时保持正式版渠道。
            candidates = []
            for item in fetch("releases?per_page=100"):
                tag = item.get("tag_name", "")
                if item.get("draft") or not item.get("prerelease"):
                    continue
                try:
                    key = version_key(tag)
                except ValueError:
                    continue
                expected = f"deck-agent-{tag.removeprefix('v')}.zip"
                if any(asset.get("name") == expected for asset in item.get("assets", [])):
                    candidates.append((key, item))
            if not candidates:
                raise ValueError("仓库还没有带安装包的公开版本。")
            release = max(candidates, key=lambda candidate: candidate[0])[1]
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise ValueError("仓库不存在、未公开或还没有发布版本。") from error
        if error.code in (403, 429):
            raise ValueError("GitHub 请求受限，请稍后重试。") from error
        raise
    tag = release.get("tag_name", "")
    latest = version_key(tag)
    filename = f"deck-agent-{tag.removeprefix('v')}.zip"
    # 优先使用版本对应的包；旧发布仍可使用历史文件名。
    assets = release.get("assets", [])
    asset = next((a for a in assets if a.get("name") == filename), None)
    if asset is None:
        asset = next((a for a in assets if a.get("name") == "deck-agent.zip"), None)
    checksum = next((a for a in assets if asset and a.get("name") == asset["name"] + ".sha256"), None)
    return {"current": current, "latest": tag, "available": latest > version_key(current),
            "notes": ("公开测试版，可能不稳定。\n\n" if release.get("prerelease") else "") + (release.get("body") or ""), "pageUrl": f"https://github.com/{repo}/releases/tag/{tag}",
            "zipUrl": asset.get("browser_download_url") if asset else None,
            "checksumUrl": checksum.get("browser_download_url") if checksum else None,
            "publishedAt": release.get("published_at")}


class UpdateDownload:
    """下载到持久目录；不解压、不修改正在运行的插件。"""
    def __init__(self, directory):
        self.directory = Path(directory)
        self.state = {"status": "idle", "downloaded": 0, "total": 0}
        self.task = None
        self.cancelled = threading.Event()
        self.prepared = None

    def snapshot(self):
        return dict(self.state)

    def start(self, release):
        if self.task and not self.task.done():
            raise ValueError("已有更新正在下载。")
        if not release.get("available"):
            raise ValueError("没有可更新的版本。")
        if not release.get("zipUrl") or not release.get("checksumUrl"):
            raise ValueError("该版本缺少安装包或 SHA-256 校验文件，请前往发布页手动安装。")
        self.cancelled.clear()
        self.prepared = None
        self.state = {"status": "downloading", "downloaded": 0, "total": 0, "version": release["latest"]}
        self.task = asyncio.create_task(self._run(dict(release)))

    async def _run(self, release):
        try:
            self.prepared = await asyncio.to_thread(self._download, release)
            self.state = {**self.state, "status": "ready"}
        except Exception as error:
            self.state = {**self.state, "status": "cancelled" if self.cancelled.is_set() else "error", "error": str(error)}

    def cancel(self):
        if self.task and not self.task.done():
            self.cancelled.set()
            self.state = {**self.state, "status": "cancelling"}

    def _open(self, url):
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != "github.com" or not parsed.path.startswith("/") or "/releases/download/" not in parsed.path:
            raise ValueError("安装包必须来自 GitHub Release 的 HTTPS 下载地址。")
        return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Deck-Agent"}), timeout=30)

    def _download(self, release):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        # 同一时间仅保留一个缓存包，不随重试持续占用磁盘。
        for old in self.directory.glob("deck-agent-*.zip*"):
            old.unlink()
        filename = "deck-agent-" + release["latest"].removeprefix("v") + ".zip"
        target = self.directory / filename
        partial = target.with_suffix(".zip.part")
        try:
            with self._open(release["checksumUrl"]) as response:
                checksum = response.read(4097).decode("utf-8").strip()
            parts = checksum.split()
            if len(checksum) > 4096 or not parts or not re.fullmatch(r"[a-fA-F0-9]{64}", parts[0]) or (len(parts) > 1 and parts[1].lstrip("*") != filename):
                raise ValueError("SHA-256 校验文件格式或文件名不正确。")
            expected = parts[0].lower()
            digest = hashlib.sha256()
            downloaded = 0
            deadline = time.monotonic() + 1800
            with self._open(release["zipUrl"]) as response, partial.open("wb") as stream:
                total = int(response.headers.get("Content-Length", 0))
                if total > 2 * 1024**3:
                    raise ValueError("安装包过大，已停止下载。")
                self.state = {**self.state, "total": total}
                while True:
                    if self.cancelled.is_set():
                        raise ValueError("下载已取消。")
                    if time.monotonic() > deadline:
                        raise ValueError("下载超时，请重试。")
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    downloaded += len(chunk)
                    if downloaded > 2 * 1024**3:
                        raise ValueError("安装包过大，已停止下载。")
                    stream.write(chunk)
                    digest.update(chunk)
                    self.state = {**self.state, "downloaded": downloaded}
            if total and downloaded != total:
                raise ValueError("安装包下载不完整，请重试。")
            if digest.hexdigest() != expected:
                raise ValueError("安装包 SHA-256 校验失败，请重新下载。")
            self.state = {**self.state, "status": "verifying"}
            self._validate_zip(partial, release["latest"])
            if self.cancelled.is_set():
                raise ValueError("下载已取消。")
            os.replace(partial, target)
            return {"artifact": "file://" + str(target.resolve()), "version": release["latest"].removeprefix("v"), "hash": expected}
        finally:
            partial.unlink(missing_ok=True)

    @staticmethod
    def _validate_zip(path, version):
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError("安装包包含重复文件。")
            total = 0
            for item in archive.infolist():
                name = PurePosixPath(item.filename)
                total += item.file_size
                if name.is_absolute() or ".." in name.parts or not name.parts or name.parts[0] != "deck-agent" or "\\" in item.filename or (item.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError("安装包包含无效路径或符号链接。")
            if total > 4 * 1024**3:
                raise ValueError("安装包解压后过大。")
            required = ("package.json", "plugin.json", "build-info.json", "main.py", "dist/index.js")
            if any("deck-agent/" + name not in names for name in required):
                raise ValueError("安装包缺少插件运行文件。")
            for name in ("package.json", "plugin.json", "build-info.json"):
                if archive.getinfo("deck-agent/" + name).file_size > 1024 * 1024:
                    raise ValueError("安装包版本信息过大。")
            package = json.loads(archive.read("deck-agent/package.json"))
            build = json.loads(archive.read("deck-agent/build-info.json"))
            plugin = json.loads(archive.read("deck-agent/plugin.json"))
            if package.get("name") != "deck-agent" or plugin.get("name") != "Deck Agent" or any(v.get("version") != version.removeprefix("v") for v in (package, build)):
                raise ValueError("安装包名称或版本与发布信息不一致。")
            if archive.testzip():
                raise ValueError("安装包文件损坏。")

    async def prepare(self):
        if self.state["status"] != "ready" or not self.prepared:
            raise ValueError("请先完成安装包下载和校验。")
        prepared = dict(self.prepared)
        path = Path(prepared["artifact"][7:])
        def verify():
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != prepared["hash"]:
                raise ValueError("缓存安装包已变化，请重新下载。")
        await asyncio.to_thread(verify)
        return prepared

    async def close(self):
        self.cancel()
        if self.task:
            await self.task
