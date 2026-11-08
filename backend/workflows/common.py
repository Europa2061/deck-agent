import contextlib
import fcntl
import hashlib
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path

from ..storage import read_json, write_json


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def relative_path(value):
    from pathlib import PurePosixPath
    path = PurePosixPath(value)
    if not value or '\\' in value or path.is_absolute() or '..' in path.parts or not path.parts or '\x00' in value:
        raise ValueError('文件相对路径无效。')
    return path


def atomic_copy(source, target):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.deck-agent-', dir=target.parent)
    os.close(fd)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)


class Store:
    def __init__(self, home=None, data=None):
        self.home = Path(home or os.environ.get('HOME', str(Path.home()))).resolve()
        self.root = Path(data or os.environ.get('DECK_AGENT_DATA_DIR', self.home / '.local/share/deck-agent')) / 'player-tools'
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.records = self.root / 'records'
        self.records.mkdir(exist_ok=True, mode=0o700)

    @contextlib.contextmanager
    def lock(self):
        with (self.root / 'write.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError('另一个玩家工具正在修改文件，请完成后重试。') from None
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def new_record(self, kind, **fields):
        return {'id': uuid.uuid4().hex, 'kind': kind, 'createdAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), **fields}

    def save(self, record):
        write_json(self.records / (record['id'] + '.json'), record)
        return record

    def get(self, record_id):
        if not isinstance(record_id, str) or len(record_id) != 32 or any(c not in '0123456789abcdef' for c in record_id):
            raise ValueError('操作编号无效。')
        record = read_json(self.records / (record_id + '.json'))
        if not record:
            raise ValueError('没有找到该操作记录。')
        return record

    def list(self, kind=None):
        records = [read_json(p) for p in self.records.glob('*.json')]
        return sorted((r for r in records if not kind or r.get('kind') == kind), key=lambda r: (r.get('createdAt', ''), r['id']), reverse=True)

    def backup(self, paths, label='', kind='backup'):
        sources = []
        for value in paths:
            path = Path(value).expanduser()
            if path.is_symlink():
                raise ValueError('请先确认符号链接实际指向，再对真实文件备份：' + str(path))
            path = path.resolve()
            if path.is_dir():
                sources.extend(p for p in path.rglob('*') if p.is_file() and not p.is_symlink())
            elif path.is_file():
                sources.append(path)
            else:
                raise ValueError('备份文件不存在：' + str(path))
        sources = list(dict.fromkeys(sources))
        if not sources:
            raise ValueError('没有找到可备份的文件。')
        if len(sources) > 20000 or sum(p.stat().st_size for p in sources) > 4 * 1024**3:
            raise ValueError('单次备份超过 20000 文件或 4GB，请拆分处理。')
        if any(p.is_relative_to(self.root.resolve()) for p in sources):
            raise ValueError('不能把工具自身的备份目录再次备份。')
        record = self.new_record(kind, label=label, status='backing_up', files=[])
        self.save(record)
        for index, path in enumerate(sources):
            destination = self.root / 'backups' / record['id'] / str(index)
            atomic_copy(path, destination)
            if file_hash(path) != file_hash(destination):
                raise ValueError('文件在备份期间变化，请退出游戏后重试：' + str(path))
            record['files'].append({'path': str(path), 'copy': str(destination), 'sha256': file_hash(destination), 'bytes': destination.stat().st_size})
        record['status'] = 'ready'
        self.save(record)
        return record

    def restore(self, record_id):
        record = self.get(record_id)
        if record.get('kind') not in ('backup', 'config-backup', 'pre-restore') or record.get('status') != 'ready':
            raise ValueError('该记录不是已完成的文件备份。')
        for item in record['files']:
            if file_hash(item['copy']) != item['sha256']:
                raise ValueError('备份文件校验失败，未恢复。')
            if Path(item['path']).resolve() != Path(item['path']):
                raise ValueError('目标变成了符号链接，未恢复。')
        existing = [item['path'] for item in record['files'] if Path(item['path']).is_file()]
        before = self.backup(existing, label='恢复前的当前文件', kind='pre-restore') if existing else None
        for item in record['files']:
            atomic_copy(item['copy'], item['path'])
        result = self.new_record('restore', backupId=record_id, beforeId=before['id'] if before else None, status='complete', restored=len(record['files']))
        return self.save(result)
