"""构建标识：版本、源码编号和打包时间，用来区分设备上装的是哪个包。"""

from __future__ import annotations

import json
import time
from pathlib import Path


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _git_commit(root: Path) -> str:
    """直接读 .git 元数据，不依赖设备上是否安装了 git。"""
    dot = root / ".git"
    try:
        if dot.is_file():  # worktree / 子模块：文件内容为 "gitdir: <路径>"
            pointer = dot.read_text(encoding="utf-8").strip()
            if not pointer.startswith("gitdir:"):
                return ""
            dot = Path(pointer.split(":", 1)[1].strip())
            if not dot.is_absolute():
                dot = (root / dot).resolve()
        head = (dot / "HEAD").read_text(encoding="utf-8").strip()
        if not head.startswith("ref:"):
            return head
        ref = head.split(":", 1)[1].strip()
        reference = dot / ref
        if reference.is_file():
            return reference.read_text(encoding="utf-8").strip()
        for line in (dot / "packed-refs").read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1] == ref:
                return parts[0]
    except (OSError, ValueError):
        pass
    return ""


def _file_time(path: Path) -> str:
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(path.stat().st_mtime))
    except OSError:
        return ""


def collect(root) -> dict:
    """优先使用安装包写入的标记，其次运行时标记，最后本机源码信息。"""
    root = Path(root)
    packaged = _read_json(root / "build-info.json")
    runtime = _read_json(root / "runtime/build-info.json")
    stamp = packaged or runtime
    version = str(_read_json(root / "package.json").get("version") or "0.0.0")
    commit = str(stamp.get("commit") or _git_commit(root) or "unknown")[:12]
    built_at = str(stamp.get("builtAt") or _file_time(root / "dist/index.js") or "")
    return {
        "version": version,
        "commit": commit,
        "builtAt": built_at,
        "id": f"{version}+{commit}",
        "source": "package" if packaged else "local",
        "platform": str(stamp.get("platform") or ""),
        "pi": str(stamp.get("pi") or ""),
    }
