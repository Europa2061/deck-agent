import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/decky_compat_report.py"


def make_package(path, *, include_dist=True, plugin=None):
    plugin = plugin if plugin is not None else {"name": "Deck Agent", "author": "test", "flags": [], "api_version": 1}
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("deck-agent/plugin.json", json.dumps(plugin))
        archive.writestr("deck-agent/package.json", json.dumps({"version": "0.1.0"}))
        archive.writestr("deck-agent/main.py", "")
        archive.writestr("deck-agent/LICENSE", "")
        if include_dist:
            archive.writestr("deck-agent/dist/index.js", "")
    return path


class DeckyCompatReportTests(unittest.TestCase):
    def run_report(self, package):
        return subprocess.run([sys.executable, str(SCRIPT), str(package)], capture_output=True, text=True, timeout=60)

    def test_loader_requirements_pass_and_official_deviations_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = make_package(Path(tmp) / "plugin.zip")
            result = self.run_report(package)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS dist/index.js", result.stdout)
            self.assertIn("WARN 仓库只有 package-lock.json", result.stdout)

    def test_missing_frontend_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = make_package(Path(tmp) / "plugin.zip", include_dist=False)
            result = self.run_report(package)
            self.assertEqual(result.returncode, 1)
            self.assertIn("缺少 dist/index.js", result.stdout)

    def test_incomplete_plugin_json_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = make_package(Path(tmp) / "plugin.zip", plugin={"name": "Deck Agent"})
            result = self.run_report(package)
            self.assertEqual(result.returncode, 1)
            self.assertIn("plugin.json 缺少字段", result.stdout)


if __name__ == "__main__":
    unittest.main()
