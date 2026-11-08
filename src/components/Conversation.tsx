import { Logo } from './Logo';
import { useEffect, useRef, useState } from 'react';
import { Focusable, GamepadButton } from '@decky/ui';
import { act, actionPending, announce, clearDraft, flushDraft, materializeSession, NEW_SESSION_ID, once, pendingMessage, platform, refresh, request, sessionFeedback, setDraft, setPendingMessage, setSessionFeedback } from '../client';
import type { Content, LiveTool, Message, Model, Session, Snapshot, UIRequest } from '../types';
import { Button, CustomControls, ErrorBox, Field, Loading, Modal, Select, Status } from './ui';
import { Icon } from './Icon';
import { Markdown } from './Markdown';
import { useComposerLayout } from './useComposerLayout';
import { conversationTurns, processLabel, type ConversationTurn } from './conversation-turns';

const scenePresets = [
  {
    title: '帮我排查游戏问题或优化画面配置',
    prompt: '请先识别这台 Steam Deck 上安装的游戏版本，结合日志和现有配置排查问题，或按我的目标给出画面和性能设置建议。需要改配置时，先说明改动和影响，等我确认后备份原配置再修改，并告诉我怎么验证和恢复。\n\n遇到的问题或想改善的地方（如闪退、画质、帧率或续航）：\n需要排查或优化的游戏是：',
  },
  {
    title: '备份或恢复游戏存档',
    prompt: '请帮我找到这台 Steam Deck 上的游戏存档。备份前先列出将备份的文件。恢复前先列出可用备份和恢复位置，等我确认后，先保护当前存档再恢复。如果可能与 Steam 云存档冲突，请先告诉我。完成后告诉我备份位置和结果。\n\n要做的操作（备份或恢复）：\n需要备份或恢复存档的游戏是：',
  },
  {
    title: '按我的需求寻找并安装游戏 Mod',
    prompt: '如果我描述的是想实现的效果，请帮我找合适的 Mod 或汉化包。如果我指定了 Mod，请直接检查对应的来源。先核对游戏版本、Steam Deck 兼容性、依赖和冲突，再说明要下载什么、会改哪些文件。等我确认后再安装，保留原文件，并告诉我怎么验证、停用或卸载。\n\n想实现的效果，或指定 Mod／汉化包的名称、链接或文件路径：\n需要安装 Mod 的游戏是：',
  },
  {
    title: '在 GitHub 上寻找并安装 Decky 插件',
    prompt: '请在 GitHub 的 decky-plugin 主题下，按我的需求找合适的 Decky 插件。如果我提供了仓库或本地安装包，请直接检查该来源。先说明插件用途、来源、版本和已知兼容情况，核对安装包，再让我在 Decky 的确认窗口里确认安装。装好后检查版本和加载状态。\n\n想要的插件功能，或指定的仓库链接／本地 ZIP 路径：',
  },
];

function textOf(message: Message) {
  return typeof message.content === 'string' ? message.content : message.content?.filter(c => c.type === 'text').map(c => c.text || '').join('\n') || '';
}
function MessageView({ message }: { message: Message }) {
  const [expanded, setExpanded] = useState(false);
  if (message.role === 'toolResult') return <div className="da-tool"><Button onClick={() => setExpanded(v => !v)}><span className="da-tool-title"><code>{message.toolName || 'tool'}</code><span>{message.isError ? '执行出错' : '执行结果'}</span><span>{expanded ? '⌃' : '›'}</span></span></Button>{expanded && <pre>{textOf(message)}</pre>}</div>;
  const tools = Array.isArray(message.content) ? message.content.filter(c => c.type === 'toolCall') : [];
  const text = textOf(message);
  return <div className={`da-message ${message.role === 'user' ? 'user' : 'assistant'}`}>
    {message.role === 'assistant' && <Logo className="da-avatar" size={24} />}<div className="da-message-body">{message.role === 'user' ? <p>{text}</p> : <Markdown text={text} />}
      {tools.map((tool, i) => <ToolCall key={tool.id || i} tool={tool} />)}
      {message.errorMessage && <ErrorBox text={message.errorMessage} />}
      {Array.isArray(message.content) && message.content.some(c => c.type === 'image') && <span className="da-muted">[图像结果已保留在 Pi 会话中]</span>}
    </div></div>;
}
function TurnView({ turn }: { turn: ConversationTurn }) {
  const [expanded, setExpanded] = useState(turn.active);
  return <div className="da-turn">
    {turn.user && <MessageView message={turn.user} />}
    {turn.process.length > 0 && <div className={`da-process ${turn.active ? 'running' : 'completed'}`}>
      <Button className="da-process-toggle" popup={false} variant="ghost" title={expanded ? '收起执行过程' : '展开执行过程'} expanded={expanded} onClick={() => setExpanded(value => !value)}>
        <span>{processLabel(turn)}{turn.toolCount > 0 && <span className="da-process-count"> · {turn.toolCount} 次工具调用</span>}</span><span aria-hidden="true">{expanded ? '⌄' : '›'}</span>
      </Button>
      {expanded && <Focusable flow-children="column" className="da-process-details">{turn.process.map((message, index) => <MessageView key={index} message={message} />)}</Focusable>}
    </div>}
    {turn.result && <MessageView message={turn.result} />}
    {turn.interrupted && <p className="da-turn-interrupted" role="status">用户中断任务</p>}
  </div>;
}
function ToolCall({ tool }: { tool: Content }) {
  const [expanded, setExpanded] = useState(false);
  return <div className="da-tool-call"><Button variant="ghost" onClick={() => setExpanded(v => !v)}>{tool.name} · 工具调用 {expanded ? '⌃' : '›'}</Button>{expanded && <pre>{JSON.stringify(tool.arguments, null, 2)}</pre>}</div>;
}
function RunningTool({ tool }: { tool: LiveTool }) {
  const [expanded, setExpanded] = useState(false);
  return <div className="da-tool"><Button onClick={() => setExpanded(v => !v)}><span className="da-tool-title"><code>{tool.name}</code><span>正在执行</span><span>{expanded ? '⌃' : '›'}</span></span></Button>{expanded && <><pre>{JSON.stringify(tool.args, null, 2)}</pre><pre>{tool.result?.content?.filter(c => c.type === 'text').map(c => c.text).join('\n') || '等待工具输出…'}</pre></>}</div>;
}

export function Composer({ session, draft, compact = false, presetFocus = 0, openModel, error, voiceError }: {
  session: Session; draft: string; compact?: boolean; presetFocus?: number; openModel: () => void; error: (text: string) => void; voiceError: (text: string) => void;
}) {
  const [supplement, setSupplement] = useState(false);
  const [more, setMore] = useState(false);
  const input = useComposerLayout(draft);
  useEffect(() => {
    const el = input.current;
    const win = el?.ownerDocument.defaultView;
    if (!presetFocus || !el || !win) return;
    const frame = win.requestAnimationFrame(() => {
      el.focus({ preventScroll: true });
      const end = el.value.length;
      el.setSelectionRange(end, end);
      el.scrollTop = el.scrollHeight;
      platform.keyboard(el);
    });
    return () => win.cancelAnimationFrame(frame);
  }, [input, presetFocus]);
  const busy = ['running', 'waiting', 'starting'].includes(session.status);
  const hasText = Boolean(draft.trim());
  const sending = actionPending('send:' + session.id) || (session.id !== NEW_SESSION_ID && pendingMessage(session.id)?.failed === false && actionPending('send:' + NEW_SESSION_ID));
  const stopping = actionPending('stop:' + session.id);
  function send(behavior?: string) {
    if (!draft.trim() || sending) return;
    if (busy && !behavior) { setSupplement(true); return; }
    let id = session.id; const text = draft;
    return once('send:' + id, async () => {
      error(''); setSessionFeedback(id, '正在发送…'); setPendingMessage(id, { text, failed: false });
      try {
        if (id === NEW_SESSION_ID) {
          id = await materializeSession(text);
          setPendingMessage(NEW_SESSION_ID); setSessionFeedback(NEW_SESSION_ID, '');
          setPendingMessage(id, { text, failed: false });
        }
        await flushDraft(id);
        const response = await request<{ disposition?: string }>('send', { sessionId: id, text, behavior });
        clearDraft(id, text); setPendingMessage(id); setSupplement(false);
        setSessionFeedback(id, response?.disposition === 'handled' ? '输入已由扩展处理' : behavior === 'followUp' ? '已加入队列，当前任务结束后处理' : behavior === 'steer' ? '已提交补充要求' : '已发送，等待模型回复…');
        await refresh();
      } catch (e) {
        setPendingMessage(id, { text, failed: true }); setSessionFeedback(id, '发送失败，草稿已保留');
        error(String(e instanceof Error ? e.message : e)); throw e;
      }
    });
  }
  const stop = () => once('stop:' + session.id, async () => {
    setSessionFeedback(session.id, '正在停止任务…');
    try { await act('stop', { sessionId: session.id }); setSessionFeedback(session.id, ''); }
    catch (e) { error(String(e)); setSessionFeedback(session.id, '停止失败，可以重试'); throw e; }
  });
  return <CustomControls><Focusable flow-children="row" className={`da-composer-wrap ${compact ? 'compact' : ''}`} aria-label="消息与任务操作"><div className="da-composer">
    <Button title="Skills 与更多操作" expanded={more} className="da-icon-button da-composer-plus" onClick={() => { if (input.current) platform.hideKeyboard(input.current); setMore(true); }}><Icon name="plus" /></Button>
    <Focusable className="da-compose-focus" onOKActionDescription="编辑消息" onActivate={() => { if (input.current) { input.current.focus(); platform.keyboard(input.current); } }}>
      <textarea ref={input} rows={1} aria-label={compact ? '侧边栏消息' : '消息输入'} placeholder={busy ? '补充要求…' : '想做点什么？'} value={draft}
        onChange={event => setDraft(session.id, event.target.value)} onBlur={() => { void flushDraft(session.id); }}
        onPointerUp={event => { if (event.button === 0) platform.keyboard(event.currentTarget); }}
        onKeyDown={event => { if (event.key === 'Enter') { event.stopPropagation(); if ((event.ctrlKey || event.metaKey) && !event.nativeEvent.isComposing) { event.preventDefault(); void send()?.catch(() => {}); } } }} />
    </Focusable><Focusable flow-children="row" className="da-composer-actions">
      <Button className="da-model-picker" title="切换模型" onClick={openModel}>{session.model || '选择模型'} ⌄</Button>
      {busy && <Button className="da-icon-button da-composer-action da-stop-action" title="停止任务" loading={stopping} busyText="停止中" onClick={stop}><Icon name="stop" /></Button>}
      {(sending || hasText || !busy) && <Button className={`da-icon-button da-composer-action ${hasText ? 'da-send-action da-submit-action' : 'da-mic-action'}`} title={sending ? '发送消息' : hasText ? busy ? '补充任务' : '发送消息' : '开始语音输入'} loading={sending} busyText="发送中" onClick={() => {
        if (hasText) return send();
        return once('voice_start', () => act('voice_start', { sessionId: session.id })).catch(e => { voiceError(String(e)); throw e; });
      }}><Icon name={hasText ? 'send' : 'mic'} /></Button>}
    </Focusable></div></Focusable>
    {more && <Modal title="Skills 与命令" close={() => setMore(false)}><ComposerCommands sessionId={session.id} close={() => { setMore(false); setTimeout(() => input.current?.focus(), 0); }} /></Modal>}
    {supplement && <Modal title="怎样补充这条要求？" close={() => setSupplement(false)}><div className="da-form"><Button loading={sending} busyText="正在提交…" onClick={() => send('steer')}>尽快补充给当前任务</Button><Button loading={sending} busyText="正在加入队列…" onClick={() => send('followUp')}>当前任务结束后再处理</Button></div></Modal>}
  </CustomControls>;
}

export function Conversation({ data, session, draft, menu, model, error, voiceError }: { data: Snapshot; session: Session; draft: string; menu: () => void; model: () => void; error: (text: string) => void; voiceError: (text: string) => void }) {
  const scroll = useRef<HTMLDivElement>(null);
  const nearEnd = useRef(true);
  const [showLatest, setShowLatest] = useState(false);
  const [presetFocus, setPresetFocus] = useState(0);
  const active = data.active?.id === session.id ? data.active : null;
  const messages = active?.messages || [];
  const pending = pendingMessage(session.id);
  const feedback = sessionFeedback(session.id);
  const sending = actionPending('send:' + session.id) || (session.id !== NEW_SESSION_ID && pendingMessage(session.id)?.failed === false && actionPending('send:' + NEW_SESSION_ID));
  const stopping = actionPending('stop:' + session.id);
  const running = ['running', 'starting'].includes(session.status);
  const turns = conversationTurns(messages, running || session.status === 'waiting', session.status === 'stopped');
  const status = session.status === 'stopped' ? '' : sending ? '正在发送…' : stopping ? '正在停止任务…' : session.status === 'waiting' ? '等待你确认后继续' : session.status === 'starting' ? '正在启动 Pi…' : active?.tools.length ? `正在执行 ${active.tools[0].name}…` : running ? messages.at(-1)?.role === 'assistant' ? '正在生成回复…' : '等待模型回复…' : feedback;
  useEffect(() => {
    if (scroll.current && nearEnd.current) scroll.current.scrollTop = scroll.current.scrollHeight;
    else if (messages.length) setShowLatest(true);
  }, [messages, pending, active?.tools]);
  const latest = () => { if (scroll.current) scroll.current.scrollTop = scroll.current.scrollHeight; nearEnd.current = true; setShowLatest(false); };
  const pageScroll = (direction: number) => {
    const el = scroll.current; if (!el) return false;
    const before = el.scrollTop; el.scrollTop += direction * Math.max(80, el.clientHeight * .6);
    return el.scrollTop !== before;
  };
  return <><header className="da-chat-head"><div className="da-row da-grow"><h2>{session.name}</h2><span className="da-cwd" title={session.cwd}>▱ {session.cwd}</span></div><Status value={sending ? 'sending' : stopping ? 'stopping' : session.status === 'idle' && feedback === '任务已结束' ? 'completed' : session.status} />{session.id !== NEW_SESSION_ID && <Button title="会话操作" onClick={menu}>···</Button>}</header>
    {session.error && <ErrorBox text={session.error} />}
    {session.status === 'interrupted' && <div className="da-context">上次执行已中断，请检查结果后再继续。<Button onClick={() => setDraft(session.id, '请检查上次任务已完成到哪一步，再从未完成处继续，不要重复已经完成的操作。')}>准备继续</Button></div>}
    <Focusable flow-children="column" className="da-chat-content" aria-label="对话记录" tabIndex={0} ref={scroll} onOKActionDescription="阅读对话" onGamepadDirection={event => {
      // Steam 把 undefined 当作已处理；未滚动的方向必须显式放行。
      if (event.target !== event.currentTarget) return false;
      const direction = event.detail.button === GamepadButton.DIR_UP ? -1 : event.detail.button === GamepadButton.DIR_DOWN ? 1 : 0;
      if (direction && pageScroll(direction)) { event.stopPropagation(); return true; }
      return false;
    }} onKeyDown={event => {
      if (event.target !== event.currentTarget) return;
      if ((event.key === 'ArrowUp' || event.key === 'ArrowDown') && pageScroll(event.key === 'ArrowUp' ? -1 : 1)) { event.preventDefault(); event.stopPropagation(); }
    }} onScroll={() => { const e = scroll.current!; nearEnd.current = e.scrollHeight - e.scrollTop - e.clientHeight < 80; if (nearEnd.current) setShowLatest(false); }}>
      {!active && session.id !== NEW_SESSION_ID ? <div className="da-empty"><Loading text="正在加载会话记录…" /><Button onClick={() => refresh(true)}>重新读取</Button></div> : messages.length ? turns.map(turn => <TurnView key={`${turn.key}:${turn.active ? 'active' : 'complete'}`} turn={turn} />) : !pending && <div className="da-empty"><Logo className="da-empty-mark" size={64} /><h1>今天，想做点什么？</h1><Focusable flow-children="grid" className="da-quick-prompts">{scenePresets.map(({ title, prompt }) => <Button key={title} onClick={() => {
        setDraft(session.id, prompt);
        setPresetFocus(count => count + 1);
      }}>{title}</Button>)}</Focusable></div>}
      {pending && <div className={`da-message user da-message-pending ${pending.failed ? 'failed' : ''}`}><p>{pending.text}</p><small>{pending.failed ? '未发送 · 草稿已保留，可重试' : '正在发送…'}</small></div>}
      {active?.tools.map(tool => <RunningTool key={tool.id} tool={tool} />)}
      {Object.entries(active?.widgets || {}).map(([key, lines]) => lines.length > 0 && <pre key={key}>{lines.join('\n')}</pre>)}
    </Focusable>
    {showLatest && <div className="da-latest"><Button onClick={latest}>↓ 回到最新消息</Button></div>}
    {status && <div className={`da-task-feedback ${running || sending || stopping ? 'working' : ''}`} role="status">{running || sending || stopping ? <span className="da-spinner" aria-hidden="true" /> : <span aria-hidden="true">{session.status === 'waiting' ? '!' : session.status === 'error' || pending?.failed ? '!' : '✓'}</span>}<span>{status}</span></div>}
    {running && feedback.startsWith('已') && <p className="da-extension-status">{feedback}</p>}
    {Object.entries(active?.statusEntries || {}).filter(([, value]) => value).map(([key, value]) => <p key={key} className="da-extension-status">{value}</p>)}<Composer session={session} draft={draft} presetFocus={presetFocus} openModel={model} error={error} voiceError={voiceError} /></>;
}

export function ModelPicker({ session, close }: { session: Session; close: () => void }) {
  const [models, setModels] = useState<Model[]>([]);
  const [model, setModel] = useState((session.provider || '') + '\n' + (session.model || ''));
  const [thinking, setThinking] = useState(session.thinking || 'off');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let alive = true;
    setLoading(true); setError('');
    void request<{ models: Model[] }>(session.id === NEW_SESSION_ID ? 'configured_models' : 'models', { sessionId: session.id }).then(c => {
      if (!alive) return;
      setModels(c.models);
      setModel(current => c.models.some(m => m.provider + '\n' + m.id === current) ? current : c.models.length ? c.models[0].provider + '\n' + c.models[0].id : '');
    }).catch(e => { if (alive) { setModels([]); setError(String(e)); } }).finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [session.id, retry]);
  const valid = models.some(m => m.provider + '\n' + m.id === model);
  return <Modal title="当前会话的模型" close={close} actions={<><Button onClick={close}>取消</Button><Button variant="primary" disabled={loading || !valid} loading={saving} busyText="切换中…" onClick={() => { setSaving(true); const [provider, id] = model.split('\n'); return act('set_model', { sessionId: session.id, provider, model: id, thinking }).then(() => { announce('会话模型已切换'); close(); }).catch(e => setError(String(e))).finally(() => setSaving(false)); }}>{saving ? '切换中…' : '切换模型'}</Button></>}>
    <div className="da-form">{loading && <p className="da-muted">正在读取可用模型…</p>}{!loading && !error && !models.length && <p>暂无可用模型，请先在设置中配置供应商。</p>}<Select label="模型" disabled={loading || !models.length} value={model} options={models.map(m => ({ value: m.provider + '\n' + m.id, label: `${m.provider} · ${m.name || m.id}` }))} onChange={setModel} />
      <Select label="思考强度" value={thinking} options={['off', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max'].map(v => ({ value: v, label: v }))} onChange={setThinking} />
      <Button disabled={loading || saving} onClick={() => setRetry(v => v + 1)}>刷新模型列表</Button>
      <ErrorBox text={error} /></div>
  </Modal>;
}

type ComposerCommand = { name: string; description?: string; source?: string };
function ComposerCommands({ sessionId, close }: { sessionId: string; close: () => void }) {
  const [commands, setCommands] = useState<ComposerCommand[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let alive = true;
    setLoading(true); setError('');
    void request<{ commands: ComposerCommand[] }>('commands', { sessionId }).then(c => {
      if (alive) setCommands(c.commands);
    }).catch(e => { if (alive) setError(String(e)); }).finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [sessionId, retry]);
  const choose = (text: string) => { setDraft(sessionId, text); close(); };
  return <div className="da-composer-command-groups">
    {loading ? <p className="da-muted">正在读取 Skills 与命令…</p> : error ? <><ErrorBox text={error} /><Button onClick={() => setRetry(v => v + 1)}>重新读取</Button></> : <>
      {[{ title: 'Skills', skill: true }, { title: '命令', skill: false }].map(group => {
        const items = commands.filter(c => (c.source === 'skill' || c.name.startsWith('skill:')) === group.skill);
        return <section key={group.title} aria-label={group.title}><h3>{group.title}</h3>
          {items.length ? items.map(c => <Button key={c.name} onClick={() => choose('/' + c.name + ' ')}><strong>{group.skill ? c.name.replace(/^skill:/, '') : '/' + c.name}</strong>{c.description && <span className="da-command-description">{c.description}</span>}</Button>) : <p className="da-muted">{group.skill ? sessionId === NEW_SESSION_ID ? '发送首条消息后可查看 Skills' : '暂无可用 Skills' : sessionId === NEW_SESSION_ID ? '发送首条消息后可查看命令' : '暂无可用命令'}</p>}
        </section>;
      })}
    </>}
    <div className="da-composer-command-footer"><Button onClick={() => choose('帮我查看当前 Pi 的 Skills、扩展、MCP 和配置文件，按我的需求使用 Pi 原生机制配置。')}>让 Agent 配置</Button></div>
  </div>;
}

export function ExtensionDialog({ request: ui, close }: { request: UIRequest; close: () => void }) {
  const [value, setValue] = useState(ui.prefill || '');
  const [error, setError] = useState('');
  const respond = (result: string | boolean, cancelled = false) => {
    return once('ui:' + ui.sessionId + ':' + ui.id, () => act('ui_response', { sessionId: ui.sessionId, requestId: ui.id, value: result, cancelled })).then(close).catch(e => { setError(String(e)); });
  };
  return <Modal title={ui.title || 'Pi 扩展请求'} close={() => respond('', true)} actions={<><Button onClick={() => respond('', true)}>取消</Button><Button variant="primary" disabled={ui.method === 'select' && !value} onClick={() => respond(ui.method === 'confirm' ? true : value)}>确认</Button></>}>
    <div className="da-form"><p className="da-muted">Pi 扩展</p>{ui.message && <p>{ui.message}</p>}{ui.method === 'select' ? ui.options?.map(option => <Button key={option} variant={value === option ? 'selected' : ''} onClick={() => setValue(option)}>{option}</Button>) : ui.method === 'editor' ? <textarea className="da-editor" aria-label="说明内容" value={value} onChange={e => setValue(e.target.value)} /> : ui.method === 'input' ? <Field label="内容" value={value} onChange={setValue} placeholder={ui.placeholder} /> : null}<ErrorBox text={error} /></div>
  </Modal>;
}
