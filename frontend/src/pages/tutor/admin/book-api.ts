/**
 * 1:1 复刻自 DeepTutor web/lib/book-api.ts（tupu 批8 book 页依赖）。
 * 替换点：
 * 1) 移除原仓 lib/api 的 apiFetch/apiUrl/wsUrl 依赖：apiFetch→原生 fetch
 *    （同源请求默认携带 cookie）、apiUrl(x) 一律脱壳为 x 相对路径
 *    （由 setupProxy.js 转发到后端 28000）；
 * 2) WebSocket URL：wsUrl(`${BASE}/ws`) 改为
 *    (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + `${BASE}/ws`
 *    同路径拼接；
 * 3) 对 book-ws-operation / book-types 的导入改为同目录相对导入
 *    './book-ws-operation' / './book-types'；
 * 其余 endpoint 路径 / method / headers / body / 导出名逐字保留，未裁剪。
 */

import {
  runBookSocketOperation,
  type BookWsEvent,
} from "./book-ws-operation";
import type {
  Book,
  BookDetail,
  BookProposal,
  Page,
  Spine,
  Block,
} from "./book-types";

const BASE = "/api/v1/book";

function requestOverSocket<T extends BookWsEvent>(
  message: BookWsEvent,
  resultType: string,
  onEvent?: (event: BookWsEvent) => void,
): Promise<T> {
  return runBookSocketOperation<T>(
    () =>
      new WebSocket(
        (location.protocol === "https:" ? "wss://" : "ws://") +
          location.host +
          `${BASE}/ws`,
      ),
    {
      message,
      resultType,
      onEvent,
    },
  );
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
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
    requestOverSocket<{
      type: "create_result";
      book: Book;
      proposal: BookProposal;
    }>({ type: "create", ...payload }, "create_result", onEvent),
  confirmProposal: (
    book_id: string,
    proposal?: BookProposal,
    onEvent?: (event: BookWsEvent) => void,
  ) =>
    requestOverSocket<{
      type: "confirm_proposal_result";
      book: Book;
      spine: Spine;
    }>(
      { type: "confirm_proposal", book_id, proposal: proposal ?? null },
      "confirm_proposal_result",
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
    requestOverSocket<{ type: "compile_page_result"; page: Page }>(
      { type: "compile_page", book_id, page_id, force },
      "compile_page_result",
      onEvent,
    ),
  regenerateBlock: (
    book_id: string,
    page_id: string,
    block_id: string,
    params_override?: Record<string, unknown>,
    onEvent?: (event: BookWsEvent) => void,
  ) =>
    requestOverSocket<{
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
      "regenerate_block_result",
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
  const res = await fetch(
    `/api/v1/chat/sessions/${encodeURIComponent(session_id)}`,
  );
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`chat session ${session_id} → ${res.status}`);
  return (await res.json()) as LegacyChatSession;
}

// Re-exported so callers can keep importing the event type from book-api.
export type { BookWsEvent } from "./book-ws-operation";
