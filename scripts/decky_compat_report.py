"""按 Decky 加载器与官方 CLI 的规则检查安装包，并列出与官方打包器的差异。

加载条件不满足时以非 0 退出，用于 CI 门禁；与官方 CLI 的差异只提示，
因为本插件的随包运行时和资源不在官方 CLI 的打包白名单内（见 docs/debugging.md）。
"""

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.release_version import package_path
# 官方 decky plugin build 只打包这些条目（0.0.8 的 zip_plugin 实现）。
OFFICIAL_TOP_LEVEL = {
    "LICENSE", "main.py", "package.json", "plugin.json", "README.md",
    "dist", "bin", "defaults", "py_modules",
}
VERSION = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", nargs="?", default=str(package_path(ROOT)))
    args = parser.parse_args()
    package = Path(args.package)
    problems, notes = [], []

    print("== Decky 加载条件 ==")
    if not package.is_file():
        print("FAIL 找不到安装包：%s" % package)
        return 1
    with zipfile.ZipFile(package) as archive:
        entries = [name for name in archive.namelist() if name and not name.endswith("/")]
        roots = {name.split("/", 1)[0] for name in entries if "/" in name}
        if len(roots) != 1:
            problems.append("ZIP 必须只有一个根目录，实际为：%s" % (sorted(roots) or "无"))
            root = None
        else:
            root = roots.pop()

        def require(relative, label):
            if root is None or f"{root}/{relative}" not in entries:
                problems.append("缺少 %s" % label)
                return False
            return True

        for relative, label in (
            ("plugin.json", "plugin.json"),
            ("package.json", "package.json"),
            ("main.py", "main.py"),
            ("dist/index.js", "dist/index.js"),
            ("LICENSE", "LICENSE"),
        ):
            if require(relative, label):
                print("PASS %s" % label)

        if root is not None:
            try:
                plugin = json.loads(archive.read(f"{root}/plugin.json"))
            except (KeyError, ValueError) as error:
                problems.append("plugin.json 无法解析：%s" % error)
                plugin = {}
            missing = [key for key in ("name", "author", "flags", "api_version") if key not in plugin]
            if missing:
                problems.append("plugin.json 缺少字段：%s" % "、".join(missing))
            else:
                print("PASS plugin.json 字段（name/author/flags/api_version）")
            try:
                version = json.loads(archive.read(f"{root}/package.json")).get("version", "")
            except (KeyError, ValueError) as error:
                version = ""
                problems.append("package.json 无法解析：%s" % error)
            if version and VERSION.match(str(version)):
                print("PASS 版本号 %s" % version)
            elif version:
                problems.append("package.json 的 version 不是有效语义版本：%s" % version)

            forbidden = [name for name in entries
                         if name.endswith(("auth.json", ".dev-data")) or ".dev-data/" in name
                         or name.startswith(f"{root}/references/")]
            if forbidden:
                problems.append("安装包包含不应分发的文件：%s" % "、".join(forbidden[:5]))
            else:
                print("PASS 不含密钥、开发数据或参考仓库")

    print("\n== 与官方 Decky CLI 打包器的差异（不影响本插件安装） ==")
    inner = {name[len(root) + 1:].split("/", 1)[0] for name in entries if root and name.startswith(root + "/")}
    extra = sorted(name for name in inner if name not in OFFICIAL_TOP_LEVEL)
    if extra:
        notes.append("官方 CLI 不打包：%s（本插件由 scripts/package.py 保留）" % "、".join(extra))
    if root is not None and "backend" in inner and f"{root}/backend/Dockerfile" not in entries:
        notes.append("含 backend/ 但没有 Dockerfile：官方 CLI 会把它当作自定义后端而拒绝")
    if not (ROOT / "pnpm-lock.yaml").exists():
        notes.append("仓库只有 package-lock.json：官方 builder 使用 pnpm --frozen-lockfile，需要 pnpm-lock.yaml")
    notes.append("官方 CLI 的 builder 镜像只有 linux/amd64；Apple Silicon 需 DOCKER_DEFAULT_PLATFORM=linux/amd64")
    for note in notes:
        print("WARN %s" % note)
    print("说明：Decky CLI 无法直接产出含随包运行时和资源的安装包，"
          "本仓库以 scripts/package.py + smoke_package.py 为准；细节见 docs/debugging.md。")

    if problems:
        print("\n检查未通过：")
        for problem in problems:
            print("FAIL %s" % problem)
        return 1
    print("\n检查通过：安装包满足 Decky 加载条件。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
