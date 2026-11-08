import { useEffect, useLayoutEffect, useRef } from 'react';
import { platform } from '../client';
import { composerViewport } from './composer-viewport';

export function useComposerLayout(draft: string) {
  const input = useRef<HTMLTextAreaElement>(null);
  const resize = () => {
    const el = input.current;
    if (!el) return;
    const win = el.ownerDocument.defaultView!;
    const page = el.closest<HTMLElement>('.da-steam-page');
    const app = el.closest<HTMLElement>('.da-app');
    const composer = el.closest<HTMLElement>('.da-composer')!;
    const available = page?.clientHeight || Math.min(win.visualViewport?.height || win.innerHeight, parseFloat(app?.style.maxHeight || '') || Infinity);
    const maximum = Math.max(60, Math.min(144, Math.floor(available * .4)));
    const scrollTop = el.scrollTop;
    // 先用单行布局的宽度检测折行，再按实际布局测量高度。
    composer.removeAttribute('data-multiline');
    el.style.maxHeight = maximum + 'px';
    el.style.height = '0px';
    composer.toggleAttribute('data-multiline', el.scrollHeight > el.clientHeight);
    el.style.height = Math.min(maximum, Math.max(38, el.scrollHeight)) + 'px';
    const caretAtEnd = el.ownerDocument.activeElement === el && el.selectionStart === el.selectionEnd && el.selectionEnd === el.value.length;
    el.scrollTop = caretAtEnd ? el.scrollHeight : scrollTop;
    const qam = el.closest<HTMLElement>('.da-qam');
    if (qam && app?.style.maxHeight) {
      const hidden = composer.getBoundingClientRect().bottom - qam.getBoundingClientRect().bottom;
      if (hidden > 0) qam.scrollTop += hidden + 6;
    }
  };
  useLayoutEffect(resize, [draft]);
  useEffect(() => {
    const el = input.current;
    if (!el) return;
    const doc = el.ownerDocument, win = doc.defaultView!;
    const app = el.closest<HTMLElement>('.da-app')!;
    const page = el.closest<HTMLElement>('.da-steam-page');
    const composer = el.closest<HTMLElement>('.da-composer')!;
    const composerWrap = el.closest<HTMLElement>('.da-composer-wrap');
    const savedTransform = composerWrap?.style.transform || '';
    const savedHeight = page?.style.height || '';
    const saved = { top: page?.style.top || '', bottom: page?.style.bottom || '', maxHeight: app.style.maxHeight, minHeight: app.style.minHeight };
    let timer: ReturnType<typeof setInterval> | undefined;
    let previous = '';
    let settleUntil = Date.now() + 1000;
    const update = () => {
      const focused = doc.activeElement === el;
      const keyboard = platform.keyboardBounds(el);
      const viewport = win.visualViewport;
      const topBar = parseFloat(win.getComputedStyle(app).getPropertyValue('--basicui-header-height')) || 40;
      const footer = parseFloat(win.getComputedStyle(app).getPropertyValue('--basicui-footer-height')) || 48;
      const parent = page?.parentElement?.getBoundingClientRect();
      const host = parent && parent.width >= win.innerWidth * .8 && parent.height >= 80 ? { top: parent.top, bottom: parent.bottom } : null;
      const { top, bottom } = composerViewport({ height: win.innerHeight, topBar, footer, keyboard, host,
        viewport: (focused || keyboard) && viewport ? { top: viewport.offsetTop, bottom: viewport.offsetTop + viewport.height } : null });
      const parentTop = parent?.top || 0;
      const key = `${top}/${bottom}/${win.innerWidth}/${win.innerHeight}/${parentTop}`;
      if (previous !== key) {
        previous = key;
        if (page) {
          page.style.top = (topBar - parentTop) + 'px';
          page.style.bottom = 'auto';
          page.style.height = Math.max(100, win.innerHeight - topBar - footer) + 'px';
          if (composerWrap) {
            const lift = keyboard ? Math.min(0, bottom - (win.innerHeight - footer)) : 0;
            composerWrap.style.transform = lift ? `translateY(${lift}px)` : savedTransform;
            composerWrap.style.zIndex = lift ? '5' : '';
          }
        } else if (keyboard || (focused && viewport && viewport.height < win.innerHeight - 80)) {
          app.style.minHeight = '0px'; app.style.maxHeight = Math.max(80, bottom - app.getBoundingClientRect().top) + 'px';
        } else { app.style.maxHeight = saved.maxHeight; app.style.minHeight = saved.minHeight; }
        resize();
      }
      if (focused || keyboard) settleUntil = Date.now() + 600;
      if (!focused && !keyboard && Date.now() >= settleUntil && timer) { clearInterval(timer); timer = undefined; }
    };
    const start = () => { update(); if (!timer) timer = setInterval(update, 150); };
    // Steam 键盘接管焦点时 textarea 也会失焦；只在用户切换到插件内
    // 的其他控件时收起键盘，不能把键盘本身的焦点变化当成退出输入。
    const leaveInput = (event: Event) => {
      const target = event.target as Node | null;
      if (target && app.contains(target) && !el.closest('.da-compose-focus')?.contains(target)) platform.hideKeyboard(el);
    };
    const focus = (event: FocusEvent) => {
      if (event.target === el) start();
      else if ((event.target as HTMLElement | null)?.closest?.('button,input,textarea,[role=button],[role=combobox]')) leaveInput(event);
    };
    const host = page?.parentElement || doc.documentElement;
    const actions = composer.querySelector<HTMLElement>('.da-composer-actions')!;
    let composerWidth = composer.clientWidth;
    let actionsWidth = actions.clientWidth;
    const observer = new win.ResizeObserver(entries => {
      const hostChanged = entries.some(entry => entry.target === host);
      if (!hostChanged && composer.clientWidth === composerWidth && actions.clientWidth === actionsWidth) return;
      composerWidth = composer.clientWidth;
      actionsWidth = actions.clientWidth;
      if (hostChanged) update();
      resize();
    });
    observer.observe(host);
    observer.observe(composer);
    observer.observe(actions);
    doc.addEventListener('focusin', focus);
    doc.addEventListener('pointerdown', leaveInput, true);
    win.addEventListener('resize', update);
    win.addEventListener('deck-agent-keyboard', start);
    win.visualViewport?.addEventListener('resize', update);
    win.visualViewport?.addEventListener('scroll', update);
    start();
    return () => {
      clearInterval(timer); observer.disconnect();
      doc.removeEventListener('pointerdown', leaveInput, true);
      doc.removeEventListener('focusin', focus); win.removeEventListener('resize', update); win.removeEventListener('deck-agent-keyboard', start);
      win.visualViewport?.removeEventListener('resize', update); win.visualViewport?.removeEventListener('scroll', update);
      if (page) { page.style.top = saved.top; page.style.bottom = saved.bottom; page.style.height = savedHeight; }
      if (composerWrap) { composerWrap.style.transform = savedTransform; composerWrap.style.zIndex = ''; }
      app.style.maxHeight = saved.maxHeight; app.style.minHeight = saved.minHeight;
      platform.hideKeyboard(el);
    };
  }, []);
  return input;
}
