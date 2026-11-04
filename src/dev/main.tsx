import { createRoot } from 'react-dom/client';
import { App } from '../App';
import { SteamPage } from '../components/SteamPage';
import { configureBridge } from '../client';
import type { Notice } from '../types';
import { createDemoBridge } from './demo';
const params = new URLSearchParams(location.search);
const demo = params.has('demo') ? createDemoBridge() : null;

const token = new URLSearchParams(location.hash.slice(1)).get('token') || sessionStorage.getItem('deck-agent-dev-token') || '';
if (token) { sessionStorage.setItem('deck-agent-dev-token', token); history.replaceState(null, '', location.pathname + location.search); }
let sequence = 0;
const bridge = demo || {
  async request<T>(action: string, payload = {}) {
    const response = await fetch('/api/request', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Deck-Agent-Token': token }, body: JSON.stringify({ action, payload }) });
    if (!response.ok) throw new Error('开发后端连接失败，请检查启动时给出的令牌链接。');
    const result = await response.json();
    if (!result.ok) throw new Error(result.error);
    return result.value as T;
  },
  listen(callback) {
    const timer = setInterval(() => { void fetch('/api/events?after=' + sequence, { headers: { 'X-Deck-Agent-Token': token } }).then(r => r.json()).then((events: { sequence: number; event: Notice }[]) => { events.forEach(item => { sequence = item.sequence; callback(item.event); }); }).catch(() => {}); }, 250);
    return () => clearInterval(timer);
  },
  openPage() { location.search = ''; }, closePage() { history.back(); },
  keyboard(element) { element.focus(); },
  notify(event) { console.info(event.title, event.message); },
  external(url) { window.open(url, '_blank', 'noopener,noreferrer'); },
};
configureBridge({ ...bridge, closePage: () => renderPreview(true), openPage: () => renderPreview(false, false) });
const root = createRoot(document.getElementById('root')!);
function renderPreview(closed = false, compact = params.has('compact')) {
  const app = <App compact={compact} />;
  root.render(closed ? <div style={{ height: '100dvh', background: '#23262e', color: '#dcdedf', display: 'grid', placeContent: 'center', gap: 16, textAlign: 'center' }}><h2>已返回 Steam（浏览器演示）</h2><p>正式插件会返回 Steam 库，后台任务继续运行。</p><button onClick={() => renderPreview(false)}>重新打开 Deck Agent</button></div> : ((params.has('steam') || demo) ? <>
  <div style={{ position: 'fixed', inset: '0 0 auto', height: 'var(--basicui-header-height, 40px)', background: '#0e141b', color: 'white', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', padding: '0 24px' }}>{demo ? <><span style={{ marginRight: 'auto', fontSize: 12 }}>交互预览 · 演示数据，不调用真实模型</span><button onClick={() => { demo.reset(); location.reload(); }} style={{ padding: '4px 10px', color: '#d8e8f4', background: '#203447', border: '1px solid #3b536b', borderRadius: 6, cursor: 'pointer' }}>重置演示</button></> : 'Steam · 状态栏'}</div>
  <SteamPage>{app}</SteamPage>
  <div style={{ position: 'fixed', inset: 'auto 0 0', height: 'var(--basicui-footer-height, 48px)', background: '#0e141b', color: 'white', display: 'flex', alignItems: 'center', padding: '0 24px' }}>STEAM 菜单　　A 选择　　B 返回</div>
</> : <div style={{ width: '100vw', height: '100dvh' }}>{app}</div>));
}
renderPreview();
