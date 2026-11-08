import { useEffect, useSyncExternalStore } from 'react';
import type { Notice, PreparedUpdate, Session, Snapshot } from './types';

export interface Bridge {
  request<T>(action: string, payload?: Record<string, unknown>): Promise<T>;
  listen(callback: (event: Notice) => void): () => void;
  openPage(): void;
  closePage(): void;
  keyboard(element: HTMLTextAreaElement): void;
  keyboardBounds?(element: HTMLTextAreaElement): { top: number; bottom: number } | null;
  hideKeyboard?(element: HTMLTextAreaElement): void;
  notify(event: Notice): void;
  external(url: string): void;
  checkInstaller?(): void;
  installUpdate?(update: PreparedUpdate): Promise<void>;
}
export const NEW_SESSION_ID = '__new__';
const newDraftKey = 'deck-agent-new-draft-v1';
function cachedDraft(): string | undefined {
  try { return globalThis.localStorage?.getItem(newDraftKey) ?? undefined; } catch { return undefined; }
}
function cacheDraft(text?: string) {
  try { if (text === undefined) globalThis.localStorage?.removeItem(newDraftKey); else globalThis.localStorage?.setItem(newDraftKey, text); } catch { /* 后端仍会保存草稿。 */ }
}
let bridge: Bridge;
let data: Snapshot | null = null;
let activeId: string | null = cachedDraft() ? NEW_SESSION_ID : null;
let error = '';
let revision = 0;
let selection = 0;
let refreshTask: Promise<void> | undefined;
let refreshQueued = false;
let openQueued = false;
const feedback = new Map<string, string>();
const submitted = new Map<string, { text: string; failed: boolean }>();
const pendingActions = new Map<string, Promise<unknown>>();
let announcement = '';
let announcementTimer: ReturnType<typeof setTimeout> | undefined;
const listeners = new Set<() => void>();
const drafts = new Map<string, string>();
const cached = cachedDraft();
if (cached !== undefined) drafts.set(NEW_SESSION_ID, cached);
let draftEpoch = 0;
const savedDrafts = new Map<string, { text: string; epoch: number }>();
const draftWrites = new Map<string, Promise<void>>();
const draftTimers = new Map<string, ReturnType<typeof setTimeout>>();
let stopEvents: (() => void) | undefined;
let timer: ReturnType<typeof setTimeout> | undefined;
let refreshTimer: ReturnType<typeof setInterval> | undefined;

function publish() { revision++; listeners.forEach(fn => fn()); }
export function configureBridge(value: Bridge) {
  bridge = value;
  if (drafts.has(NEW_SESSION_ID)) void flushDraft(NEW_SESSION_ID);
  stopEvents?.();
  clearTimeout(timer); timer = undefined;
  stopEvents = bridge.listen(event => {
    if (event.type === 'notice' && data?.preferences.notifications) bridge.notify(event);
    if (event.type === 'notice' && event.sessionId && event.message) {
      feedback.set(event.sessionId, event.message); publish();
    }
    // 固定窗口合并事件，持续流式输出也会刷新，不能每次重新计时。
    if (!timer) timer = setTimeout(() => { timer = undefined; void refresh(); }, 120);
  });
  // 休眠或前端重载后用快照补齐丢失事件；不重发任何任务。
  clearInterval(refreshTimer);
  refreshTimer = setInterval(() => { if (listeners.size) void refresh(); }, 5000);
  return () => {
    stopEvents?.(); clearTimeout(timer); timer = undefined; clearInterval(refreshTimer);
    for (const id of draftTimers.keys()) void flushDraft(id);
    draftTimers.clear();
  };
}

export async function request<T = void>(action: string, payload: Record<string, unknown> = {}): Promise<T> {
  return bridge.request<T>(action, payload);
}
export function refresh(open = false): Promise<void> {
  if (refreshTask) { refreshQueued = true; openQueued ||= open; return refreshTask; }
  const id = activeId;
  const generation = selection;
  const savedBeforeRequest = draftEpoch;
  refreshTask = (async () => { try {
    const snapshot = await request<Snapshot>(open && id && id !== NEW_SESSION_ID ? 'open_session' : 'snapshot', id ? { sessionId: id } : {});
    if (generation !== selection) return;
    for (const item of snapshot.sessions) {
      const previous = data?.sessions.find(s => s.id === item.id);
      if (previous && ['running', 'waiting', 'starting'].includes(previous.status) && item.status === 'idle') feedback.set(item.id, '任务已结束');
    }
    data = snapshot; error = '';
    for (const item of [...snapshot.sessions, { id: NEW_SESSION_ID, draft: snapshot.newSessionDraft || '' }]) {
      const saved = savedDrafts.get(item.id);
      // 只让保存之后发出的快照接管草稿，避免在途旧快照导致输入闪空。
      if (saved && saved.epoch <= savedBeforeRequest && drafts.get(item.id) === saved.text) {
        drafts.delete(item.id); savedDrafts.delete(item.id);
      }
    }
    if (activeId !== NEW_SESSION_ID && (!activeId || !snapshot.sessions.some(s => s.id === activeId))) {
      activeId = (!activeId && snapshot.newSessionDraft) ? NEW_SESSION_ID : snapshot.sessions.find(s => !s.archived)?.id || snapshot.sessions[0]?.id || NEW_SESSION_ID;
      if (activeId !== NEW_SESSION_ID) { selection++; refreshQueued = true; openQueued = true; }
    }
    publish();
  } catch (reason) { if (generation === selection) { error = String(reason instanceof Error ? reason.message : reason); publish(); } }
  })().finally(() => {
    refreshTask = undefined;
    if (refreshQueued) { const nextOpen = openQueued; refreshQueued = false; openQueued = false; void refresh(nextOpen); }
  });
  return refreshTask;
}
// 打开草稿界面只更新本地选择，不请求后端，也不进入历史列表。
export function openNewSession() { activeId = NEW_SESSION_ID; selection++; publish(); }
export async function materializeSession(text: string): Promise<string> {
  const { id } = await request<{ id: string }>('create_session', { fromDraft: true, text });
  // 提交后的草稿归正式会话；创建期间后来输入的内容仍留在新会话草稿里。
  drafts.set(id, text); savedDrafts.set(id, { text, epoch: ++draftEpoch });
  clearDraft(NEW_SESSION_ID, text);
  await flushDraft(NEW_SESSION_ID);
  const pending = pendingMessage(NEW_SESSION_ID);
  if (pending) { setPendingMessage(id, pending); setPendingMessage(NEW_SESSION_ID); setSessionFeedback(NEW_SESSION_ID, ''); }
  if (activeId === NEW_SESSION_ID) await selectSession(id);
  return id;
}
export async function selectSession(id: string) {
  activeId = id; selection++; publish();
  await refresh(true);
  // 切换发生在另一个会话的快照请求中时，等待新的会话请求。
  if (activeId === id && data?.active?.id !== id) await refreshTask;
}
export async function act<T = void>(action: string, payload: Record<string, unknown> = {}): Promise<T> {
  const result = await request<T>(action, payload);
  const current = refresh(); await current;
  if (refreshTask && refreshTask !== current) await refreshTask;
  return result;
}
// 对同一会话的同一操作共用请求，两个入口也不会重复发送。
export function once<T>(key: string, run: () => Promise<T>): Promise<T> {
  const current = pendingActions.get(key);
  if (current) return current as Promise<T>;
  const task = run().finally(() => { pendingActions.delete(key); publish(); });
  pendingActions.set(key, task); publish(); return task;
}
export function actionPending(key: string) { return pendingActions.has(key); }
export function sessionFeedback(id: string) { return feedback.get(id) || ''; }
export function setSessionFeedback(id: string, text: string) { feedback.set(id, text); publish(); }
export function pendingMessage(id: string) { return submitted.get(id); }
export function setPendingMessage(id: string, item?: { text: string; failed: boolean }) {
  if (item) submitted.set(id, item); else submitted.delete(id); publish();
}
export function announce(text: string) {
  announcement = text; publish(); clearTimeout(announcementTimer);
  announcementTimer = setTimeout(() => { announcement = ''; publish(); }, 3000);
}
export function setDraft(id: string, text: string) {
  drafts.set(id, text); if (id === NEW_SESSION_ID) cacheDraft(text); publish();
  clearTimeout(draftTimers.get(id));
  draftTimers.set(id, setTimeout(() => { void flushDraft(id); }, 350));
}
export function flushDraft(id: string): Promise<void> {
  clearTimeout(draftTimers.get(id)); draftTimers.delete(id);
  const previous = draftWrites.get(id) || Promise.resolve();
  const task = previous.then(async () => {
    const text = drafts.get(id);
    if (text === undefined || savedDrafts.get(id)?.text === text) return;
    await request('draft', { sessionId: id, text });
    if (drafts.get(id) === text) {
      savedDrafts.set(id, { text, epoch: ++draftEpoch });
      if (id === NEW_SESSION_ID) cacheDraft();
    }
  }).catch(reason => { error = String(reason); publish(); }).finally(() => {
    if (draftWrites.get(id) === task) draftWrites.delete(id);
  });
  draftWrites.set(id, task); return task;
}
export function clearDraft(id: string, submitted: string) {
  const current = drafts.get(id) ?? (id === NEW_SESSION_ID ? data?.newSessionDraft : data?.sessions.find(s => s.id === id)?.draft) ?? '';
  if (current.trim() && current.trim() !== submitted.trim()) return;
  clearTimeout(draftTimers.get(id)); draftTimers.delete(id);
  drafts.set(id, '');
  if (id === NEW_SESSION_ID) { cacheDraft(''); savedDrafts.delete(id); }
  else savedDrafts.set(id, { text: '', epoch: ++draftEpoch });
}
export const platform = {
  openPage: () => bridge.openPage(), closePage: () => bridge.closePage(),
  keyboard: (element: HTMLTextAreaElement) => bridge.keyboard(element),
  keyboardBounds: (element: HTMLTextAreaElement) => bridge.keyboardBounds?.(element) || null,
  hideKeyboard: (element: HTMLTextAreaElement) => bridge.hideKeyboard?.(element),
  external: (url: string) => bridge.external(url),
  checkInstaller: () => {
    if (!bridge.installUpdate) throw new Error('请在 Steam Deck 的 Decky 中安装更新。');
    bridge.checkInstaller?.();
  },
  installUpdate: async (update: PreparedUpdate) => {
    if (!bridge.installUpdate) throw new Error('请在 Steam Deck 的 Decky 中安装更新。');
    await bridge.installUpdate(update);
  },
};

export function useAgent() {
  useSyncExternalStore(callback => { listeners.add(callback); return () => { listeners.delete(callback); }; }, () => revision);
  useEffect(() => { void refresh(); }, []);
  const provider = data?.providers?.find(p => p.default);
  const session: Session | undefined = activeId === NEW_SESSION_ID && data ? {
    id: NEW_SESSION_ID, name: '新会话', cwd: data.preferences.defaultCwd,
    status: 'idle', archived: false, pending: [], updated: 0,
    draft: data.newSessionDraft || '', provider: provider?.id, model: provider?.model, thinking: provider?.thinking, ...data.newSessionModel,
  } : data?.sessions.find(s => s.id === activeId);
  return { data, session, error, activeId, announcement, draft: session ? drafts.get(session.id) ?? session.draft ?? '' : '' };
}


export function installPlayerPlugin(ticket: string): Promise<void> {
  return once('player-plugin:' + ticket, async () => {
    platform.checkInstaller();
    const prepared = await request<PreparedUpdate>('player_plugin_claim', { ticket });
    try {
      await platform.installUpdate(prepared);
      announce('已打开 Decky 原生安装确认，完成后请核对插件版本。');
    } catch (error) {
      await request('player_plugin_failed', { ticket, error: String(error) });
      throw error;
    } finally { await refresh(); }
  });
}
