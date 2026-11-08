import difflib
import re
import shutil
from pathlib import Path

from .common import atomic_copy


def parse_vdf(text):
    tokens = re.finditer(r'"((?:\\.|[^"\\])*)"|([{}])|//[^\n]*', text)
    root, stack, key = {}, [], None
    current = root
    for token in tokens:
        if token.group(0).startswith('//'):
            continue
        string, brace = token.group(1), token.group(2)
        if brace == '{':
            if key is None:
                raise ValueError('VDF 缺少字段名。')
            child = {}
            current[key] = child
            stack.append(current)
            current, key = child, None
        elif brace == '}':
            if not stack:
                raise ValueError('VDF 括号不匹配。')
            current, key = stack.pop(), None
        else:
            value = re.sub(r'\\([\\"])', r'\1', string)
            if key is None:
                key = value
            else:
                current[key], key = value, None
    if stack:
        raise ValueError('VDF 文件不完整。')
    return root


def inventory(store):
    libraries = []
    errors = []
    for candidate in (store.home / '.local/share/Steam', store.home / '.steam/steam', store.home / '.steam/root'):
        if candidate.is_dir() and candidate.resolve() not in libraries:
            libraries.append(candidate.resolve())
    for root in list(libraries):
        path = root / 'steamapps/libraryfolders.vdf'
        if path.is_file():
            try:
                data = parse_vdf(path.read_text(errors='replace')).get('libraryfolders', {})
                for key, item in data.items():
                    value = item.get('path') if isinstance(item, dict) else item if key.isdigit() else None
                    if value:
                        library = Path(value).resolve()
                        if library.is_dir() and library not in libraries:
                            libraries.append(library)
            except (ValueError, OSError) as error:
                errors.append({'path': str(path), 'error': str(error)})
    games = []
    for library in libraries:
        for manifest in sorted((library / 'steamapps').glob('appmanifest_*.acf')):
            try:
                data = parse_vdf(manifest.read_text(errors='replace'))['AppState']
                app_id = str(data['appid'])
                install = (library / 'steamapps/common' / data['installdir']).resolve()
                if not install.is_relative_to((library / 'steamapps/common').resolve()):
                    raise ValueError('游戏目录越界。')
                games.append({'id': app_id, 'name': data['name'], 'path': str(install), 'installed': install.is_dir(),
                              'library': str(library), 'buildId': data.get('buildid'), 'prefix': str(library / 'steamapps/compatdata' / app_id / 'pfx'),
                              'shaderCache': str(library / 'steamapps/shadercache' / app_id), 'sizeBytes': int(data.get('SizeOnDisk', 0))})
            except (KeyError, ValueError, OSError) as error:
                errors.append({'path': str(manifest), 'error': str(error)})
    return {'games': games, 'libraries': [str(p) for p in libraries], 'errors': errors,
            'note': '这是 Steam 已安装游戏列表；非 Steam 游戏可用明确路径分析，不把兼容环境路径当成当前 Proton 版本。'}


def select_game(store, params):
    game_id = str(params.get('gameId', ''))
    if game_id:
        matches = [g for g in inventory(store)['games'] if g['id'] == game_id]
        if len(matches) != 1:
            raise ValueError('游戏编号未找到或存在多个安装位置，请提供明确 path。')
        return matches[0]
    if params.get('path'):
        path = Path(params['path']).expanduser().resolve()
        if not path.is_dir():
            raise ValueError('游戏目录不存在。')
        return {'id': None, 'name': path.name, 'path': str(path), 'library': None}
    raise ValueError('请提供 gameId，或明确的游戏目录 path。')


def diagnose(store, params):
    game = select_game(store, params)
    space = shutil.disk_usage(game['path'])
    logs = []
    candidates = [store.home / ('steam-' + str(game['id']) + '.log')] if game['id'] else []
    for value in params.get('logPaths', []):
        candidates.append(Path(value).expanduser())
    for path in candidates[:8]:
        if path.is_file():
            with path.open('rb') as stream:
                stream.seek(max(0, path.stat().st_size - 32768))
                logs.append({'path': str(path), 'tail': stream.read(32768).decode(errors='replace'), 'truncated': path.stat().st_size > 32768})
    config_files = []
    root = Path(game['path'])
    for directory in (root, root / 'config', root / 'configs', root / 'settings'):
        if directory.is_dir():
            config_files.extend(str(p) for p in directory.iterdir() if p.is_file() and p.suffix.lower() in ('.ini', '.cfg', '.json', '.toml', '.xml', '.yaml'))
    return {'game': game, 'freeBytes': space.free, 'logs': logs, 'configCandidates': sorted(config_files)[:100],
            'protonLogLaunchOption': 'PROTON_LOG=1 %command%',
            'note': '结果是本机证据，不代表故障已修复或画质/帧率已提升。AppData 等配置位置按游戏文档继续查找。'}


def config_preview(store, params):
    path = Path(params['file']).expanduser()
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 2 * 1024**2:
        raise ValueError('请选择不超过 2MB 的真实配置文件。')
    original = path.read_text(encoding='utf-8')
    old, new = params.get('old'), params.get('new')
    if not isinstance(old, str) or not old or not isinstance(new, str):
        raise ValueError('请提供要替换的原文 old 和新文 new。')
    if original.count(old) != 1:
        raise ValueError('原文必须精确命中一次；先读取文件，再缩小替换范围。')
    updated = original.replace(old, new, 1)
    return path.resolve(), original, updated, ''.join(difflib.unified_diff(original.splitlines(True), updated.splitlines(True), fromfile=str(path), tofile=str(path)))


def config_apply(store, params):
    path, original, updated, diff = config_preview(store, params)
    backup = store.backup([str(path)], label=params.get('label', '游戏配置修改'), kind='config-backup')
    import tempfile
    with tempfile.TemporaryDirectory(dir=path.parent) as tmp:
        source = Path(tmp) / 'config'
        source.write_text(updated, encoding='utf-8')
        source.chmod(path.stat().st_mode & 0o777)
        if path.read_text(encoding='utf-8') != original:
            raise ValueError('配置在修改期间发生变化，未覆盖。')
        atomic_copy(source, path)
    return {'backupId': backup['id'], 'file': str(path), 'diff': diff, 'applied': True, 'verifiedInGame': False}
