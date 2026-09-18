/**
 * 复刻自 DeepTutor 原仓 web/lib/unified-ws.ts（类型面：StreamEvent/LLMSelection/ChatMessage）。
 * 引擎批6补漏：UnifiedWSClient 类体已删（vendor WS 引擎清除，L7 断言③），类型保留——复刻件契约零改。
 */

// ---- StreamEvent types (mirror Python StreamEventType) ----

export type StreamEventType =
  | "stage_start"
  | "stage_end"
  | "thinking"
  | "observation"
  | "content"
  | "tool_call"
  | "tool_result"
  | "progress"
  | "sources"
  | "result"
  | "confirmation_card"
  | "error"
  | "session"
  | "session_meta"
  | "done";

export interface StreamEvent {
  type: StreamEventType;
  source: string;
  stage: string;
  content: string;
  metadata: Record<string, unknown>;
  session_id?: string;
  turn_id?: string;
  seq?: number;
  timestamp: number;
}

export interface LLMSelection {
  profile_id: string;
  model_id: string;
}

// ---- Client message ----

export interface StartTurnMessage {
  type: "message" | "start_turn";
  content: string;
  tools?: string[];
  capability?: string | null;
  knowledge_bases?: string[];
  session_id?: string | null;
  attachments?: {
    type: string;
    url?: string;
    base64?: string;
    filename?: string;
    mime_type?: string;
  }[];
  language?: string;
  config?: Record<string, unknown>;
  notebook_references?: {
    notebook_id: string;
    record_ids: string[];
  }[];
  history_references?: string[];
  question_notebook_references?: number[];
  book_references?: {
    book_id: string;
    page_ids: string[];
  }[];
  persona?: string;
  llm_selection?: LLMSelection | null;
  /** H5 用户标识：后端据此切到 h5 用户上下文（MU-3 会话隔离）。 */
  u?: string;
  /** H5 访问码（P3-B/R4）：后端 h5_user_guarded 校验用；未设码时缺省。 */
  code?: string;
  /** Edit-branching: when present (even as ``null``) the new user message
   *  attaches at this exact parent — creating a sibling rather than
   *  appending to the session tail. */
  parent_message_id?: number | null;
}

export interface SubscribeTurnMessage {
  type: "subscribe_turn";
  turn_id: string;
  after_seq?: number;
}

export interface SubscribeSessionMessage {
  type: "subscribe_session";
  session_id: string;
  after_seq?: number;
}

export interface ResumeTurnMessage {
  type: "resume_from";
  turn_id: string;
  seq?: number;
}

export interface UnsubscribeMessage {
  type: "unsubscribe";
  turn_id?: string;
  session_id?: string;
}

export interface CancelTurnMessage {
  type: "cancel_turn";
  turn_id: string;
}

export interface RegenerateMessage {
  type: "regenerate";
  session_id: string;
  overrides?: Record<string, unknown>;
  /** H5 用户标识（MU-3）：后端据此切 h5 上下文再执行 regenerate。 */
  u?: string;
  /** H5 访问码（P3-B/R4）：后端 h5_user_guarded 校验用；未设码时缺省。 */
  code?: string;
}

/**
 * Deliver the user's answer for an ``ask_user`` paused turn so the
 * agentic loop can resume on the same turn. The user's reply is
 * substituted into the matching ``role=tool`` message body before the
 * next LLM iteration runs.
 *
 * Either ``text`` (legacy single-question shape) or ``answers``
 * (v2 multi-question shape) must be provided. When both are present
 * the backend prefers ``answers``.
 */
export interface SubmitUserReplyMessage {
  type: "submit_user_reply";
  turn_id: string;
  text?: string;
  answers?: Array<{ questionId: string; text: string }>;
}

export type ChatMessage =
  | StartTurnMessage
  | SubscribeTurnMessage
  | SubscribeSessionMessage
  | ResumeTurnMessage
  | UnsubscribeMessage
  | CancelTurnMessage
  | RegenerateMessage
  | SubmitUserReplyMessage;

// ---- Connection manager ----

export type EventHandler = (event: StreamEvent) => void;

/* 引擎批6补漏：UnifiedWSClient 类体已删（vendor WS 引擎清除，L7 断言③）；
 * StreamEvent/LLMSelection/ChatMessage 等类型保留——30+ 复刻件契约零改。 */
