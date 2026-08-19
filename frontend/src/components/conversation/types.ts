export type RunEventRecord = {
  event_type?: string;
  payload?: any;
};

export type RuntimeContextRecord = {
  protocol_version?: string;
  scene_code?: string;
  page_code?: string;
  workspace?: Record<string, any>;
  session?: Record<string, any>;
  request?: Record<string, any>;
  memory?: Record<string, any>;
  capabilities?: Record<string, any>;
};

export type ConversationBlock = {
  block_id?: string;
  block_type?: string;
  title?: string;
  text?: string;
  data?: any;
};

export type ConversationCard = {
  protocol_version?: string;
  card_id?: string;
  card_type: string;
  title?: string;
  summary?: string;
  status?: string;
  data?: any;
};

export type ConversationCardAction = {
  action_type: 'submit_clarification';
  submit_value: string;
  card: ConversationCard;
  option?: Record<string, any>;
  selected_options?: Record<string, any>[];
  manual_text?: string;
};

export type FinalAnswerStructured = {
  summary?: string;
  execution_process?: string;
  sql?: string;
  row_count?: number;
  recommendations?: string[];
};

/** 统一最终交付协议：关键发现（指标卡） */
export type FinalFinding = {
  label?: string;
  value?: string;
  level?: 'info' | 'success' | 'warning' | 'error';
};

/** 统一最终交付协议：标题/摘要/发现/告警/推荐（表格数据仍走 sql_result） */
export type FinalDelivery = {
  answer_type?: 'relationship_list' | 'overload_analysis' | 'data_list' | 'aggregation' | 'knowledge' | 'empty' | 'error';
  title?: string;
  summary?: string[];
  findings?: FinalFinding[];
  warnings?: string[];
  recommendations?: string[];
  row_count?: number;
  result_available_for_ui?: boolean;
};

export type ChatMessagePayload = {
  text?: string;
  live_text?: string;
  live_meta?: string;
  finalTokens?: string[];
  cards?: ConversationCard[];
  llm_error?: any;
  runtime_context?: RuntimeContextRecord | null;
  blocks?: ConversationBlock[];
  stream_events?: RunEventRecord[];
  thinkStream?: any[];
  final_answer?: string;
  final_answer_structured?: FinalAnswerStructured | null;
  final_delivery?: FinalDelivery | null;   // 统一最终交付协议（标题/摘要/发现/告警/推荐/row_count）
  response_format_degraded?: boolean;  // R3: 结构化输出降级标识（GLM 不兼容时为 true）
  recommendations?: Array<{ label: string; shortcut?: string }>;
  completedTasks?: string[];
  confirmed?: Record<string, any>;
  sqlExecuted?: boolean;
  sql_result?: { columns?: string[]; rows?: any[]; row_count?: number; sql?: string; returned_rows?: number; preview_row_count?: number; is_preview?: boolean; result_available_for_ui?: boolean } | null;
  traceLogs?: any[];
  /** 意图理解卡（P0）：执行前推 intent，执行后补 filter_check，置顶让用户核对 AI 是否听懂 */
  intent?: { task: string; entities?: string[]; filters: Array<{ desc: string; field: string; values: string[] }> } | null;
  filter_check?: { sql_where: string; row_count: number } | null;
  /** 受控 Skill 问答平台 v2：确定性路由结果 + 受控执行契约（五张业务卡数据源） */
  route?: {
    route_type: string; skill_id?: string; workflow_step?: string; matched_rules?: string[];
    route_reason?: string; confidence?: string; fallback_level?: string;
    candidates?: Array<{ skill_id: string; description?: string }>; priority?: number;
  } | null;
  contract?: {
    run_id?: string; skill_id: string; skill_version?: string; workflow_step: string;
    allowed_tools?: string[]; forbidden_tools?: string[]; template_ids?: string[];
    scope?: Record<string, any>; selected_engine?: string | null; engine_reason?: string | null;
    output_mode?: string; stop_when?: string[]; route_reason?: string; route_type?: string;
  } | null;
  /** 评审 P2-2：策略事件（policy.rejected）与模板事件（template.bound/drift）追加去重累积 */
  policy_events?: Array<{ kind?: string; tool_call_id?: string; tool_name?: string; reason?: string; attempt?: number; blocked?: boolean; detail?: string }>;
  template_events?: Array<{ kind?: string; detail?: string; structure_match?: boolean; template_id?: string }>;
  /** 融合设计 M3 G7：证据链（路由/表/示例命中/验证/自评/纠错）+ 置信度三级（高/中/低） */
  evidence?: {
    route?: string | null;
    tables?: string[];
    examples_used?: Array<{ q?: string; sim?: number }>;
    verification?: { row_count?: number; null_rates?: Record<string, number>; warnings?: string[] } | null;
    rubric?: { status?: string; iterations?: number } | null;
    corrections?: number;
  } | null;
  confidence?: string;   // 高 / 中 / 低
  /** 融合 M3 G7 实时事件缓存（query_verified / rubric 流式中间态，终态以 evidence 快照为准） */
  verification_live?: { row_count?: number; null_rates?: Record<string, number>; warnings?: string[] } | null;
  rubric_live?: { status?: string; iterations?: number; feedback_summary?: string; confidence?: string } | null;
};

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  text?: string;
  loading?: boolean;
  payload?: ChatMessagePayload;
};

export type ConversationSceneConfig = {
  sceneCode: string;
  pageCode: string;
  conversationTitle: string;
  pageTitle: string;
  assistantName?: string;
  emptyMessage?: string;
  emptyDescription?: string;
  placeholder?: string;
  exampleQueries?: string[];
  sendButtonText?: string;
  clearButtonText?: string;
  chatCardTitle?: string;
  inputCardTitle?: string;
  chatHeight?: number;
  runtime?: ConversationSceneRuntimeConfig;
};

export type ConversationSubmitOptions = {
  userText: string;
  inputPayload?: any;
  initialLoadingText?: string;
  runStartedText?: string;
  stepStartedText?: (args: { payload: any; prev: ChatMessage }) => string | undefined;
  stepCompletedText?: (args: { payload: any; completedCount: number; prev: ChatMessage }) => string | undefined;
  stepFailedText?: (args: { payload: any; prev: ChatMessage }) => string | undefined;
  failedText?: string;
  interruptedText?: string;
  errorToastText?: string;
  successToastText?: string;
  shouldShowSuccessToast?: (args: { payload: any; assistantPayload: ChatMessagePayload }) => boolean;
  buildAssistantPayload?: (runData: any, events: RunEventRecord[]) => ChatMessagePayload;
  buildAssistantText?: (payload?: ChatMessagePayload) => string;
};

export type ConversationSceneRuntimeConfig = {
  buildSubmitOptions: (args: {
    userText: string;
    runtimeState?: Record<string, any>;
  }) => Omit<ConversationSubmitOptions, 'userText'>;
};
