"""发布前核对源码版本、锁文件、ZIP、构建标识与 SHA-256；只读，不打包或升级。"""
import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.release_version import next_version


def verify(root, archive_path=None, tag=None):
    root = Path(root)
    version = json.loads((root / "package.json").read_text())["version"]
    next_version(version)  # 校验三段式格式，不实际升级。
    lock = json.loads((root / "package-lock.json").read_text())
    if lock["version"] != version or lock["packages"][""]["version"] != version:
        raise ValueError("package.json 与锁文件版本不一致。")
    if tag is not None and tag != f"v{version}":
        raise ValueError(f"标签应为 v{version}。")
    path = Path(archive_path) if archive_path else root / "out" / f"deck-agent-{version}.zip"
    if path.name != f"deck-agent-{version}.zip":
        raise ValueError("ZIP 文件名与源码版本不一致。")
    checksum = path.with_suffix(".zip.sha256").read_text().split()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if checksum != [digest, path.name]:
        raise ValueError("SHA-256 或校验文件中的文件名不一致。")
    with zipfile.ZipFile(path) as archive:
        if archive.testzip():
            raise ValueError("ZIP 完整性检查失败。")
        names = archive.namelist()
        if any(not name.startswith("deck-agent/") or ".." in Path(name).parts for name in names):
            raise ValueError("ZIP 必须只有 deck-agent/ 根目录，且不能包含越界路径。")
        manifest = json.loads(archive.read("deck-agent/package.json"))
        build = json.loads(archive.read("deck-agent/build-info.json"))
        if manifest["version"] != version or build["version"] != version:
            raise ValueError("包内版本或构建标识与源码不一致。")
        if build.get("platform") != "linux-x64":
            raise ValueError("安装包不是 Linux x64 发行构建。")
    return version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path)
    parser.add_argument("--tag", help="将要发布的标签，例如 v0.6.0")
    args = parser.parse_args()
    try:
        version = verify(ROOT, args.zip, args.tag)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        raise SystemExit(f"发布检查失败：{error}") from error
    print(f"发布文件检查通过：{version}（不代表真机验收已完成）")


if __name__ == "__main__":
    main()
