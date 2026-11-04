"""插件自己的元数据；对话内容由 Pi 保存。"""

import json
import os
import tempfile
from pathlib import Path

from .session_state import is_abort_error


def read_json(path: Path, default=None):
    if not path.exists():
        return {} if default is None else default
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".deck-agent-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Storage:
    def __init__(self, settings: Path, data: Path, home: Path):
        self.settings = settings
        self.data = data
        self.home = home
        self.agent = settings / "pi"
        self.sessions_dir = data / "sessions"
        for path in (settings, data, self.agent, self.sessions_dir):
            path.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.metadata_path = data / "sessions.json"
        self.preferences_path = settings / "deck-agent.json"
        self.preferences = read_json(self.preferences_path, {
            "defaultCwd": str(home / "DeckAgent"), "notifications": True,
            "updateAuto": True, "releaseRepo": "", "language": "auto", "inputDevice": "auto",
        })
        self.new_draft_path = data / "new-session-draft.json"
        self.new_draft = read_json(self.new_draft_path, {"draft": ""})
        self.sessions = read_json(self.metadata_path, [])
        for item in self.sessions:
            if item.get("status") in ("error", "stopped") and is_abort_error(item.get("error")):
                item["status"] = "stopped"
                item.pop("error", None)
            if item.get("status") in ("running", "waiting", "starting"):
                item["status"] = "interrupted"
        self.save_sessions()

    def save_new_draft(self):
        write_json(self.new_draft_path, self.new_draft)

    def save_sessions(self):
        write_json(self.metadata_path, self.sessions)

    def save_preferences(self):
        write_json(self.preferences_path, self.preferences)

    def cwd(self, value: str, create=False) -> Path:
        if value == "~" or value.startswith("~/"):
            value = str(self.home) + value[1:]
        path = Path(value)
        if not path.is_absolute():
            raise ValueError("请输入绝对路径或以 ~/ 开头的目录。")
        if create:
            path.mkdir(parents=True, exist_ok=True)
        if not path.is_dir():
            raise ValueError("工作目录不存在，请选择已有目录。")
        return path.resolve()

    def session(self, session_id: str):
        for item in self.sessions:
            if item["id"] == session_id:
                return item
        raise ValueError("会话不存在。")
