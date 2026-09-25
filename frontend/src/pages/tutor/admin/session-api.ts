/**
 * 1:1 复刻自 DeepTutor web/lib/session-api.ts（tupu 批8 book 页依赖）。
 * 替换点：
 * 1) 移除原仓 lib/api 的 apiFetch/apiUrl 依赖：apiFetch→原生 fetch（同源请求
 *    默认携带 cookie）、apiUrl(x) 一律脱壳为 x 相对路径（由 setupProxy.js
 *    转发到后端 28000）；
 * 2) 原仓 client-cache（withClientCache / invalidateClientCache）与 unified-ws
 *    （StreamEventType / StreamEvent / LLMSelection）按使用面
 *    内联到本文件（定义逐字保留、不对外导出，导出面与原 session-api.ts 完全
 *    一致，未裁剪任何函数）；
 * 3) 仅新增本文件头注释；
 * 4) tupu 适配（2026-09-18，C3 补网）：全部裸 fetch 增补 authHeaders() Bearer 注入
 *    （原仓 cookie 会话在 tupu auth=1 Bearer 执法下恒 401 -> expectJson 硬跳 /login）；
 * 其余 endpoint 路径 / method / headers / body / query / 导出名逐字保留。
 */

// ---- 以下类型按使用面内联自 DeepTutor web/lib/unified-ws.ts（定义逐字保留）----

import { getAccessToken } from "../../../auth/st";

type StreamEventType =
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
  | "error"
  | "session"
  | "session_meta"
  | "done";

interface StreamEvent {
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

interface LLMSelection {
  profile_id: string;
  model_id: string;
}

// ---- 以下缓存工具按使用面内联自 DeepTutor web/lib/client-cache.ts（定义逐字保留）----

type CacheEntry<T> = {
  data?: T;
  promise?: Promise<T>;
  expiresAt: number;
};

const clientCache = new Map<string, CacheEntry<unknown>>();

interface CacheOptions {
  ttlMs?: number;
  force?: boolean;
}

async function withClientCache<T>(
  key: string,
  loader: () => Promise<T>,
  options: CacheOptions = {},
): Promise<T> {
  const { ttlMs = 30_000, force = false } = options;

  if (typeof window === "undefined") {
    return loader();
  }

  const now = Date.now();
  const cached = clientCache.get(key) as CacheEntry<T> | undefined;
  if (!force && cached) {
    if (cached.data !== undefined && cached.expiresAt > now) {
      return cached.data;
    }
    if (cached.promise) {
      return cached.promise;
    }
  }

  const promise = loader()
    .then((value) => {
      clientCache.set(key, {
        data: value,
        expiresAt: Date.now() + ttlMs,
      });
      return value;
    })
    .catch((error) => {
      clientCache.delete(key);
      throw error;
    });

  clientCache.set(key, {
    promise,
    expiresAt: now + ttlMs,
  });

  return promise;
}

function invalidateClientCache(prefix: string): void {
  // Array.from 包裹：MapIterator 在本仓 tsconfig target=es5 下不可直接 for-of（TS2802），语义等价
  for (const key of Array.from(clientCache.keys())) {
    if (key.startsWith(prefix)) {
      clientCache.delete(key);
    }
  }
}

// ---- 以下为原 session-api.ts 正文（除 fetch 脱壳外逐字保留）----

export interface SessionMessage {
  id: number;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  capability?: string;
  events: StreamEvent[];
  attachments: Array<{
    type: string;
    filename?: string;
    base64?: string;
    url?: string;
    mime_type?: string;
    id?: string;
    extracted_text?: string;
    generated?: boolean;
    size_bytes?: number;
  }>;
  metadata?: Record<string, unknown>;
  created_at: number;
  /** Edit-branching: id of the message this row continues. `null` for the
   *  first message in a session. Siblings share the same parent. */
  parent_message_id?: number | null;
}

export interface SessionSummary {
  id: string;
  session_id: string;
  title: string;
  created_at: number;
  updated_at: number;
  message_count: number;
  last_message: string;
  status?:
    | "idle"
    | "running"
    | "completed"
    | "failed"
    | "cancelled"
    | "rejected";
  active_turn_id?: string;
  preferences?: {
    capability?: string;
    tools?: string[];
    knowledge_bases?: string[];
    language?: string;
    llm_selection?: LLMSelection | null;
    /** Session-level persona preference; "" / absent = Default (no persona). */
    persona?: string;
    /** Edit-branching: maps a parent_message_id → the child id currently
     *  shown at that branch point. Missing keys default to the latest
     *  sibling (most recently created child). */
    selected_branches?: Record<string, number>;
  };
}

export interface ActiveTurnSummary {
  id: string;
  turn_id: string;
  session_id: string;
  capability: string;
  status: "running" | "completed" | "failed" | "cancelled" | "rejected";
  error: string;
  created_at: number;
  updated_at: number;
  finished_at?: number | null;
  last_seq: number;
}

export interface SessionDetail {
  id: string;
  session_id: string;
  title: string;
  created_at: number;
  updated_at: number;
  status?:
    | "idle"
    | "running"
    | "completed"
    | "failed"
    | "cancelled"
    | "rejected";
  active_turn_id?: string;
  compressed_summary?: string;
  summary_up_to_msg_id?: number;
  preferences?: {
    capability?: string;
    tools?: string[];
    knowledge_bases?: string[];
    language?: string;
    llm_selection?: LLMSelection | null;
    /** Session-level persona preference; "" / absent = Default (no persona). */
    persona?: string;
    /** Edit-branching: maps a parent_message_id → the child id currently
     *  shown at that branch point. Missing keys default to the latest
     *  sibling (most recently created child). */
    selected_branches?: Record<string, number>;
  };
  messages: SessionMessage[];
  active_turns?: ActiveTurnSummary[];
}

export interface QuizResultItem {
  question_id?: string;
  question: string;
  question_type?: string;
  options?: Record<string, string>;
  user_answer: string;
  correct_answer: string;
  explanation?: string;
  difficulty?: string;
  is_correct: boolean;
}

async function expectJson<T>(response: Response): Promise<T> {
  if (response.status === 401 && typeof window !== "undefined") {
    const next = encodeURIComponent(window.location.pathname);
    window.location.href = `/login?next=${next}`;
    return new Promise(() => {});
  }
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

// tupu 适配（2026-09-18 C3 补网）：后端执法只认 Bearer（auth=1 新常态），本文件原为
// cookie 裸 fetch，未带 token 的 sessions 调用一律 401 -> expectJson 硬跳 /login 死循环。
function authHeaders(): Record<string, string> {
  try {
    const t = getAccessToken();
    return t ? { Authorization: `Bearer ${t}` } : {};
  } catch {
    return {};
  }
}

export async function listSessions(
  limit = 50,
  offset = 0,
  options?: { force?: boolean },
): Promise<SessionSummary[]> {
  const qs = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return withClientCache<SessionSummary[]>(
    `sessions:${limit}:${offset}`,
    async () => {
      const response = await fetch(`/api/v1/sessions?${qs.toString()}`, {
        cache: "no-store",
        headers: authHeaders(),
      });
      const data = await expectJson<{ sessions: SessionSummary[] }>(response);
      return data.sessions ?? [];
    },
    {
      force: options?.force,
      ttlMs: 15_000,
    },
  );
}

export async function getSession(
  sessionId: string,
  signal?: AbortSignal,
  u?: string,
): Promise<SessionDetail> {
  const qs = u ? `?u=${encodeURIComponent(u)}` : "";
  const response = await fetch(`/api/v1/sessions/${sessionId}${qs}`, {
    cache: "no-store",
    signal,
    headers: authHeaders(),
  });
  return expectJson<SessionDetail>(response);
}

export async function updateSessionTitle(
  sessionId: string,
  title: string,
): Promise<SessionDetail> {
  const response = await fetch(`/api/v1/sessions/${sessionId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ title }),
  });
  const data = await expectJson<{ session: SessionDetail }>(response);
  invalidateClientCache("sessions:");
  return data.session;
}

export async function deleteSession(sessionId: string): Promise<void> {
  const response = await fetch(`/api/v1/sessions/${sessionId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  await expectJson<{ deleted: boolean }>(response);
  invalidateClientCache("sessions:");
}

export async function recordQuizResults(
  sessionId: string,
  answers: QuizResultItem[],
  turnId?: string | null,
): Promise<void> {
  const response = await fetch(`/api/v1/sessions/${sessionId}/quiz-results`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ answers, turn_id: turnId || "" }),
  });
  await expectJson<{ recorded: boolean }>(response);
}

export async function deleteMessage(
  sessionId: string,
  messageId: number,
): Promise<void> {
  const response = await fetch(
    `/api/v1/sessions/${sessionId}/messages/${messageId}`,
    { method: "DELETE", headers: authHeaders() },
  );
  await expectJson<{ deleted: boolean }>(response);
}

export async function updateBranchSelection(
  sessionId: string,
  selectedBranches: Record<string, number>,
): Promise<void> {
  const response = await fetch(
    `/api/v1/sessions/${sessionId}/branch-selection`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ selected_branches: selectedBranches }),
    },
  );
  await expectJson<{ selected_branches: Record<string, number> }>(response);
}
