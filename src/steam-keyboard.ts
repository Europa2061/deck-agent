import { Router } from '@decky/ui';

interface KeyboardRef { ShowVirtualKeyboard(): void; SetAsCurrentVirtualKeyboardTarget(): void; DelayHideVirtualKeyboard(delay: number): void }
const refs = new WeakMap<HTMLTextAreaElement, KeyboardRef>();
const requested = new WeakSet<HTMLTextAreaElement>();
function managerFor(element: HTMLTextAreaElement) {
  const windows = Router.WindowStore?.SteamUIWindows || [];
  const instance = windows.find(w => w.m_BrowserWindow === element.ownerDocument.defaultView) || Router.WindowStore?.GamepadUIMainWindowInstance;
  return instance?.m_VirtualKeyboardManager;
}
export function openKeyboard(element: HTMLTextAreaElement) {
  const manager = managerFor(element);
  if (!manager) return;
  requested.add(element);
  element.focus({ preventScroll: true });
  let ref = refs.get(element);
  if (!ref) {
    const notify = () => { const win = element.ownerDocument.defaultView; if (win) win.dispatchEvent(new win.Event('deck-agent-keyboard')); };
    const restore = () => {
      if (!requested.has(element) || !element.isConnected || element.disabled || manager.m_currentVirtualKeyboardRef !== refs.get(element) || !manager.m_bIsInlineVirtualKeyboardOpen?.Value) return;
      const active = element.ownerDocument.activeElement;
      // 不覆盖用户主动切换到其他控件后的焦点。
      if (active !== element && active !== element.ownerDocument.body && active !== element.ownerDocument.documentElement) return;
      element.focus({ preventScroll: true });
      refs.get(element)?.SetAsCurrentVirtualKeyboardTarget();
      notify();
    };
    const shown = () => { notify(); element.ownerDocument.defaultView?.requestAnimationFrame(restore); };
    ref = manager.CreateVirtualKeyboardRef({
      BIsElementValidForInput: () => element.isConnected && !element.disabled && element.ownerDocument.activeElement === element,
      onEnterKeyPress: () => 'Enter',
      onKeyboardShow: shown,
      onKeyboardFullyVisible: () => { restore(); notify(); },
    }) as KeyboardRef;
    refs.set(element, ref);
  }
  ref.SetAsCurrentVirtualKeyboardTarget();
  ref.ShowVirtualKeyboard();
}
export function hideKeyboard(element: HTMLTextAreaElement) { requested.delete(element); refs.get(element)?.DelayHideVirtualKeyboard(100); }
export function keyboardBounds(element: HTMLTextAreaElement) {
  const manager = managerFor(element);
  const ref = refs.get(element);
  if (!ref || !manager?.m_bIsInlineVirtualKeyboardOpen?.Value || manager.m_currentVirtualKeyboardRef !== ref) return null;
  const win = element.ownerDocument.defaultView!;
  // Steam 内联键盘不改变 visualViewport。使用其网格和外层布局的实际边界，
  // 避免依赖每次 Steam 更新都可能变化的哈希类名。
  const grid = element.ownerDocument.querySelector<HTMLElement>('[role="grid"][class*="Layout_"]');
  if (grid) {
    let bounds: { top: number; bottom: number } | null = null;
    for (let node: HTMLElement | null = grid; node; node = node.parentElement) {
      const rect = node.getBoundingClientRect();
      if (rect.width < win.innerWidth * 0.8 || rect.height < 100 || rect.height > win.innerHeight * 0.8) break;
      bounds = { top: Math.max(0, rect.top), bottom: Math.min(win.innerHeight, rect.bottom) };
    }
    if (bounds && bounds.bottom > bounds.top) return bounds;
  }
  // 打开动画或 Steam 布局变化时，先按键盘位置保守留出半屏。
  return manager.KeyboardLocation === 'center-top'
    ? { top: 0, bottom: Math.ceil(win.innerHeight / 2) }
    : { top: Math.floor(win.innerHeight / 2), bottom: win.innerHeight };
}
