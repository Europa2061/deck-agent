"""检查公开文档的中英文配对和本地文件链接，不访问网络。"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(root=ROOT):
    root = Path(root)
    documents = [root / "README.md", root / "README.en.md", *sorted((root / "docs").glob("*.md"))]
    errors = []
    for path in documents:
        if not path.is_file():
            errors.append(f"缺少文档：{path.relative_to(root)}")
            continue
        if path.parent == root / "docs":
            pair = path.name.replace(".en.md", ".md") if path.name.endswith(".en.md") else path.stem + ".en.md"
            if not (path.parent / pair).is_file():
                errors.append(f"缺少中英文配对：{path.relative_to(root)} → {pair}")
        for url in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if "://" in url or url.startswith("#"):
                continue
            local = url.split("#", 1)[0]
            target = (path.parent / local).resolve()
            if local and (not target.exists() or not target.is_relative_to(root.resolve()) or ".internal" in target.parts):
                errors.append(f"无效或内部链接：{path.relative_to(root)} → {url}")
    return errors


if __name__ == "__main__":
    problems = check()
    if problems:
        raise SystemExit("\n".join(problems))
    print("公开文档的中英文配对与本地链接检查通过。")
