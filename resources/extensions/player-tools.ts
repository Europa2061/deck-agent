import { spawn } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');

// 参数经 stdin 传递；模型仍可选择 Pi 原生 read/edit/write/bash 完成特殊任务。
function invoke(tool: string, params: Record<string, unknown>, signal?: AbortSignal): Promise<any> {
  return new Promise((done, fail) => {
    if (signal?.aborted) { fail(new Error('操作已取消。')); return; }
    const env = { ...process.env };
    if (env.DECK_AGENT_EMBEDDED_PYTHON === '1') {
      // 避免让系统 Python 继承 PyInstaller 私有运行库与内部启动标记。
      if (env.LD_LIBRARY_PATH_ORIG) env.LD_LIBRARY_PATH = env.LD_LIBRARY_PATH_ORIG;
      else delete env.LD_LIBRARY_PATH;
      delete env.PYTHONHOME;
      delete env.PYTHONPATH;
      for (const key of Object.keys(env)) if (key.startsWith('_PYI')) delete env[key];
    }
    const child = spawn(env.DECK_AGENT_PYTHON || 'python3', [resolve(root, 'backend/player_tools.py')], {
      stdio: ['pipe', 'pipe', 'pipe'], detached: process.platform !== 'win32', env,
    });
    let output = ''; let error = ''; let size = 0; let killTimer: ReturnType<typeof setTimeout> | undefined;
    const kill = (force = false) => { try { process.kill(process.platform === 'win32' ? child.pid! : -child.pid!, force ? 'SIGKILL' : 'SIGTERM'); } catch { /* 已退出。 */ } };
    const abort = () => { kill(); killTimer = setTimeout(() => kill(true), 5000); };
    signal?.addEventListener('abort', abort, { once: true });
    const timeout = setTimeout(abort, 31 * 60 * 1000);
    child.stdout.on('data', data => { size += data.length; if (size > 8 * 1024 * 1024) abort(); else output += data; });
    child.stderr.on('data', data => { error = (error + data).slice(-2000); });
    const cleanup = () => { clearTimeout(timeout); clearTimeout(killTimer); signal?.removeEventListener('abort', abort); };
    child.on('error', reason => { cleanup(); fail(reason); });
    child.on('close', () => {
      cleanup();
      if (signal?.aborted) { fail(new Error('操作已停止；请检查历史记录中的完成状态。')); return; }
      try { const result = JSON.parse(output); if (!result.ok) throw new Error(result.error); done(result.value); }
      catch (reason) { fail(output ? reason : new Error('玩家工具未完成：' + error)); }
    });
    child.stdin.on('error', () => {});
    child.stdin.end(JSON.stringify({ tool, params }));
  });
}

export default async function (pi: any) {
  const { Type } = await import(pathToFileURL(resolve(root, 'runtime/node_modules/typebox/build/index.mjs')).href);
  const string = (description: string) => Type.Optional(Type.String({ description }));
  const fields = {
    gameId: string('Steam AppID；先用 deck_games list 发现。'), game: string('Ludusavi 数据库中的游戏名称；先 find。'),
    path: string('明确的游戏目录；非 Steam 游戏也可提供。'), logPaths: Type.Optional(Type.Array(Type.String())),
    file: string('游戏配置文件的绝对路径。'), old: string('配置文件中精确命中一次的原文。'), new: string('替换后的配置文本。'),
    backupPath: string('可选 Ludusavi 备份目录。恢复前保护返回 before.path，恢复该副本时将它传为 backupPath。'),
    backupId: string('备份或历史版本编号。'), label: string('备份/修改备注。'), paths: Type.Optional(Type.Array(Type.String(), { description: '用户选定的存档文件或目录绝对路径。' })),
    prefix: string('可选额外 Proton/Wine pfx 目录。'), query: string('搜索关键词；可结合游戏英文名、需求和版本。'),
    provider: Type.Optional(Type.Union([Type.Literal('web'), Type.Literal('github')])),
    url: string('HTTPS 网页或作者提供的文件下载地址。'), sha256: string('作者或发行接口提供的 SHA-256，若无则不填，不能伪造。'),
    archive: string('用户提供或 download 返回的本地压缩包绝对路径。'), target: string('经过确认的游戏/Mods 目标目录，必须存在。'),
    name: string('Mod 显示名称；建议包含版本。'), source: string('Mod 原始项目或发布页面。'),
    stripComponents: Type.Optional(Type.Integer({ minimum: 0, maximum: 10, description: '部署时去掉的压缩包路径前缀层数，先 inspect 确认。' })),
    modId: string('Mod 安装记录编号。'), repo: string('owner/repo 或 GitHub 仓库 URL。'), tag: string('指定 Release 标签；不填时优先正式版。'),
    ticket: string('prepare 返回的插件安装记录 id。'),
  };
  const specs = [
    { name: 'deck_games', label: '游戏诊断与配置', actions: ['list', 'diagnose', 'config_preview', 'config_apply', 'restore', 'history'],
      description: '发现本机 Steam 游戏（含多库/SD 卡），按 gameId/path 诊断日志与配置；config_preview/apply 使用 file/old/new 精确替换并保存可恢复副本。不会自动声称游戏已修复或帧率提升。' },
    { name: 'deck_saves', label: '存档备份与恢复', actions: ['status', 'install', 'find', 'preview_backup', 'backup', 'backups', 'preview_restore', 'restore', 'path_backup', 'path_restore', 'history'],
      description: 'Ludusavi 存档工具。status 检查依赖，install 在插件数据目录准备固定官方 Linux x64 程序；find 按 gameId/game 查游戏。backup/restore 等操作只针对 game。path_backup(paths)/path_restore(backupId) 处理明确文件路径；恢复前保护当前文件。' },
    { name: 'deck_mods', label: 'Mod 搜索与管理', actions: ['search', 'read_source', 'download', 'inspect', 'plan', 'install', 'list', 'disable', 'enable', 'uninstall'],
      description: '按需求搜索 Mod（默认 web，可选 github）、读取原始说明、下载指定 URL；inspect 查看 archive，plan/install 使用 archive/target/stripComponents，备份被覆盖文件并登记归属。disable/enable/uninstall 使用 modId。支持 ZIP/TAR 部署；复杂加载器仍可使用 Pi 通用工具。' },
    { name: 'deck_plugins', label: '商店外 Decky 插件', actions: ['search', 'inspect', 'read_source', 'prepare', 'install', 'status'],
      description: 'search 严格限定 GitHub topic:decky-plugin；inspect(repo) 读取发行信息。prepare(repo/url/archive) 下载并验证真实插件 ZIP，返回 id；install(ticket=id) 交给前端打开 Decky 原生确认，尚不代表成功。status 核对安装请求与本机插件版本。' },
  ];
  const toolFields: Record<string, string[]> = {
    deck_games: ['gameId', 'path', 'logPaths', 'file', 'old', 'new', 'label', 'backupId'],
    deck_saves: ['gameId', 'game', 'backupId', 'backupPath', 'paths', 'label', 'prefix'],
    deck_mods: ['query', 'provider', 'url', 'sha256', 'archive', 'target', 'name', 'source', 'stripComponents', 'modId', 'gameId'],
    deck_plugins: ['query', 'repo', 'url', 'sha256', 'archive', 'tag', 'ticket'],
  };
  for (const spec of specs) {
    pi.registerTool({ ...spec, actions: undefined,
      parameters: Type.Object({ action: Type.Union(spec.actions.map(action => Type.Literal(action))), ...Object.fromEntries(toolFields[spec.name].map(key => [key, fields[key as keyof typeof fields]])) }),
      async execute(_id: string, params: Record<string, any>, signal: AbortSignal, onUpdate: any, ctx: any) {
        const sensitive = (spec.name === 'deck_games' && ['config_apply', 'restore'].includes(params.action))
          || (spec.name === 'deck_saves' && ['restore', 'path_restore'].includes(params.action))
          || (spec.name === 'deck_mods' && ['install', 'disable', 'enable', 'uninstall'].includes(params.action));
        if (sensitive) {
          let preview: any;
          if (params.action === 'config_apply') preview = await invoke(spec.name, { ...params, action: 'config_preview' }, signal);
          else if (spec.name === 'deck_mods' && params.action === 'install') preview = await invoke(spec.name, { ...params, action: 'plan' }, signal);
          else if (spec.name === 'deck_saves' && params.action === 'restore') preview = await invoke(spec.name, { ...params, action: 'preview_restore' }, signal);
          const description = JSON.stringify({ action: params.action, ...params, preview }, null, 2).slice(0, 14000);
          if (!ctx.hasUI) throw new Error('当前界面不能确认文件修改，请在 Deck Agent 页面操作。');
          if (!(await ctx.ui.confirm(spec.label + '：确认修改', description))) return { content: [{ type: 'text', text: '用户取消，未执行修改。' }], details: { cancelled: true } };
        }
        if (signal?.aborted) throw new Error('操作已取消。');
        onUpdate?.({ content: [{ type: 'text', text: spec.label + '：' + params.action + '…' }], details: { running: true } });
        const result = await invoke(spec.name, params, signal);
        const text = JSON.stringify(result, null, 2);
        return { content: [{ type: 'text', text: text.length > 48000 ? text.slice(0, 48000) + '\n…结果已截断，可按操作编号读取本地记录。' : text }],
          details: { playerTool: spec.name, ...(spec.name === 'deck_plugins' && params.action === 'install' ? { installTicket: result.ticket } : {}) } };
      },
    });
  }
}
