// 只供浏览器交互预览；生产入口不引用此文件，也不会调用真实模型或工具。
import type { Bridge } from '../client';
import type { Message, Notice, Provider, Session, Snapshot, Voice } from '../types';

type DemoSession = Session & { readVersion: number; autoTitle?: boolean };
type State = { newDraft?: string; newModel?: Snapshot['newSessionModel']; sessions: DemoSession[]; messages: Record<string, Message[]>; preferences: Snapshot['preferences']; providers: Provider[]; voiceSelection?: { modelId: string; source: string } };
const key = 'deck-agent-sidebar-demo-v2';
const models = [
  { provider: 'demo', id: 'demo-chat', name: '演示模型', reasoning: false, api: 'openai-completions' },
  { provider: 'demo', id: 'demo-reasoning', name: '演示思考模型', reasoning: true, api: 'openai-completions' },
];
const reply = '## 演示回复\n\n这是交互预览的演示数据，**没有调用真实模型，也没有执行设备命令**。\n\n- 可以切换会话，检查未读蓝点\n- 可以点击放大镜搜索会话\n- 可以直接新建会话和编辑多行消息\n\n```text\n输入框支持直接编辑\n```';
function seed(): State {
  const session = (id: string, name: string, status: Session['status'], readVersion: number): DemoSession => ({ id, name, status, readVersion, replyVersion: 1, draft: '', cwd: '/home/deck/DeckAgent', archived: false, pending: [], updated: Date.now() / 1000, provider: 'demo', model: 'demo-chat', thinking: 'off' });
  return {
    sessions: [session('demo-read', '设备状态检查', 'idle', 1), session('demo-running', '整理游戏库', 'running', 1), session('demo-unread', '存储空间分析', 'idle', 0)],
    messages: {
      'demo-read': [{ role: 'user', content: '帮我看看设备状态。', timestamp: Date.now() - 120000 }, { role: 'assistant', content: [{ type: 'text', text: '先检查设备状态和可用空间。' }, { type: 'toolCall', name: 'read', id: 'demo-check', arguments: { path: '设备状态（演示）' } }], timestamp: Date.now() - 110000 }, { role: 'toolResult', toolCallId: 'demo-check', toolName: 'read', content: '设备状态与存储检查完成。这是演示数据。', timestamp: Date.now() - 2000 }, { role: 'assistant', timestamp: Date.now() - 1000, content: '## 设备状态检查\n\n这是**交互预览**。左侧包含进行中、未读和已读会话，可以直接测试。\n\n- 点击左上角放大镜搜索\n- 新会话点击后打开草稿，首次发送才创建\n- 关于与更新在「设置」里\n\n消息不会发给真实模型。' }],
      'demo-running': [{ role: 'user', content: '整理一下游戏库。' }],
      'demo-unread': [{ role: 'user', content: '分析一下存储空间。' }, { role: 'assistant', content: '## 存储分析\n\n这是一条**未读演示回复**。打开本会话后，左侧蓝点会恢复灰色。' }],
    },
    preferences: { defaultCwd: '/home/deck/DeckAgent', notifications: false, updateAuto: false, releaseRepo: '', language: 'auto', inputDevice: 'auto' },
    providers: [{ id: 'demo', name: '演示供应商', model: 'demo-chat', enabledModels: ['demo-chat'], thinking: 'off', baseUrl: '', api: 'openai-completions', custom: false, configured: true, default: true }],
  };
}
export function createDemoBridge(): Bridge & { reset(): void } {
  let state = seed();
  try { const saved = JSON.parse(sessionStorage.getItem(key) || 'null'); if (Array.isArray(saved?.sessions) && saved?.messages && saved?.preferences && Array.isArray(saved?.providers)) state = saved; } catch { /* 损坏的演示缓存使用初始状态。 */ }
  const listeners = new Set<(event: Notice) => void>();
  const timers = new Map<string, ReturnType<typeof setTimeout>>();
  const asr = [
    { id: 'sensevoice-int8', name: 'SenseVoice Small INT8', description: '中文优先，适合日常中文和中英混说。', downloadBytes: 239549735, installed: false, source: 'https://huggingface.co/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17' },
    { id: 'whisper-small-int8', name: 'Whisper Small INT8', description: '多语种识别，模型较大，转写可能需要更长时间。', downloadBytes: 375485327, installed: false, source: 'https://huggingface.co/csukuangfj/sherpa-onnx-whisper-small' },
    { id: 'whisper-base-int8', name: 'Whisper Base INT8', description: '多语种轻量选项，比 Small 占用更少资源。', downloadBytes: 160609290, installed: false, source: 'https://huggingface.co/csukuangfj/sherpa-onnx-whisper-base' },
    { id: 'paraformer-zh-yue-en-int8', name: 'Paraformer 中英粤 INT8', description: '支持普通话、粤语和英语，可识别中英混说。', downloadBytes: 244803083, installed: false, source: 'https://huggingface.co/csukuangfj/sherpa-onnx-paraformer-trilingual-zh-cantonese-en' },
  ];
  const voice: Voice = { status: 'missing', modelId: asr[0].id, downloadSource: 'huggingface', name: asr[0].name, models: asr, downloaded: 0, total: asr[0].downloadBytes, engineReady: true, captureReady: true };
  if (state.voiceSelection) { const selected = asr.find(m => m.id === state.voiceSelection?.modelId) || asr[0]; voice.modelId = selected.id; voice.name = selected.name; voice.total = selected.downloadBytes; voice.downloadSource = state.voiceSelection.source; }
  const availableModels = () => {
    const result = [...models];
    for (const p of state.providers) for (const id of p.enabledModels || [p.model]) if (!result.some(m => m.provider === p.id && m.id === id)) result.push({ provider: p.id, id, name: id, reasoning: false, api: p.api });
    return result;
  };
  const enabledModels = () => availableModels().filter(m => state.providers.some(p => p.id === m.provider && (p.enabledModels || [p.model]).includes(m.id)));
  const publish = () => { sessionStorage.setItem(key, JSON.stringify(state)); listeners.forEach(fn => fn({ type: 'changed' })); };
  const find = (id: unknown) => { const s = state.sessions.find(s => s.id === id); if (!s) throw new Error('会话不存在'); return s; };
  const finishLater = (s: DemoSession, ms: number) => {
    clearTimeout(timers.get(s.id));
    timers.set(s.id, setTimeout(() => {
      if (s.status !== 'running') return;
      (state.messages[s.id] ||= []).push({ role: 'assistant', content: reply, timestamp: Date.now() });
      s.status = 'idle'; s.replyVersion = (s.replyVersion || 0) + 1; s.updated = Date.now() / 1000;
      timers.delete(s.id); publish();
    }, ms));
  };
  const snapshot = (id?: unknown): Snapshot => ({
    newSessionDraft: state.newDraft || '', newSessionModel: state.newModel,
    sessions: state.sessions.map(s => ({ ...s, unread: (s.replyVersion || 0) > s.readVersion })), preferences: state.preferences, providers: state.providers,
    runtime: { ready: true, piVersion: '演示模式' }, version: '0.2.1',
    build: { id: '浏览器交互预览', version: '0.2.1', commit: '', builtAt: '', source: 'demo', platform: 'browser', pi: '演示模式' }, voice,
    active: id ? { id: String(id), messages: state.messages[String(id)] || [], statusEntries: {}, widgets: {}, tools: [] } : null,
  });
  for (const s of state.sessions) if (s.status === 'running') finishLater(s, 20000);
  return {
    reset() { timers.forEach(clearTimeout); timers.clear(); state = seed(); finishLater(state.sessions[1], 20000); publish(); },
    async request<T>(action: string, p: Record<string, unknown> = {}) {
      let value: unknown;
      switch (action) {
        case 'snapshot': case 'open_session': value = snapshot(p.sessionId); break;
        case 'create_session': {
          const id = crypto.randomUUID();
          state.sessions.unshift({ id, name: '新会话', cwd: state.preferences.defaultCwd, status: 'idle', archived: false, draft: p.fromDraft ? String(p.text || '') : '', updated: Date.now() / 1000, pending: [], provider: 'demo', model: 'demo-chat', thinking: 'off', ...(p.fromDraft ? state.newModel : {}), readVersion: 0, replyVersion: 0, autoTitle: true });
          state.messages[id] = []; value = { id }; publish(); break;
        }
        case 'draft': if (p.sessionId === '__new__') state.newDraft = String(p.text || ''); else find(p.sessionId).draft = String(p.text || ''); publish(); break;
        case 'mark_read': { const s = find(p.sessionId); s.readVersion = Math.max(s.readVersion, Math.min(Number(p.replyVersion) || 0, s.replyVersion || 0)); publish(); break; }
        case 'send': {
          const s = find(p.sessionId); s.draft = ''; s.status = 'running';
          if (s.autoTitle) { s.name = String(p.text).replace(/\s+/g, ' ').slice(0, 18); s.autoTitle = false; }
          (state.messages[s.id] ||= []).push({ role: 'user', content: String(p.text), timestamp: Date.now() });
          const callId = 'demo-' + crypto.randomUUID();
          state.messages[s.id].push({ role: 'assistant', content: [{ type: 'text', text: '正在检查演示数据。' }, { type: 'toolCall', name: 'read', id: callId, arguments: { path: '设备状态（演示）' } }], timestamp: Date.now() }, { role: 'toolResult', toolCallId: callId, toolName: 'read', content: '检查完成，仅演示界面，不执行真实命令。', timestamp: Date.now() });
          finishLater(s, 1800); value = { disposition: 'started' }; publish(); break;
        }
        case 'stop': { const s = find(p.sessionId); clearTimeout(timers.get(s.id)); s.status = 'stopped'; publish(); break; }
        case 'session_meta': {
          const s = find(p.sessionId);
          if (p.name) { s.name = String(p.name); s.autoTitle = false; }
          if (typeof p.archived === 'boolean') s.archived = p.archived;
          if (p.delete) { clearTimeout(timers.get(s.id)); state.sessions = state.sessions.filter(i => i !== s); delete state.messages[s.id]; }
          publish(); break;
        }
        case 'models': case 'configured_models': value = { models: enabledModels() }; break;
        case 'catalog': value = { providers: [{ id: 'demo', name: '演示供应商' }], models: availableModels() }; break;
        case 'set_model': { if (p.sessionId === '__new__') { state.newModel = { provider: String(p.provider), model: String(p.model), thinking: String(p.thinking || 'off') }; publish(); break; } const s = find(p.sessionId); s.provider = String(p.provider); s.model = String(p.model); s.thinking = String(p.thinking || 'off'); publish(); break; }
        case 'commands': if (p.sessionId === '__new__') { value = { commands: [] }; break; } value = { commands: [{ name: 'skill:deck-check', description: '检查设备状态与存储空间（演示）', source: 'skill' }, { name: 'skill:game-library', description: '整理游戏库（演示）', source: 'skill' }, { name: 'help', description: '查看帮助（演示）', source: 'extension' }, { name: 'status', description: '查看状态（演示）', source: 'prompt' }] }; break;
        case 'preferences': Object.assign(state.preferences, p); publish(); break;
        case 'diagnostics': value = { mode: '浏览器交互预览', realModelConnected: false, sessions: state.sessions.length }; break;
        case 'update_status': value = { status: 'idle', downloaded: 0, total: 0 }; break;
        case 'updates': throw new Error('交互预览不访问 GitHub 检查更新。');
        case 'test_provider': throw new Error('交互预览不测试真实模型连接。');
        case 'voice_select': {
          const model = asr.find(m => m.id === (p.modelId || voice.modelId))!;
          voice.modelId = model.id; voice.name = model.name; voice.total = model.downloadBytes;
          if (p.source) voice.downloadSource = String(p.source);
          voice.status = 'missing'; state.voiceSelection = { modelId: model.id, source: voice.downloadSource || 'huggingface' }; publish(); break;
        }
        case 'voice_devices': value = [{ id: 'demo-internal-mic', name: '内置麦克风（演示）' }, { id: 'demo-headset-mic', name: '耳机麦克风（演示）' }]; break;
        case 'voice_download': throw new Error('浏览器预览不下载真实权重。正式插件从所选站点下载并校验模型。');
        case 'voice_start': throw new Error('交互预览未连接麦克风，可直接测试文字输入。');
        case 'save_provider': {
          const provider: Provider = { id: String(p.id), name: String(p.name || p.id), model: String(p.model), enabledModels: p.enabledModels as string[] || [String(p.model)], api: String(p.api || 'openai-completions'), baseUrl: String(p.baseUrl || ''), custom: Boolean(p.custom), configured: true, default: state.providers.find(i => i.id === p.id)?.default || !state.providers.length, thinking: String(p.thinking || 'off') };
          state.providers = [...state.providers.filter(i => i.id !== provider.id), provider];
          if (state.preferences.titleModel?.provider === provider.id && !provider.enabledModels?.includes(state.preferences.titleModel.model)) state.preferences.titleModel = null;
          publish(); break;
        }
        case 'remove_provider': state.providers = state.providers.filter(i => i.id !== p.id); if (state.preferences.titleModel?.provider === p.id) state.preferences.titleModel = null; publish(); break;
        case 'default_provider': state.providers.forEach(i => { i.default = i.id === p.id; }); publish(); break;
        default: throw new Error('此操作不在浏览器交互预览范围内。');
      }
      return structuredClone(value) as T;
    },
    listen(fn) { listeners.add(fn); return () => { listeners.delete(fn); }; },
    keyboard(el) { el.focus(); }, openPage() { location.search = '?demo'; }, closePage() { location.search = '?demo'; },
    notify() {}, external(url) { window.open(url, '_blank', 'noopener,noreferrer'); },
  };
}
