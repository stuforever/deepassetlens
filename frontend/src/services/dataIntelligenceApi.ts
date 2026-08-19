/**
 * 数据智能对话 API client
 *
 * 后端端点：/api/data-intelligence/chat
 * 后端服务：backend/app/api/data_intelligence.py
 *
 * 与现有 /api/v1/* 不同，独立走 /api/data-intelligence/*
 * 通过 setupProxy.js 转发到后端 28000
 */

import { createApiClient } from './http';

const DI_BASE_URL = '/api/data-intelligence';

const diApi = createApiClient(DI_BASE_URL, { timeout: 30000 });

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
  final_delivery?: {
    answer_type?: string;
    title?: string;
    summary?: string[];
    findings?: Array<{ label?: string; value?: string; level?: string }>;
    warnings?: string[];
    recommendations?: string[];
    row_count?: number;
    result_available_for_ui?: boolean;
  } | null;
  recommendations?: Array<{ label: string; shortcut?: string }>;
  recommended_next?: Array<{ task: string; label: string; shortcut?: string }>;
  next_step_recommendation?: { recommendations: Array<{ task: string; label: string; shortcut?: string }> } | null;
  message_card?: ConversationCard | null;
  /** 受控 Skill 问答平台 v2：确定性路由结果（前端 RouteCard） */
  route?: {
    route_type: string; skill_id?: string; workflow_step?: string; matched_rules?: string[];
    route_reason?: string; confidence?: string; fallback_level?: string;
    candidates?: Array<{ skill_id: string; description?: string }>; priority?: number;
    contract?: Record<string, any> | null;
  } | null;
  /** 受控执行契约（前端五张业务卡数据源，与后端 QueryContract 完全一致） */
  contract?: {
    run_id?: string; skill_id: string; skill_version?: string; workflow_step: string;
    allowed_tools?: string[]; forbidden_tools?: string[]; template_ids?: string[];
    scope?: Record<string, any>; selected_engine?: string | null; engine_reason?: string | null;
    output_mode?: string; stop_when?: string[]; route_reason?: string; route_type?: string;
  } | null;
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
  onThinkToken?: (tk: { task: string; token: string; kind?: string; delta?: string; round_id?: string; content?: string; tool_call_id?: string; tool_name?: string; candidate_content?: string; attempt?: number; reason?: string }) => void;
  onSqlResult?: (data: { columns: string[]; rows: any[]; row_count: number; sql?: string; returned_rows?: number; preview_row_count?: number; is_preview?: boolean; result_available_for_ui?: boolean }) => void;
  onTrace?: (trace: { node: string; status: string; detail?: string; [k: string]: any }) => void;
  onIntent?: (intent: { task: string; entities?: string[]; filters: Array<{ desc: string; field: string; values: string[] }> }) => void;
  onFilterCheck?: (fc: { sql_where: string; row_count: number }) => void;
  onRoute?: (route: { route_type: string; skill_id?: string; workflow_step?: string; matched_rules?: string[]; route_reason?: string; confidence?: string; fallback_level?: string; candidates?: any[]; priority?: number }) => void;
  onContract?: (contract: {
    run_id?: string; skill_id: string; skill_version?: string; workflow_step: string;
    allowed_tools?: string[]; forbidden_tools?: string[]; template_ids?: string[];
    scope?: Record<string, any>; selected_engine?: string | null; engine_reason?: string | null;
    output_mode?: string; stop_when?: string[]; route_reason?: string; route_type?: string;
    multi_engine?: boolean; forbid_markdown_detail_table?: boolean;
    confirmed_engines?: string[]; entity_engine_map?: Record<string, string>; stop_reached?: boolean;
  }) => void;
  /** 评审 P1-3：运行中引擎确认/复合终止（engine.selected / stop.reached）实时更新契约 */
  onContractUpdate?: (payload: {
    kind: string; contract?: Record<string, any>;
    selected_engine?: string | null; multi_engine?: boolean; completed_engines?: string[];
    entity_engine_map?: Record<string, string>; reason?: string;
  }) => void;
  /** 评审 P1-3：策略拒绝/阻断实时事件 */
  onPolicy?: (payload: { kind: string; tool_name?: string; reason?: string; attempt?: number; blocked?: boolean }) => void;
  /** 评审 P1-3：模板绑定/漂移实时事件 */
  onTemplate?: (payload: { kind: string; detail?: string }) => void;
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
            else if (currentEvent === 'intent' && cb.onIntent) cb.onIntent(parsed);
            else if (currentEvent === 'filter_check' && cb.onFilterCheck) cb.onFilterCheck(parsed);
            else if (currentEvent === 'route' && cb.onRoute) cb.onRoute(parsed);
            else if (currentEvent === 'contract' && cb.onContract) cb.onContract(parsed);
            else if (currentEvent === 'contract_update' && cb.onContractUpdate) cb.onContractUpdate(parsed);
            else if (currentEvent === 'policy' && cb.onPolicy) cb.onPolicy(parsed);
            else if (currentEvent === 'template' && cb.onTemplate) cb.onTemplate(parsed);
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
    // AbortError(用户点停止)也走 safeError -> onError, 由 stoppedRef 判定静默 resolve(null),
    // 避免 submitted 阶段 abort 被吞导致 300s 假超时
    safeError(e.name === 'AbortError' ? '已中止' : String(e));
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
    onThinkToken?: (tk: { task: string; token: string; kind?: string; delta?: string; round_id?: string; content?: string; tool_call_id?: string; tool_name?: string; candidate_content?: string; attempt?: number; reason?: string }) => void,
    onSqlResult?: (data: { columns: string[]; rows: any[]; row_count: number; sql?: string; returned_rows?: number; preview_row_count?: number; is_preview?: boolean; result_available_for_ui?: boolean }) => void,
    onTrace?: (trace: { node: string; status: string; detail?: string; [k: string]: any }) => void,
    onIntent?: (intent: { task: string; entities?: string[]; filters: Array<{ desc: string; field: string; values: string[] }> }) => void,
    onFilterCheck?: (fc: { sql_where: string; row_count: number }) => void,
    onRoute?: (route: { route_type: string; skill_id?: string; workflow_step?: string; matched_rules?: string[]; route_reason?: string; confidence?: string; fallback_level?: string; candidates?: any[]; priority?: number }) => void,
    onContract?: (contract: {
      run_id?: string; skill_id: string; skill_version?: string; workflow_step: string;
      allowed_tools?: string[]; forbidden_tools?: string[]; template_ids?: string[];
      scope?: Record<string, any>; selected_engine?: string | null; engine_reason?: string | null;
      output_mode?: string; stop_when?: string[]; route_reason?: string; route_type?: string;
      multi_engine?: boolean; forbid_markdown_detail_table?: boolean;
      confirmed_engines?: string[]; entity_engine_map?: Record<string, string>; stop_reached?: boolean;
    }) => void,
    onContractUpdate?: (payload: {
      kind: string; contract?: Record<string, any>;
      selected_engine?: string | null; multi_engine?: boolean; completed_engines?: string[];
      entity_engine_map?: Record<string, string>; reason?: string;
    }) => void,
    onPolicy?: (payload: { kind: string; tool_name?: string; reason?: string; attempt?: number; blocked?: boolean }) => void,
    onTemplate?: (payload: { kind: string; detail?: string }) => void,
  ): AbortController => {
    return _streamChat('/chat/freeplan/stream', payload, {
      onThink, onDone, onError, onStatus, onToken, onFinal, onRecommend, onThinkToken, onSqlResult, onTrace, onIntent, onFilterCheck, onRoute, onContract, onContractUpdate, onPolicy, onTemplate,
    });
  },

  /** 健康检查 */
  health: async (): Promise<{ status: string; service: string }> => {
    const resp = await diApi.get('/health');
    return resp.data;
  },

  /** 受控路由预览（RouteSimulator）：前端不自行猜测路由/契约，统一走后端 SkillRouter */
  routePreview: async (payload: { user_input: string; last_skill?: string; last_step?: string; customer_names?: string[] }): Promise<{ ok: boolean; route?: any; error?: string }> => {
    const resp = await diApi.post('/route/preview', payload);
    return resp.data;
  },

  /** 批4 治理：Skill 目录快照（运行观测台） */
  skillsCatalog: async (): Promise<{ ok: boolean; catalog?: any[]; warnings?: string[]; error?: string }> => {
    const resp = await diApi.get('/skills/catalog');
    return resp.data;
  },

  /** 批4 治理：运行指标 + 审计轨迹（运行观测台） */
  skillsMetrics: async (): Promise<{ ok: boolean; counters?: Record<string, number>; by_route_type?: Record<string, number>; by_skill?: Record<string, number>; policy_by_reason?: Record<string, number>; audit?: any[]; error?: string }> => {
    const resp = await diApi.get('/skills/metrics');
    return resp.data;
  },

  /** 批4 治理：路由模拟（Skill 工作台，与生产同一裁判） */
  simulateRoute: async (payload: { user_input: string; last_skill?: string; last_step?: string; customer_names?: string[] }): Promise<{ ok: boolean; route?: any; error?: string }> => {
    const resp = await diApi.post('/skills/simulate-route', payload);
    return resp.data;
  },

  /** 清除自由问答会话的后端 checkpoint 记忆 */
  clearFreeplanMemory: async (threadId: string): Promise<{ status: string; cleared: boolean }> => {
    const resp = await diApi.delete(`/chat/freeplan/threads/${encodeURIComponent(threadId)}/memory`);
    return resp.data;
  },
};

export default dataIntelligenceApi;
