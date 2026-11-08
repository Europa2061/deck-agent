import io
import json
import os
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from backend.player_tools import dispatch
from backend.workflows.common import Store, file_hash
from backend.workflows import games, mods, plugins, saves, network, archives

ROOT = Path(__file__).resolve().parents[1]


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name).resolve()
        self.store = Store(self.home, self.home / 'data')
        self.game = self.home / 'game'
        self.game.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def archive(self, files, name='mod.zip'):
        path = self.home / name
        with zipfile.ZipFile(path, 'w') as source:
            for item, value in files.items():
                source.writestr(item, value)
        return path

    def test_multi_library_inventory_vdf_escaping_and_nonsteam_diagnosis(self):
        self.assertEqual(games.parse_vdf('"x" { "empty" "" "path" "a\\\\b" }')['x'], {'empty': '', 'path': 'a\\b'})
        steam = self.home / '.local/share/Steam'
        sd = self.home / 'SD card'
        (steam / 'steamapps').mkdir(parents=True)
        (sd / 'steamapps/common/Demo').mkdir(parents=True)
        (steam / 'steamapps/libraryfolders.vdf').write_text('"libraryfolders" { "0" { "path" "' + str(steam) + '" } "1" { "path" "' + str(sd) + '" } }')
        (sd / 'steamapps/appmanifest_12.acf').write_text('"AppState" { "appid" "12" "name" "测试游戏" "installdir" "Demo" "SizeOnDisk" "1024" }')
        result = games.inventory(self.store)
        self.assertEqual(len(result['games']), 1)
        self.assertEqual(result['games'][0]['path'], str(sd / 'steamapps/common/Demo'))
        (self.game / 'settings.ini').write_text('quality=high\n')
        self.assertIn(str(self.game / 'settings.ini'), games.diagnose(self.store, {'path': str(self.game)})['configCandidates'])

    def test_config_change_and_restore_both_preserve_previous_file(self):
        config = self.game / 'settings.ini'
        config.write_text('quality=high\n')
        result = games.config_apply(self.store, {'file': str(config), 'old': 'quality=high', 'new': 'quality=medium'})
        self.assertEqual(config.read_text(), 'quality=medium\n')
        restored = self.store.restore(result['backupId'])
        self.assertEqual(config.read_text(), 'quality=high\n')
        self.assertEqual(Path(self.store.get(restored['beforeId'])['files'][0]['copy']).read_text(), 'quality=medium\n')
        with self.assertRaises(ValueError):
            games.config_apply(self.store, {'file': str(config), 'old': 'missing', 'new': 'bad'})
        self.assertEqual(config.read_text(), 'quality=high\n')

    def test_mod_install_disable_enable_uninstall_preserves_original(self):
        (self.game / 'config.ini').write_text('original')
        archive = self.archive({'top/config.ini': 'modded', 'top/Mods/foo.txt': 'new'})
        params = {'archive': str(archive), 'target': str(self.game), 'stripComponents': 1, 'name': 'Demo mod', 'source': 'https://example.com/mod'}
        preview = mods.plan(self.store, params)
        self.assertEqual(preview['overwriteCount'], 1)
        record = mods.install(self.store, params)
        self.assertEqual((self.game / 'config.ini').read_text(), 'modded')
        with self.assertRaisesRegex(ValueError, '已有 Mod'):
            mods.plan(self.store, params)
        mods.disable(self.store, record['id'])
        self.assertEqual((self.game / 'config.ini').read_text(), 'original')
        self.assertFalse((self.game / 'Mods/foo.txt').exists())
        mods.enable(self.store, record['id'])
        self.assertEqual((self.game / 'Mods/foo.txt').read_text(), 'new')
        mods.uninstall(self.store, record['id'])
        self.assertEqual((self.game / 'config.ini').read_text(), 'original')
        self.assertFalse((self.game / 'Mods/foo.txt').exists())

    def test_mod_conflicts_external_changes_and_traversal_blocked(self):
        bad = self.archive({'../escape': 'bad'}, 'bad.zip')
        with self.assertRaises(ValueError):
            archives.members(bad)
        good = self.archive({'file.txt': 'new'})
        record = mods.install(self.store, {'archive': str(good), 'target': str(self.game)})
        (self.game / 'file.txt').write_text('game update')
        with self.assertRaisesRegex(ValueError, '其他程序改变'):
            mods.disable(self.store, record['id'])
        self.assertEqual((self.game / 'file.txt').read_text(), 'game update')
        linked = self.home / 'linked'
        linked.mkdir()
        (self.game / 'link').symlink_to(linked, target_is_directory=True)
        other = self.archive({'link/x.txt': 'bad'}, 'link.zip')
        with self.assertRaises(ValueError):
            mods.plan(self.store, {'archive': str(other), 'target': str(self.game)})

    def test_interrupted_mod_can_restore_written_files(self):
        (self.game / 'first').write_text('old')
        archive = self.archive({'first': 'new', 'second': 'new'})
        from backend.workflows.common import atomic_copy
        def fail_second(source, target):
            if str(target).endswith('/second'):
                raise OSError('disk full')
            atomic_copy(source, target)
        with patch('backend.workflows.mods.atomic_copy', side_effect=fail_second):
            with self.assertRaises(OSError):
                mods.install(self.store, {'archive': str(archive), 'target': str(self.game)})
        record = self.store.list('mod')[0]
        self.assertEqual(record['status'], 'interrupted')
        mods.disable(self.store, record['id'])
        self.assertEqual((self.game / 'first').read_text(), 'old')
        self.assertFalse((self.game / 'second').exists())

    def plugin_archive(self, name='Sample Plugin'):
        return self.archive({'sample/plugin.json': json.dumps({'name': name, 'author': 'Example', 'api_version': 1}),
                             'sample/package.json': json.dumps({'version': '1.2.3'}), 'sample/dist/index.js': 'export default ()=>({});'}, 'plugin.zip')

    def test_plugin_prepare_queue_native_claim_and_tamper_detection(self):
        archive = self.plugin_archive()
        record = plugins.prepare(self.store, {'archive': str(archive)})
        self.assertEqual(record['manifest']['name'], 'Sample Plugin')
        plugins.queue(self.store, record['id'])
        self.assertEqual(plugins.pending(self.store)[0]['ticket'], record['id'])
        with patch.dict(os.environ, {'DECK_AGENT_PLUGINS_DIR': str(self.home / 'plugins')}):
            claim = plugins.claim(self.store, record['id'])
        self.assertEqual(claim['name'], 'Sample Plugin')
        self.assertEqual(claim['installType'], 0)
        self.assertEqual(plugins.pending(self.store), [])
        with self.assertRaises(ValueError):
            plugins.claim(self.store, record['id'])
        archive.write_bytes(b'bad')
        with self.assertRaises(ValueError):
            plugins.queue(self.store, record['id'])

    def test_plugin_source_zip_and_self_install_rejected(self):
        source_zip = self.archive({'source/README.md': 'source'}, 'source.zip')
        with self.assertRaisesRegex(ValueError, '运行文件'):
            plugins.inspect_zip(source_zip)
        with self.assertRaisesRegex(ValueError, '关于与更新'):
            plugins.inspect_zip(self.plugin_archive('Deck Agent'))

    def test_topic_scope_enforced_and_web_search_results_not_instructions(self):
        with patch('backend.workflows.network.github', return_value={'items': [
                {'full_name': 'a/good', 'html_url': 'https://github.com/a/good', 'topics': ['decky-plugin']},
                {'full_name': 'b/other', 'html_url': 'https://github.com/b/other', 'topics': ['other']}]}) as fetch:
            result = network.repo_search('transfer OR topic:other', topic='decky-plugin')
        self.assertEqual(len(result['items']), 1)
        self.assertIn('topic%3Adecky-plugin', fetch.call_args.args[0])
        rss = b'<rss><channel><item><title>Demo mod</title><link>https://example.com/mod</link><description>test</description></item></channel></rss>'
        with patch('backend.workflows.network.read_url', return_value=rss):
            self.assertEqual(network.web_search('demo')["items"][0]['title'], 'Demo mod')

    def test_cli_uses_json_stdin_without_shell_interpolation(self):
        env = {**os.environ, 'HOME': str(self.home), 'DECK_AGENT_DATA_DIR': str(self.home / 'cli-data')}
        result = subprocess.run([__import__('sys').executable, str(ROOT / 'backend/player_tools.py')], input=json.dumps({'tool': 'deck_games', 'params': {'action': 'list'}}), text=True, capture_output=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['ok'])

    def test_saves_calls_isolated_cli_and_preserves_current_before_restore(self):
        calls = []
        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            if 'backup' in cmd and '--preview' in cmd:
                value = {'games': {'Demo': {'files': {'/tmp/demo.sav': {}}}}}
            else:
                value = {'overall': {'processedGames': 1}, 'games': {}}
            return subprocess.CompletedProcess(cmd, 0, json.dumps(value).encode(), b'')
        with patch('backend.workflows.saves.command', return_value=['ludusavi']), patch('backend.workflows.saves.subprocess.run', side_effect=fake_run):
            result = saves.restore(self.store, {'game': 'Demo', 'backupId': 'backup-1'})
        self.assertIsNotNone(result['before'])
        self.assertEqual([c[c.index('--config') + 2] for c in calls], ['backup', 'backup', 'restore'])
        self.assertTrue(all('--no-cloud-sync' in c for c in calls))
        self.assertIn('--backup', calls[-1])
        self.assertEqual(calls[-1][-2:], ['--', 'Demo'])


    def test_linux_mod_execute_permissions_survive_disable_enable(self):
        path = self.home / 'executable.zip'
        info = zipfile.ZipInfo('loader.sh')
        info.external_attr = 0o104755 << 16
        with zipfile.ZipFile(path, 'w') as source:
            source.writestr(info, '#!/bin/sh\nprintf mod-ok')
        record = mods.install(self.store, {'archive': str(path), 'target': str(self.game)})
        target = self.game / 'loader.sh'
        self.assertEqual(target.stat().st_mode & 0o7777, 0o755)
        self.assertEqual(subprocess.check_output([str(target)]), b'mod-ok')
        mods.disable(self.store, record['id'])
        mods.enable(self.store, record['id'])
        self.assertEqual(subprocess.check_output([str(target)]), b'mod-ok')

    def test_dismissed_plugin_can_requeue_same_ticket(self):
        record = plugins.prepare(self.store, {'archive': str(self.plugin_archive())})
        record['status'] = 'dismissed'
        self.store.save(record)
        plugins.queue(self.store, record['id'])
        self.assertEqual(plugins.pending(self.store)[0]['ticket'], record['id'])

    def test_ludusavi_restore_supports_protected_backup_path_and_rejects_empty_result(self):
        calls = []
        path = self.home / 'protection'
        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            value = {'games': {}} if '--preview' in cmd else {'overall': {'processedGames': 0}, 'games': {}}
            return subprocess.CompletedProcess(cmd, 0, json.dumps(value).encode(), b'')
        with patch('backend.workflows.saves.command', return_value=['ludusavi']), patch('backend.workflows.saves.subprocess.run', side_effect=fake_run):
            with self.assertRaisesRegex(ValueError, '没有实际恢复'):
                saves.restore(self.store, {'game': 'Demo', 'backupPath': str(path)})
        self.assertEqual(calls[-1][calls[-1].index('--path') + 1], str(path))
        self.assertFalse(self.store.list('ludusavi-restore'))


    def test_network_download_resumes_and_reuses_verified_cache(self):
        from backend.workflows.common import file_hash
        import hashlib
        data = b'a' * (64 * 1024) + b'last chunk'
        class Response(io.BytesIO):
            def __init__(self, body, status=200, start=0, fail=False):
                super().__init__(body); self.status=status; self.headers={'Content-Length':str(len(body))}; self.fail=fail
                if status==206:self.headers['Content-Range']='bytes '+str(start)+'-'+str(len(data)-1)+'/'+str(len(data))
            def read(self, size=-1):
                if self.fail and self.tell()>=64*1024:raise TimeoutError('interrupted')
                return super().read(size)
        expected = hashlib.sha256(data).hexdigest()
        with patch('backend.workflows.network.open_url', side_effect=[Response(data,fail=True),Response(data[64*1024:],206,64*1024)]) as fetch, patch('backend.workflows.network.time.sleep'):
            result=network.download(self.store,'https://example.com/mod.zip',expected)
        self.assertTrue(fetch.call_args_list[1].args[1]['Range'].startswith('bytes=65536-'))
        self.assertEqual(file_hash(result['path']),expected)
        with patch('backend.workflows.network.open_url',side_effect=AssertionError('cache should avoid network')):
            self.assertEqual(network.download(self.store,'https://example.com/mod.zip',expected)['id'],result['id'])

    def test_tar_dot_root_and_github_readme_are_supported(self):
        import tarfile,base64
        path=self.home/'payload.tar.gz'
        payload=self.home/'payload';payload.mkdir();(payload/'mod.txt').write_text('mod')
        with tarfile.open(path,'w:gz') as source:source.add(payload,arcname='.')
        target=self.home/'unpacked';target.mkdir()
        archives.extract(path,target)
        self.assertEqual((target/'mod.txt').read_text(),'mod')
        body='# Install\nUse the correct game version.'
        with patch('backend.workflows.network.github',return_value={'content':base64.b64encode(body.encode()).decode()}):
            result=network.page('https://github.com/author/project#readme')
        self.assertIn('Use the correct game version.',result['text'])


    def test_download_joins_intentional_partial_content_responses(self):
        import hashlib
        data=b'first-partsecond-part'
        class Partial(io.BytesIO):
            status=206
            def __init__(self,part,start):
                super().__init__(part)
                self.headers={'Content-Range':f'bytes {start}-{start+len(part)-1}/{len(data)}','Content-Length':str(len(part))}
        first=b'first-part';second=b'second-part'
        with patch('backend.workflows.network.open_url',side_effect=[Partial(first,0),Partial(second,len(first))]) as fetch:
            result=network.download(self.store,'https://example.com/mod.zip',hashlib.sha256(data).hexdigest())
        self.assertEqual(Path(result['path']).read_bytes(),data)
        self.assertTrue(fetch.call_args_list[1].args[1]['Range'].startswith('bytes=10-'))

    def test_service_import_does_not_require_optional_xml_stdlib(self):
        script = '''import builtins
original=builtins.__import__
def limited(name,*args,**kwargs):
 if name=='xml' or name.startswith('xml.'):
  raise ModuleNotFoundError("Decky embedded Python omits xml")
 return original(name,*args,**kwargs)
builtins.__import__=limited
import backend.service
'''
        result=subprocess.run([__import__('sys').executable,'-c',script],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
