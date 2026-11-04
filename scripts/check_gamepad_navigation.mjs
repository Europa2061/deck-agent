/** 实机导航回归：先将 Deck 的 8081 转发到本机 18081，再打开待检查界面。 */
import { readFile } from 'node:fs/promises';

const endpoint = new URL(process.argv[2] || 'http://127.0.0.1:18081');
const pages = await (await fetch(new URL('/json/list', endpoint))).json();
const target = pages.find(page => page.title === 'SharedJSContext');
if (!target) throw new Error('没有找到 Steam SharedJSContext，请确认 CEF 和端口转发。');
const socketURL = new URL(target.webSocketDebuggerUrl);
socketURL.host = endpoint.host;
const socket = new WebSocket(socketURL);
const pending = new Map();
let sequence = 0;
const timeout = setTimeout(() => {
  for (const entry of pending.values()) entry.reject(new Error('Steam 导航检查超时。'));
  socket.close();
}, 15000);
try {
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
  socket.onmessage = event => {
    const response = JSON.parse(event.data);
    const entry = pending.get(response.id);
    if (!entry) return;
    pending.delete(response.id);
    if (response.error) entry.reject(new Error(response.error.message));
    else entry.resolve(response.result);
  };
  const expression = await readFile(new URL('../tests/fixtures/steam_navigation.js', import.meta.url), 'utf8');
  const result = await new Promise((resolve, reject) => {
    const id = ++sequence;
    pending.set(id, { resolve, reject });
    socket.send(JSON.stringify({ id, method: 'Runtime.evaluate', params: { expression, returnByValue: true, awaitPromise: true } }));
  });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
  const report = result.result.value;
  console.log(JSON.stringify(report, null, 2));
  if (!report.pass) process.exitCode = 1;
} finally {
  clearTimeout(timeout);
  socket.close();
}
