export interface VerticalBounds { top: number; bottom: number }
export function composerViewport({ height, topBar, footer, keyboard, host, viewport }: {
  height: number; topBar: number; footer: number;
  keyboard: VerticalBounds | null; host: VerticalBounds | null; viewport: VerticalBounds | null;
}): VerticalBounds {
  let top = topBar, bottom = height - footer;
  // Steam 主页面容器本身会随键盘移动；直接使用它的可用区，避免重复避让。
  if (host && host.bottom - host.top >= 80) {
    top = Math.max(top, host.top);
    bottom = Math.min(bottom, host.bottom);
    if (host.bottom < height - footer) bottom -= 8;
    if (host.top > topBar) top += 8;
  } else {
    if (viewport) { top = Math.max(top, viewport.top); bottom = Math.min(bottom, viewport.bottom); }
    if (keyboard) {
      if (keyboard.top > height / 4) bottom = Math.min(bottom, keyboard.top - 8);
      else top = Math.max(top, keyboard.bottom + 8);
    }
  }
  // 动画期间的无效或相互冲突的边界不能把页面压成空白。
  return bottom - top >= 100 ? { top, bottom } : { top: topBar, bottom: height - footer };
}
