import { ModelRuntime } from '@earendil-works/pi-coding-agent';
import path from 'node:path';
const dir = process.env.PI_CODING_AGENT_DIR;
if (!dir) throw new Error('PI_CODING_AGENT_DIR is required');
const runtime = await ModelRuntime.create({authPath:path.join(dir,'auth.json'), modelsPath:path.join(dir,'models.json'), modelsStorePath:path.join(dir,'models-store.json'), allowModelNetwork:false});
if (runtime.getError()) throw new Error(runtime.getError());
process.stdout.write(JSON.stringify({
  providers:runtime.getProviders().map(p=>({id:p.id,name:p.name||p.id})),
  models:runtime.getModels().map(m=>({provider:m.provider,id:m.id,name:m.name,reasoning:m.reasoning,api:m.api,contextWindow:m.contextWindow})),
}));
