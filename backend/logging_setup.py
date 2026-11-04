"""插件日志：轮转落盘、会话与进程标记、错误留存，便于 SSH 远程排查。

普通模式只记录关键事件；`DECK_AGENT_DEBUG=1` 或设置目录中存在 `debug-log`
文件时记录细节。日志不写入密钥、完整对话、命令参数、工具输出和语音内容；
已登记的密钥会在写入前替换成占位符。
"""

from __future__ import annotations

import logging
import os
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOGGER_NAME = "deck_agent"
LOG_FILENAME = "deck-agent.log"
DEBUG_MARKER = "debug-log"
MAX_BYTES = 5 * 1024 * 1024
# 当前文件 + 2 份历史，最多 3 个文件，总计约 15 MB。
BACKUP_COUNT = 2
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FORMAT = "%(asctime)s %(levelname)-5s pid=%(process)d session=%(session)s %(message)s"

_secrets: set[str] = set()
_log_dir: Path | None = None
logging.getLogger(LOGGER_NAME).addHandler(logging.NullHandler())


def register_secret(*values):
    """登记需要在日志中隐藏的密钥原文；过短的值不参与替换，避免误伤正常文本。"""
    for value in values:
        if isinstance(value, str) and len(value) >= 8:
            _secrets.add(value)


def redact(text):
    for value in _secrets:
        if value in text:
            text = text.replace(value, "[已隐藏]")
    return text


class _Formatter(logging.Formatter):
    def format(self, record):
        # 调用堆栈一起脱敏，异常里也可能带上供应商返回的原文。
        return redact(super().format(record))


class _FileHandler(RotatingFileHandler):
    def _open(self):
        stream = super()._open()
        try:
            # 轮转后新建的文件也保持 0600。
            os.chmod(self.baseFilename, 0o600)
        except OSError:
            pass
        return stream


def setup_logging(log_dir, *, debug=False, extra_logger=None):
    """配置轮转文件日志并返回主日志器；目录不可用时退回 Decky 自带日志。"""
    global _log_dir
    logger = logging.getLogger(LOGGER_NAME)
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)
    logger.propagate = False
    try:
        directory = Path(log_dir)
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        _log_dir = directory
        handler = next((item for item in logger.handlers if getattr(item, "deck_agent_file", False)), None)
        if handler is None:
            handler = _FileHandler(
                directory / LOG_FILENAME, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8",
            )
            handler.setFormatter(_Formatter(LOG_FORMAT, datefmt=TIME_FORMAT, defaults={"session": "-"}))
            handler.deck_agent_file = True
            logger.addHandler(handler)
        handler.setLevel(level)
        try:
            os.chmod(handler.baseFilename, 0o600)
        except OSError:
            pass
        if extra_logger is not None and handler not in extra_logger.handlers:
            # Decky 的 logger 就是 root logger；同一文件里也能看到它的记录。
            # 不改动它的级别，避免调试模式淹没第三方日志。
            extra_logger.addHandler(handler)
    except OSError:
        logger.warning("日志目录不可用，仅保留 Decky 日志：%s", log_dir)
    return logger


def debug_enabled(settings_dir) -> bool:
    flag = os.environ.get("DECK_AGENT_DEBUG", "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return True
    try:
        return (Path(settings_dir) / DEBUG_MARKER).exists()
    except OSError:
        return False


def short_session(session_id) -> str:
    return str(session_id)[:8] if session_id else "-"


def logger_for(session_id=None):
    return logging.LoggerAdapter(logging.getLogger(LOGGER_NAME), {"session": short_session(session_id)})


def log_directory():
    return _log_dir


def log_files():
    if _log_dir is None or not _log_dir.is_dir():
        return []
    result = []
    for path in sorted(_log_dir.glob(LOG_FILENAME + "*"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            stat = path.stat()
        except OSError:
            continue
        result.append({
            "name": path.name, "bytes": stat.st_size,
            "modified": time.strftime(TIME_FORMAT, time.localtime(stat.st_mtime)),
        })
    return result


def recent_errors(limit=20, window=64 * 1024):
    """从当前和上一份日志末尾取出最近的警告、错误和堆栈行。"""
    if _log_dir is None:
        return []
    found = []
    for name in (LOG_FILENAME + ".1", LOG_FILENAME):
        path = _log_dir / name
        if not path.is_file():
            continue
        try:
            with path.open("rb") as stream:
                stream.seek(0, os.SEEK_END)
                size = stream.tell()
                stream.seek(max(0, size - window))
                text = stream.read().decode("utf-8", errors="replace")
        except OSError:
            continue
        found.extend(line[:400] for line in text.splitlines()
                     if " ERROR " in line or " WARNING " in line or "Traceback" in line)
    return found[-limit:]
