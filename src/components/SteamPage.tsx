import type { ReactNode } from 'react';

// Steam 的状态栏和按键提示在路由内容上方绘制，完整页只占两栏之间的空间。
export function SteamPage({ children }: { children: ReactNode }) {
  return <div className="da-steam-frame" style={{ position: 'relative', width: '100%', height: '100%', minHeight: 0 }}><div className="da-steam-page" style={{
    position: 'absolute', top: 'var(--basicui-header-height, 40px)', right: 0,
    bottom: 'var(--basicui-footer-height, 48px)', left: 0,
    minHeight: 0,
  }}>{children}</div></div>;
}
