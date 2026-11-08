export type Json = Record<string, unknown>;
export type Phase = 'idle' | 'running' | 'waiting' | 'stopped' | 'error' | 'interrupted' | 'starting';
export interface UIRequest {
  id: string; sessionId: string; instanceId: string; method: string;
  title?: string; message?: string; options?: string[]; placeholder?: string; prefill?: string;
}
export interface Session {
  id: string; name: string; cwd: string; status: Phase; archived: boolean;
  draft: string; updated: number; provider?: string; model?: string; thinking?: string;
  pending: UIRequest[]; error?: string;
  replyVersion?: number; unread?: boolean;
}
export interface Content { type: string; text?: string; name?: string; id?: string; arguments?: unknown }
export interface Message {
  role: string; content: string | Content[]; toolCallId?: string; toolName?: string;
  userInterrupted?: boolean; isError?: boolean; errorMessage?: string; stopReason?: string; timestamp?: number; durationMs?: number;
}
export interface Provider {
  id: string; name: string; model: string; thinking: string; baseUrl: string;
  api: string; custom: boolean; configured: boolean; default: boolean;
  reasoning?: boolean; enabledModels?: string[];
}
export interface ProviderForm extends Partial<Provider> { id: string; model: string; key: string; reasoning?: boolean }
export interface Model { provider: string; id: string; name: string; reasoning: boolean; api: string }
export interface Catalog { providers: { id: string; name: string }[]; models: Model[] }
export interface Preferences {
  defaultCwd: string; notifications: boolean; updateAuto: boolean; releaseRepo: string;
  language: string; inputDevice: string; titleModel?: { provider: string; model: string } | null;
}
export interface VoiceModel { id: string; name: string; description: string; downloadBytes: number; installed: boolean; source: string }
export interface Voice {
  status: string; name: string; modelId?: string; downloadSource?: string; models?: VoiceModel[]; downloaded: number; total: number; error?: string;
  sessionId?: string; recordingStarted?: number; engineReady: boolean; captureReady: boolean;
}
export interface LiveTool { id: string; name: string; args: unknown; result?: { content?: Content[] } }
export interface Snapshot {
  pluginInstalls?: { ticket: string; name: string; version: string; status: string; error?: string }[];
  newSessionDraft?: string; newSessionModel?: Pick<Session, 'provider' | 'model' | 'thinking'>;
  sessions: Session[]; preferences: Preferences; providers: Provider[];
  runtime: { ready: boolean; error?: string; piVersion: string }; version: string;
  build: { id: string; version: string; commit: string; builtAt: string; source: string; platform: string; pi: string };
  voice: Voice; active: { id: string; messages: Message[]; statusEntries: Record<string, string>; widgets: Record<string, string[]>; tools: LiveTool[] } | null;
}
export interface Notice { type: string; title?: string; message?: string; sessionId?: string }
export interface Release { current: string; latest: string; available: boolean; notes: string; pageUrl: string; zipUrl?: string; checksumUrl?: string }

export interface UpdateDownload { status: 'idle' | 'downloading' | 'verifying' | 'cancelling' | 'cancelled' | 'ready' | 'error'; downloaded: number; total: number; version?: string; error?: string }
export interface PreparedUpdate { artifact: string; version: string; hash: string; name?: string; installType?: number }
