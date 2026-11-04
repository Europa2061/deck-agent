import { useEffect, useRef, useState } from 'react';
import { act, announce, once, platform, request } from '../client';
import type { Catalog, Model, Provider, PreparedUpdate, ProviderForm, Release, Snapshot, UpdateDownload } from '../types';
import { Focusable, GamepadButton, Tabs } from '@decky/ui';
import { Button, ErrorBox, Field, Loading, Modal, NativeControls, Select, Toggle } from './ui';

export function ProviderEditor({ provider, catalog, close }: { provider: Partial<Provider>; catalog?: Catalog; close: () => void }) {
  const [form, setForm] = useState<ProviderForm>({ id: provider.id || '', model: provider.model || '', key: '', thinking: provider.thinking || 'off', api: provider.api || 'openai-completions', ...provider });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [remove, setRemove] = useState(false);
  const [modelSearch, setModelSearch] = useState('');
  const [enabled, setEnabled] = useState(provider.enabledModels?.length ? provider.enabledModels : provider.model ? [provider.model] : []);
  const field = (key: keyof ProviderForm, value: unknown) => setForm(previous => ({ ...previous, [key]: value }));
  const [loadedCatalog, setLoadedCatalog] = useState(catalog);
  const [catalogError, setCatalogError] = useState('');
  const [retry, setRetry] = useState(0);
  const busyRef = useRef(false);
  useEffect(() => {
    if (catalog) return;
    let alive = true; setCatalogError('');
    void request<Catalog>('catalog', { refresh: true }).then(c => { if (alive) setLoadedCatalog(c); }).catch(e => { if (alive) setCatalogError(String(e)); });
    return () => { alive = false; };
  }, [catalog, retry]);
  const models = (loadedCatalog?.models || []).filter(m => m.provider === form.id);
  async function submit(test = false) {
    if (busyRef.current) return;
    busyRef.current = true; setError(''); setResult(''); setBusy(true);
    try {
      if (!form.id || !form.model || (!provider.configured && !form.key)) throw new Error('请填写供应商、API Key 和模型。');
      if (test) { await request('test_provider', { ...form }); setResult('连接成功'); }
      else { await act('save_provider', { ...form, enabledModels: enabled }); announce('供应商配置已保存'); close(); }
    } catch (reason) { setError((test ? '连接测试失败：' : '') + String(reason instanceof Error ? reason.message : reason)); }
    finally { busyRef.current = false; setBusy(false); }
  }
  const thinking = models.find(m => m.id === form.model)?.reasoning || form.reasoning;
  if (!loadedCatalog) return <Modal title="读取供应商配置" close={close} actions={<Button onClick={close}>取消</Button>}>{catalogError ? <><ErrorBox text={catalogError} /><Button onClick={() => setRetry(v => v + 1)}>重新读取</Button></> : <Loading text="正在读取模型目录…" />}</Modal>;
  if (remove) return <Modal title="移除这个供应商？" close={() => setRemove(false)} actions={<><Button onClick={() => setRemove(false)}>取消</Button><Button variant="danger" disabled={busy} busyText="正在移除…" onClick={() => { setBusy(true); return once('remove_provider:' + provider.id, () => act('remove_provider', { id: provider.id })).then(() => { announce('供应商已移除'); close(); }).catch(e => { setError(String(e)); throw e; }).finally(() => setBusy(false)); }}>移除供应商</Button></>}><p>配置和密钥会被移除，会话历史保留。</p><ErrorBox text={error} /></Modal>;
  return <Modal title={(provider.configured ? '编辑 ' : '添加 ') + (provider.name || provider.id || '自定义供应商')} close={close}
    actions={<><Button disabled={busy} onClick={close}>取消</Button><Button variant="primary" loading={busy} busyText="正在处理配置…" onClick={() => submit()}>{busy ? '处理中…' : provider.configured ? '保存配置' : '添加供应商'}</Button></>}>
    <div className="da-form">
      {form.custom && <>{!provider.configured && <Field label="供应商 ID" value={form.id} onChange={v => field('id', v)} placeholder="custom-provider" />}
        <Field label="显示名称" value={form.name || ''} onChange={v => field('name', v)} placeholder="我的模型接口" />
        <Select label="接口协议" value={form.api || 'openai-completions'} onChange={v => field('api', v)} options={[
          { value: 'openai-completions', label: 'OpenAI Chat Completions' }, { value: 'openai-responses', label: 'OpenAI Responses' },
          { value: 'anthropic-messages', label: 'Anthropic Messages' }, { value: 'google-generative-ai', label: 'Google Generative AI' },
        ]} /></>}
      <Focusable flow-children="row" className="da-secret"><Field label="API Key" password={!showKey} value={form.key} placeholder={provider.configured ? '已配置，留空保留' : '输入 API Key'} onChange={v => field('key', v)} /><Button onClick={() => setShowKey(v => !v)}>{showKey ? '隐藏' : '显示'}</Button></Focusable>
      <Field label={form.custom ? '接口地址' : '接口地址（可选）'} value={form.baseUrl || ''} onChange={v => field('baseUrl', v)} placeholder="https://api.example.com/v1" />
      <section className="da-provider-models"><Focusable flow-children="row" className="da-row"><h3 className="da-grow">已选模型 · {enabled.length}</h3><span className="da-muted">聊天中只显示这些模型</span></Focusable>
        {enabled.map(id => <Focusable flow-children="row" className="da-enabled-model" key={id}><span className="da-grow"><strong>{models.find(m => m.id === id)?.name || id}</strong><small>{id}</small></span><Button variant={form.model === id ? 'selected' : 'ghost'} onClick={() => field('model', id)}>{form.model === id ? '默认' : '设为默认'}</Button><Button title={'移除模型 ' + id} onClick={() => { const next = enabled.filter(m => m !== id); setEnabled(next); if (form.model === id) field('model', next[0] || ''); }}>移除</Button></Focusable>)}
        {!enabled.length && <p className="da-muted">请添加至少一个可用模型。</p>}
        <Field label="添加模型" value={modelSearch} onChange={setModelSearch} placeholder="搜索模型名称，或输入模型 ID" />
        <Focusable flow-children="grid" className="da-model-add-list">{models.filter(m => !enabled.includes(m.id) && (m.id + ' ' + m.name).toLowerCase().includes(modelSearch.trim().toLowerCase())).slice(0, 8).map(m => <Button key={m.id} onClick={() => { setEnabled(v => [...v, m.id]); if (!form.model) field('model', m.id); setModelSearch(''); }}>＋ {m.name || m.id}</Button>)}</Focusable>
        {modelSearch.trim() && !enabled.includes(modelSearch.trim()) && !models.some(m => m.id === modelSearch.trim()) && <Button onClick={() => { const id = modelSearch.trim(); setEnabled(v => [...v, id]); if (!form.model) field('model', id); setModelSearch(''); }}>添加模型 ID：{modelSearch.trim()}</Button>}
      </section>
      <Select label="默认思考强度" disabled={!thinking} value={thinking ? form.thinking || 'off' : 'off'} options={['off', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max'].map(value => ({ value, label: ({ off: '关闭', minimal: '最低', low: '低', medium: '中', high: '高', xhigh: '更高', max: '最高' } as Record<string, string>)[value] }))} onChange={v => field('thinking', v)} />
      {form.custom && <label className="da-check"><input type="checkbox" checked={Boolean(form.reasoning)} onChange={e => field('reasoning', e.target.checked)} />此模型支持思考</label>}
      <ErrorBox text={error} />
      <Focusable flow-children="row" className="da-row"><Button loading={busy} busyText="正在测试连接…" title="发起一次简短的模型请求" onClick={() => submit(true)}>测试连接</Button><span className="da-success">{result}</span></Focusable>
      {provider.configured && <Button variant="danger" disabled={busy} onClick={() => setRemove(true)}>移除供应商</Button>}
    </div>
  </Modal>;
}

export function Settings({ data, openProvider, configureAgent, initialTab = 'providers' }: { initialTab?: string; data: Snapshot; openProvider: (p?: Provider) => void; configureAgent: () => void }) {
  const [tab, setTab] = useState(initialTab);
  const [error, setError] = useState('');
  const [cwd, setCwd] = useState(data.preferences.defaultCwd);
  const [info, setInfo] = useState<unknown>(null);
  async function save(payload: Record<string, unknown>) {
    setError('');
    try { await once('preferences:' + Object.keys(payload).sort().join(','), () => act('preferences', payload)); announce('设置已保存'); }
    catch (e) { setError(String(e)); throw e; }
  }
  const tabs = [['providers', '供应商与模型'], ['voice', '语音输入'], ['general', '通用'], ['about', '关于与更新']];

  const content = <>    {tab === 'about' ? <Updates version={data.version} build={data.build} repo={data.preferences.releaseRepo} auto={data.preferences.updateAuto} active={data.sessions.some(s => ['running', 'waiting'].includes(s.status))} /> : <div className="da-page-content"><ErrorBox text={error} />
      {tab === 'providers' ? data.providers.length ? <div className="da-provider-list">{data.providers.map(p => <div key={p.id} className="da-provider-card">
        <span className="da-provider-letter" aria-hidden="true">{(p.name || p.id)[0].toUpperCase()}</span>
        <div className="da-provider-info"><div className="da-provider-title"><h3>{p.name || p.id}</h3>{p.default && <span className="da-badge">默认</span>}</div><p>{p.enabledModels?.length || 1} 个可用模型</p><p className="da-provider-model" title={p.model}>{p.model || '未设置默认模型'}</p></div>
        <Focusable flow-children="row" className="da-provider-actions">{!p.default && <Button successText="已设为默认" onClick={() => act('default_provider', { id: p.id }).then(() => announce('默认供应商已切换'))}>设为默认</Button>}<Button title={'编辑 ' + p.id} onClick={() => openProvider(p)}>编辑</Button></Focusable>
      </div>)}</div> : <div className="da-empty"><span className="da-empty-mark">π</span><h2>还没有供应商</h2><Button variant="primary" onClick={() => openProvider()}>＋ 新增供应商</Button></div>
      : tab === 'voice' ? <VoiceSettings data={data} error={setError} save={save} />
        : <div className="da-general"><Focusable flow-children="row" className="da-setting"><div className="da-grow"><Field label="默认工作目录" value={cwd} onChange={setCwd} /></div><Button busyText="保存中…" successText="已保存" onClick={() => save({ defaultCwd: cwd })}>保存</Button></Focusable>
          <TitleModelSettings value={data.preferences.titleModel} save={save} />
          <Toggle label="后台任务通知" value={data.preferences.notifications} description="任务结束或等待确认时通知你" onChange={notifications => save({ notifications })} />
          <Focusable flow-children="row" className="da-setting"><h3>Pi 配置与扩展</h3><Button onClick={configureAgent}>让 Agent 配置</Button></Focusable>
          <Focusable flow-children="row" className="da-setting"><h3>运行环境</h3><span className={data.runtime.ready ? 'da-success' : 'da-error'}>{`Pi ${data.runtime.piVersion} · ${data.runtime.ready ? '已就绪' : data.runtime.error || '未就绪'}`}</span></Focusable>
          <Focusable flow-children="row" className="da-setting"><h3>诊断信息</h3><Button busyText="正在读取…" onClick={() => request('diagnostics').then(setInfo)}>查看</Button></Focusable>
        </div>}
    </div>}{info !== null && <Modal title="诊断信息" close={() => setInfo(null)} actions={<Button onClick={() => setInfo(null)}>完成</Button>}><pre>{JSON.stringify(info, null, 2)}</pre></Modal>}</>;
  return <NativeControls className="da-settings" onButtonDown={event => {
    const b = event.detail.button; if (b !== GamepadButton.BUMPER_LEFT && b !== GamepadButton.BUMPER_RIGHT) return;
    const doc = (event.currentTarget as HTMLElement).ownerDocument;
    if (doc.querySelector('[aria-modal="true"]') || ['INPUT', 'TEXTAREA', 'SELECT'].includes(doc.activeElement?.tagName || '')) return;
    event.stopPropagation(); const index = tabs.findIndex(([id]) => id === tab); setTab(tabs[(index + (b === GamepadButton.BUMPER_LEFT ? -1 : 1) + tabs.length) % tabs.length][0]);
  }} actionDescriptionMap={{ [GamepadButton.BUMPER_LEFT]: '上个分类', [GamepadButton.BUMPER_RIGHT]: '下个分类' }}><Tabs activeTab={tab} onShowTab={setTab} tabs={tabs.map(([id, title]) => ({ id, title, content: id === tab ? <>{id === 'providers' && data.providers.length > 0 && <div className="da-settings-actions"><Button variant="primary" onClick={() => openProvider()}>新增供应商</Button></div>}{content}</> : null }))} /></NativeControls>;
}

function TitleModelSettings({ value, save }: { value: Snapshot['preferences']['titleModel']; save: (p: Record<string, unknown>) => Promise<void> }) {
  const [models, setModels] = useState<Model[]>([]);
  const [error, setError] = useState('');
  useEffect(() => { let alive = true; void request<{ models: Model[] }>('configured_models').then(r => { if (alive) setModels(r.models); }).catch(e => { if (alive) setError(String(e)); }); return () => { alive = false; }; }, []);
  const selected = value ? value.provider + '\n' + value.model : '';
  return <div className="da-form"><Select label="会话自动命名模型" value={selected} options={[{ value: '', label: '跟随会话模型（默认）' }, ...models.map(m => ({ value: m.provider + '\n' + m.id, label: m.provider + ' · ' + (m.name || m.id) }))]} onChange={v => { const [provider, model] = v.split('\n'); return save({ titleModel: v ? { provider, model } : null }); }} /><p className="da-muted">首次发送后自动生成简短标题。可单独选一个轻量模型，手动改名后不会覆盖。</p><ErrorBox text={error} /></div>;
}

function VoiceSettings({ data, error, save }: { data: Snapshot; error: (text: string) => void; save: (p: Record<string, unknown>) => Promise<void> }) {
  const [remove, setRemove] = useState(false);
  const [pending, setPending] = useState(false);
  const pendingRef = useRef(false);
  const voice = data.voice;
  const active = ['recording', 'transcribing', 'downloading'].includes(voice.status);
  const locked = active || pending;
  const progress = voice.total ? Math.min(100, Math.round(100 * voice.downloaded / voice.total)) : 0;
  const run = (action: string, payload = {}) => once('voice:' + action, () => act(action, payload)).catch(e => { error(String(e)); throw e; });
  const selectOrDownload = async (modelId: string, download = false) => {
    if (pendingRef.current || active) return;
    pendingRef.current = true; setPending(true);
    try {
      if (modelId !== voice.modelId) await act('voice_select', { modelId });
      if (download) await act('voice_download');
    } catch (e) { error(String(e)); }
    finally { pendingRef.current = false; setPending(false); }
  };
  return <div className="da-voice-settings"><section className="da-voice-section" aria-labelledby="da-voice-models-title"><div className="da-voice-section-head"><h2 id="da-voice-models-title">识别模型</h2><p className="da-muted">中文日常输入优先 SenseVoice；想减少资源占用可选 Whisper Base。默认使用 2 个 CPU 线程，速度随游戏负载变化。</p></div>
    <div className="da-voice-models">{voice.models?.map(m => {
      const selected = voice.modelId === m.id;
      const downloading = selected && voice.status === 'downloading';
      const status = selected ? ({ ready: '已下载', downloading: '下载中', paused: '已暂停', missing: '未下载', error: '需要处理', recording: '正在录音', transcribing: '正在转写' } as Record<string, string>)[voice.status] : m.installed ? '已下载' : '未下载';
      return <div key={m.id} className={`da-voice-model ${selected ? 'selected' : ''}`}>
        <div className="da-voice-model-top"><strong>{m.name}</strong><Focusable flow-children="row" className="da-voice-model-actions">
          <Button title={`${selected ? '已选择' : '选择'} ${m.name}`} variant={selected ? 'selected' : ''} pressed={selected} disabled={locked} busyText="正在选择…" onClick={() => selectOrDownload(m.id)}>{selected ? '已选择' : '选择'}</Button>
          {selected && m.installed ? <Button title={`删除 ${m.name}`} variant="danger" disabled={locked} onClick={() => setRemove(true)}>删除</Button> : !m.installed && !downloading && <Button title={`${selected && voice.status === 'paused' ? '继续下载' : '下载'} ${m.name}`} variant="primary" disabled={locked} busyText="准备下载…" onClick={() => selectOrDownload(m.id, true)}>{selected && voice.status === 'paused' ? '继续下载' : '下载'}</Button>}
        </Focusable></div>
        <span className="da-voice-model-description">{m.description}</span>
        <div className="da-voice-model-meta"><span>大小 {Math.round(m.downloadBytes / 1048576)} MB</span><span className="da-voice-model-tag">本地识别</span><span className={`da-voice-model-tag ${m.installed ? 'installed' : ''}`}>{status}</span></div>
        {downloading && <div className="da-voice-download-progress"><progress value={progress} max={100} aria-label={`${m.name} 下载进度`} /><Focusable flow-children="row" className="da-row"><span className="da-muted da-grow">{progress}%</span><Button disabled={pending} onClick={() => run('voice_pause')}>暂停</Button><Button disabled={pending} onClick={() => run('voice_cancel_download')}>取消下载</Button></Focusable></div>}
        {selected && <ErrorBox text={voice.error} />}
      </div>;
    })}</div>
    {!voice.engineReady && <ErrorBox text="当前安装包尚未包含 Linux 语音引擎。" />}
    </section><section className="da-voice-section" aria-labelledby="da-voice-download-title"><div className="da-voice-section-head"><h2 id="da-voice-download-title">下载设置</h2></div>
    <Select label="模型下载来源" disabled={locked} value={voice.downloadSource || 'huggingface'} options={[{ value: 'huggingface', label: 'Hugging Face 官方' }, { value: 'hf-mirror', label: 'hf-mirror 镜像站' }]} onChange={source => run('voice_select', { source })} />
    </section><section className="da-voice-section" aria-labelledby="da-voice-input-title"><div className="da-voice-section-head"><h2 id="da-voice-input-title">输入设置</h2><p className="da-muted">设置麦克风和识别语言。</p></div>
    <div className="da-voice-input-fields"><MicrophoneSettings value={data.preferences.inputDevice} save={save} /><Select label="识别语言" disabled={voice.modelId === 'paraformer-zh-yue-en-int8'} value={data.preferences.language} options={[{ value: 'auto', label: '自动 / 中英混说' }, { value: 'zh', label: '中文' }, { value: 'en', label: 'English' }]} onChange={language => save({ language })} /></div>
    {voice.modelId === 'paraformer-zh-yue-en-int8' && <p className="da-muted">Paraformer 使用模型自身的中英粤识别，不受上方语言设置影响。</p>}
    </section>{remove && <Modal title="删除当前语音模型？" close={() => setRemove(false)} actions={<><Button onClick={() => setRemove(false)}>取消</Button><Button variant="danger" busyText="正在删除…" onClick={async () => { await run('voice_delete'); setRemove(false); announce('语音模型已删除'); }}>删除模型</Button></>}><p>只删除当前选择的模型，其他已下载模型保留。</p></Modal>}</div>;
}

function MicrophoneSettings({ value, save }: { value: string; save: (p: Record<string, unknown>) => Promise<void> }) {
  const [devices, setDevices] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const doc = root.current?.ownerDocument;
    const win = doc?.defaultView;
    let alive = true;
    let inflight = false;
    const load = async () => {
      if (inflight || !alive || doc?.visibilityState === 'hidden') return;
      inflight = true;
      try {
        const items = await request<{ id: string; name: string }[]>('voice_devices');
        if (alive) { setDevices(previous => JSON.stringify(previous) === JSON.stringify(items) ? previous : items); setError(''); }
      } catch (reason) {
        if (alive) setError(String(reason instanceof Error ? reason.message : reason));
      } finally { inflight = false; if (alive) setLoading(false); }
    };
    void load();
    const timer = setInterval(() => { void load(); }, 5000);
    doc?.addEventListener('visibilitychange', load);
    win?.addEventListener('focus', load);
    win?.navigator.mediaDevices?.addEventListener('devicechange', load);
    return () => {
      alive = false; clearInterval(timer);
      doc?.removeEventListener('visibilitychange', load);
      win?.removeEventListener('focus', load);
      win?.navigator.mediaDevices?.removeEventListener('devicechange', load);
    };
  }, []);
  const selected = !value || value === '@DEFAULT_AUDIO_SOURCE@' ? 'auto' : value;
  const unavailable = selected !== 'auto' && !devices.some(device => device.id === selected);
  return <div ref={root} className="da-microphone-settings"><Select label="麦克风" value={selected} options={[
    { value: 'auto', label: '系统默认' },
    ...devices.map(device => ({ value: device.id, label: device.name })),
    ...(unavailable ? [{ value: selected, label: loading ? '正在查找已选麦克风…' : '已选麦克风不可用' }] : []),
  ]} onChange={inputDevice => save({ inputDevice })} />
    <p className="da-muted" role="status">{loading ? '正在检测麦克风…' : '自动检测已连接的麦克风'}</p>
    {error ? <p className="da-muted">{error} 可继续使用系统默认麦克风。</p> : unavailable && !loading ? <p className="da-muted">已选麦克风未连接，请重新连接或选择其他设备。</p> : null}
  </div>;
}

export function ProviderPicker({ data, close, choose }: { data: Snapshot; close: () => void; choose: (p: Partial<Provider>, catalog: Catalog) => void }) {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  useEffect(() => { let alive = true; void request<Catalog>('catalog', { refresh: true }).then(c => { if (alive) setCatalog(c); }).catch(e => { if (alive) setError(String(e)); }); return () => { alive = false; }; }, []);
  const items = catalog?.providers.filter(p => !data.providers.some(configured => configured.id === p.id) && (p.id + p.name).toLowerCase().includes(search.toLowerCase()));
  return <Modal title="新增供应商" close={close}><div className="da-form"><Field label="搜索供应商" value={search} onChange={setSearch} /><ErrorBox text={error} />{!catalog && !error && <p>正在读取 Pi 模型目录…</p>}
    <div className="da-provider-choices">{items?.map(p => <Button key={p.id} onClick={() => { const model = catalog!.models.find(m => m.provider === p.id); choose({ ...p, model: model?.id || '', api: model?.api }, catalog!); }}>{p.name || p.id} ›</Button>)}</div>
    <Button variant="primary" onClick={() => choose({ custom: true, name: '', id: '' }, catalog || { providers: [], models: [] })}>＋ 自定义兼容接口</Button></div></Modal>;
}

function Updates({ version, build, repo: saved, auto, active }: { version: string; build: Snapshot['build']; repo: string; auto: boolean; active: boolean }) {
  const repo = saved; const [release, setRelease] = useState<Release | null>(null); const [error, setError] = useState(''); const [busy, setBusy] = useState(false); const [install, setInstall] = useState(false);
  const check = async () => { setError(''); setBusy(true); try { setRelease(await request<Release>('updates')); } catch (e) { setError(String(e)); } finally { setBusy(false); } };
  const [download, setDownload] = useState<UpdateDownload>({ status: 'idle', downloaded: 0, total: 0 });
  const [message, setMessage] = useState('');
  const [working, setWorking] = useState(false);
  const workingRef = useRef(false);
  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try { const state = await request<UpdateDownload>('update_status'); if (alive) setDownload(state); }
      catch (e) { if (alive) setError(String(e)); }
      finally { if (alive) timer = setTimeout(() => { void poll(); }, 1000); }
    };
    void poll();
    return () => { alive = false; clearTimeout(timer); };
  }, []);
  const downloading = ['downloading', 'verifying', 'cancelling'].includes(download.status);
  const runUpdate = async (installNow = false) => {
    if (workingRef.current) return;
    workingRef.current = true; setWorking(true); setError(''); setMessage('');
    try {
      if (installNow) {
        platform.checkInstaller();
        const prepared = await request<PreparedUpdate>('update_prepare');
        await platform.installUpdate(prepared);
        setMessage('已打开 Decky 安装确认。确认后会重载插件；取消后可再次点击安装。');
      } else if (release) {
        setDownload(await request<UpdateDownload>('update_download', { version: release.latest }));
      }
    } catch (e) { setError(String(e instanceof Error ? e.message : e)); }
    finally { workingRef.current = false; setWorking(false); }
  };
  useEffect(() => { if (auto && saved) void check(); }, []);
  return <><header className="da-chat-head"><h2>关于与更新</h2></header><div className="da-page-content da-form da-updates"><div className="da-update-panel"><div className="da-update-info"><span className="da-muted">当前版本</span><h1>{version}</h1><dl className="da-build-details"><div><dt>构建</dt><dd>{build.id}</dd></div></dl><p>{release ? release.available ? `发现新版本 ${release.latest}` : '你正在使用最新版本' : saved ? 'GitHub Releases' : '更新暂不可用'}</p></div><div className="da-update-actions"><Button disabled={!repo || downloading || working} loading={busy} busyText="检查中…" variant="primary" onClick={() => check()}>{busy ? '检查中…' : '检查更新'}</Button>{release?.available && <><Button disabled={busy || working || downloading || !release.zipUrl || !release.checksumUrl} onClick={() => runUpdate()}>下载更新</Button><Button onClick={() => setInstall(true)}>手动安装</Button></>}</div></div>
    {download.status !== 'idle' && <div className="da-model-card" aria-live="polite"><h3>{download.version} 更新安装包</h3><p>{({ downloading: '正在下载…', verifying: '正在校验安装包…', cancelling: '正在取消…', cancelled: '下载已取消，可以重试。', ready: '安装包已下载，SHA-256 和版本校验通过。', error: '下载失败，请重试。' } as Record<string, string>)[download.status]}</p>{downloading && <><progress aria-label="更新下载进度" max={download.total || undefined} value={download.total ? download.downloaded : undefined} /><p>{(download.downloaded / 1048576).toFixed(1)} MB{download.total ? ` / ${(download.total / 1048576).toFixed(1)} MB` : ''}</p><Button disabled={download.status === 'cancelling'} onClick={async () => { try { setDownload(await request<UpdateDownload>('update_cancel')); } catch (e) { setError(String(e)); } }}>取消下载</Button></>}{download.status === 'ready' && <><p>安装会重载插件，请先结束任务和录音。请勿在安装确认期间启动新任务。</p><Button disabled={active || working} loading={working} busyText="准备安装…" onClick={() => runUpdate(true)}>安装已下载的更新</Button>{active && <ErrorBox text="当前有任务正在执行或等待输入，请结束后再安装。" />}</>}<ErrorBox text={download.error || ''} /></div>}
    {message && <p role="status">{message}</p>}
    <ErrorBox text={error} /><Toggle label="自动检查更新" value={auto} onChange={updateAuto => act('preferences', { updateAuto })} />
    {release && <><pre className="da-release-notes">{release.notes}</pre><Button onClick={() => platform.external(release.pageUrl)}>查看发布页</Button></>}
    {install && release && <Modal title="通过 Decky 手动安装" close={() => setInstall(false)} actions={<Button onClick={() => setInstall(false)}>完成</Button>}><div className="da-form">{active && <ErrorBox text="当前有任务正在执行或等待输入，安装会重载插件，请先处理任务。" />}<ol><li>从发布页取得对应版本的 deck-agent-X.Y.Z.zip。已下载的包保存在 Decky 数据目录的 deck-agent/updates/ 中。</li><li>进入 Decky 设置 → 开发者。</li><li>选择下载好的本地 ZIP 文件。</li><li>确认安装并重新打开 Deck Agent。</li></ol><Button onClick={() => platform.external(release.pageUrl)}>打开发布页</Button></div></Modal>}
  </div></>;
}
