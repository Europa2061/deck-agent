"""安装包的版本升级与文件命名，统一使用三段式语义版本。"""
import json
import re


def next_version(current, bump="patch"):
    if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", current):
        raise ValueError("版本号必须为 X.Y.Z 三段非负整数，且不能有前导零。")
    major, minor, patch = map(int, current.split("."))
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    if bump == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError("升级类型必须为 major、minor 或 patch。")


def bump_version(root, bump="patch"):
    package_path = root / "package.json"
    lock_path = root / "package-lock.json"
    package = json.loads(package_path.read_text())
    lock = json.loads(lock_path.read_text())
    version = next_version(package["version"], bump)
    package["version"] = lock["version"] = lock["packages"][""]["version"] = version
    for path, value in ((package_path, package), (lock_path, lock)):
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    return version


def package_path(root):
    version = json.loads((root / "package.json").read_text())["version"]
    # 同样校验读取的版本，避免把路径字符带进文件名。
    next_version(version)
    return root / "out" / f"deck-agent-{version}.zip"
