/**
 * ── 复刻来源与替换点（tupu antd 复刻，批9 F2 / SA-D）────────────────────────
 * 源文件：DeepTutor web/lib/learning-api.ts
 * 目标：frontend/src/pages/tutor/h5/h5shared/learningApi.ts（1:1 复刻，逻辑逐字保留）
 * 替换点：
 * - 移除原仓 lib/api 依赖：apiFetch(apiUrl(x), init) → fetch(x, init)（apiUrl 为
 *   pass-through 恒等；apiFetch 的唯一运行时效果 credentials:"include" 显式保留，
 *   401 重定向门依赖 runtimeAuthEnabled，tupu 无 auth.ts 恒为 false，等价省略）；
 * - 文件名按 tupu 命名惯例 learningApi.ts，导出名全部逐字保留（含 generateModulesFromNotebook
 *   等本组未直接消费的导出——完整移植供后续批共用，未裁剪）。
 * ─────────────────────────────────────────────────────────────────────
 */

/** 追加 H5 用户标识（缺省空 => 与桌面现状完全一致）。 */
function uQs(u: string): string {
  return u ? `?u=${encodeURIComponent(u)}` : "";
}

export interface ModuleInit {
  id: string;
  name: string;
  order: number;
  pass_threshold?: number;
  knowledge_points: {
    id: string;
    name: string;
    type: string;
    module_id: string;
  }[];
}

export interface LearningKnowledgePoint {
  id: string;
  name: string;
  type: string;
}

export interface LearningModule {
  id: string;
  name: string;
  order: number;
  pass_threshold: number;
  knowledge_points: LearningKnowledgePoint[];
}

export interface ProgressDetail {
  book_id: string;
  modules: LearningModule[];
  mastery_levels: Record<string, number>;
  current_module_id?: string;
  current_stage?: string;
  diagnostic?: unknown;
}

export async function fetchProgress(
  bookId: string,
  u = "",
): Promise<ProgressDetail> {
  const res = await fetch(
    `/api/v1/learning/progress/${bookId}${uQs(u)}`,
    { credentials: "include" },
  );
  if (!res.ok) throw new Error(`Failed to fetch progress: ${res.status}`);
  return res.json() as Promise<ProgressDetail>;
}

export async function initModules(
  bookId: string,
  modules: ModuleInit[],
  u = "",
) {
  const res = await fetch(
    `/api/v1/learning/progress/${bookId}/init-modules${uQs(u)}`,
    {
      credentials: "include",
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ modules }),
    },
  );
  if (!res.ok) throw new Error(`Failed to init modules: ${res.status}`);
  return res.json();
}

// ── Mastery map (the dashboard view) ──────────────────────────────────────
// Mirrors deeptutor/learning/policy.py map_summary + next_objective.

export type ObjectiveStatus = "new" | "learning" | "mastered";

export interface MapKnowledgePoint {
  id: string;
  name: string;
  type: string;
  status: ObjectiveStatus;
  mastery: number;
}

export interface MapModule {
  id: string;
  name: string;
  order: number;
  mastered: number;
  total: number;
  knowledge_points: MapKnowledgePoint[];
}

export interface MasteryMap {
  counts: { mastered: number; learning: number; new: number; total: number };
  due_reviews: number;
  complete: boolean;
  modules: MapModule[];
}

export interface NextStep {
  action: string;
  knowledge_point_name: string;
  knowledge_point_type: string;
  status: string;
  mastery: number;
  threshold: number;
  reason: string;
}

export interface MasteryMapResult {
  book_id: string;
  next: NextStep;
  map: MasteryMap;
}

export async function fetchMasteryMap(
  pathId: string,
  u = "",
): Promise<MasteryMapResult> {
  const res = await fetch(
    `/api/v1/learning/progress/${encodeURIComponent(pathId)}/map${uQs(u)}`,
    { credentials: "include" },
  );
  if (!res.ok) throw new Error(`Failed to fetch mastery map: ${res.status}`);
  return res.json() as Promise<MasteryMapResult>;
}

export interface ProgressSummary {
  book_id: string;
  name: string;
  modules_count: number;
  kp_count: number;
  current_stage: string;
  avg_mastery_pct: number;
  updated_at: number;
}

export interface ProgressListResult {
  summaries: ProgressSummary[];
  errors: { book_id: string; error: string }[];
}

export async function fetchAllProgress(u = ""): Promise<ProgressListResult> {
  const res = await fetch(`/api/v1/learning/progress${uQs(u)}`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Failed to fetch all progress: ${res.status}`);
  return res.json();
}

export async function deleteProgress(bookId: string, u = "") {
  const res = await fetch(
    `/api/v1/learning/progress/${encodeURIComponent(bookId)}${uQs(u)}`,
    { credentials: "include", method: "DELETE" },
  );
  if (!res.ok) throw new Error(`Failed to delete progress: ${res.status}`);
  return res.json();
}

export async function redoProgress(bookId: string, u = "") {
  const res = await fetch(
    `/api/v1/learning/progress/${encodeURIComponent(bookId)}/redo${uQs(u)}`,
    { credentials: "include", method: "POST" },
  );
  if (!res.ok) throw new Error(`Failed to redo progress: ${res.status}`);
  return res.json();
}

export async function importFromBook(
  bookId: string,
  chapters: { title: string; knowledge_points: string[] }[],
  u = "",
) {
  const res = await fetch(
    `/api/v1/learning/progress/${encodeURIComponent(bookId)}/import-from-book${uQs(u)}`,
    {
      credentials: "include",
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chapters }),
    },
  );
  if (!res.ok) throw new Error(`Failed to import from book: ${res.status}`);
  return res.json();
}

export async function generateModulesFromNotebook(
  bookId: string,
  notebookId: string,
  records: { id: string; type: string; title: string; output: string }[],
): Promise<{ modules: ModuleInit[] }> {
  const res = await fetch(
    `/api/v1/learning/progress/${encodeURIComponent(bookId)}/generate-from-notebook`,
    {
      credentials: "include",
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ notebook_id: notebookId, records }),
    },
  );
  if (!res.ok)
    throw new Error(`Failed to generate modules from notebook: ${res.status}`);
  return res.json();
}
