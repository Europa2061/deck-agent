import contextlib
import hashlib
import io
import json
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from backend.updates import check_release
from scripts import package as packager
from scripts.release_version import next_version, package_path


class PackageVersionTests(unittest.TestCase):
    def test_semver_upgrade_and_reset(self):
        self.assertEqual(next_version("0.9.9"), "0.9.10")
        self.assertEqual(next_version("1.9.7", "minor"), "1.10.0")
        self.assertEqual(next_version("1.9.7", "major"), "2.0.0")
        for invalid in ("1.2", "01.2.3", "1.2.3-beta", "../1.2.3", "v1.2.3"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                next_version(invalid)

    def test_repeated_packages_upgrade_manifests_and_keep_versioned_archives(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {
                "package.json": json.dumps({"name": "deck-agent", "version": "0.1.0"}),
                "package-lock.json": json.dumps({"version": "0.1.0", "packages": {"": {"version": "0.1.0"}}}),
                "runtime/build-info.json": json.dumps({"platform": "linux-x64", "pi": "1.5.0"}),
                "runtime/package.json": json.dumps({"dependencies": {"@earendil-works/pi-coding-agent": "1.5.0"}}),
                "runtime/node_modules/@earendil-works/pi-coding-agent/package.json": json.dumps({"version": "1.5.0"}),
                "runtime/node_modules/@earendil-works/pi-ai/package.json": json.dumps({"version": "1.5.0"}),
                "runtime/node/bin/node": "test-node",
                "runtime/stt/bin/sherpa-onnx-offline": "test-stt",
                "dist/index.js": "test-frontend",
                "backend/__init__.py": "", "resources/system.md": "test",
                "main.py": "", "plugin.json": "{}", "LICENSE": "test", "README.md": "test", "README.en.md": "test",
                "docs/THIRD_PARTY.md": "许可证", "docs/THIRD_PARTY.en.md": "Licenses",
            }
            for name, content in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            for bump, expected in (("patch", "0.1.1"), ("patch", "0.1.2"), ("minor", "0.2.0")):
                with patch.object(packager, "ROOT", root), patch.object(packager.sys, "argv", ["package.py", "--bump", bump]), patch.object(packager, "commit_and_dirty", return_value=("test", False)), contextlib.redirect_stdout(io.StringIO()):
                    packager.main()
                lock = json.loads((root / "package-lock.json").read_text())
                self.assertEqual(lock["version"], expected)
                self.assertEqual(lock["packages"][""]["version"], expected)
                package = package_path(root)
                self.assertEqual(package.name, f"deck-agent-{expected}.zip")
                with zipfile.ZipFile(package) as archive:
                    self.assertIsNone(archive.testzip())
                    self.assertEqual(archive.read("deck-agent/docs/THIRD_PARTY.en.md"), b"Licenses")
                    self.assertEqual(json.loads(archive.read("deck-agent/package.json"))["version"], expected)
                    self.assertEqual(json.loads(archive.read("deck-agent/build-info.json"))["version"], expected)
                checksum, filename = package.with_suffix(".zip.sha256").read_text().split()
                self.assertEqual(filename, package.name)
                self.assertEqual(checksum, hashlib.sha256(package.read_bytes()).hexdigest())
            self.assertEqual(len(list((root / "out").glob("*.zip"))), 3)
            # 不能把旧的已安装 Pi 或旧发行标记包装成新版本。
            for filename in ("runtime/build-info.json", "runtime/node_modules/@earendil-works/pi-ai/package.json"):
                target = root / filename
                original = target.read_text()
                target.write_text(original.replace("1.5.0", "1.4.0"))
                with patch.object(packager, "ROOT", root), patch.object(packager.sys, "argv", ["package.py"]):
                    with self.assertRaises(SystemExit):
                        packager.main()
                self.assertEqual(json.loads((root / "package.json").read_text())["version"], "0.2.0")
                target.write_text(original)


    def test_ci_package_has_committed_version_and_clean_build_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {
                ".gitignore": "out/\nruntime/symlinks.json\nruntime/executables.json\n",
                "package.json": json.dumps({"name": "deck-agent", "version": "0.1.0"}),
                "package-lock.json": json.dumps({"version": "0.1.0", "packages": {"": {"version": "0.1.0"}}}),
                "runtime/build-info.json": json.dumps({"platform": "linux-x64", "pi": "test-pi"}),
                "runtime/package.json": json.dumps({"dependencies": {"@earendil-works/pi-coding-agent": "test-pi"}}),
                "runtime/node_modules/@earendil-works/pi-coding-agent/package.json": json.dumps({"version": "test-pi"}),
                "runtime/node_modules/@earendil-works/pi-ai/package.json": json.dumps({"version": "test-pi"}),
                "runtime/node/bin/node": "test", "runtime/stt/bin/sherpa-onnx-offline": "test",
                "dist/index.js": "test", "backend/__init__.py": "", "resources/system.md": "test",
                "main.py": "", "plugin.json": "{}", "LICENSE": "test", "README.md": "test", "README.en.md": "test",
            }
            for name, content in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            def git(*args):
                return subprocess.check_output(["git", *args], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
            git("init")
            git("config", "user.name", "test")
            git("config", "user.email", "test@example.invalid")
            git("add", "--", *files.keys())
            git("commit", "-m", "测试初始化 / Test setup")
            with patch.object(packager, "ROOT", root), patch.object(packager.sys, "argv", ["package.py", "--commit-version"]), contextlib.redirect_stdout(io.StringIO()):
                packager.main()
            with zipfile.ZipFile(package_path(root)) as archive:
                stamp = json.loads(archive.read("deck-agent/build-info.json"))
            self.assertEqual(stamp["commit"], git("rev-parse", "HEAD")[:12])
            self.assertFalse(stamp["dirty"])
            self.assertEqual(stamp["version"], "0.1.1")
            self.assertEqual(git("status", "--porcelain"), "")
            self.assertIn("发布 0.1.1 / Release 0.1.1", git("log", "-1", "--format=%s"))
            self.assertIn("Synchronize package version", git("log", "-1", "--format=%b"))
            (root / "main.py").write_text("pending work")
            with patch.object(packager, "ROOT", root), patch.object(packager.sys, "argv", ["package.py", "--commit-version"]):
                with self.assertRaisesRegex(SystemExit, "干净工作区"):
                    packager.main()
            self.assertEqual(json.loads((root / "package.json").read_text())["version"], "0.1.1")

    def test_release_uses_matching_versioned_asset(self):
        release = {"tag_name": "v0.2.0", "assets": [
            {"name": "deck-agent-0.1.9.zip", "browser_download_url": "https://example.com/old"},
            {"name": "deck-agent.zip", "browser_download_url": "https://example.com/legacy"},
            {"name": "deck-agent-0.2.0.zip", "browser_download_url": "https://example.com/current"},
        ]}
        with patch("backend.updates.urllib.request.urlopen") as response:
            response.return_value.__enter__.return_value = io.StringIO(json.dumps(release))
            result = check_release("test/repo", "0.1.0")
        self.assertTrue(result["available"])
        self.assertEqual(result["zipUrl"], "https://example.com/current")


if __name__ == "__main__":
    unittest.main()
