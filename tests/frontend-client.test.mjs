import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';

// 直接运行实际客户端代码，仅替换不参与请求逻辑的 React 订阅钩子。
async function client() {
  const source = await readFile(new URL('../src/client.ts', import.meta.url), 'utf8');
  const code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText
    .replace(/import .*? from 'react';/, 'const useEffect = () => {}; const useSyncExternalStore = () => {};');
  return import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}#${Math.random()}`);
}
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(predicate) {
  for (let i = 0; i < 100; i++) { if (predicate()) return; await wait(10); }
  assert.fail('等待客户端状态超时');
}
function bridge(delay = 15) {
  let callback;
  let concurrent = 0;
  const stats = { calls: [], maxConcurrent: 0 };
  const sessions = ['a', 'b'].map(id => ({ id, name: id, status: 'idle', draft: '', pending: [] }));
  return {
    stats,
    sessions,
    emit() { callback({ type: 'changed' }); },
    listen(fn) { callback = fn; return () => {}; },
    async request(action, payload) {
      concurrent++; stats.maxConcurrent = Math.max(stats.maxConcurrent, concurrent);
      stats.calls.push({ action, ...payload });
      const snapshot = { sessions: structuredClone(sessions), newSessionDraft: stats.newDraft || '', active: payload.sessionId ? { id: payload.sessionId, messages: [] } : null, preferences: {} };
      await wait(delay); concurrent--;
      if (action === 'create_session') { const id = 'created'; sessions.push({ id, name: '新会话', status: 'idle', draft: payload.text || '', pending: [] }); return { id }; }
      if (action === 'draft' && payload.sessionId === '__new__') { stats.newDraft = payload.text; return; }
      if (action === 'draft') { sessions.find(s => s.id === payload.sessionId).draft = payload.text; return; }
      return snapshot;
    },
  };
}

test('连续事件仍持续刷新，慢快照不会并发堆积或一直被丢弃', async () => {
  const c = await client(); const b = bridge(180); const dispose = c.configureBridge(b);
  try {
    await c.refresh(); await until(() => c.useAgent().data?.active?.id === 'a');
    b.stats.calls.length = 0;
    for (let i = 0; i < 10; i++) { b.emit(); await wait(70); }
    assert.ok(b.stats.calls.length >= 3, `持续事件期间只刷新 ${b.stats.calls.length} 次`);
    assert.equal(b.stats.maxConcurrent, 1);
    assert.equal(c.useAgent().session.id, 'a');
  } finally { dispose(); await wait(450); }
});

test('快照在途时切换会话，旧会话结果不能覆盖新选择', async () => {
  const c = await client(); const b = bridge(80); const dispose = c.configureBridge(b);
  try {
    await c.refresh(); await until(() => c.useAgent().data?.active?.id === 'a');
    const old = c.refresh();
    const change = c.selectSession('b');
    assert.equal(c.useAgent().session.id, 'b');
    await Promise.all([old, change]);
    assert.equal(c.useAgent().data.active.id, 'b');
    assert.equal(b.stats.maxConcurrent, 1);
  } finally { dispose(); }
});

test('重复入口共用一次请求，不同会话不互相阻塞，失败后可以重试', async () => {
  const c = await client(); let calls = 0;
  const run = async () => { calls++; await wait(30); return 'ok'; };
  const first = c.once('send:a', run); const duplicate = c.once('send:a', run);
  assert.equal(first, duplicate); assert.equal(c.actionPending('send:a'), true);
  await c.once('send:b', run); await first;
  assert.equal(calls, 2); assert.equal(c.actionPending('send:a'), false);
  await assert.rejects(c.once('send:a', async () => { throw new Error('offline'); }));
  assert.equal(await c.once('send:a', run), 'ok');
});

test('草稿保存不闪空，发送回执保留后来输入，语音等后端更新仍能接管', async () => {
  const c = await client(); const b = bridge(); const dispose = c.configureBridge(b);
  try {
    await c.refresh(); await until(() => c.useAgent().data?.active?.id === 'a');
    c.setDraft('a', '原消息'); await c.flushDraft('a');
    assert.equal(c.useAgent().draft, '原消息');
    await c.refresh(); assert.equal(c.useAgent().draft, '原消息');
    c.setDraft('a', '后来输入的新草稿'); await c.flushDraft('a'); await c.refresh();
    c.clearDraft('a', '原消息');
    assert.equal(c.useAgent().draft, '后来输入的新草稿');
    b.sessions[0].draft = '语音回填'; await c.refresh();
    assert.equal(c.useAgent().draft, '语音回填');
  } finally { dispose(); }
});


test('打开新会话无请求，草稿切走后恢复，快照不会选回历史会话', async () => {
  const c = await client(); const b = bridge(); const dispose = c.configureBridge(b);
  try {
    await c.refresh(); await until(() => c.useAgent().data?.active?.id === 'a');
    const count = b.stats.calls.length;
    c.openNewSession();
    assert.equal(b.stats.calls.length, count);
    assert.equal(c.useAgent().session.id, c.NEW_SESSION_ID);
    c.setDraft(c.NEW_SESSION_ID, '先写下来'); await c.flushDraft(c.NEW_SESSION_ID);
    await c.selectSession('b'); c.openNewSession(); await c.refresh(true);
    assert.equal(c.useAgent().draft, '先写下来');
    assert.equal(c.useAgent().data.sessions.length, 2);
    assert.equal(b.stats.calls.some(x => x.action === 'open_session' && x.sessionId === c.NEW_SESSION_ID), false);
    assert.equal(b.stats.calls.some(x => x.action === 'create_session'), false);
  } finally { dispose(); }
});

test('首次提交才创建，创建期间新输入保留，切换选择不被抢走', async () => {
  const c = await client(); const b = bridge(40); const dispose = c.configureBridge(b);
  try {
    await c.refresh(); await until(() => c.useAgent().data?.active?.id === 'a');
    c.openNewSession(); c.setDraft(c.NEW_SESSION_ID, '第一条');
    const creation = c.materializeSession('第一条');
    c.setDraft(c.NEW_SESSION_ID, '下一条草稿');
    await c.selectSession('b'); const id = await creation;
    assert.equal(c.useAgent().session.id, 'b');
    assert.equal(b.sessions.find(s => s.id === id).draft, '第一条');
    c.openNewSession(); await c.refresh();
    assert.equal(c.useAgent().draft, '下一条草稿');
    assert.equal(b.stats.calls.filter(x => x.action === 'create_session').length, 1);
  } finally { dispose(); }
});

test('新会话草稿即时缓存，前端重新加载后恢复，创建失败可重试', async () => {
  const values = new Map();
  globalThis.localStorage = { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) };
  let dispose;
  try {
    let c = await client(); let b = bridge(); dispose = c.configureBridge(b);
    await c.refresh(); c.openNewSession(); c.setDraft(c.NEW_SESSION_ID, '退出前未发送');
    assert.equal(values.get('deck-agent-new-draft-v1'), '退出前未发送');
    const unsaved = values.get('deck-agent-new-draft-v1');
    dispose(); dispose = undefined; await wait(40); values.set('deck-agent-new-draft-v1', unsaved);
    c = await client(); b = bridge(); dispose = c.configureBridge(b);
    await c.refresh(); assert.equal(c.useAgent().draft, '退出前未发送');
    const original = b.request;
    b.request = async (action, payload) => { if (action === 'create_session') throw new Error('offline'); return original(action, payload); };
    await assert.rejects(c.materializeSession('退出前未发送'), /offline/);
    assert.equal(c.useAgent().draft, '退出前未发送');
    b.request = original;
    const id = await c.materializeSession('退出前未发送');
    assert.equal(c.useAgent().session.id, id);
    c.openNewSession(); assert.equal(c.useAgent().draft, '');
  } finally { dispose?.(); delete globalThis.localStorage; }
});


test('本地缓存已同步后，重新打开仍从后端恢复未发送草稿', async () => {
  const c = await client(); const b = bridge(); b.stats.newDraft = '后端保存的未发送内容';
  const dispose = c.configureBridge(b);
  try {
    await c.refresh();
    assert.equal(c.useAgent().session.id, c.NEW_SESSION_ID);
    assert.equal(c.useAgent().draft, '后端保存的未发送内容');
  } finally { dispose(); }
});

test('更新交接只提交 Decky 原生确认请求，缺少接口时提示手动安装', async () => {
  const source = await readFile(new URL('../src/decky-updates.ts', import.meta.url), 'utf8');
  const code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
  const adapter = await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`);
  const previous = globalThis.DeckyBackend;
  const calls = [];
  try {
    delete globalThis.DeckyBackend;
    assert.throws(() => adapter.checkInstaller(), /手动|安装指引/);
    globalThis.DeckyBackend = { call: async (...args) => { calls.push(args); } };
    const update = { artifact: 'file:///home/deck/update.zip', version: '0.6.0', hash: 'a'.repeat(64) };
    await adapter.installUpdate(update);
    assert.deepEqual(calls, [['utilities/install_plugin', update.artifact, 'Deck Agent', '0.6.0', update.hash, 2]]);
    await assert.rejects(adapter.installUpdate({ ...update, artifact: 'https://example.com/update.zip' }), /无效/);
    assert.equal(calls.length, 1);
    await adapter.installUpdate({ ...update, name: 'Sample Plugin', installType: 0 });
    assert.deepEqual(calls[1], ['utilities/install_plugin', update.artifact, 'Sample Plugin', '0.6.0', update.hash, 0]);
  } finally { if (previous === undefined) delete globalThis.DeckyBackend; else globalThis.DeckyBackend = previous; }
});


test('第三方插件交接合并重复点击，原生接口失败后保留可重试请求', async () => {
  const c = await client(); const b = bridge(5); const original = b.request;
  const calls = []; let fail = true;
  b.request = async (action, payload) => {
    calls.push(action);
    if (action === 'player_plugin_claim') { await wait(10); return { artifact: 'file:///tmp/sample.zip', name: 'Sample', version: '1.0.0', hash: 'a'.repeat(64), installType: 0 }; }
    if (action === 'player_plugin_failed') return;
    return original(action, payload);
  };
  b.checkInstaller = () => {};
  b.installUpdate = async () => { if (fail) throw new Error('native unavailable'); };
  const dispose = c.configureBridge(b);
  try {
    const first = c.installPlayerPlugin('ticket'); const second = c.installPlayerPlugin('ticket');
    assert.equal(first, second);
    await assert.rejects(first, /native unavailable/);
    assert.equal(calls.filter(a => a === 'player_plugin_claim').length, 1);
    assert.equal(calls.filter(a => a === 'player_plugin_failed').length, 1);
    fail = false;
    await c.installPlayerPlugin('ticket');
    assert.equal(calls.filter(a => a === 'player_plugin_claim').length, 2);
  } finally { dispose(); }
});
