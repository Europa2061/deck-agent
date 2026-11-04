import { ModelRuntime } from '@earendil-works/pi-coding-agent';
import path from 'node:path';
try {
  const dir=process.env.PI_CODING_AGENT_DIR;
  const runtime=await ModelRuntime.create({authPath:path.join(dir,'auth.json'),modelsPath:path.join(dir,'models.json'),allowModelNetwork:false});
  const model=runtime.getModel(process.argv[2],process.argv[3]);
  if(!model) throw new Error('找不到该模型，请检查模型 ID 和接口配置。');
  const message=await runtime.completeSimple(model,{messages:[{role:'user',content:'Reply OK.',timestamp:Date.now()}]},{maxTokens:16,signal:AbortSignal.timeout(30000)});
  if(message.stopReason==='error'||message.stopReason==='aborted') throw new Error(message.errorMessage||'连接测试未完成。');
  process.stdout.write(JSON.stringify({ok:true}));
} catch(error) { process.stdout.write(JSON.stringify({ok:false,error:String(error.message||error)})); }
