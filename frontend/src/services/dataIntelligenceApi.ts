/**
 * 数据智能对话 API client
 *
 * 后端端点：/api/data-intelligence/chat
 * 后端服务：backend/app/api/data_intelligence.py
 *
 * 与现有 /api/v1/* 不同，独立走 /api/data-intelligence/*
 * 通过 setupProxy.js 转发到后端 8000
 */

import axios from 'axios';

const DI_BASE_URL = '/api/data-intelligence';

const diApi = axios.create({
  baseURL: DI_BASE_URL,
  timeout: 30000,
});

export type UserSelectionPayload = {
  label?: string;
  value?: string;
  name?: string;
  code?: string;
  level?: string;
  entity_code?: string;
  attribute_code?: string;
  is_main_table?: boolean;
};

export type ChatRequestPayload = {
  thread_id?: string;
  user_input: string;
  user_selection?: UserSelectionPayload[];
  format?: 'default' | 'card';
  llm_connection_id?: string;
  mode?: 'free_plan' | 'legacy';
};

export type ConversationCard = {
  card_id?: string;
  card_type: string;
  title?: string;
  summary?: string;
  data?: Record<string, any>;
};

export type ChatResponse = {
  thread_id: string;
  current_task: string;
  goal?: string;
  pending_clarification?: Record<string, any> | null;
  confirmed?: Record<string, any>;
  completed_tasks: string[];
  flags: {
    chain_locked?: boolean;
    entity_locked?: boolean;
    attribute_locked?: boolean;
    relation_locked?: boolean;
    sql_executed?: boolean;
  };
  trace?: Array<Record<string, any>>;
  think_stream?: Array<Record<string, any>>;
  final_answer?: string;
  final_answer_structured?: { summary?: string; execution_process?: string; sql?: string; row_count?: number; recommendations?: string[] } | null;
  recommendations?: Array<{ label: string; shortcut?: string }>;
  recommended_next?: Array<{ task: string; label: string; shortcut?: string }>;
  next_step_recommendation?: { recommendations: Array<{ task: string; label: string; shortcut?: string }> } | null;
  message_card?: ConversationCard | null;
};

/** SSE 流式对话内部实现（chatStream 和 freePlanChatStream 共用） */
type StreamCallbacks = {
  onThink: (item: any) => void;
  onDone: (resp: ChatResponse) => void;
  onError: (err: string) => void;
  onStatus?: (status: { node: string; phase: string; text: string }) => void;
  onToken?: (token: { text: string }) => void;
  onFinal?: (final: { answer: string; structured?: any }) => void;
  onRecommend?: (rec: { questions: Array<{ label: string; shortcut?: string }> }) => void;
  onThinkToken?: (tk: { task: string; token: string; kind?: string }) => void;
  onSqlResult?: (data: { columns: string[]; rows: any[]; row_count: number; sql?: string }) => void;
  onTrace?: (trace: { node: string; status: string; detail?: string; [k: string]: any }) => void;
};

function _streamChat(
  endpoint: string,
  payload: ChatRequestPayload,
  cb: StreamCallbacks,
): AbortController {
  const controller = new AbortController();
  const baseURL = diApi.defaults.baseURL || '';
  let terminated = false;
  const safeDone = (resp: ChatResponse) => { if (!terminated) { terminated = true; cb.onDone(resp); } };
  const safeError = (err: string) => { if (!terminated) { terminated = true; cb.onError(err); } };

  fetch(`${baseURL}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      thread_id: payload.thread_id,
      user_input: payload.user_input,
      user_selection: payload.user_selection || [],
      format: payload.format || 'card',
      llm_connection_id: payload.llm_connection_id,
      mode: payload.mode || 'free_plan',
    }),
    signal: controller.signal,
  }).then(async (resp) => {
    if (!resp.ok) { safeError(`HTTP ${resp.status} ${resp.statusText}`); return; }
    const reader = resp.body?.getReader();
    if (!reader) { safeError('无法读取响应流'); return; }
    const decoder = new TextDecoder();
    let buffer = '';
    let currentEvent = '';
    const processBuffer = (finalFlush: boolean) => {
      const lines = buffer.split('\n');
      if (!finalFlush) { buffer = lines.pop() || ''; } else { buffer = ''; }
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith('data: ')) {
          const data = line.slice(6);
          try {
            const parsed = JSON.parse(data);
            if (currentEvent === 'think') cb.onThink(parsed);
            else if (currentEvent === 'think_token' && cb.onThinkToken) cb.onThinkToken(parsed);
            else if (currentEvent === 'status' && cb.onStatus) cb.onStatus(parsed);
            else if (currentEvent === 'token' && cb.onToken) cb.onToken(parsed);
            else if (currentEvent === 'final' && cb.onFinal) cb.onFinal(parsed);
            else if (currentEvent === 'recommend' && cb.onRecommend) cb.onRecommend(parsed);
            else if (currentEvent === 'sql_result' && cb.onSqlResult) cb.onSqlResult(parsed);
            else if (currentEvent === 'trace' && cb.onTrace) cb.onTrace(parsed);
            else if (currentEvent === 'done') safeDone(parsed as ChatResponse);
            else if (currentEvent === 'error') safeError(parsed.error || '未知错误');
          } catch (e) {
            console.warn(`[${endpoint}] SSE data JSON 解析失败`, { event: currentEvent, dataSnippet: data.slice(0, 200), error: String(e) });
          }
        }
      }
    };
    while (true) {
      let readResult: ReadableStreamReadResult<Uint8Array>;
      try {
        readResult = await reader.read();
      } catch (readErr: any) {
        if (!terminated) safeError(`流读取失败: ${readErr?.message || readErr}`);
        return;
      }
      const { done, value } = readResult;
      if (done) {
        if (buffer.trim()) processBuffer(true);
        if (!terminated) safeError('服务端连接已关闭（未收到 done 事件）');
        return;
      }
      buffer += decoder.decode(value, { stream: true });
      processBuffer(false);
    }
  }).catch((e) => {
    if (e.name !== 'AbortError') safeError(String(e));
  });
  return controller;
}

export const dataIntelligenceApi = {
  /** 自由规划问答端点（DeepAgent 边规划边思考模式）- SSE 推送，事件格式与 chatStream 一致 */
  freePlanChatStream: (
    payload: ChatRequestPayload,
    onThink: (item: any) => void,
    onDone: (resp: ChatResponse) => void,
    onError: (err: string) => void,
    onStatus?: (status: { node: string; phase: string; text: string }) => void,
    onToken?: (token: { text: string }) => void,
    onFinal?: (final: { answer: string; structured?: any }) => void,
    onRecommend?: (rec: { questions: Array<{ label: string; shortcut?: string }> }) => void,
    onThinkToken?: (tk: { task: string; token: string; kind?: string }) => void,
    onSqlResult?: (data: { columns: string[]; rows: any[]; row_count: number; sql?: string }) => void,
    onTrace?: (trace: { node: string; status: string; detail?: string; [k: string]: any }) => void,
  ): AbortController => {
    return _streamChat('/chat/freeplan/stream', payload, {
      onThink, onDone, onError, onStatus, onToken, onFinal, onRecommend, onThinkToken, onSqlResult, onTrace,
    });
  },

  /** 健康检查 */
  health: async (): Promise<{ status: string; service: string }> => {
    const resp = await diApi.get('/health');
    return resp.data;
  },
};

export default dataIntelligenceApi;
