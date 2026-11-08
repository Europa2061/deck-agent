"""Pi 内置玩家工具的 JSON CLI；参数从 stdin 读取，不拼接 shell。"""
import json
import signal
import sys
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = 'backend'

from .workflows.common import Store
from .workflows import archives, games, mods, network, plugins, saves

MUTATIONS = {
    'deck_games': {'config_apply', 'restore'},
    'deck_saves': {'install', 'backup', 'restore', 'path_backup', 'path_restore'},
    'deck_mods': {'download', 'install', 'disable', 'enable', 'uninstall'},
    'deck_plugins': {'prepare', 'install'},
}


def dispatch(store, tool, p):
    action = p.get('action')
    if tool == 'deck_games':
        if action == 'list': return games.inventory(store)
        if action == 'diagnose': return games.diagnose(store, p)
        if action == 'config_preview':
            path, _, _, diff = games.config_preview(store, p)
            return {'file': str(path), 'diff': diff, 'applied': False}
        if action == 'config_apply': return games.config_apply(store, p)
        if action == 'restore': return store.restore(p['backupId'])
        if action == 'history': return {'operations': store.list()[:50]}
    elif tool == 'deck_saves':
        if action == 'status': return saves.status(store)
        if action == 'install': return saves.install(store)
        if action == 'find': return saves.find(store, p)
        if action == 'preview_backup': return saves.backup(store, p, preview=True)
        if action == 'backup': return saves.backup(store, p)
        if action == 'backups': return saves.backups(store, p)
        if action == 'preview_restore': return saves.restore(store, p, preview=True)
        if action == 'restore': return saves.restore(store, p)
        if action == 'path_backup': return store.backup(p['paths'], p.get('label', '指定存档文件备份'))
        if action == 'path_restore': return store.restore(p['backupId'])
        if action == 'history': return {'operations': [r for r in store.list() if r['kind'] in ('backup', 'ludusavi-backup', 'ludusavi-restore', 'pre-restore')][:50]}
    elif tool == 'deck_mods':
        if action == 'search': return network.repo_search(p['query']) if p.get('provider') == 'github' else network.web_search(p['query'])
        if action == 'read_source': return network.page(p['url'])
        if action == 'download': return network.download(store, p['url'], p.get('sha256'))
        if action == 'inspect':
            path, kind, files = archives.members(p['archive'], p.get('stripComponents', 0))
            return {'archive': str(path), 'format': kind, 'files': files[:300], 'fileCount': len(files), 'truncated': len(files) > 300}
        if action == 'plan': return mods.plan(store, p)
        if action == 'install': return mods.install(store, p)
        if action == 'list': return {'mods': [r for r in store.list('mod') if not p.get('gameId') or r.get('gameId') == p['gameId']]}
        if action == 'disable': return mods.disable(store, p['modId'])
        if action == 'enable': return mods.enable(store, p['modId'])
        if action == 'uninstall': return mods.uninstall(store, p['modId'])
    elif tool == 'deck_plugins':
        if action == 'search': return network.repo_search(p['query'], topic='decky-plugin')
        if action == 'inspect': return plugins.inspect_repo(p['repo'])
        if action == 'read_source': return network.page(p['url'])
        if action == 'prepare': return plugins.prepare(store, p)
        if action == 'install': return plugins.queue(store, p['ticket'])
        if action == 'status': return plugins.status(store, p.get('ticket'))
    raise ValueError('未知工具或操作；请核对工具提供的 action。')


def main():
    try:
        request = json.load(sys.stdin)
        tool, params = request['tool'], request['params']
        store = Store()
        # 进程中止时让当前操作留下日志；不把半完成动作报告为成功。
        def stop(_signum, _frame):
            raise InterruptedError('操作被停止，请检查 history 中的完成状态后继续。')
        signal.signal(signal.SIGTERM, stop)
        import contextlib
        with store.lock() if params.get('action') in MUTATIONS.get(tool, set()) else contextlib.nullcontext():
            result = dispatch(store, tool, params)
        print(json.dumps({'ok': True, 'value': result}, ensure_ascii=False))
    except Exception as error:
        print(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == '__main__':
    main()
