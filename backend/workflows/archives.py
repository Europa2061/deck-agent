import stat
import tarfile
import zipfile
from pathlib import Path

from .common import relative_path


MAX_FILES = 20000
MAX_SIZE = 4 * 1024**3


def members(archive, strip=0):
    path = Path(archive).expanduser().resolve()
    entries = []
    if zipfile.is_zipfile(path):
        kind = 'zip'
        with zipfile.ZipFile(path) as source:
            for item in source.infolist():
                if item.is_dir() and item.filename in ('.', './'):
                    continue
                name = relative_path(item.filename)
                if stat.S_ISLNK(item.external_attr >> 16):
                    raise ValueError('压缩包含符号链接，请先人工核实。')
                if not item.is_dir():
                    entries.append((item.filename, name.parts, item.file_size, (item.external_attr >> 16) & 0o777 or 0o644))
    elif tarfile.is_tarfile(path):
        kind = 'tar'
        with tarfile.open(path) as source:
            for item in source.getmembers():
                if item.isdir() and item.name in ('.', './'):
                    continue
                name = relative_path(item.name)
                if not item.isdir() and not item.isfile():
                    raise ValueError('压缩包含链接或特殊文件，请先人工核实。')
                if item.isfile():
                    entries.append((item.name, name.parts, item.size, item.mode & 0o777))
    else:
        raise ValueError('内置部署器支持 ZIP / TAR；其他格式可由模型检查本机解压工具后处理。')
    if not isinstance(strip, int) or strip < 0 or strip > 10:
        raise ValueError('stripComponents 必须在 0 到 10 之间。')
    files = []
    for original, parts, size, mode in entries:
        if len(parts) <= strip:
            continue
        files.append({'source': original, 'relative': '/'.join(parts[strip:]), 'bytes': size, 'mode': mode})
    if not files or len(files) > MAX_FILES or sum(f['bytes'] for f in files) > MAX_SIZE:
        raise ValueError('压缩包为空或超过 20000 文件 / 4GB 限制，请缩小处理范围。')
    if len(set(f['relative'] for f in files)) != len(files):
        raise ValueError('压缩包包含重复目标文件。')
    return path, kind, files


def extract(archive, destination, strip=0):
    path, kind, files = members(archive, strip)
    destination = Path(destination).resolve()
    opener = zipfile.ZipFile if kind == 'zip' else tarfile.open
    with opener(path) as source:
        for item in files:
            target = destination / item['relative']
            if not target.resolve().is_relative_to(destination):
                raise ValueError('解压路径越界。')
            target.parent.mkdir(parents=True, exist_ok=True)
            stream = source.open(item['source']) if kind == 'zip' else source.extractfile(item['source'])
            with stream, target.open('wb') as output:
                import shutil
                shutil.copyfileobj(stream, output, 1024 * 1024)
            target.chmod(item['mode'])
    return files
