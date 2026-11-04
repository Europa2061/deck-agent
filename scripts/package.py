"""生成 Decky 手动安装识别的单根目录插件 ZIP。"""
import argparse
import json
import hashlib
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.build_info import collect as collect_build
from scripts.release_version import bump_version, package_path


def commit_and_dirty():
    """取当前源码编号；工作区有未提交改动时额外标记 dirty。"""
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
                                         stderr=subprocess.DEVNULL, timeout=15).strip()[:12]
    except (OSError, subprocess.SubprocessError):
        commit = ""
    if not commit:
        return (os.environ.get("GITHUB_SHA") or os.environ.get("DECK_AGENT_COMMIT") or "unknown")[:12], False
    try:
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True,
                                         stderr=subprocess.DEVNULL, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return commit, False
    return commit, bool(status.strip())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bump", choices=("major", "minor", "patch"), default="patch",
                        help="打包前升级版本号，默认 patch（修复）；新功能用 minor，不兼容变更用 major")
    parser.add_argument("--commit-version", action="store_true",
                        help="CI 发行用：要求干净工作区，升级版本后创建中英文版本提交，再生成安装包")
    args = parser.parse_args()
    if args.commit_version:
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
        if status.strip():
            raise SystemExit("自动发行需要干净工作区；请先提交源码和文档改动。")
    runtime = ROOT / "runtime"
    info_path = runtime / "build-info.json"
    if not info_path.exists() or json.loads(info_path.read_text()).get("platform") != "linux-x64":
        raise SystemExit("缺少已验证的 Linux x64 运行时，请先在 Linux 执行 python3 scripts/prepare_runtime.py。")
    runtime_info = json.loads(info_path.read_text())
    expected_pi = json.loads((runtime / "package.json").read_text())["dependencies"]["@earendil-works/pi-coding-agent"]
    for dependency in ("pi-coding-agent", "pi-ai"):
        installed = runtime / "node_modules/@earendil-works" / dependency / "package.json"
        if not installed.exists() or json.loads(installed.read_text()).get("version") != expected_pi:
            raise SystemExit("Pi 依赖未同步，请重新准备 Linux x64 运行时。")
    if runtime_info.get("pi") != expected_pi:
        raise SystemExit("发行标记中的 Pi 版本不一致，请重新准备 Linux x64 运行时。")
    for path in (ROOT / "dist/index.js", runtime / "node/bin/node", runtime / "stt/bin/sherpa-onnx-offline"):
        if not path.is_file():
            raise SystemExit("缺少发行文件：" + str(path))
    links = {}
    executables = []
    for path in runtime.rglob("*"):
        if path.is_file() and path.stat().st_mode & 0o111:
            executables.append(str(path.relative_to(runtime)))
        if path.is_symlink():
            target = str(path.readlink())
            if not path.resolve().is_relative_to(runtime.resolve()):
                raise SystemExit("运行时包含越界链接：" + str(path))
            links[str(path.relative_to(runtime))] = target
    # Decky 使用 Python ZipFile.extractall，不保留符号链接；首次加载时恢复。
    (runtime / "symlinks.json").write_text(json.dumps(links, indent=2) + "\n")
    (runtime / "executables.json").write_text(json.dumps(executables, indent=2) + "\n")
    # 每个包写入可辨认的构建标识：版本、源码编号、打包时间。
    version = bump_version(ROOT, args.bump)
    if args.commit_version:
        subprocess.run(["git", "add", "--", "package.json", "package-lock.json"], cwd=ROOT, check=True)
        subprocess.run(["git", "commit", "-m", f"发布 {version} / Release {version}", "-m",
                        f"同步安装包版本为 {version}。\nSynchronize package version to {version}."], cwd=ROOT, check=True)
    print("本次打包版本", version, flush=True)
    stamp = collect_build(ROOT)
    commit, dirty = commit_and_dirty()
    build_id = f"{stamp['version']}+{commit}" + ("+dirty" if dirty else "")
    build_stamp = {
        "version": stamp["version"],
        "id": build_id,
        "commit": commit,
        "dirty": dirty,
        "builtAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "package",
        "platform": "linux-x64",
        "pi": expected_pi,
        "runtime": json.loads(info_path.read_text()),
    }
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    zip_path = package_path(ROOT)
    if zip_path.exists():
        raise SystemExit("该版本安装包已存在，请检查版本号后重新打包：" + str(zip_path))
    temporary = zip_path.with_suffix(".zip.tmp")
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for folder in ("backend", "dist", "runtime", "resources", "docs"):
            for path in sorted((ROOT / folder).rglob("*")):
                if path.is_file() and not path.is_symlink() and not any(part in ("__pycache__", ".cache") for part in path.parts):
                    archive.write(path, "deck-agent/" + str(path.relative_to(ROOT)))
        for name in ("main.py", "plugin.json", "package.json", "LICENSE", "README.md", "README.en.md"):
            archive.write(ROOT / name, "deck-agent/" + name)
        archive.writestr("deck-agent/build-info.json", json.dumps(build_stamp, indent=2, ensure_ascii=False) + "\n")
    with zipfile.ZipFile(temporary) as archive:
        if archive.testzip():
            raise RuntimeError("安装包完整性检查失败。")
        manifests = [name for name in archive.namelist() if name.endswith("/plugin.json") and name.count("/") == 1]
        assert manifests == ["deck-agent/plugin.json"]
        assert json.loads(archive.read("deck-agent/package.json"))["version"] == version
    temporary.replace(zip_path)
    print(zip_path, zip_path.stat().st_size, "bytes")
    print("构建标识", build_stamp["id"], build_stamp["builtAt"])
    with zip_path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    zip_path.with_suffix(".zip.sha256").write_text(digest + "  " + zip_path.name + "\n")


if __name__ == "__main__":
    main()
