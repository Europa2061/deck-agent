import json
import os
import re
import zipfile
from pathlib import Path

from . import network
from .common import file_hash
from ..storage import read_json, write_json


def inspect_repo(repo):
    repo = network.repository(repo)
    info = network.github('repos/' + repo)
    releases = network.github('repos/' + repo + '/releases?per_page=10')
    return {'repo': repo, 'description': info.get('description'), 'archived': info.get('archived'), 'topics': info.get('topics', []),
            'readmeUrl': info['html_url'] + '#readme',
            'releases': [{'tag': r['tag_name'], 'prerelease': r.get('prerelease'), 'url': r['html_url'], 'notes': (r.get('body') or '')[:12000],
                          'assets': [{'name': a['name'], 'url': a['browser_download_url'], 'bytes': a.get('size'), 'digest': a.get('digest')} for a in r.get('assets', [])]}
                         for r in releases if not r.get('draft')],
            'note': 'Topic 不是官方审核标志，也不表示未上架商店；选择作者发行的插件 ZIP，不能用源码 ZIP。'}


def inspect_zip(path):
    from .archives import members
    path, kind, files = members(path)
    if kind != 'zip':
        raise ValueError('Decky 插件需要 ZIP 安装包。')
    roots = set(item['relative'].split('/')[0] for item in files)
    if len(roots) != 1:
        raise ValueError('插件 ZIP 必须只有一个根目录。')
    root = next(iter(roots))
    names = {f['relative'] for f in files}
    if not {root + '/plugin.json', root + '/package.json', root + '/dist/index.js'}.issubset(names):
        raise ValueError('该 ZIP 缺少 Decky 插件运行文件，可能是源码包。')
    with zipfile.ZipFile(path) as source:
        for name in ('plugin.json', 'package.json'):
            if source.getinfo(root + '/' + name).file_size > 1024**2:
                raise ValueError('插件清单过大。')
        plugin = json.loads(source.read(root + '/plugin.json'))
        package = json.loads(source.read(root + '/package.json'))
    name, version = plugin.get('name'), package.get('version')
    if not isinstance(name, str) or not name.strip() or len(name) > 150 or '/' in name or '\\' in name or not isinstance(version, str) or not version:
        raise ValueError('插件名称或版本无效。')
    if name == 'Deck Agent' or root == 'deck-agent':
        raise ValueError('Deck Agent 自身请使用「关于与更新」，避免任务执行中重载自己。')
    return {'name': name, 'version': version, 'root': root, 'author': plugin.get('author'), 'flags': plugin.get('flags', []), 'apiVersion': plugin.get('api_version'),
            'bytes': path.stat().st_size, 'sha256': file_hash(path), 'fileCount': len(files)}


def prepare(store, params):
    repo = network.repository(params['repo']) if params.get('repo') else None
    source = params.get('url')
    expected = params.get('sha256')
    if not params.get('archive'):
        if repo:
            releases = inspect_repo(repo)['releases']
            releases = [r for r in releases if not params.get('tag') or r['tag'] == params['tag']]
            if not params.get('tag'):
                stable = [r for r in releases if not r['prerelease']]
                releases = stable or releases
            if not releases:
                raise ValueError('没有找到对应的公开发行版本。')
            assets = releases[0]['assets']
            candidates = [a for a in assets if a['name'].lower().endswith('.zip') and not re.search(r'(source|legal|symbols)', a['name'], re.I)]
            if source:
                candidates = [a for a in assets if a['url'] == source]
            if len(candidates) != 1:
                raise ValueError('发行文件不唯一，请先 inspect 后指定所需 ZIP 的 url。')
            asset = candidates[0]
            source = asset['url']
            digest = asset.get('digest') or ''
            if digest.startswith('sha256:'):
                expected = digest[7:]
        if not source:
            raise ValueError('请提供仓库 repo、安装包 url 或本地 archive。')
        downloaded = network.download(store, source, expected)
        path = Path(downloaded['path'])
    else:
        path = Path(params['archive']).expanduser().resolve()
        if expected and file_hash(path) != expected.lower():
            raise ValueError('安装包校验失败。')
    info = inspect_zip(path)
    record = store.new_record('plugin-install', repo=repo, source=source, path=str(path), manifest=info, status='prepared', sourceChecksumVerified=bool(expected))
    return store.save(record)


def queue(store, ticket):
    record = store.get(ticket)
    if record.get('kind') != 'plugin-install' or record.get('status') not in ('prepared', 'prompted', 'failed', 'dismissed'):
        raise ValueError('请先准备插件安装包，取得有效 ticket。')
    if inspect_zip(record['path'])['sha256'] != record['manifest']['sha256']:
        raise ValueError('安装包已变化，请重新 prepare。')
    record['status'] = 'queued'
    store.save(record)
    queue_path = store.root / 'plugin-queue.json'
    tickets = read_json(queue_path, [])
    write_json(queue_path, list(dict.fromkeys(tickets + [record['id']]))[-100:])
    return {'ticket': record['id'], 'name': record['manifest']['name'], 'version': record['manifest']['version'],
            'status': 'queued', 'note': '等待 Deck Agent 前端打开 Decky 原生确认；此时尚未安装成功。可用 status 核对。'}


def pending(store):
    records = [store.get(ticket) for ticket in read_json(store.root / 'plugin-queue.json', [])]
    return [{'ticket': r['id'], 'name': r['manifest']['name'], 'version': r['manifest']['version'], 'status': r['status'], 'error': r.get('error')} for r in records if r['status'] in ('queued', 'failed')]


def claim(store, ticket):
    record = store.get(ticket)
    if record.get('kind') != 'plugin-install' or record.get('status') not in ('queued', 'failed'):
        raise ValueError('该安装请求已处理；取消后可再次调用 install。')
    info = inspect_zip(record['path'])
    if info['sha256'] != record['manifest']['sha256']:
        raise ValueError('安装包校验失败。')
    record['status'] = 'prompted'
    store.save(record)
    return {'artifact': 'file://' + str(Path(record['path']).resolve()), 'name': info['name'], 'version': info['version'], 'hash': info['sha256'],
            'flags': info['flags'], 'sourceChecksumVerified': record['sourceChecksumVerified'],
            'installType': 2 if any(p['name'] == info['name'] for p in installed(store)) else 0}


def installed(store):
    directory = Path(os.environ.get('DECK_AGENT_PLUGINS_DIR', store.home / 'homebrew/plugins'))
    result = []
    if directory.is_dir():
        for root in directory.iterdir():
            try:
                plugin = json.loads((root / 'plugin.json').read_text())
                package = json.loads((root / 'package.json').read_text())
                result.append({'name': plugin.get('name'), 'version': package.get('version'), 'path': str(root), 'flags': plugin.get('flags', [])})
            except (OSError, ValueError):
                continue
    return result


def status(store, ticket=None):
    actual = installed(store)
    records = [store.get(ticket)] if ticket else store.list('plugin-install')[:30]
    for record in records:
        if record.get('kind') != 'plugin-install':
            raise ValueError('该记录不是插件安装。')
        record['observedInstalled'] = any(p['name'] == record['manifest']['name'] and p['version'] == record['manifest']['version'] for p in actual)
    return {'installed': actual, 'requests': records, 'note': 'observedInstalled 只核对磁盘清单，仍需检查 Decky 是否成功加载。'}
