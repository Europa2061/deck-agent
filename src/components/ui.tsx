import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { DialogButton, DropdownItem, Focusable, ModalRoot, TextField, ToggleField, showModal, type FooterLegendProps, type FocusableProps } from '@decky/ui';
import { styles } from '../styles';

const NativeContext = createContext(false);
export function CustomControls({ children }: { children: ReactNode }) { return <NativeContext.Provider value={false}>{children}</NativeContext.Provider>; }
export function NativeControls({ children, className = '', ...props }: FocusableProps) {
  return <NativeContext.Provider value={true}><Focusable {...props} flow-children="column" className={`da-native-controls ${className}`}>{children}</Focusable></NativeContext.Provider>;
}
export function Loading({ text = '正在加载…' }: { text?: string }) {
  return <div className="da-loading" role="status"><span className="da-spinner" aria-hidden="true" />{text}</div>;
}

type ButtonProps = FooterLegendProps & {
  children: ReactNode; onClick?: () => void | Promise<unknown>; variant?: string; disabled?: boolean;
  title?: string; className?: string; expanded?: boolean; popup?: boolean; pressed?: boolean; current?: boolean; loading?: boolean;
  busyText?: string; successText?: string;
};
export function Button({ children, onClick, variant = '', disabled = false, title, className = '', expanded, popup = true, pressed, current, loading = false, busyText = '处理中…', successText, ...navigation }: ButtonProps) {
  const native = useContext(NativeContext);
  const lock = useRef(false);
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState('');
  const [failure, setFailure] = useState('');
  const timeout = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(() => () => clearTimeout(timeout.current), []);
  const busy = loading || pending;
  const Component = DialogButton;
  const click = () => {
    if (lock.current || busy || disabled) return;
    setFailure(''); setResult(''); clearTimeout(timeout.current);
    try {
      const value = onClick?.();
      if (value && typeof value.then === 'function') {
        lock.current = true; setPending(true);
        void value.then(() => {
          if (successText) { setResult(successText); timeout.current = setTimeout(() => setResult(''), 2200); }
        }).catch(e => setFailure(String(e instanceof Error ? e.message : e))).finally(() => { lock.current = false; setPending(false); });
      }
    } catch (e) { setFailure(String(e instanceof Error ? e.message : e)); }
  };
  return <><Component {...navigation} onOKActionDescription={navigation.onOKActionDescription || title || '选择'} aria-label={title} aria-busy={busy} aria-pressed={pressed} aria-current={current ? 'page' : undefined} aria-expanded={expanded} aria-haspopup={expanded === undefined || !popup ? undefined : 'dialog'} disabled={disabled || busy} className={`da-button ${native ? 'da-native-button' : 'da-custom-button'} ${variant} ${className}`} onClick={click}>
    <span title={title} className="da-button-content">{busy ? <><span className="da-spinner" aria-hidden="true" /><span className="da-busy-text">{busyText}</span></> : result ? `✓ ${result}` : <>{native && variant === 'selected' && <span aria-hidden="true">✓</span>}{children}</>}</span>
  </Component>{failure && <span className="da-button-error" role="alert">{failure}，请重试</span>}</>;
}
export function Field({ label, value, onChange, placeholder, password = false }: {
  label: string; value: string; onChange: (value: string) => void; placeholder?: string; password?: boolean;
}) {
  const native = useContext(NativeContext);
  const field = <TextField label={native ? <span className="da-control-label">{label}</span> : undefined} aria-label={label} value={value} bIsPassword={password} placeholder={placeholder} onChange={event => onChange(event.target.value)} />;
  return native ? <div className="da-native-field">{field}</div> : <label className="da-field"><span>{label}</span>{field}</label>;
}
export function Select({ label, value, options, onChange, disabled = false }: {
  label: string; value: string; options: { value: string; label: string }[]; onChange: (value: string) => void | Promise<unknown>; disabled?: boolean;
}) {
  const lock = useRef(false); const [pending, setPending] = useState(false); const [error, setError] = useState('');
  return <div className="da-native-select"><DropdownItem label={<span className="da-control-label">{label}</span>} layout="below" menuLabel={label} contextMenuPositionOptions={{ strClassName: 'da-compact-dropdown-menu' }} selectedOption={value} disabled={disabled || pending} rgOptions={options.map(o => ({ data: o.value, label: o.label }))} onChange={option => {
    if (lock.current) return;
    lock.current = true; setPending(true); setError('');
    void Promise.resolve().then(() => onChange(option.data)).catch(e => setError(String(e instanceof Error ? e.message : e))).finally(() => { lock.current = false; setPending(false); });
  }} />{pending && <Loading text="正在保存选择…" />}<ErrorBox text={error} /></div>;
}
export function Toggle({ label, value, onChange, description }: { label: string; value: boolean; onChange: (value: boolean) => Promise<unknown>; description?: string }) {
  const lock = useRef(false); const [pending, setPending] = useState<boolean | null>(null); const [error, setError] = useState(''); const [saved, setSaved] = useState(false);
  return <div className="da-native-toggle"><ToggleField label={<span className="da-control-label">{label}</span>} description={<span className="da-control-description">{pending !== null ? '正在保存…' : error || (saved ? '已保存' : description)}</span>} checked={pending ?? value} disabled={pending !== null} onChange={next => {
    if (lock.current) return;
    lock.current = true; setPending(next); setError(''); setSaved(false);
    void onChange(next).then(() => setSaved(true)).catch(e => setError(String(e instanceof Error ? e.message : e))).finally(() => { lock.current = false; setPending(null); });
  }} />{error && <ErrorBox text={error} />}</div>;
}

// 由 Steam 的弹窗管理器负责层级和手柄隔离；内部保留长表单的固定标题与操作区。
export function Modal({ title, children, close, actions }: { title: string; children: ReactNode; close: () => void; actions?: ReactNode }) {
  const closeRef = useRef(close); closeRef.current = close;
  const [host, setHost] = useState<HTMLDivElement | null>(null);
  useEffect(() => {
    const dialog = showModal(<ModalRoot className="da-native-modal-root" bAllowFullSize bHideCloseIcon bDisableBackgroundDismiss onCancel={() => closeRef.current()} closeModal={() => closeRef.current()}>
      <div className="da-app da-dialog-surface"><style>{styles}</style><div ref={setHost} className="da-dialog-host" /></div>
    </ModalRoot>, undefined, { bNeverPopOut: true, strTitle: title });
    return () => dialog.Close();
  }, []);
  useEffect(() => {
    if (!host) return;
    const win = host.ownerDocument.defaultView!;
    const frame = win.requestAnimationFrame(() => {
      (host.querySelector<HTMLElement>('input:not(:disabled),textarea:not(:disabled)') || host.querySelector<HTMLElement>('button:not(:disabled),[role="button"][tabindex]'))?.focus();
    });
    return () => win.cancelAnimationFrame(frame);
  }, [host, title]);
  return host ? createPortal(<NativeControls className={`da-modal ${actions ? 'da-modal-with-actions' : ''}`} role="dialog" aria-modal="true" aria-label={title} onButtonDown={e => e.stopPropagation()} onCancelActionDescription="返回" onCancelButton={e => { e.stopPropagation(); closeRef.current(); }}>
    <div className="da-modal-head"><h2>{title}</h2><Button title="关闭对话框" onClick={close}>×</Button></div>
    <Focusable flow-children="column" className="da-modal-body">{children}</Focusable>{actions && <Focusable flow-children="row" className="da-modal-actions">{actions}</Focusable>}
  </NativeControls>, host) : null;
}
export function ErrorBox({ text }: { text?: string }) { return text ? <div role="alert" className="da-error">{text}</div> : null; }
export function Status({ value }: { value?: string }) {
  const labels: Record<string, string> = { sending: '发送中', stopping: '停止中', completed: '已完成', idle: '已就绪', running: '执行中', waiting: '等待输入', stopped: '已停止', interrupted: '已中断', error: '出错', starting: '启动中' };
  return <span className={`da-status ${value}`}><i />{labels[value || 'idle'] || value}</span>;
}
