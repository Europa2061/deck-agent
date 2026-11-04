import asyncio
import hashlib
import json
import os
import re
import shutil
import signal
import ssl
import tarfile
import threading
import time
import urllib.request
import wave
from pathlib import Path

from .logging_setup import logger_for
from .storage import read_json, write_json


def pipewire_environment():
    """Decky 从系统服务启动时，音频工具仍须连接插件用户的会话。"""
    env = dict(os.environ)
    runtime = Path(f"/run/user/{os.getuid()}")
    if (runtime / "pipewire-0").is_socket():
        env["XDG_RUNTIME_DIR"] = str(runtime)
        env["PIPEWIRE_RUNTIME_DIR"] = str(runtime)
    return env


def download_ssl_context():
    """Decky 自带的 Python 可能找不到 SteamOS 的系统证书。"""
    context = ssl.create_default_context()
    for path in ("/etc/ssl/certs/ca-certificates.crt", "/etc/ssl/cert.pem"):
        if Path(path).is_file():
            context.load_verify_locations(cafile=path)
            break
    return context


def file_digest(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


class VoiceService:
    def __init__(self, root, data, changed, fill_draft):
        self.root, self.data = root, data
        self.data.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.legacy_manifest = read_json(root / "resources/voice-model.json")
        self.catalog = read_json(root / "resources/voice-models.json")
        self.selection = read_json(data / "selection.json")
        self.model_id = self.selection.get("modelId", self.catalog["default"])
        if self.model_id == "whisper-tiny-int8":
            self.model_id = "whisper-small-int8"
        if self.model_id not in {m["id"] for m in self.catalog["models"]}:
            self.model_id = self.catalog["default"]
        self.source = self.selection.get("source", "huggingface")
        if self.source not in ("huggingface", "hf-mirror"):
            self.source = "huggingface"
        self.manifest = next(m for m in self.catalog["models"] if m["id"] == self.model_id).copy()
        self.model = data / "models" / self.model_id
        self._migrate_legacy()
        self.changed, self.fill_draft = changed, fill_draft
        self.cancel = threading.Event()
        self.download_task = None
        self.operation = None
        self.process = None
        self.recording_session = None
        self.recording_started = None
        self.error = None
        self.lock = asyncio.Lock()
        self.closed = False
        self.downloaded = self._downloaded()
        self.status = "ready" if self.ready() else ("paused" if self.downloaded else "missing")

    def _migrate_legacy(self):
        old = self.data / "model"
        marker = read_json(old / "verified.json")
        default = next(m for m in self.catalog["models"] if m["id"] == self.catalog["default"])
        target = self.data / "models" / default["id"]
        if target.exists() or marker.get("sha256") != self.legacy_manifest.get("sha256"):
            return
        for f in default["artifacts"]:
            path = old / f["name"]
            if not path.is_file() or file_digest(path) != f["sha256"]:
                return
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        old.rename(target)
        write_json(target / "verified.json", {"sha256": default["sha256"]})

    def _downloaded(self):
        total = 0
        for f in self.manifest.get("artifacts", []):
            path = self.model / f["name"]
            partial = self.model / (f["name"] + ".part")
            total += path.stat().st_size if path.exists() else partial.stat().st_size if partial.exists() else 0
        return total

    def ready(self):
        marker = read_json(self.model / "verified.json")
        required = self.manifest.get("files", ["model.int8.onnx", "tokens.txt"])
        # 旧归档可包含可选 README/LICENSE，新清单全部文件都是转写必需文件。
        if not self.manifest.get("artifacts"):
            required = ["model.int8.onnx", "tokens.txt"]
        return marker.get("sha256") == self.manifest["sha256"] and all((self.model / f).is_file() for f in required)

    def snapshot(self):
        models = []
        for m in self.catalog["models"]:
            folder = self.data / "models" / m["id"]
            installed = read_json(folder / "verified.json").get("sha256") == m["sha256"] and all((folder / f).is_file() for f in m["files"])
            models.append({k: m[k] for k in ("id", "name", "description", "downloadBytes", "source") } | {"installed": installed})
        return {"status": self.status, "name": self.manifest["name"], "downloaded": self.downloaded,
                "modelId": self.model_id, "downloadSource": self.source, "models": models,
                "total": self.manifest["downloadBytes"], "error": self.error,
                "sessionId": self.recording_session, "recordingStarted": self.recording_started,
                "engineReady": (self.root / "runtime/stt/bin/sherpa-onnx-offline").is_file(),
                "captureReady": bool(shutil.which("pw-record"))}

    def _download_files(self, loop):
        self.model.mkdir(parents=True, exist_ok=True, mode=0o700)
        needed = max(0, self.manifest["downloadBytes"] - self._downloaded()) + 64000000
        if shutil.disk_usage(self.data).free < needed:
            raise RuntimeError(f"存储空间不足，下载还需至少 {needed // 1048576 + 1} MB。")
        host = "https://hf-mirror.com" if self.source == "hf-mirror" else "https://huggingface.co"
        last_update = 0
        for f in self.manifest["artifacts"]:
            if self.cancel.is_set():
                return False
            target = self.model / f["name"]
            if target.exists():
                if target.stat().st_size == f["bytes"] and file_digest(target) == f["sha256"]:
                    continue
                target.unlink()
            partial = target.with_name(target.name + ".part")
            offset = partial.stat().st_size if partial.exists() else 0
            if offset > f["bytes"]:
                partial.unlink()
                offset = 0
            if offset < f["bytes"]:
                headers = {"User-Agent": "Deck-Agent"}
                if offset:
                    headers["Range"] = f"bytes={offset}-"
                url = f"{host}/{self.manifest['repo']}/resolve/{self.manifest['revision']}/{f['name']}"
                with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20, context=download_ssl_context()) as response:
                    if offset and response.status != 206:
                        offset = 0
                    if response.status == 206 and not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-"):
                        raise RuntimeError("服务器返回的续传范围不匹配。")
                    with partial.open("ab" if offset else "wb") as stream:
                        count = offset
                        while not self.cancel.is_set():
                            chunk = response.read(256 * 1024)
                            if not chunk:
                                break
                            count += len(chunk)
                            if count > f["bytes"]:
                                raise RuntimeError("下载大小超过固定模型清单。")
                            stream.write(chunk)
                            self.downloaded = self._downloaded() - partial.stat().st_size + count
                            if time.monotonic() - last_update > 0.3:
                                last_update = time.monotonic()
                                asyncio.run_coroutine_threadsafe(self.changed(), loop)
            if self.cancel.is_set():
                return False
            digest = hashlib.sha256()
            with partial.open('rb') as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
            if partial.stat().st_size != f["bytes"] or digest.hexdigest() != f["sha256"]:
                partial.unlink(missing_ok=True)
                raise RuntimeError("模型文件校验失败，请重新下载。")
            partial.replace(target)
            self.downloaded = self._downloaded()
        write_json(self.model / "verified.json", {"sha256": self.manifest["sha256"]})
        return True

    def recognizer_args(self, language):
        if self.manifest.get("engine") == "paraformer":
            return ["--paraformer=" + str(self.model / "model.int8.onnx"), "--tokens=" + str(self.model / "tokens.txt")]
        if self.manifest.get("engine") == "whisper":
            prefix = self.manifest["id"].removeprefix("whisper-").removesuffix("-int8")
            args = [f"--whisper-encoder={self.model / (prefix + '-encoder.int8.onnx')}",
                    f"--whisper-decoder={self.model / (prefix + '-decoder.int8.onnx')}",
                    f"--tokens={self.model / (prefix + '-tokens.txt')}", "--whisper-task=transcribe", "--whisper-tail-paddings=300"]
            if language in ("zh", "en"):
                args.append("--whisper-language=" + language)
            return args
        return ["--sense-voice-use-itn=1", "--sense-voice-language=" + (language if language in ("auto", "zh", "en") else "auto"),
                "--sense-voice-model=" + str(self.model / "model.int8.onnx"), "--tokens=" + str(self.model / "tokens.txt")]

    def _download(self, loop):
        if self.manifest.get("artifacts"):
            return self._download_files(loop)
        partial = self.data / "model.part"
        offset = partial.stat().st_size if partial.exists() else 0
        if shutil.disk_usage(self.data).free < self.manifest["requiredFreeBytes"] - offset:
            raise RuntimeError("存储空间不足，请释放至少 470 MB 可用空间后重试。")
        if offset < self.manifest["downloadBytes"]:
            headers = {"User-Agent": "Deck-Agent/0.1.0"}
            if offset:
                headers["Range"] = f"bytes={offset}-"
            request = urllib.request.Request(self.manifest["url"], headers=headers)
            with urllib.request.urlopen(request, timeout=15, context=download_ssl_context()) as response:
                if offset and response.status != 206:
                    offset = 0  # 服务器不支持续传时从头下载，避免拼接损坏。
                if response.status == 206 and not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-"):
                    raise RuntimeError("服务器返回的续传范围不匹配。")
                last_update = 0
                with partial.open("ab" if offset else "wb") as stream:
                    self.downloaded = offset
                    while not self.cancel.is_set():
                        chunk = response.read(256 * 1024)
                        if not chunk:
                            break
                        stream.write(chunk)
                        self.downloaded += len(chunk)
                        if self.downloaded > self.manifest["downloadBytes"]:
                            raise RuntimeError("下载文件大小与固定模型清单不一致。")
                        if time.monotonic() - last_update > 0.3:
                            last_update = time.monotonic()
                            asyncio.run_coroutine_threadsafe(self.changed(), loop)
        if self.cancel.is_set():
            return False
        digest = hashlib.sha256()
        with partial.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
        if digest.hexdigest() != self.manifest["sha256"]:
            partial.unlink(missing_ok=True)
            raise RuntimeError("模型校验失败，请重新下载。")
        logger_for().info("语音模型 SHA-256 校验通过 bytes=%d", self.downloaded)
        staging = self.data / "extracting"
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(mode=0o700)
        # 只取白名单内的普通文件，不按归档路径提取，不接受链接。
        with tarfile.open(partial, "r:bz2") as archive:
            for member in archive:
                name = Path(member.name).name
                if member.isfile() and name in self.manifest["files"]:
                    if member.size > 300 * 1024 * 1024:
                        raise RuntimeError("模型归档文件过大。")
                    source = archive.extractfile(member)
                    with (staging / name).open("wb") as destination:
                        shutil.copyfileobj(source, destination)
        if not all((staging / name).is_file() for name in ("model.int8.onnx", "tokens.txt")):
            raise RuntimeError("模型包缺少模型或词表。")
        write_json(staging / "verified.json", {"sha256": self.manifest["sha256"]})
        shutil.rmtree(self.model, ignore_errors=True)
        self.model.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        staging.rename(self.model)
        partial.unlink(missing_ok=True)
        logger_for().info("语音模型已解压并启用")
        return True

    async def download(self):
        log = logger_for()
        self.status, self.error = "downloading", None
        self.cancel.clear()
        started = time.monotonic()
        log.info("开始下载语音模型 offset=%d total=%d", self.downloaded, self.manifest["downloadBytes"])
        try:
            completed = await asyncio.to_thread(self._download, asyncio.get_running_loop())
            self.status = "ready" if completed else "paused"
            log.info("语音模型下载结束 status=%s 耗时=%.0fs", self.status, time.monotonic() - started)
        except Exception as error:
            self.status, self.error = "error", str(error)
            log.error("语音模型下载失败：%s", error)
        finally:
            await self.changed()

    async def _stop_process(self):
        process = self.process
        if process and process.returncode is None:
            process.send_signal(signal.SIGINT)
            try:
                await asyncio.wait_for(process.wait(), 4)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

    async def transcribe(self, session_id, language):
        log = logger_for(session_id)
        log.info("开始本地转写 language=%s", language)
        started = time.monotonic()
        self.status = "transcribing"
        await self.changed()
        binary = self.root / "runtime/stt/bin/sherpa-onnx-offline"
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = str(self.root / "runtime/stt/lib") + ":" + env.get("LD_LIBRARY_PATH", "")
        audio = self.data / "input.wav"
        try:
            with wave.open(str(audio)) as wav:
                if wav.getnframes() < 1600:
                    raise RuntimeError("录音太短，没有检测到清晰语音。")
            self.process = await asyncio.create_subprocess_exec(
                str(binary), "--num-threads=2", "--debug=0", *self.recognizer_args(language), str(audio),
                env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(self.process.communicate(), 180)
            if self.process.returncode:
                raise RuntimeError("本地转写失败：" + stderr.decode(errors="replace")[-500:])
            text = ""
            for line in (stdout + b"\n" + stderr).decode(errors="replace").splitlines():
                try:
                    result = json.loads(line)
                    if isinstance(result, dict) and isinstance(result.get("text"), str):
                        text = result["text"]
                except ValueError:
                    continue
            text = re.sub(r"<\|.*?\|>", "", text).strip()
            if not text:
                raise RuntimeError("没有检测到清晰语音，请重新录音。")
            if not self.closed:
                await self.fill_draft(session_id, text)
            self.status, self.error = "ready", None
            log.info("本地转写完成 chars=%d 耗时=%.1fs", len(text), time.monotonic() - started)
        except asyncio.CancelledError:
            await self._stop_process()
            self.status = "ready"
            raise
        except Exception as error:
            await self._stop_process()
            self.status, self.error = ("ready" if self.ready() else "error"), str(error)
            log.error("本地转写失败 耗时=%.1fs：%s", time.monotonic() - started, error)
            await self.changed({"title": "语音转写未完成", "message": self.error, "sessionId": session_id})
        finally:
            self.process = None
            self.recording_session = None
            self.recording_started = None
            audio.unlink(missing_ok=True)
            await self.changed()

    async def microphone_devices(self):
        binary = shutil.which("pw-dump")
        if not binary:
            raise RuntimeError("无法读取麦克风列表：系统未找到 pw-dump。")
        process = await asyncio.create_subprocess_exec(binary, env=pipewire_environment(), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            stdout, _ = await asyncio.wait_for(process.communicate(), 5)
        except BaseException as exc:
            if process.returncode is None:
                process.kill()
                await process.wait()
            if isinstance(exc, asyncio.TimeoutError):
                raise RuntimeError("读取麦克风列表超时，请检查 PipeWire 是否正常运行。") from exc
            raise
        if process.returncode:
            raise RuntimeError("无法读取麦克风列表，请检查 PipeWire 是否正常运行。")
        try:
            nodes = json.loads(stdout)
            if not isinstance(nodes, list):
                raise ValueError("invalid PipeWire data")
        except (ValueError, UnicodeDecodeError) as exc:
            raise RuntimeError("无法读取麦克风列表：设备信息格式不正确。") from exc
        devices = []
        seen = set()
        for node in nodes:
            if not isinstance(node, dict) or node.get("type") != "PipeWire:Interface:Node":
                continue
            info = node.get("info") or {}
            props = info.get("props") or {} if isinstance(info, dict) else {}
            if not isinstance(props, dict) or props.get("media.class") != "Audio/Source":
                continue
            name = props.get("node.name")
            if not isinstance(name, str) or not name or name in seen:
                continue
            seen.add(name)
            label = props.get("node.description") or props.get("node.nick") or name
            devices.append({"id": name, "name": str(label)})
        return devices

    async def request(self, action, payload, preferences):
        if action == "voice_devices":
            return await self.microphone_devices()
        log = logger_for(payload.get("sessionId"))
        async with self.lock:
            if action == "voice_select":
                if self.status in ("recording", "transcribing", "downloading") or (self.download_task and not self.download_task.done()):
                    raise ValueError("请先停止录音、转写或下载，再切换模型或下载来源。")
                model_id = payload.get("modelId", self.model_id)
                source = payload.get("source", self.source)
                if model_id not in {m["id"] for m in self.catalog["models"]} or source not in ("huggingface", "hf-mirror"):
                    raise ValueError("不支持这个语音模型或下载来源。")
                self.model_id, self.source = model_id, source
                self.manifest = next(m for m in self.catalog["models"] if m["id"] == model_id).copy()
                self.model = self.data / "models" / model_id
                self.downloaded = self._downloaded()
                self.status = "ready" if self.ready() else "paused" if self.downloaded else "missing"
                self.error = None
                write_json(self.data / "selection.json", {"modelId": model_id, "source": source})
            elif action == "voice_download":
                if self.download_task and not self.download_task.done():
                    return None
                if self.status in ("recording", "transcribing"):
                    raise ValueError("请先结束语音输入。")
                self.status = "downloading"
                self.download_task = asyncio.create_task(self.download())
            elif action in ("voice_pause", "voice_cancel_download"):
                log.info("语音模型下载 %s", "取消" if action == "voice_cancel_download" else "暂停")
                self.cancel.set()
                if self.download_task:
                    await self.download_task
                if action == "voice_cancel_download":
                    (self.data / "model.part").unlink(missing_ok=True)
                    for partial in self.model.glob("*.part"):
                        partial.unlink(missing_ok=True)
                    self.downloaded = self._downloaded()
                    self.status = "ready" if self.ready() else "paused" if self.downloaded else "missing"
            elif action == "voice_delete":
                if self.status in ("recording", "transcribing", "downloading"):
                    raise ValueError("语音模型仍在使用，请先停止录音、转写或下载。")
                log.info("删除本地语音模型")
                shutil.rmtree(self.model, ignore_errors=True)
                self.status, self.downloaded = "missing", 0
            elif action == "voice_start":
                if not self.ready():
                    raise ValueError("请先下载并校验本地语音模型。")
                if self.status in ("recording", "transcribing", "downloading"):
                    raise ValueError("已有录音、转写或模型下载正在进行。")
                binary = self.root / "runtime/stt/bin/sherpa-onnx-offline"
                if not binary.exists():
                    raise RuntimeError("安装包缺少 Linux 语音引擎。")
                capture = shutil.which("pw-record")
                if not capture:
                    raise RuntimeError("没有找到 PipeWire 的 pw-record，请在 SteamOS 上检查录音环境。")
                target = preferences.get("inputDevice") or "auto"
                if target == "@DEFAULT_AUDIO_SOURCE@":
                    target = "auto"
                self.process = await asyncio.create_subprocess_exec(capture, "--rate=16000", "--channels=1", "--format=s16",
                    "--target=" + target, str(self.data / "input.wav"), env=pipewire_environment(),
                    stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
                await asyncio.sleep(0.15)
                if self.process.returncode is not None:
                    stderr = await self.process.stderr.read()
                    raise RuntimeError("麦克风不可用：" + stderr.decode(errors="replace")[-400:])
                self.status, self.error = "recording", None
                self.recording_session = payload["sessionId"]
                self.recording_started = time.time()
                log.info("开始录音 pid=%s device=%s", self.process.pid, preferences.get("inputDevice", "@DEFAULT_AUDIO_SOURCE@"))
            elif action == "voice_finish":
                if self.status != "recording":
                    raise ValueError("当前没有录音。")
                log.info("录音结束 时长=%.1fs", time.time() - (self.recording_started or time.time()))
                await self._stop_process()
                self.operation = asyncio.create_task(self.transcribe(self.recording_session, preferences.get("language", "auto")))
                self.status = "transcribing"
            elif action == "voice_cancel":
                if self.status in ("recording", "transcribing"):
                    log.info("取消语音输入")
                if self.operation and not self.operation.done():
                    self.operation.cancel()
                    await asyncio.gather(self.operation, return_exceptions=True)
                await self._stop_process()
                self.process = None
                self.recording_session = self.recording_started = None
                self.status = "ready" if self.ready() else "missing"
                (self.data / "input.wav").unlink(missing_ok=True)
            else:
                raise ValueError("未知语音操作。")
        await self.changed()

    async def close(self):
        self.closed = True
        self.cancel.set()
        if self.download_task:
            await self.download_task
        await self.request("voice_cancel", {}, {})
