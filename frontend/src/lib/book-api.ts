import { apiFetch, apiUrl } from "./api";
import type { BookWsEvent } from "./book-ws-operation";
import type {
  Book,
  BookDetail,
  BookProposal,
  Page,
  Spine,
  Block,
} from "./book-types";

const BASE = "/api/v1/book";

/**
 * 引擎批5 5.3：生成类操作切桥（E-25）——原 WS requestOverSocket（runBookSocketOperation）
 * 删除，改为 POST /api/v2/skills/capability（skill_code=tutor/book-generate）SSE 消费。
 * 帧映射：metadata.ws_event→onEvent（BookWsEvent 同型）；result.metadata.ws_result→resolve；
 * error→reject。接口签名与原函数一致，调用点零改动。
 */
async function requestOverBridge<T>(
  message: Record<string, unknown>,
  onEvent?: (event: BookWsEvent) => void,
): Promise<T> {
  // R5批③：裸 fetch → apiFetch（credentials:include + 401 统一门控）——auth=ON 部署生成类操作此前不携带会话凭据
  const resp = await apiFetch(apiUrl("/api/v2/skills/capability"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      skill_code: "sishu/book-generate",
      message: String(message.type || "book_op"),
      config: { ...message },
    }),
  });
  if (!resp.ok || !resp.body) throw new Error(`book bridge HTTP ${resp.status}`);
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let result: T | null = null;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const raw = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      for (const line of raw.split("\n")) {
        if (!line.startsWith("data:")) continue;
        let ev: {
          type?: string;
          content?: string;
          metadata?: Record<string, unknown>;
        };
        try {
          ev = JSON.parse(line.slice(5).trim());
        } catch {
          continue;
        }
        const md = ev.metadata || {};
        if (md.ws_event) {
          onEvent?.(md.ws_event as unknown as BookWsEvent);
        } else if (ev.type === "result" && md.ws_result) {
          result = md.ws_result as T;
        } else if (ev.type === "error") {
          throw new Error(ev.content || "book bridge error");
        }
      }
    }
  }
  if (result === null) throw new Error("book bridge: 未收到结果帧");
  return result;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await apiFetch(apiUrl(`${BASE}${path}`), {
    // R5批③：...init 前置——原顺序下 init.headers 会整体覆盖预合并的 Content-Type/自定义头
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    let detail: string;
    try {
      const data = await res.json();
      detail = (data && (data.detail || data.message)) || res.statusText;
    } catch {
      detail = res.statusText;
    }
    throw new Error(`book api ${path} → ${res.status}: ${detail}`);
  }
  return (await res.json()) as T;
}

export interface CreateBookPayload {
  user_intent: string;
  chat_session_id?: string;
  chat_selections?: Array<{ session_id: string; message_ids: number[] }>;
  notebook_refs?: Array<Record<string, unknown>>;
  knowledge_bases?: string[];
  question_categories?: number[];
  question_entries?: number[];
  language?: string;
}

export const bookApi = {
  list: () => request<{ books: Book[] }>("/books"),
  get: (book_id: string) =>
    request<BookDetail>(`/books/${encodeURIComponent(book_id)}`),
  delete: (book_id: string) =>
    request<{ deleted: boolean; book_id: string }>(
      `/books/${encodeURIComponent(book_id)}`,
      { method: "DELETE" },
    ),
  getSpine: (book_id: string) =>
    request<{ spine: Spine }>(`/books/${encodeURIComponent(book_id)}/spine`),
  getPage: (book_id: string, page_id: string) =>
    request<{ page: Page }>(
      `/books/${encodeURIComponent(book_id)}/pages/${encodeURIComponent(page_id)}`,
    ),
  create: (
    payload: CreateBookPayload,
    onEvent?: (event: BookWsEvent) => void,
  ) =>
    requestOverBridge<{
      type: "create_result";
      book: Book;
      proposal: BookProposal;
    }>({ type: "create", ...payload }, onEvent),
  confirmProposal: (
    book_id: string,
    proposal?: BookProposal,
    onEvent?: (event: BookWsEvent) => void,
  ) =>
    requestOverBridge<{
      type: "confirm_proposal_result";
      book: Book;
      spine: Spine;
    }>(
      { type: "confirm_proposal", book_id, proposal: proposal ?? null },
      onEvent,
    ),
  confirmSpine: (book_id: string, spine?: Spine, auto_compile = true) =>
    request<{ pages: Page[] }>("/books/confirm-spine", {
      method: "POST",
      body: JSON.stringify({ book_id, spine: spine ?? null, auto_compile }),
    }),
  compilePage: (
    book_id: string,
    page_id: string,
    force = false,
    onEvent?: (event: BookWsEvent) => void,
  ) =>
    requestOverBridge<{ type: "compile_page_result"; page: Page }>(
      { type: "compile_page", book_id, page_id, force },
      onEvent,
    ),
  regenerateBlock: (
    book_id: string,
    page_id: string,
    block_id: string,
    params_override?: Record<string, unknown>,
    onEvent?: (event: BookWsEvent) => void,
  ) =>
    requestOverBridge<{
      type: "regenerate_block_result";
      block: Block | null;
    }>(
      {
        type: "regenerate_block",
        book_id,
        page_id,
        block_id,
        params_override: params_override ?? null,
      },
      onEvent,
    ),

  insertBlock: (params: {
    book_id: string;
    page_id: string;
    block_type: string;
    params?: Record<string, unknown>;
    position?: number;
    compile_now?: boolean;
  }) =>
    request<{ block: Block }>("/books/insert-block", {
      method: "POST",
      body: JSON.stringify({
        compile_now: true,
        ...params,
      }),
    }),

  deleteBlock: (book_id: string, page_id: string, block_id: string) =>
    request<{ ok: boolean }>("/books/delete-block", {
      method: "POST",
      body: JSON.stringify({ book_id, page_id, block_id }),
    }),

  moveBlock: (
    book_id: string,
    page_id: string,
    block_id: string,
    new_position: number,
  ) =>
    request<{ ok: boolean }>("/books/move-block", {
      method: "POST",
      body: JSON.stringify({ book_id, page_id, block_id, new_position }),
    }),

  changeBlockType: (params: {
    book_id: string;
    page_id: string;
    block_id: string;
    new_type: string;
    params_override?: Record<string, unknown>;
  }) =>
    request<{ block: Block }>("/books/change-block-type", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  deepDive: (params: {
    book_id: string;
    parent_page_id: string;
    topic: string;
    block_id?: string;
    content_type?: string;
  }) =>
    request<{ page: Page }>("/books/deep-dive", {
      method: "POST",
      body: JSON.stringify({ content_type: "concept", ...params }),
    }),

  recordQuizAttempt: (params: {
    book_id: string;
    page_id: string;
    block_id: string;
    question_id?: string;
    user_answer?: string;
    is_correct: boolean;
  }) =>
    request<{ progress: Record<string, unknown> }>("/books/quiz-attempt", {
      method: "POST",
      body: JSON.stringify(params),
    }),

  supplement: (book_id: string, page_id: string, topic: string) =>
    request<{ block: Block }>("/books/supplement", {
      method: "POST",
      body: JSON.stringify({ book_id, page_id, topic }),
    }),

  setPageChatSession: (book_id: string, page_id: string, session_id: string) =>
    request<{ book: Book }>("/books/page-chat-session", {
      method: "POST",
      body: JSON.stringify({ book_id, page_id, session_id }),
    }),

  rebuild: (book_id: string, auto_compile = true) =>
    request<{ pages: Page[] }>("/books/rebuild", {
      method: "POST",
      body: JSON.stringify({ book_id, auto_compile }),
    }),

  health: (book_id: string) =>
    request<{
      kb_drift: {
        book_id: string;
        has_drift: boolean;
        new_kbs?: string[];
        removed_kbs?: string[];
        changed_kbs?: string[];
        stale_page_ids?: string[];
      };
      log_health: {
        book_id: string;
        total_entries: number;
        error_entries: number;
        block_failures: number;
        last_compile_at?: string;
        last_error_at?: string;
        repeated_failures?: { signature: string; count: number }[];
      };
    }>(`/books/${encodeURIComponent(book_id)}/health`),

  refreshFingerprints: (book_id: string) =>
    request<{
      book_id: string;
      kb_fingerprints: Record<string, string>;
      stale_page_ids: string[];
    }>(`/books/${encodeURIComponent(book_id)}/refresh-fingerprints`, {
      method: "POST",
    }),
};

export interface LegacyChatSession {
  session_id: string;
  messages?: Array<{ role: string; content: string }>;
}

export async function getLegacyChatSession(
  session_id: string,
): Promise<LegacyChatSession | null> {
  const res = await apiFetch(
    apiUrl(`/api/v1/chat/sessions/${encodeURIComponent(session_id)}`),
  );
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`chat session ${session_id} → ${res.status}`);
  return (await res.json()) as LegacyChatSession;
}

// Re-exported so callers can keep importing the event type from book-api.
export type { BookWsEvent } from "./book-ws-operation";
