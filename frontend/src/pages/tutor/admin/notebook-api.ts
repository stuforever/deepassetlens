/**
 * notebook-api.ts —— 使用面复刻（1:1 复刻被引用链）
 *
 * 来源：DeepTutor web/lib/notebook-api.ts（383 行）
 * 复刻范围：仅保留 BookCreator 引用链上的导出——
 *   - 函数：listNotebooks / getNotebook / listNotebookEntries / listCategories
 *   - 类型：NotebookRecordType / NotebookSummary / NotebookRecordItem / NotebookDetail /
 *           NotebookAnswerImage / NotebookEntry / NotebookCategory / NotebookEntryListResponse
 *   - 内部助手：expectJson
 * 裁剪掉的导出（BookCreator 未使用）：createNotebook / updateNotebook / deleteNotebook /
 *   deleteNotebookRecord / getNotebookEntry / lookupNotebookEntry / updateNotebookEntry /
 *   upsertNotebookEntry / deleteNotebookEntry / addEntryToCategory / removeEntryFromCategory /
 *   createCategory / renameCategory / deleteCategory / NotebookAnswerImageUpload。
 *
 * 替换点：apiFetch(apiUrl("/api/v1/...")) → fetch('/api/v1/...')
 *   （tupu 同源代理转发，fetch 默认 same-origin 携带 cookie，与原 credentials:'include' 等价；
 *     原 apiFetch 的 401→/login 跳转为 DeepTutor 鉴权专属，不复刻）
 * 函数体其余逐字保留。
 */

// ── Real notebook system (file-backed under data/user/workspace/notebook) ──
//
// Notebooks created in the Knowledge → Notebooks tab and consumed everywhere
// chat output is saved (SaveToNotebookModal) or referenced
// (NotebookRecordPicker) live in this system. They are distinct from the
// "Question Notebook" categories below which only track quiz entries.

export type NotebookRecordType =
  | "solve"
  | "question"
  | "research"
  | "chat"
  | "co_writer"
  | "tutorbot";

export interface NotebookSummary {
  id: string;
  name: string;
  description?: string;
  color?: string;
  icon?: string;
  record_count?: number;
  created_at?: number;
  updated_at?: number;
}

export interface NotebookRecordItem {
  id: string;
  type: NotebookRecordType | string;
  title: string;
  summary?: string;
  user_query: string;
  output: string;
  metadata?: Record<string, unknown>;
  created_at?: number;
  kb_name?: string | null;
}

export interface NotebookDetail extends NotebookSummary {
  records: NotebookRecordItem[];
}

export async function listNotebooks(): Promise<NotebookSummary[]> {
  const response = await fetch("/api/v1/notebook/list", {
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  const data = (await response.json()) as { notebooks: NotebookSummary[] };
  return data.notebooks ?? [];
}

export async function getNotebook(notebookId: string): Promise<NotebookDetail> {
  const response = await fetch(`/api/v1/notebook/${notebookId}`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return (await response.json()) as NotebookDetail;
}

// ── Question notebook (quiz entries + categories) ─────────────────

export interface NotebookAnswerImage {
  id: string;
  url: string;
  filename: string;
  mime_type: string;
}

export interface NotebookEntry {
  id: number;
  session_id: string;
  session_title: string;
  turn_id: string;
  question_id: string;
  question: string;
  question_type: string;
  options: Record<string, string>;
  correct_answer: string;
  explanation: string;
  difficulty: string;
  user_answer: string;
  user_answer_images?: NotebookAnswerImage[];
  is_correct: boolean;
  bookmarked: boolean;
  followup_session_id: string;
  /** Latest AI-judge text for this entry; empty when never run. */
  ai_judgment?: string;
  created_at: number;
  updated_at: number;
  categories?: NotebookCategory[];
}

export interface NotebookCategory {
  id: number;
  name: string;
  created_at: number;
  entry_count: number;
}

export interface NotebookEntryListResponse {
  items: NotebookEntry[];
  total: number;
}

async function expectJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

// ── Entries ──────────────────────────────────────────────────────

export async function listNotebookEntries(
  filter: {
    category_id?: number;
    bookmarked?: boolean;
    is_correct?: boolean;
    limit?: number;
    offset?: number;
  } = {},
): Promise<NotebookEntryListResponse> {
  const params = new URLSearchParams();
  if (filter.category_id !== undefined)
    params.set("category_id", String(filter.category_id));
  if (filter.bookmarked !== undefined)
    params.set("bookmarked", String(filter.bookmarked));
  if (filter.is_correct !== undefined)
    params.set("is_correct", String(filter.is_correct));
  if (filter.limit !== undefined) params.set("limit", String(filter.limit));
  if (filter.offset !== undefined) params.set("offset", String(filter.offset));
  const query = params.toString();
  const response = await fetch(
    `/api/v1/question-notebook/entries${query ? `?${query}` : ""}`,
    { cache: "no-store" },
  );
  return expectJson<NotebookEntryListResponse>(response);
}

// ── Categories ──────────────────────────────────────────────────

export async function listCategories(): Promise<NotebookCategory[]> {
  const response = await fetch("/api/v1/question-notebook/categories", {
    cache: "no-store",
  });
  return expectJson<NotebookCategory[]>(response);
}
