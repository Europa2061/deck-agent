import json
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import archives, network
from .common import atomic_copy

# 官方发行文件及 SHA-256，依赖安装固定版本，避免在玩家设备上静默追最新。
LUDUSAVI_VERSION = '0.31.0'
LUDUSAVI_SHA256 = '7322ff45d41eae7ae064a80d8c9ecccc5b8fb6fc090a603a66369cd4b054068d'
LEGAL_SHA256 = '9fce11fc44942efdd5969928d89b106c229f9a041d7a713c424a6da981660ebf'


def command(store):
    binary = store.root / 'bin/ludusavi'
    if binary.is_file():
        return [str(binary)]
    installed = shutil.which('ludusavi')
    if installed:
        return [installed]
    flatpak = shutil.which('flatpak')
    if flatpak:
        result = subprocess.run([flatpak, 'info', 'com.github.mtkennerly.ludusavi'], capture_output=True, timeout=15)
        if result.returncode == 0:
            return [flatpak, 'run', 'com.github.mtkennerly.ludusavi']
    return None


def status(store):
    cmd = command(store)
    return {'available': bool(cmd), 'command': cmd, 'portableVersion': LUDUSAVI_VERSION,
            'backupPath': str(store.root / 'ludusavi-backups'), 'note': '未安装时可调用 install；只放入插件数据目录，不需要 sudo。'}


def install(store):
    if sys.platform != 'linux' or platform.machine() not in ('x86_64', 'AMD64'):
        raise ValueError('自动准备的官方依赖为 Linux x64；当前平台请提供已安装的 Ludusavi。')
    if command(store):
        return status(store)
    base = 'https://github.com/mtkennerly/ludusavi/releases/download/v' + LUDUSAVI_VERSION + '/ludusavi-v' + LUDUSAVI_VERSION
    legal = network.download(store, base + '-legal.zip', LEGAL_SHA256, 30 * 1024**2)
    downloaded = network.download(store, base + '-linux.tar.gz', LUDUSAVI_SHA256, 100 * 1024**2)
    with tempfile.TemporaryDirectory(dir=store.root) as tmp:
        files = archives.extract(downloaded['path'], tmp)
        candidates = [Path(tmp) / item['relative'] for item in files if Path(item['relative']).name == 'ludusavi']
        if len(candidates) != 1:
            raise ValueError('Ludusavi 官方包中的程序文件不明确。')
        binary = store.root / 'bin/ludusavi'
        atomic_copy(candidates[0], binary)
        binary.chmod(0o700)
        try:
            result = subprocess.run([str(binary), '--version'], capture_output=True, text=True, timeout=15)
            if result.returncode or ('ludusavi ' + LUDUSAVI_VERSION) not in result.stdout.lower():
                raise ValueError('Ludusavi 无法启动或版本不符。')
        except BaseException:
            binary.unlink(missing_ok=True)
            raise
    return {**status(store), 'licenseArchive': legal['path'], 'sha256Verified': True}


def run(store, args, timeout=180):
    cmd = command(store)
    if not cmd:
        raise ValueError('未找到 Ludusavi，请先调用 install，或使用明确文件路径的 path_backup。')
    config = store.root / 'ludusavi-config'
    config.mkdir(exist_ok=True, mode=0o700)
    if not (config / 'config.yaml').exists():
        from .games import inventory
        from ..storage import write_json
        write_json(config / 'config.yaml', {
            'roots': [{'path': root, 'store': 'steam'} for root in inventory(store)['libraries']],
            'backup': {'retention': {'full': 10, 'differential': 5}},
        })
    result = subprocess.run(cmd + ['--config', str(config)] + args, capture_output=True, timeout=timeout)
    try:
        data = json.loads(result.stdout)
    except (ValueError, UnicodeError):
        raise ValueError('Ludusavi 未返回可解析结果：' + result.stderr.decode(errors='replace')[-1000:]) from None
    if result.returncode or any(data.get('errors', {}).values()):
        raise ValueError('Ludusavi 操作未全部成功：' + json.dumps(data, ensure_ascii=False)[:4000])
    return data


def game_name(params):
    name = params.get('game', '').strip()
    if not name:
        raise ValueError('请明确选择单个游戏名称 game；先用 find 查数据库名称。')
    return name


def find(store, params):
    args = ['find', '--api']
    if params.get('gameId'):
        if not str(params['gameId']).isdigit():
            raise ValueError('Steam gameId 应为数字。')
        args += ['--steam-id', str(params['gameId'])]
    else:
        args += ['--', game_name(params)]
    return run(store, args)


def backup(store, params, preview=False, path=None):
    name = game_name(params)
    target = Path(path or params.get('backupPath') or store.root / 'ludusavi-backups').expanduser().resolve()
    args = ['backup', '--api', '--no-cloud-sync', '--path', str(target)]
    args += ['--preview'] if preview else ['--force']
    if params.get('prefix'):
        args += ['--wine-prefix', str(Path(params['prefix']).expanduser().resolve())]
    data = run(store, args + ['--', name])
    if not preview:
        if not data.get('overall', {}).get('processedGames'):
            raise ValueError('没有实际备份任何游戏，请先检查 preview_backup 的识别结果。')
        record = store.new_record('ludusavi-backup', game=name, path=str(target), status='complete', result=data)
        store.save(record)
        return {'operationId': record['id'], 'path': str(target), 'result': data}
    return data


def backups(store, params):
    return run(store, ['backups', '--api', '--path', str(Path(params.get('backupPath') or store.root / 'ludusavi-backups').expanduser().resolve()), '--', game_name(params)])


def restore(store, params, preview=False):
    name = game_name(params)
    args = ['restore', '--api', '--no-cloud-sync', '--path', str(Path(params.get('backupPath') or store.root / 'ludusavi-backups').expanduser().resolve())]
    if params.get('backupId'):
        args += ['--backup', str(params['backupId'])]
    if preview:
        return run(store, args + ['--preview', '--', name])
    # 独立目录保护恢复前的当前进度，不改变玩家选中的历史备份。
    current = backup(store, params, preview=True)
    has_current = any(game.get('files') or game.get('registry') for game in current.get('games', {}).values())
    before = backup(store, params, path=store.root / 'restore-protection' / __import__('uuid').uuid4().hex) if has_current else None
    data = run(store, args + ['--force', '--', name])
    if not data.get('overall', {}).get('processedGames'):
        raise ValueError('没有实际恢复任何游戏；请检查游戏名称和 backupId，当前保护副本仍保留。')
    record = store.new_record('ludusavi-restore', game=name, backupId=params.get('backupId'), before=before, status='complete', result=data)
    store.save(record)
    return {'operationId': record['id'], 'before': before, 'result': data}
