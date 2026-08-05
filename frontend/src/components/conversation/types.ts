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
  recommendations?: Array<{ label: string; shortcut?: string }>;
  completedTasks?: string[];
  confirmed?: Record<string, any>;
  sqlExecuted?: boolean;
  sql_result?: { columns?: string[]; rows?: any[]; row_count?: number; sql?: string } | null;
  traceLogs?: any[];
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
