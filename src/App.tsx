import { Logo } from './components/Logo';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Focusable, GamepadButton, PanelSection, PanelSectionRow } from '@decky/ui';
import { act, installPlayerPlugin, NEW_SESSION_ID, openNewSession, once, platform, refresh, selectSession, setDraft, useAgent } from './client';
import type { Catalog, Provider, Session, Snapshot, UIRequest } from './types';
import { Conversation, ExtensionDialog, ModelPicker } from './components/Conversation';
import { ProviderEditor, ProviderPicker, Settings } from './components/Settings';
import { Button, ErrorBox, Field, Loading, Modal, NativeControls, Status } from './components/ui';
import { styles } from './styles';
import { Icon } from './components/Icon';

type Dialog = { type: string; provider?: Partial<Provider>; catalog?: Catalog; ui?: UIRequest; sessionId?: string } | null;

export function App({ compact = false }: { compact?: boolean }) {
  const { data, session, draft, error: connectionError, announcement } = useAgent();
  const [view, setView] = useState('chat');
  const root = useRef<HTMLDivElement>(null);
  const [modal, setModal] = useState<Dialog>(null);
  const [error, setError] = useState('');
  const [voiceError, setVoiceError] = useState('');
  const [settingsTab, setSettingsTab] = useState('providers');
  const [settingsKey, setSettingsKey] = useState(0);
  const close = useCallback(() => setModal(null), []);
  const openSession = (id: string) => { setView('chat'); void selectSession(id); };
  const newSession = useCallback(() => {
    openNewSession(); setModal(null); setView('chat'); setError('');
    if (compact) platform.openPage();
  }, [compact]);
  useEffect(() => {
    if (compact || view !== 'chat' || modal || !session?.unread || data?.active?.id !== session.id) return;
    const doc = root.current?.ownerDocument;
    if (!doc) return;
    let sent = false;
    const mark = () => {
      if (sent || doc.visibilityState !== 'visible' || !doc.hasFocus()) return;
      sent = true;
      void act('mark_read', { sessionId: session.id, replyVersion: session.replyVersion || 0 }).catch(e => { sent = false; setError(String(e)); });
    };
    mark(); doc.addEventListener('visibilitychange', mark); doc.defaultView?.addEventListener('focus', mark);
    return () => { doc.removeEventListener('visibilitychange', mark); doc.defaultView?.removeEventListener('focus', mark); };
  }, [compact, view, modal, session?.id, session?.unread, session?.replyVersion, data?.active?.id]);
  useEffect(() => {
    if (modal?.type === 'extension' && modal.ui && data && !data.sessions.find(s => s.id === modal.ui?.sessionId)?.pending.some(r => r.id === modal.ui?.id)) close();
  }, [data, modal?.ui?.id, close]);
  useEffect(() => {
    const doc = root.current?.ownerDocument;
    if (!doc) return;
    const key = (event: KeyboardEvent) => {
      if (modal || (root.current?.ownerDocument || document).querySelector('[aria-modal="true"]') || ['INPUT', 'TEXTAREA', 'SELECT'].includes((root.current?.ownerDocument || document).activeElement?.tagName || '')) return;
      if (view === 'chat' && event.key.toLowerCase() === 'y') { event.preventDefault(); newSession(); }
      if (!compact && view === 'chat' && event.key.toLowerCase() === 'x' && session) { event.preventDefault(); void once('voice_start', () => act('voice_start', { sessionId: session.id })).catch(e => setVoiceError(String(e))); }
      if (event.key === 'Escape') { if (view !== 'chat') setView('chat'); else platform.closePage(); }
    };
    doc.addEventListener('keydown', key);
    return () => doc.removeEventListener('keydown', key);
  }, [compact, modal, session?.id, view, newSession, Boolean(data)]);

  function editProvider(p?: Provider) {
    setModal(p ? { type: 'provider-editor', provider: p } : { type: 'provider-picker' });
  }

  if (!data) return <div className="da-app"><style>{styles}</style><div className="da-empty"><h2>Deck Agent</h2><p>正在连接后端…</p><ErrorBox text={connectionError} /><Button onClick={() => { void refresh(); }}>重试连接</Button></div></div>;
  const items = data.sessions.filter(s => !s.archived);
  const recent = [...items].sort((a, b) => b.updated - a.updated).slice(0, 6);
  const voiceBusy = ['recording', 'transcribing'].includes(data.voice.status);
  const pending = session?.pending || [];
  const menuSession = modal?.type === 'session-menu' ? data.sessions.find(s => s.id === modal.sessionId) : undefined;
  const openSessionMenu = (sessionId: string) => setModal({ type: 'session-menu', sessionId });
  return <Focusable ref={root} flow-children="row" onCancelActionDescription={view === 'chat' ? '返回 Steam' : '返回会话'} onSecondaryActionDescription={!compact && view === 'chat' ? '语音输入' : undefined} onOptionsActionDescription={view === 'chat' ? '新会话' : undefined} className={`da-app ${compact ? 'da-compact' : ''}`} onCancelButton={() => { if (!modal && !voiceBusy) { if (view !== 'chat') setView('chat'); else platform.closePage(); } }}
    onSecondaryButton={event => { if (!compact && !modal && view === 'chat' && !voiceBusy && session && !['INPUT', 'TEXTAREA'].includes((root.current?.ownerDocument || document).activeElement?.tagName || '')) { event.stopPropagation(); void once('voice_start', () => act('voice_start', { sessionId: session.id })).catch(e => setVoiceError(String(e))); } }}
    onOptionsButton={event => { if (!modal && view === 'chat' && !['INPUT', 'TEXTAREA'].includes((root.current?.ownerDocument || document).activeElement?.tagName || '')) { event.stopPropagation(); newSession(); } }}
    onButtonDown={event => { if (compact || modal || view !== 'chat' || voiceBusy || !session || ['INPUT', 'TEXTAREA', 'SELECT'].includes((root.current?.ownerDocument || document).activeElement?.tagName || '')) return; const button = event.detail.button; if (button !== GamepadButton.BUMPER_LEFT && button !== GamepadButton.BUMPER_RIGHT) return; const list = data.sessions.filter(s => !s.archived); const index = list.findIndex(s => s.id === session.id); if (list.length) { event.stopPropagation(); openSession(list[(index + (button === GamepadButton.BUMPER_LEFT ? -1 : 1) + list.length) % list.length].id); } }}>
    <style>{styles}</style>
    {announcement && <div className="da-announcement" role="status">✓ {announcement}</div>}
    {compact ? <NativeControls className="da-qam">
      <PluginRequests data={data} />
      <PanelSection><PanelSectionRow><Button className="da-qam-create" onClick={newSession}><Icon name="compose" />发起会话</Button></PanelSectionRow>
        <ErrorBox text={connectionError || error} />
      </PanelSection>
      <PanelSection title="最近会话"><div className="da-qam-recents">{recent.map(s => <PanelSectionRow key={s.id}><Button className="da-qam-session" variant={s.id === session?.id ? 'active' : ''} current={s.id === session?.id} title={'打开会话：' + s.name} onClick={async () => { await selectSession(s.id); platform.openPage(); }}><span className="da-qam-session-info"><span className="da-session-name"><SessionDot session={s} /><span className="da-session-title">{s.name}</span></span>{s.status !== 'idle' && <Status value={s.status} />}</span><span className="da-qam-arrow" aria-hidden="true">›</span></Button></PanelSectionRow>)}</div>{!recent.length && <p className="da-qam-empty da-muted">暂无会话</p>}</PanelSection>
    </NativeControls>
      : <><Focusable flow-children="column" className="da-rail" aria-label="会话导航"><div className="da-brand"><Logo className="da-logo" size={26} /><strong>Deck Agent</strong></div>
        <Focusable flow-children="row" className="da-rail-actions"><Button className="da-search-button da-icon-button" title="搜索会话" onClick={() => setModal({ type: 'search' })}><Icon name="search" /></Button><Button className="da-new-session" variant="new" onClick={newSession}><Icon name="compose" />新会话</Button></Focusable>
        <div className="da-rail-sessions"><div className="da-session-label">会话</div>
          <div className="da-session-scroll">{items.map(s => <SessionRow key={s.id} session={s} current={s.id === session?.id} active={view === 'chat' && s.id === session?.id} open={openSession} menu={openSessionMenu} />)}{!items.length && <p className="da-muted">暂无会话</p>}</div>
        </div><div className="da-rail-bottom"><Button variant={view === 'settings' ? 'selected' : 'ghost'} onClick={() => { setSettingsTab('providers'); setView('settings'); }}>⚙ 设置</Button></div>
      </Focusable><Focusable flow-children="column" className="da-main">{connectionError ? <ErrorBox text={connectionError} /> : (voiceError || error) && <Focusable flow-children="row" className="da-error da-error-banner" role="alert">
        <span className="da-error-message" title={voiceError || error}>{voiceError || error}</span>
        {voiceError && <Button onClick={() => { setVoiceError(''); setSettingsTab('voice'); setSettingsKey(key => key + 1); setView('settings'); }}>去配置</Button>}
        <Button variant="ghost" onClick={() => voiceError ? setVoiceError('') : setError('')}>关闭</Button>
      </Focusable>}
        <PluginRequests data={data} />
        {!data.runtime.ready && <ErrorBox text={data.runtime.error} />}
        {view === 'settings' ? <Settings key={settingsKey} initialTab={settingsTab} data={data} openProvider={p => { void editProvider(p); }} configureAgent={() => {
          const text = '帮我查看当前 Pi 的 Skills、扩展、MCP 与配置文件，再按我的需求使用 Pi 原生机制配置。';
          if (session) { setDraft(session.id, text); setView('chat'); }
          else { newSession(); setDraft(NEW_SESSION_ID, text); }
        }} />
          : session ? <><Conversation key={session.id} data={data} session={session} draft={draft} menu={() => openSessionMenu(session.id)} model={() => setModal({ type: 'model' })} error={setError} voiceError={setVoiceError} />
            {pending.length > 0 && <div className="da-pending"><span>Pi 扩展正在等待输入</span><Button variant="primary" onClick={() => setModal({ type: 'extension', ui: pending[0] })}>查看请求</Button></div>}</>
            : <div className="da-empty"><Logo className="da-empty-mark" size={64} /><h1>你的 Deck，多一个帮手。</h1>{data.providers.length ? <Button variant="primary" onClick={newSession}>开始新会话</Button> : <Button variant="primary" onClick={() => setView('settings')}>连接模型</Button>}</div>}
      </Focusable></>}
    {modal?.type === 'search' && <SessionSearch sessions={data.sessions} close={close} choose={id => { close(); openSession(id); }} />}
    {menuSession && <SessionMenu key={menuSession.id} session={menuSession} close={close} done={() => { close(); void refresh(); }} />}
    {modal?.type === 'model' && session && <ModelPicker session={session} close={close} />}
    {modal?.type === 'provider-picker' && <ProviderPicker data={data} close={close} choose={(provider, catalog) => setModal({ type: 'provider-editor', provider, catalog })} />}
    {modal?.type === 'provider-editor' && <ProviderEditor key={modal.provider?.id || 'custom'} provider={modal.provider!} catalog={modal.catalog} close={close} />}
    {modal?.type === 'extension' && modal.ui && data.sessions.find(s => s.id === modal.ui?.sessionId)?.pending.some(r => r.id === modal.ui?.id) && <ExtensionDialog key={modal.ui.id} request={modal.ui} close={close} />}
    {voiceBusy && <VoiceDialog voice={data.voice} close={close} />}
  </Focusable>;
}

const SESSION_HOLD_MS = 500;

function SessionRow({ session, current, active, open, menu }: {
  session: Session; current: boolean; active: boolean; open: (id: string) => void; menu: (id: string) => void;
}) {
  const gamepadStart = useRef<number | null>(null);
  const pointerStart = useRef<{ id: number; time: number; x: number; y: number } | null>(null);
  const pointerHeld = useRef(false);
  return <Button title={session.name} current={current} preferredFocus={active} variant={active ? 'active' : 'ghost'}
    onOKActionDescription="打开会话（长按操作）"
    // Steam 按下 A 就会触发默认点击，等松开才能区分短按和长按。
    onOKButton={event => { event.preventDefault(); event.stopPropagation(); }}
    onButtonDown={event => {
      if (event.detail.button === GamepadButton.OK && !event.detail.is_repeat) gamepadStart.current = performance.now();
    }}
    onButtonUp={event => {
      if (event.detail.button !== GamepadButton.OK || gamepadStart.current === null) return;
      event.stopPropagation();
      const held = performance.now() - gamepadStart.current >= SESSION_HOLD_MS;
      gamepadStart.current = null;
      (held ? menu : open)(session.id);
    }}
    onGamepadBlur={() => { gamepadStart.current = null; }}
    onPointerDown={event => {
      if (!event.isPrimary || event.button !== 0) return;
      pointerHeld.current = false;
      pointerStart.current = { id: event.pointerId, time: performance.now(), x: event.clientX, y: event.clientY };
    }}
    onPointerUp={event => {
      const start = pointerStart.current;
      if (start?.id !== event.pointerId) return;
      pointerStart.current = null;
      pointerHeld.current = performance.now() - start.time >= SESSION_HOLD_MS
        && Math.hypot(event.clientX - start.x, event.clientY - start.y) < 10;
    }}
    onPointerCancel={() => { pointerStart.current = null; pointerHeld.current = false; }}
    onClick={() => {
      const held = pointerHeld.current;
      pointerHeld.current = false;
      (held ? menu : open)(session.id);
    }}>
    <span className="da-session-name"><SessionDot session={session} /><span className="da-session-title">{session.name}</span></span>
  </Button>;
}

function SessionDot({ session }: { session: Session }) {
  if (session.status === 'waiting' || session.status === 'error' || session.status === 'interrupted') return <span className={`da-session-dot attention ${session.status}`} role="img" aria-label={session.status === 'waiting' ? '等待你确认' : session.status === 'error' ? '任务出错' : '任务已中断'}>!</span>;
  const busy = ['running', 'starting'].includes(session.status);
  const state = busy ? 'busy' : session.unread ? 'unread' : 'read';
  return <span className={`da-session-dot ${state}`} role="img" aria-label={busy ? '进行中' : session.unread ? '有未读回复' : '已读'} />;
}

function SessionSearch({ sessions, close, choose }: { sessions: Session[]; close: () => void; choose: (id: string) => void }) {
  const [query, setQuery] = useState('');
  const items = sessions.filter(s => (s.name + ' ' + s.cwd).toLowerCase().includes(query.trim().toLowerCase()));
  return <Modal title="搜索会话" close={close}><div className="da-form"><Field label="会话名称或工作目录" value={query} onChange={setQuery} placeholder="搜索会话…" />
    <div className="da-search-results">{items.map(s => <Button key={s.id} onClick={() => choose(s.id)}><span className="da-row"><SessionDot session={s} /><span className="da-search-session"><strong>{s.name}</strong><small>{s.cwd}</small></span>{s.archived && <span className="da-badge">归档</span>}</span></Button>)}{!items.length && <p className="da-muted">未找到会话</p>}</div>
  </div></Modal>;
}

function SessionMenu({ session, close, done }: { session: Session; close: () => void; done: () => void }) {
  const [name, setName] = useState(session.name);
  const [error, setError] = useState('');
  const [step, setStep] = useState<'menu' | 'rename' | 'delete'>('menu');
  const busy = ['starting', 'running', 'waiting'].includes(session.status);
  const run = (payload: Record<string, unknown>) => { return once('session_meta:' + session.id, () => act('session_meta', { sessionId: session.id, ...payload })).then(done).catch(e => { setError(String(e)); throw e; }); };
  const back = () => { setError(''); setStep('menu'); };
  const title = step === 'rename' ? '重命名会话' : step === 'delete' ? '删除这条会话记录？' : '会话操作';
  return <Modal title={title} close={close} actions={<Button onClick={step === 'menu' ? close : back}>返回</Button>}>
    <div className="da-form">
      <p>{session.name}</p><ErrorBox text={error} />
      {step === 'rename' ? <><Field label="会话名称" value={name} onChange={setName} /><Button disabled={!name.trim()} onClick={() => run({ name })}>保存名称</Button></>
        : step === 'delete' ? <><p>历史对话会被删除，已完成的文件操作不会撤销。</p><Button variant="danger" disabled={busy} onClick={() => run({ delete: true })}>删除记录</Button></>
        : <><Button onClick={() => setStep('rename')}>重命名</Button>
          {busy && <Button busyText="正在停止…" onClick={() => act('stop', { sessionId: session.id }).then(done)}>停止当前任务</Button>}
          <Button disabled={busy} onClick={() => run({ archived: !session.archived })}>{session.archived ? '取消归档' : '归档会话'}</Button>
          <Button variant="danger" disabled={busy} onClick={() => setStep('delete')}>删除会话记录</Button></>}
    </div>
  </Modal>;
}

function VoiceDialog({ voice, close }: { voice: { status: string; recordingStarted?: number }; close: () => void }) {
  const [seconds, setSeconds] = useState(0); const [error, setError] = useState('');
  useEffect(() => { const timer = setInterval(() => setSeconds(Math.max(0, Math.floor(Date.now() / 1000 - (voice.recordingStarted || Date.now() / 1000)))), 250); return () => clearInterval(timer); }, [voice.recordingStarted]);
  const cancel = () => once('voice_cancel', () => act('voice_cancel')).then(close).catch(e => { setError(String(e)); });
  return <Modal title={voice.status === 'recording' ? '正在听你说' : '正在本地转写'} close={cancel} actions={<><Button onClick={cancel}>取消</Button>{voice.status === 'recording' && <Button variant="primary" busyText="正在结束录音…" onClick={() => act('voice_finish').catch(e => { setError(String(e)); throw e; })}>结束并转写</Button>}</>}><div className="da-recording"><span>♩</span><h1>{voice.status === 'recording' ? `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}` : <Loading text="正在识别，请稍候…" />}</h1><ErrorBox text={error} /></div></Modal>;
}


function PluginRequests({ data }: { data: Snapshot }) {
  return <>{data.pluginInstalls?.map(item => <Focusable key={item.ticket} flow-children="column" className="da-model-card" aria-live="polite">
    <strong>{item.name} {item.version} 待安装</strong>
    <p>安装包已准备，继续后由 Decky 显示原生确认。</p>
    <ErrorBox text={item.error || ''} />
    <Focusable flow-children="row" className="da-row">
      <Button busyText="准备安装…" onClick={() => installPlayerPlugin(item.ticket)}>继续安装</Button>
      <Button onClick={() => act('player_plugin_dismiss', { ticket: item.ticket })}>暂不安装</Button>
    </Focusable>
  </Focusable>)}</>;
}
