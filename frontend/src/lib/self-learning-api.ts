/** Self-directed Learning API - chapter-centric data fetching. */

import { apiUrl } from "./api";

// ---- Types ----

export interface TextbookNode {
  id: string;
  name: string;
  subject: string;
  grade: string | null;
  publisher: string | null;
  version: string | null;
  chapters: ChapterNode[];
}

export interface ChapterNode {
  id: string;
  textbook_id: string;
  parent_id: string | null;
  name: string;
  order: number;
  kp_ids: string[];
  page_start: number | null;
  page_end: number | null;
  children: ChapterNode[];
}

export interface KnowledgePointSummary {
  id: string;
  name: string;
  subject: string;
  grade: string | null;
  difficulty: number | null;
  path: string;
  description: string | null;
  explanation: string | null;
  examples: { title: string; content: string }[];
  formula: { name: string; latex: string; derivation: string } | null;
  figure: { type: string; config?: Record<string, unknown> } | null;
  related: { kp_id: string; relation: string; name: string }[];
}

export interface ChapterOverview {
  chapter: {
    id: string;
    name: string;
    textbook_id: string;
    parent_id: string | null;
    order: number;
    page_start: number | null;
    page_end: number | null;
    kp_ids: string[];
  };
  textbook: {
    id: string | null;
    name: string;
    subject: string;
    grade: string | null;
  };
  children: { id: string; name: string; order: number }[];
  knowledge_points: KnowledgePointSummary[];
  wrong_questions: {
    count: number;
    recent: { id: string; title: string; difficulty: number; mastery_status: string | null }[];
  };
  related_books: { id: string; title: string; status: string; page_count: number; chapter_count: number }[];
  mastery_progress: { book_id: string; total_modules: number; matched_modules: number; completed: number } | null;
}

// ---- API calls ----

export async function fetchTextbookTree(): Promise<TextbookNode[]> {
  const res = await fetch(apiUrl("/api/v1/self-learning/textbooks"));
  if (!res.ok) throw new Error("Failed to fetch textbooks");
  return res.json();
}

export async function fetchChapterOverview(chapterId: string, u?: string): Promise<ChapterOverview> {
  const qs = u ? `?u=${encodeURIComponent(u)}` : "";
  const res = await fetch(apiUrl(`/api/v1/self-learning/chapter/${chapterId}${qs}`));
  if (!res.ok) throw new Error("Failed to fetch chapter overview");
  return res.json();
}

export async function fetchWrongQuestionsByChapter(chapterId: string, u?: string) {
  const qs = u ? `&u=${encodeURIComponent(u)}` : "";
  const res = await fetch(apiUrl(`/api/v1/mother-questions?chapter_id=${chapterId}&page_size=50${qs}`));
  if (!res.ok) throw new Error("Failed to fetch wrong questions");
  return res.json();
}

export async function fetchTextbookPages(textbookId: string) {
  const res = await fetch(apiUrl(`/api/v1/curriculum/textbooks/${textbookId}/pages`));
  if (!res.ok) return [];
  return res.json();
}

export async function fetchBooks() {
  const res = await fetch(apiUrl("/api/v1/book/books"));
  if (!res.ok) return [];
  const data = await res.json();
  return data.books || data || [];
}

export async function fetchMemoryL2() {
  const res = await fetch(apiUrl("/api/v1/memory/l2"));
  if (!res.ok) return null;
  return res.json();
}

export async function fetchMemoryL3() {
  const res = await fetch(apiUrl("/api/v1/memory/l3"));
  if (!res.ok) return null;
  return res.json();
}

// ---- Learner Profile (学情画像, design §3.2/§3.6) ----

export interface KpMasteryDto {
  kp_id: string;
  kp_name: string;
  subject: string;
  mastery: number;
  attempts: number;
  correct_rate: number;
  last_practiced_at?: number | null;
  next_review_at?: number | null;
  status: "new" | "learning" | "weak" | "mastered";
  error_types: string[];
}

export interface LearnerProfileDto {
  user_id: string;
  openid?: string;
  profile_openid?: string;
  kp_mastery: Record<string, KpMasteryDto>;
  weak_points: Array<{ kp_id: string; kp_name: string; mastery: number }>;
  strong_points: Array<{ kp_id: string; kp_name: string }>;
  due_reviews: Array<{ kp_id: string; kp_name: string; due_at: number; reason: string }>;
  streak_days: number;
  total_study_minutes: number;
  badges: Array<{ id: string; name: string; desc: string; icon: string }>;
  updated_at: number;
}

export async function fetchLearnerProfile(openid?: string): Promise<LearnerProfileDto | null> {
  try {
    const qs = openid ? `?openid=${encodeURIComponent(openid)}` : "";
    const res = await fetch(apiUrl(`/api/v1/learning/learner-profile${qs}`));
    if (!res.ok) return null;
    return (await res.json()) as LearnerProfileDto;
  } catch {
    return null;
  }
}

// ---- Chapter courseware book (one-click generate) ----

export interface ChapterBook {
  id: string;
  title: string;
  status: string;
  chapter_count: number;
  page_count: number;
  metadata?: Record<string, unknown>;
}

/** List books generated for this curriculum chapter (via metadata). */
export async function fetchChapterBooks(chapterId: string): Promise<ChapterBook[]> {
  const res = await fetch(apiUrl("/api/v1/book/books"));
  if (!res.ok) return [];
  const data = await res.json();
  const books: ChapterBook[] = data?.books || data || [];
  return books.filter(
    (b) =>
      b.status !== "archived" &&
      (b.metadata as Record<string, unknown> | undefined)?.curriculum_chapter_id ===
        chapterId,
  );
}

/** One-click create a chapter-scoped courseware book (async background compile). */
export async function createChapterBook(
  chapterId: string,
): Promise<{ book_id: string; status: string; reused: boolean }> {
  const res = await fetch(apiUrl(`/api/v1/self-learning/chapter/${chapterId}/book`), {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to create chapter book");
  return res.json();
}

// ---- Grade-7 interactive resources (courseware / 闯关练习 / 语音领读) ----

export interface PracticeQuestion {
  ask: string;
  type: string;
  answer: string | string[];
  why?: string;
  options?: string[];
}

export interface Grade7Resource {
  id: string;
  subject: string;
  title: string;
  html?: string;
  page?: string;
  goals?: string[];
  count?: number;
  questions?: PracticeQuestion[];
  game_html?: string;
  chapter_ids?: string[];
  /** 闯关自适应选题（design §3.7）：priority 越小越先做，reason 说明为何 */
  priority?: number;
  adaptive_reason?: "weak" | "due" | "review" | "normal";
}

export interface ChapterAdaptive {
  adapted: boolean;
  summary: string[];
}

export interface ChapterResources {
  courseware: Grade7Resource[];
  exercises: Grade7Resource[];
  voices: Grade7Resource[];
  figures: Grade7Resource[];
  adaptive?: ChapterAdaptive;
}

export async function fetchChapterResources(
  chapterId: string,
  u?: string,
): Promise<ChapterResources> {
  const qs = u ? `?u=${encodeURIComponent(u)}` : "";
  const res = await fetch(apiUrl(`/api/v1/self-learning/chapter/${chapterId}/resources${qs}`));
  if (!res.ok) return { courseware: [], exercises: [], voices: [], figures: [] };
  return res.json();
}

/** List internal books for this chapter, including inherited parent-chapter books. */
export async function fetchChapterBooksInherited(chapterId: string): Promise<ChapterBook[]> {
  const res = await fetch(apiUrl(`/api/v1/self-learning/chapter/${chapterId}/books`));
  if (!res.ok) return [];
  const data = await res.json();
  return data?.items || [];
}
