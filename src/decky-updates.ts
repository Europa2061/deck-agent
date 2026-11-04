import type { PreparedUpdate } from './types';

// @decky/api 尚未导出安装接口；集中适配 Decky 原生安装器，避免散落内部调用。
interface Installer { call(route: string, ...args: unknown[]): Promise<unknown> }
function installer(): Installer {
  const api = (globalThis as typeof globalThis & { DeckyBackend?: Installer }).DeckyBackend;
  if (typeof api?.call !== 'function') throw new Error('当前 Decky 不支持插件内安装，请使用安装指引中的本地 ZIP。');
  return api;
}
export function checkInstaller() { installer(); }
export async function installUpdate(update: PreparedUpdate) {
  if (!update.artifact.startsWith('file:///') || !/^[a-f0-9]{64}$/.test(update.hash)) throw new Error('安装包信息无效，请重新下载。');
  // UPDATE = 2。只提交请求，保留 Decky 原生确认弹窗，由它负责卸载、替换和重载。
  await installer().call('utilities/install_plugin', update.artifact, 'Deck Agent', update.version, update.hash, 2);
}
