/**
 * S5（M23-E）：H5 学习记忆 —— 按用户隔离的「上次章节 / 最近章节 / 继续上次 / 上次教材」。
 * 原仓 lib/h5-learn-memory.ts 1:1 移植（正文零改动；消费方：h5 learn 组 + h5 wrong 组）。
 *
 * 背景：旧版记忆键是全局的（h5_recent_chapters / h5_last_learn），一台设备多个
 * 学习者（?u=）互相串章节；且学习页只写不读，每次进来自动跳回第一章。
 *
 * 本模块统一约定：
 *   h5_last_chapter::{u}     上次章节（学习页挂载恢复的数据源）
 *   h5_recent_chapters::{u}  最近 3 章（章节抽屉「最近」区）
 *   h5_last_learn::{u}       首页「继续上次」续学条
 *   h5_last_textbook::{u}    原文页上次教材
 *
 * 老用户迁移：首次读取 per-u 键时，若旧全局键存在则自动收编（最近列表、
 * 上次章节从 h5_last_learn.href 反解），最近列表不丢。
 */

export interface H5ChapterMemory {
  chapter_id: string;
  name: string;
  textbook_id?: string;
  textbook_name?: string;
  ts: number;
}

export interface H5RecentChapter {
  id: string;
  name: string;
  textbook_name?: string;
  ts: number;
}

export interface H5TextbookMemory {
  textbook_id: string;
  name: string;
  ts: number;
}

const lastChapterKey = (u: string) => `h5_last_chapter::${u}`;
const recentChaptersKey = (u: string) => `h5_recent_chapters::${u}`;
const lastLearnKey = (u: string) => `h5_last_learn::${u}`;
const lastTextbookKey = (u: string) => `h5_last_textbook::${u}`;

function readJson<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function writeJson(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* 隐私模式/配额满：记忆是增强，不是功能依赖，静默失败 */
  }
}

/** 读取上次章节；per-u 键不存在时从旧全局 h5_last_learn.href 反解收编。 */
export function readLastChapter(u: string): H5ChapterMemory | null {
  const hit = readJson<H5ChapterMemory>(lastChapterKey(u));
  if (hit?.chapter_id) return hit;
  const globalLearn = readJson<{ href?: string; name?: string; ts?: number }>("h5_last_learn");
  const m = globalLearn?.href?.match(/[?&]chapter_id=([^&]+)/);
  if (m) {
    const chapterId = decodeURIComponent(m[1]);
    const migrated: H5ChapterMemory = {
      chapter_id: chapterId,
      name: globalLearn?.name || "",
      ts: globalLearn?.ts || Date.now(),
    };
    writeJson(lastChapterKey(u), migrated);
    return migrated;
  }
  return null;
}

/** 读取最近 3 章；per-u 键不存在时收编旧全局 h5_recent_chapters。 */
export function readRecentChapters(u: string): H5RecentChapter[] {
  const hit = readJson<H5RecentChapter[]>(recentChaptersKey(u));
  if (Array.isArray(hit) && hit.length) return hit.slice(0, 3);
  const legacy = readJson<{ id?: string; name?: string }[]>("h5_recent_chapters");
  if (Array.isArray(legacy) && legacy.length) {
    const migrated: H5RecentChapter[] = legacy
      .filter((c) => c && typeof c.id === "string")
      .slice(0, 3)
      .map((c) => ({ id: c.id as string, name: c.name || "", ts: Date.now() }));
    writeJson(recentChaptersKey(u), migrated);
    return migrated;
  }
  return [];
}

/** 记住章节：三键同步写（上次章节 / 最近 3 章 / 首页继续上次）。 */
export function rememberChapter(
  u: string,
  id: string,
  name: string,
  textbookId?: string,
  textbookName?: string,
): void {
  const ts = Date.now();
  writeJson(lastChapterKey(u), {
    chapter_id: id,
    name,
    textbook_id: textbookId || "",
    textbook_name: textbookName || "",
    ts,
  });
  const prev = readRecentChapters(u);
  const next = [
    { id, name, textbook_name: textbookName || "", ts },
    ...prev.filter((c) => c.id !== id),
  ].slice(0, 3);
  writeJson(recentChaptersKey(u), next);
  writeJson(lastLearnKey(u), {
    name,
    chapter: name,
    href: `/h5/learn?chapter_id=${encodeURIComponent(id)}`,
    ts,
  });
}

/** 读取上次教材。 */
export function readLastTextbook(u: string): H5TextbookMemory | null {
  const hit = readJson<H5TextbookMemory>(lastTextbookKey(u));
  return hit?.textbook_id ? hit : null;
}

/** 记住上次教材。 */
export function rememberTextbook(u: string, textbookId: string, name: string): void {
  writeJson(lastTextbookKey(u), { textbook_id: textbookId, name, ts: Date.now() });
}
