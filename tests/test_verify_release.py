import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.verify_release import verify


class VerifyReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'package.json').write_text(json.dumps({'version': '0.6.0'}))
        (self.root / 'package-lock.json').write_text(json.dumps({
            'version': '0.6.0', 'packages': {'': {'version': '0.6.0'}}}))
        (self.root / 'out').mkdir()
        self.path = self.root / 'out/deck-agent-0.6.0.zip'
        self.write_package()

    def write_package(self, version='0.6.0', extra=None):
        with zipfile.ZipFile(self.path, 'w') as archive:
            archive.writestr('deck-agent/package.json', json.dumps({'version': version}))
            archive.writestr('deck-agent/build-info.json', json.dumps({
                'version': version, 'platform': 'linux-x64'}))
            if extra:
                archive.writestr(extra, 'unexpected')
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.path.with_suffix('.zip.sha256').write_text(f'{digest}  {self.path.name}\n')

    def test_valid_release_and_tag(self):
        self.assertEqual(verify(self.root, tag='v0.6.0'), '0.6.0')
        with self.assertRaisesRegex(ValueError, '标签'):
            verify(self.root, tag='v0.5.9')

    def test_rejects_tampered_checksum_and_wrong_internal_version(self):
        self.path.with_suffix('.zip.sha256').write_text('0' * 64 + '  ' + self.path.name)
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            verify(self.root)
        self.write_package(version='0.5.9')
        with self.assertRaisesRegex(ValueError, '包内版本'):
            verify(self.root)

    def test_rejects_wrong_root_traversal_and_lock_version(self):
        for extra in ('other/file', 'deck-agent/../escape'):
            self.write_package(extra=extra)
            with self.assertRaisesRegex(ValueError, '根目录'):
                verify(self.root)
        self.write_package()
        lock_path = self.root / 'package-lock.json'
        lock = json.loads(lock_path.read_text())
        lock['packages']['']['version'] = '0.5.9'
        lock_path.write_text(json.dumps(lock))
        with self.assertRaisesRegex(ValueError, '锁文件'):
            verify(self.root)
