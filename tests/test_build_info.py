import json
import tempfile
import unittest
from pathlib import Path

from backend.build_info import collect


class BuildInfoTests(unittest.TestCase):
    def test_dev_checkout_uses_version_and_git_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(json.dumps({"version": "1.2.3"}))
            (root / ".git/refs/heads").mkdir(parents=True)
            (root / ".git/HEAD").write_text("ref: refs/heads/main\n")
            (root / ".git/refs/heads/main").write_text("abcdef1234567890abcdef\n")
            info = collect(root)
            self.assertEqual(info["version"], "1.2.3")
            self.assertEqual(info["commit"], "abcdef123456")
            self.assertEqual(info["id"], "1.2.3+abcdef123456")
            self.assertEqual(info["source"], "local")

    def test_packed_refs_and_detached_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(json.dumps({"version": "0.1.0"}))
            (root / ".git").mkdir()
            (root / ".git/HEAD").write_text("ref: refs/heads/main\n")
            (root / ".git/packed-refs").write_text("# pack-refs with: peeled fully-peeled\n" + "9" * 40 + " refs/heads/main\n")
            self.assertEqual(collect(root)["commit"], "9" * 12)
            (root / ".git/HEAD").write_text("e" * 40 + "\n")
            self.assertEqual(collect(root)["commit"], "e" * 12)

    def test_packaged_stamp_wins_over_runtime_and_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(json.dumps({"version": "2.0.0"}))
            (root / "build-info.json").write_text(json.dumps({
                "version": "2.0.0", "commit": "1234567890ab", "builtAt": "2026-10-31T08:00:00Z",
                "source": "package", "platform": "linux-x64", "pi": "1.5.0",
            }))
            (root / "runtime").mkdir()
            (root / "runtime/build-info.json").write_text(json.dumps({"commit": "ffffffffffff", "builtAt": "2025-01-01T00:00:00Z"}))
            info = collect(root)
            self.assertEqual(info["commit"], "1234567890ab")
            self.assertEqual(info["builtAt"], "2026-10-31T08:00:00Z")
            self.assertEqual(info["source"], "package")
            self.assertEqual(info["platform"], "linux-x64")

    def test_unknown_commit_still_produces_identifier(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(json.dumps({"version": "0.1.0"}))
            info = collect(root)
            self.assertEqual(info["commit"], "unknown")
            self.assertEqual(info["id"], "0.1.0+unknown")


if __name__ == "__main__":
    unittest.main()
