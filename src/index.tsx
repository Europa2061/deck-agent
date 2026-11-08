import { Logo } from './components/Logo';
import { addEventListener, callable, definePlugin, removeEventListener, routerHook, toaster } from '@decky/api';
import { ConfirmModal, Navigation, showModal } from '@decky/ui';
import { App } from './App';
import { SteamPage } from './components/SteamPage';
import { configureBridge, selectSession } from './client';
import type { Notice } from './types';
import { checkInstaller, installUpdate } from './decky-updates';
import { openKeyboard, keyboardBounds, hideKeyboard } from './steam-keyboard';

const ROUTE = '/deck-agent';
const call = callable<[action: string, payload: Record<string, unknown>], { ok: boolean; value?: unknown; error?: string }>('request');

function openFullPage() {
  // 当前 Decky 只把新增页面注入主路由，不注入游戏 overlay 的路由表。
  if (/^\/(appoverlay|apprunning)(\/|$)/.test(location.pathname)) {
    const dialog = showModal(<ConfirmModal strTitle="从 Steam 主界面打开" strDescription="返回 Steam 主界面后，再在 Decky 中打开完整页面。当前任务会继续运行。" strOKButtonText="返回主界面" strCancelButtonText="留在侧栏" onCancel={() => dialog.Close()} closeModal={() => dialog.Close()} onOK={() => { Navigation.NavigateToLibraryTab(); Navigation.CloseSideMenus(); dialog.Close(); }} />);
    return;
  }
  Navigation.Navigate(ROUTE);
  Navigation.CloseSideMenus();
}

function Page() { return <SteamPage><App /></SteamPage>; }

export default definePlugin(() => {
  const dispose = configureBridge({
    async request<T>(action: string, payload = {}) {
      const result = await call(action, payload);
      if (!result.ok) throw new Error(result.error || '后端请求失败。');
      return result.value as T;
    },
    listen(callback) {
      const listener = addEventListener<[Notice]>('deck_agent_event', callback);
      return () => removeEventListener('deck_agent_event', listener);
    },
    checkInstaller, installUpdate,
    openPage: openFullPage,
    closePage() { Navigation.CloseSideMenus(); Navigation.NavigateToLibraryTab(); },
    keyboard: openKeyboard,
    keyboardBounds,
    hideKeyboard,
    notify(event) {
      toaster.toast({ title: event.title || 'Deck Agent', body: event.message || '', onClick: () => {
        if (event.sessionId) void selectSession(event.sessionId);
        openFullPage();
      } });
    },
    external(url) { Navigation.NavigateToExternalWeb(url); },
  });
  routerHook.addRoute(ROUTE, Page, { exact: true });
  return {
    name: 'Deck Agent', titleView: <span>Deck Agent</span>, icon: <Logo size={24} />,
    content: <App compact />,
    onDismount() { dispose(); routerHook.removeRoute(ROUTE); },
  };
});
