import type { Message } from '../types';

export interface ConversationTurn {
  key: number;
  user?: Message;
  process: Message[];
  result?: Message;
  active: boolean;
  interrupted?: boolean;
  toolCount: number;
  durationMs?: number;
}

function hasAnswer(message: Message): boolean {
  if (message.role !== 'assistant') return false;
  if (typeof message.content === 'string') return Boolean(message.content.trim() || message.errorMessage);
  if (message.content.some(part => part.type === 'toolCall')) return false;
  return Boolean(message.errorMessage || message.content.some(part => part.type === 'image' || part.type === 'text' && part.text?.trim()));
}

// 每条用户消息是一轮；只把最后的答复留在折叠区外，不改变原始消息。
export function conversationTurns(messages: Message[], active: boolean, stopped = false): ConversationTurn[] {
  const turns: ConversationTurn[] = [];
  for (const [index, message] of messages.entries()) {
    if (message.role === 'user' || !turns.length) turns.push({ key: index, user: message.role === 'user' ? message : undefined, process: [], active: false, toolCount: 0 });
    const turn = turns[turns.length - 1];
    if (message.role !== 'user') turn.process.push(message);
  }
  for (const [index, turn] of turns.entries()) {
    turn.active = active && index === turns.length - 1;
    const tail = turn.process.at(-1);
    turn.interrupted = turn.process.some(message => message.userInterrupted) || (!turn.active && stopped && index === turns.length - 1);
    turn.process = turn.process.filter(message => !message.userInterrupted || (typeof message.content === 'string' ? Boolean(message.content.trim()) : message.content.some(part => part.type === 'toolCall' || part.type === 'image' || part.type === 'text' && part.text?.trim())));
    let resultIndex = turn.process.length - 1;
    while (resultIndex >= 0 && !hasAnswer(turn.process[resultIndex])) resultIndex--;
    if (!turn.active && resultIndex >= 0 && turn.process.slice(resultIndex + 1).every(message => message.role === 'custom')) {
      [turn.result] = turn.process.splice(resultIndex, 1);
    }
    turn.toolCount = turn.process.reduce((count, message) => count + (Array.isArray(message.content) ? message.content.filter(part => part.type === 'toolCall').length : 0), 0);
    // 老记录没有时间戳时只显示过程条目，不估算耗时。
    const start = turn.user?.timestamp;
    const last = turn.result || tail;
    const end = last?.timestamp === undefined ? undefined : last.timestamp + (typeof last.durationMs === 'number' && Number.isFinite(last.durationMs) && last.durationMs >= 0 ? last.durationMs : 0);
    if (typeof start === 'number' && typeof end === 'number' && Number.isFinite(start) && Number.isFinite(end) && end > start) turn.durationMs = end - start;
  }
  return turns;
}

export function processLabel(turn: ConversationTurn): string {
  if (turn.active) return '正在执行';
  if (turn.durationMs !== undefined) {
    const seconds = Math.max(1, Math.round(turn.durationMs / 1000));
    return seconds >= 60 ? `用时 ${Math.floor(seconds / 60)}分${seconds % 60 ? ` ${seconds % 60}秒` : ''}` : `用时 ${seconds}秒`;
  }
  return '执行过程';
}
