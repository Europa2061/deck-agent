"""在 Linux x64 上准备发行运行时；不下载 STT 模型权重。"""
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = {
    "node": {
        "version": "22.23.1",
        "url": "https://nodejs.org/dist/v22.23.1/node-v22.23.1-linux-x64.tar.xz",
        "sha256": "9749e988f437343b7fa832c69ded82a312e41a03116d766797ac14f6f9eee578",
    },
    "stt": {
        "version": "2.0.1",
        "url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/v2.0.1/sherpa-onnx-v2.0.1-linux-x64-shared-no-tts.tar.bz2",
        "sha256": "b3b095f619059d54914027ff38f8a0a132ea3bbc5df32a212a9743a8bd1467b2",
    },
}


def fetch_archive(name, info):
    destination = ROOT / "runtime" / name
    with tempfile.TemporaryDirectory(prefix="deck-agent-runtime-") as directory:
        archive_path = Path(directory) / "download"
        print("下载并校验", name, info["version"], flush=True)
        with urllib.request.urlopen(info["url"], timeout=60) as source, archive_path.open("wb") as target:
            shutil.copyfileobj(source, target)
        digest = hashlib.file_digest(archive_path.open("rb"), "sha256").hexdigest()
        if digest != info["sha256"]:
            raise RuntimeError(name + " 的 SHA-256 不匹配。")
        extracted = Path(directory) / "extracted"
        with tarfile.open(archive_path) as archive:
            # 兼容 SteamOS / Debian 的早期 Python 3.11，不能依赖后加的 filter 参数。
            for member in archive.getmembers():
                target = (extracted / member.name).resolve()
                if not target.is_relative_to(extracted.resolve()):
                    raise RuntimeError("运行时归档包含越界路径。")
                if member.issym() or member.islnk():
                    linked = (target.parent / member.linkname if member.issym() else extracted / member.linkname).resolve()
                    if not linked.is_relative_to(extracted.resolve()):
                        raise RuntimeError("运行时归档包含越界链接。")
                elif not (member.isfile() or member.isdir()):
                    raise RuntimeError("运行时归档包含特殊文件。")
            archive.extractall(extracted)
        folders = list(extracted.iterdir())
        if len(folders) != 1 or not folders[0].is_dir():
            raise RuntimeError("运行时归档布局不符合预期。")
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(folders[0], destination, symlinks=True)


def current_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
                                       stderr=subprocess.DEVNULL).strip()[:12]
    except (OSError, subprocess.SubprocessError):
        return os.environ.get("GITHUB_SHA", "")[:12]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--download-only", action="store_true", help="在非 Linux 主机仅下载并校验文件，不生成可发行构建标记")
    args = parser.parse_args()
    linux = platform.system() == "Linux" and platform.machine() in ("x86_64", "amd64")
    if not linux and not args.download_only:
        raise SystemExit("请在 Linux x64 或 GitHub Actions 中准备运行时；不能把 Mac 的 node_modules 打包给 Deck。")
    (ROOT / "runtime/build-info.json").unlink(missing_ok=True)
    for name, info in ARTIFACTS.items():
        fetch_archive(name, info)
    if args.download_only:
        return
    env = dict(os.environ)
    env["PATH"] = str(ROOT / "runtime/node/bin") + ":" + env.get("PATH", "")
    subprocess.run([str(ROOT / "runtime/node/bin/npm"), "ci", "--omit=dev", "--no-audit", "--no-fund"], cwd=ROOT / "runtime", env=env, check=True)
    pi = ROOT / "runtime/node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js"
    # PATH 中提供原生 Pi 包管理命令；不提供 TUI 产品入口。
    wrapper = ROOT / "runtime/node/bin/pi"
    wrapper.write_text('#!/bin/sh\nSCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"\nexec "$SCRIPT_DIR/node" "$SCRIPT_DIR/../../node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js" "$@"\n')
    wrapper.chmod(0o755)
    subprocess.run([str(ROOT / "runtime/node/bin/node"), str(pi), "--version"], env=env, check=True)
    subprocess.run([str(ROOT / "runtime/stt/bin/sherpa-onnx-offline"), "--help"], env={**env, "LD_LIBRARY_PATH": str(ROOT / "runtime/stt/lib")}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    (ROOT / "runtime/build-info.json").write_text(json.dumps({
        "platform": "linux-x64", "pi": "1.5.0", "commit": current_commit(),
        "builtAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "artifacts": ARTIFACTS,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
