import io
import json
import unittest
import urllib.error
from unittest.mock import patch

from backend.updates import check_release


def response(value):
    return io.StringIO(json.dumps(value))


def release(version, **kwargs):
    return {"tag_name": f"v{version}", "assets": [{"name": f"deck-agent-{version}.zip",
            "browser_download_url": "https://example.com/package.zip"}], **kwargs}


class UpdateTests(unittest.TestCase):
    def test_stable_release_keeps_stable_channel(self):
        with patch("backend.updates.urllib.request.urlopen", return_value=response(release("0.6.0"))) as fetch:
            result = check_release("owner/repo", "0.5.1")
        self.assertTrue(result["available"])
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(result["latest"], "v0.6.0")

    def test_only_prereleases_selects_highest_with_matching_package(self):
        not_found = urllib.error.HTTPError("https://example.com", 404, "Not found", {}, None)
        releases = [release("0.6.0", prerelease=True), release("0.7.0", prerelease=True),
                    release("0.8.0", prerelease=True, draft=True),
                    release("0.9.0", prerelease=True, assets=[]),
                    {"tag_name": "invalid", "prerelease": True}]
        with patch("backend.updates.urllib.request.urlopen", side_effect=[not_found, response(releases)]):
            result = check_release("owner/repo", "0.5.1")
        self.assertEqual(result["latest"], "v0.7.0")
        self.assertIn("公开测试版", result["notes"])

    def test_empty_repository_and_rate_limit(self):
        not_found = urllib.error.HTTPError("https://example.com", 404, "Not found", {}, None)
        with patch("backend.updates.urllib.request.urlopen", side_effect=[not_found, response([])]):
            with self.assertRaisesRegex(ValueError, "没有带安装包"):
                check_release("owner/repo", "0.5.1")
        for code in (403, 429):
            with patch("backend.updates.urllib.request.urlopen", side_effect=urllib.error.HTTPError(
                    "https://example.com", code, "Limited", {}, None)) as fetch:
                with self.assertRaisesRegex(ValueError, "请求受限"):
                    check_release("owner/repo", "0.5.1")
                self.assertEqual(fetch.call_count, 1)
