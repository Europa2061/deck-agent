import shutil
import tempfile
from pathlib import Path

from . import archives
from .common import atomic_copy, file_hash


def plan(store, params):
    archive, kind, files = archives.members(params['archive'], params.get('stripComponents', 0))
    target = Path(params['target']).expanduser().resolve()
    if not target.is_dir():
        raise ValueError('请先选择存在的目标目录 target。')
    if target == Path(target.anchor) or target.is_relative_to(store.root.resolve()):
        raise ValueError('请选择具体游戏或 Mod 目录。')
    owned = {f['path']: r for r in store.list('mod') if r.get('status') in ('enabled', 'installing', 'interrupted') for f in r['files']}
    changes = []
    for item in files:
        path = target / item['relative']
        if not path.resolve().is_relative_to(target) or path.resolve() != path:
            raise ValueError('部署路径经过越界符号链接：' + str(path))
        if path.exists() and not path.is_file():
            raise ValueError('目标不是普通文件：' + str(path))
        if str(path) in owned:
            raise ValueError('已有 Mod 管理这个文件，请先停用相冲突的 Mod：' + owned[str(path)]['id'])
        changes.append({**item, 'path': str(path), 'overwrite': path.exists(), 'beforeHash': file_hash(path) if path.exists() else None})
    return {'archive': str(archive), 'archiveSha256': file_hash(archive), 'target': str(target), 'stripComponents': params.get('stripComponents', 0),
            'files': changes, 'fileCount': len(changes), 'overwriteCount': sum(f['overwrite'] for f in changes)}


def install(store, params):
    preview = plan(store, params)
    record = store.new_record('mod', name=params.get('name') or Path(params['archive']).name, source=params.get('source', ''),
                              gameId=params.get('gameId'), target=preview['target'], status='installing', files=[])
    directory = store.root / 'mods' / record['id']
    directory.mkdir(parents=True, mode=0o700)
    cached = directory / 'archive'
    atomic_copy(preview['archive'], cached)
    if file_hash(cached) != preview['archiveSha256']:
        raise ValueError('安装包在准备期间发生变化，请重新预览。')
    record.update(archive=str(cached), archiveSha256=preview['archiveSha256'], stripComponents=preview['stripComponents'])
    self_backup = [f['path'] for f in preview['files'] if f['overwrite']]
    original = store.backup(self_backup, label='安装 Mod 前的原文件') if self_backup else None
    record['backupId'] = original['id'] if original else None
    with tempfile.TemporaryDirectory(dir=directory) as tmp:
        archives.extract(cached, tmp, record['stripComponents'])
        for item in preview['files']:
            path = Path(item['path'])
            if (file_hash(path) if path.is_file() else None) != item['beforeHash']:
                raise ValueError('目标文件在安装准备期间发生变化，请重新预览。')
            item['installedHash'] = file_hash(Path(tmp) / item['relative'])
        record['files'] = preview['files']
        store.save(record)
        try:
            for item in record['files']:
                item['written'] = True
                store.save(record)
                atomic_copy(Path(tmp) / item['relative'], item['path'])
        except BaseException:
            record['status'] = 'interrupted'
            store.save(record)
            raise
    record['status'] = 'enabled'
    return store.save(record)


def disable(store, mod_id):
    record = store.get(mod_id)
    if record.get('kind') != 'mod' or record.get('status') not in ('enabled', 'interrupted', 'installing'):
        raise ValueError('该 Mod 当前不是已启用或可恢复的安装。')
    affected = []
    for item in record['files']:
        if not item.get('written'):
            continue
        path = Path(item['path'])
        if path.resolve() != path or (path.exists() and not path.is_file()):
            raise ValueError('目标路径发生变化，未自动覆盖：' + str(path))
        actual = file_hash(path) if path.is_file() else None
        if actual == item['installedHash']:
            affected.append(item)
        elif actual != item['beforeHash']:
            raise ValueError('文件被游戏更新或其他程序改变，未自动覆盖；请保留文件并按差异处理：' + str(path))
    backup = store.get(record['backupId']) if record.get('backupId') else None
    originals = {i['path']: i for i in backup['files']} if backup else {}
    for item in originals.values():
        if file_hash(item['copy']) != item['sha256']:
            raise ValueError('原文件备份校验失败，未停用。')
    for item in affected:
        if item['path'] in originals:
            atomic_copy(originals[item['path']]['copy'], item['path'])
        else:
            Path(item['path']).unlink()
    record['status'] = 'disabled'
    return store.save(record)


def enable(store, mod_id):
    record = store.get(mod_id)
    if record.get('kind') != 'mod' or record.get('status') != 'disabled':
        raise ValueError('该 Mod 不是停用状态。')
    if file_hash(record['archive']) != record['archiveSha256']:
        raise ValueError('缓存安装包校验失败。')
    with tempfile.TemporaryDirectory(dir=store.root) as tmp:
        archives.extract(record['archive'], tmp, record['stripComponents'])
        owned = {f['path'] for r in store.list('mod') if r.get('status') in ('enabled', 'installing', 'interrupted') for f in r['files']}
        for item in record['files']:
            path = Path(item['path'])
            if str(path) in owned or path.resolve() != path or (file_hash(path) if path.is_file() else None) != item['beforeHash']:
                raise ValueError('原文件或 Mod 归属已变化，请先检查冲突：' + str(path))
        record['status'] = 'installing'
        for item in record['files']:
            item['written'] = False
        store.save(record)
        for item in record['files']:
            item['written'] = True
            store.save(record)
            atomic_copy(Path(tmp) / item['relative'], item['path'])
    record['status'] = 'enabled'
    return store.save(record)


def uninstall(store, mod_id):
    record = store.get(mod_id)
    if record.get('kind') != 'mod':
        raise ValueError('这不是 Mod 安装记录。')
    if record.get('status') in ('enabled', 'interrupted', 'installing'):
        record = disable(store, mod_id)
    if record.get('status') != 'disabled':
        raise ValueError('该 Mod 当前无法自动卸载。')
    record['status'] = 'uninstalled'
    # 留存原文件备份及安装记录，以便排障；不删除用户提供的原压缩包。
    return store.save(record)
