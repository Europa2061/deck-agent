// 仅供浏览器开发；生产入口使用 Steam / Decky 原生控件。
import { forwardRef, useEffect, useRef, type HTMLAttributes, type ReactNode } from 'react';
import { createRoot } from 'react-dom/client';
type EventLike = { detail: { button: number }; stopPropagation(): void };
type FocusProps = HTMLAttributes<HTMLDivElement> & { children?: ReactNode; onCancel?: () => void; onActivate?: (e: unknown) => void; onCancelButton?: (e: EventLike) => void; onSecondaryButton?: unknown; onOptionsButton?: unknown; onButtonDown?: (e: EventLike) => void; 'flow-children'?: string; preferredFocus?: boolean; navEntryPreferPosition?: unknown; onOKActionDescription?: ReactNode; onCancelActionDescription?: ReactNode; onSecondaryActionDescription?: ReactNode; onOptionsActionDescription?: ReactNode; actionDescriptionMap?: unknown; onGamepadFocus?: unknown; onGamepadDirection?: unknown };
export const Focusable = forwardRef<HTMLDivElement, FocusProps>(function DevFocusable({ onCancel: _cancel, onActivate, onCancelButton, onSecondaryButton: _x, onOptionsButton: _y, onButtonDown, 'flow-children': flow, preferredFocus: _preferred, navEntryPreferPosition: _position, onOKActionDescription: _ok, onCancelActionDescription: _back, onSecondaryActionDescription: _secondary, onOptionsActionDescription: _options, actionDescriptionMap: _map, onGamepadFocus: _focus, onGamepadDirection: _direction, ...props }, ref) {
  return <div {...props} ref={ref} data-flow={flow} tabIndex={onActivate ? 0 : props.tabIndex} onKeyDown={e => {
    if (e.key === 'Enter' && onActivate) onActivate(e);
    if (e.key === 'PageUp' || e.key === 'PageDown') onButtonDown?.({ detail: { button: e.key === 'PageUp' ? 5 : 6 }, stopPropagation: () => e.stopPropagation() });
    if (e.key === 'Escape') onCancelButton?.({ detail: { button: 2 }, stopPropagation: () => e.stopPropagation() });
    props.onKeyDown?.(e);
  }} />;
});
export function DialogButton({ onClick, children, onOKActionDescription: _ok, onCancelActionDescription: _b, onSecondaryActionDescription: _x, onOptionsActionDescription: _y, onMenuActionDescription: _menu, actionDescriptionMap: _map, preferredFocus: _preferred, navEntryPreferPosition: _position, onGamepadFocus: _focus, onGamepadBlur: _blur, onButtonDown: _down, onButtonUp: _up, onOKButton: _okButton, onCancelButton: _back, onSecondaryButton: _secondary, onOptionsButton: _options, onMenuButton: _menuButton, onGamepadDirection: _direction, ...props }: Record<string, any>) {
  return <button {...props} className={(props.className || '') + ' da-dev-button'} onClick={onClick}>{children}</button>;
}
export function DialogButtonPrimary(props: Record<string, any>) { return <DialogButton {...props} className={(props.className || '') + ' da-dev-primary'} />; }
export function TextField({ label, bIsPassword, focusOnMount, 'aria-label': ariaLabel, ...props }: Record<string, any>) {
  const input = <input {...props} type={bIsPassword ? 'password' : 'text'} aria-label={ariaLabel || label} autoFocus={focusOnMount} autoComplete="off" />;
  return label ? <label className="da-dev-field"><span>{label}</span>{input}</label> : input;
}
export function DropdownItem({ label, menuLabel, rgOptions, selectedOption, disabled, onChange }: Record<string, any>) {
  return <label className="da-dev-field"><span>{label || menuLabel}</span><select aria-label={menuLabel || (typeof label === 'string' ? label : label?.props?.children)} disabled={disabled} value={selectedOption} onChange={e => onChange?.(rgOptions.find((o: any) => o.data === e.target.value))}>{rgOptions.map((o: any) => <option value={o.data} key={o.data}>{o.label}</option>)}</select></label>;
}
export const Dropdown = DropdownItem;
export function ToggleField({ label, description, checked, disabled, onChange }: Record<string, any>) {
  return <button className="da-dev-toggle" role="switch" aria-label={typeof label === 'string' ? label : label?.props?.children} aria-checked={checked} disabled={disabled} onClick={() => onChange(!checked)}><span><strong>{label}</strong>{description && <small>{description}</small>}</span><span className={`da-dev-switch ${checked ? 'on' : ''}`} /></button>;
}
export function PanelSection({ title, children }: { title?: string; children?: ReactNode }) { return <section className="da-dev-section">{title && <h3>{title}</h3>}{children}</section>; }
export function PanelSectionRow({ children }: { children?: ReactNode }) { return <div className="da-dev-section-row">{children}</div>; }
export function ModalRoot({ children, onCancel }: { children?: ReactNode; onCancel?: () => void; [key: string]: unknown }) {
  const ref = useRef<HTMLDivElement>(null);
  const cancel = useRef(onCancel); cancel.current = onCancel;
  useEffect(() => {
    const old = document.activeElement as HTMLElement | null;
    const background = [...document.querySelectorAll<HTMLElement>('.da-app')].filter(el => !ref.current?.contains(el));
    const previous = background.map(el => el.inert); background.forEach(el => { el.inert = true; });
    const key = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.preventDefault(); e.stopImmediatePropagation(); cancel.current?.(); }
      if (e.key === 'Tab') {
        const items = [...(ref.current?.querySelectorAll<HTMLElement>('button:not(:disabled),input,textarea,select,[tabindex="0"]') || [])].filter(el => el.getClientRects().length);
        if (e.shiftKey && document.activeElement === items[0]) { e.preventDefault(); items.at(-1)?.focus(); }
        if (!e.shiftKey && document.activeElement === items.at(-1)) { e.preventDefault(); items[0]?.focus(); }
      }
    };
    document.addEventListener('keydown', key, true);
    const observer = new MutationObserver(() => { const item = ref.current?.querySelector<HTMLElement>('input,textarea,button'); if (item) { item.focus(); observer.disconnect(); } });
    observer.observe(ref.current!, { childList: true, subtree: true });
    return () => { observer.disconnect(); document.removeEventListener('keydown', key, true); background.forEach((el, i) => { el.inert = previous[i]; }); if (old?.isConnected) old.focus(); };
  }, []);
  return <div ref={ref} className="da-dev-modal-backdrop">{children}</div>;
}
export function showModal(content: ReactNode) {
  const element = document.createElement('div'); document.body.append(element); const root = createRoot(element);
  root.render(content); let closed = false;
  return { Close() { if (closed) return; closed = true; queueMicrotask(() => { root.unmount(); element.remove(); }); } };
}
export enum GamepadButton { BUMPER_LEFT = 5, BUMPER_RIGHT = 6, DIR_UP = 9, DIR_DOWN = 10 }

export function Tabs({ tabs, activeTab, onShowTab }: { tabs: { id: string; title: ReactNode; content: ReactNode }[]; activeTab: string; onShowTab: (id: string) => void }) {
  return <div className="da-dev-tabs"><div role="tablist" className="da-dev-tablist">{tabs.map(tab => <button role="tab" key={tab.id} aria-selected={activeTab === tab.id} onClick={() => onShowTab(tab.id)}>{tab.title}</button>)}</div><div role="tabpanel" className="da-dev-tabpanel">{tabs.find(t => t.id === activeTab)?.content}</div></div>;
}
