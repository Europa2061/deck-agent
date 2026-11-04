import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import ts from 'typescript';

const source = await readFile(new URL('../src/components/conversation-turns.ts', import.meta.url), 'utf8');
const code = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
const { conversationTurns, processLabel } = await import(`data:text/javascript;base64,${Buffer.from(code).toString('base64')}`);
const user = text => ({ role: 'user', content: text, timestamp: 1000 });
const progress = { role: 'assistant', content: [{ type: 'text', text: '正在检查' }, { type: 'toolCall', name: 'read', id: 'one' }], timestamp: 2000 };
const tool = { role: 'toolResult', toolCallId: 'one', content: '检查详情', timestamp: 3000 };
const answer = { role: 'assistant', content: '最终结论', timestamp: 120000 };

test('执行完成后保留最终答复，将中间消息和工具结果归入同一过程', () => {
  const messages = [user('检查设备'), progress, tool, answer];
  const copy = structuredClone(messages);
  const [turn] = conversationTurns(messages, false);
  assert.deepEqual(turn.process, [progress, tool]);
  assert.equal(turn.result, answer);
  assert.equal(turn.toolCount, 1);
  assert.equal(processLabel(turn), '用时 1分 59秒');
  assert.deepEqual(messages, copy);
});

test('执行中的流式答复保持展开，完成后同一轮转为可折叠过程和独立答复', () => {
  const messages = [user('检查设备'), progress, tool, answer];
  const [running] = conversationTurns(messages, true);
  assert.equal(running.active, true);
  assert.equal(running.result, undefined);
  assert.deepEqual(running.process, [progress, tool, answer]);
  const [finished] = conversationTurns(messages, false);
  assert.equal(finished.key, running.key);
  assert.equal(finished.active, false);
  assert.equal(finished.result, answer);
});

test('多轮历史分别折叠，只有最后一轮处于执行状态', () => {
  const turns = conversationTurns([user('第一轮'), progress, tool, answer, user('第二轮'), progress], true);
  assert.equal(turns.length, 2);
  assert.equal(turns[0].active, false);
  assert.equal(turns[0].result, answer);
  assert.equal(turns[1].active, true);
  assert.equal(turns[1].result, undefined);
});

test('没有工具的直接答复不多出过程条，缺少时间戳不捏造耗时', () => {
  const [turn] = conversationTurns([user('你好'), { role: 'assistant', content: '你好' }], false);
  assert.equal(turn.process.length, 0);
  assert.equal(turn.result.content, '你好');
  assert.equal(turn.durationMs, undefined);
  assert.equal(processLabel(turn), '执行过程');
});

test('中断且没有最终答复时，保留完整过程，不把进度文字当成答复', () => {
  const [turn] = conversationTurns([user('检查'), { role: 'assistant', content: '先查看文件' }, progress, tool], false);
  assert.equal(turn.result, undefined);
  assert.equal(turn.process.length, 3);
});

test('最终错误、图片和答复后的扩展消息不会导致最终内容被藏入过程', () => {
  const failed = { role: 'assistant', content: [], errorMessage: '模型连接失败' };
  assert.equal(conversationTurns([user('检查'), progress, tool, failed], false)[0].result, failed);
  const picture = { role: 'assistant', content: [{ type: 'image' }] };
  assert.equal(conversationTurns([user('图片'), picture], false)[0].result, picture);
  const extra = { role: 'custom', content: '扩展补充' };
  const [turn] = conversationTurns([user('检查'), progress, tool, answer, extra], false);
  assert.equal(turn.result, answer);
  assert.deepEqual(turn.process, [progress, tool, extra]);
});


test('原生消息带响应时长时计入耗时，异常时间记录不显示耗时', () => {
  const [turn] = conversationTurns([user('检查'), progress, tool, { ...answer, durationMs: 1000 }], false);
  assert.equal(processLabel(turn), '用时 2分');
  const [invalid] = conversationTurns([user('检查'), progress, { ...answer, timestamp: NaN }], false);
  assert.equal(invalid.durationMs, undefined);
});

test('用户中断显示在对应轮次末尾，空取消消息不生成错误答复或空过程', () => {
  const aborted = { role: 'assistant', content: [], userInterrupted: true, stopReason: 'aborted' };
  const [turn] = conversationTurns([user('检查'), aborted], false, true);
  assert.equal(turn.interrupted, true);
  assert.equal(turn.result, undefined);
  assert.equal(turn.process.length, 0);
  const turns = conversationTurns([user('检查'), progress, aborted, user('继续'), answer], false);
  assert.equal(turns[0].interrupted, true);
  assert.equal(turns[1].interrupted, false);
  assert.equal(turns[1].result, answer);
});

test('取消时已有的部分答复继续保留，普通错误仍保留原错误信息', () => {
  const partial = { role: 'assistant', content: '已完成第一步', userInterrupted: true };
  assert.equal(conversationTurns([user('检查'), partial], false, true)[0].result, partial);
  const failed = { role: 'assistant', content: [], errorMessage: '503 Service unavailable' };
  const [turn] = conversationTurns([user('检查'), failed], false);
  assert.equal(turn.interrupted, false);
  assert.equal(turn.result.errorMessage, failed.errorMessage);
});
