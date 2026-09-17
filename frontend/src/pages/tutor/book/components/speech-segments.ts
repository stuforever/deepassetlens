"use client";

/**
 * Turn a book page's blocks into read-aloud text segments.
 *
 * Graphic / interactive blocks (figure, interactive, animation, concept_graph,
 * code) are deliberately SKIPPED — speech is for text only. Each block that
 * carries prose becomes one segment, so the speech bar can play/pause/skip
 * segment by segment and the progress bar tracks "which block is being read".
 */

import type { Block, Page } from "../../../../lib/book-types";
import type { Segment } from "../../../../hooks/usePageSpeech";

function clean(text: string): string {
  if (!text) return "";
  return (
    (text || "")
      // 数学公式：把 $...$ / $$...$$ 里的 LaTeX 转成可朗读的中文，并去掉 $ 定界符。
      .replace(/\$\$([\s\S]*?)\$\$|\$([\s\S]*?)\$/g, (_, d2: string, d1: string) =>
        latexToSpeech(d2 ?? d1),
      )
      // 兜底：去掉残留的单个 $（不成对时）。
      .replace(/\$/g, "")
      // 去掉 Markdown 结构符号（标题井号、列表、引用、加粗斜体、链接、代码块反引号）。
      .replace(/[#>*_`|]/g, "")
      // 去掉残留的 LaTeX 反斜杠命令前缀与花括号（防漏网）。
      .replace(/\\(?:[a-zA-Z]+)/g, " ")
      .replace(/[{}^_]/g, " ")
      // 折叠空白。
      .replace(/\s+/g, " ")
      .trim()
  );
}

/**
 * 把一段 LaTeX 公式/文本转换成 TTS 友好的中文念法（去掉 \、{}、^、_ 等符号）。
 * 常见命令做语义映射；未识别的命令去掉反斜杠后按单词念。
 */
function latexToSpeech(latex: string): string {
  let s = (latex || "").trim();
  const map: Array<[RegExp, string]> = [
    [/\\times/g, "乘以"],
    [/\\cdot/g, "乘以"],
    [/\\div/g, "除以"],
    [/\\frac\{([^}]*)\}\{([^}]*)\}/g, "$1 分之 $2"],
    [/\\sqrt\{([^}]*)\}/g, "$1 的平方根"],
    [/\\sqrt\[(\d+)\]\{([^}]*)\}/g, "$2 的 $1 次方根"],
    [/\\pm/g, "正负"],
    [/\\leq/g, "小于等于"],
    [/\\geq/g, "大于等于"],
    [/\\neq/g, "不等于"],
    [/\\approx/g, "约等于"],
    [/\\infty/g, "无穷大"],
    [/\\pi/g, "圆周率"],
    [/\\alpha/g, "阿尔法"],
    [/\\beta/g, "贝塔"],
    [/\\gamma/g, "伽马"],
    [/\\theta/g, "西塔"],
    [/\\sum/g, "求和"],
    [/\\prod/g, "连乘"],
    [/\\int/g, "积分"],
    [/\\text\{([^}]*)\}/g, "$1"],
    [/\\quad|\\qquad|\\;|\\,|\\!/g, " "],
  ];
  for (const [re, rep] of map) s = s.replace(re, rep);
  return (
    s
      // 次方：x^2 → x 的平方；x^n → x 的 n 次方。
      .replace(/\^\{?([^{}]+)\}?/g, "的 $1 次方")
      // 下标：x_1 → x 下标 1。
      .replace(/_\{?([^{}]+)\}?/g, "下标 $1")
      // 剩下的命令符去掉。
      .replace(/\\(?:[a-zA-Z]+)/g, " ")
      .replace(/[{}^_\\]/g, " ")
      .replace(/\s+/g, " ")
      .trim()
  );
}

function blockSegments(block: Block): Segment[] {
  const payload = (block.payload || {}) as Record<string, unknown>;
  const out: Segment[] = [];

  const push = (id: string, text: string) => {
    const c = clean(text);
    if (c) out.push({ id, text: c });
  };

  switch (block.type) {
    case "text":
      push(`${block.id}:body`, String(payload.body ?? ""));
      break;
    case "callout": {
      const label = clean(String(payload.label ?? ""));
      const body = clean(String(payload.body ?? ""));
      push(`${block.id}:body`, label ? `${label}。${body}` : body);
      break;
    }
    case "section": {
      const intro = clean(String(payload.intro ?? ""));
      const takeaway = clean(String(payload.key_takeaway ?? ""));
      const subs = Array.isArray(payload.subsections)
        ? (payload.subsections as Array<Record<string, unknown>>)
        : [];
      const subBodies = subs
        .map((s) => clean(String(s?.body ?? "")))
        .filter(Boolean)
        .join("。");
      const text = [intro, subBodies, takeaway ? `要点：${takeaway}` : ""]
        .filter(Boolean)
        .join("。");
      push(`${block.id}:body`, text);
      break;
    }
    case "quiz": {
      const questions = Array.isArray(payload.questions)
        ? (payload.questions as Array<Record<string, unknown>>)
        : [];
      questions.forEach((q, idx) => {
        push(
          `${block.id}:q${idx}`,
          `第${idx + 1}题。${String(q?.question ?? "")}`,
        );
      });
      break;
    }
    case "deep_dive": {
      const title = clean(String(payload.title ?? ""));
      const summary = clean(String(payload.summary ?? ""));
      const body = clean(String(payload.body ?? ""));
      push(`${block.id}:body`, [title, summary, body].filter(Boolean).join("。"));
      break;
    }
    case "user_note": {
      const body = clean(String(payload.body ?? ""));
      const note = clean(String(payload.note ?? ""));
      push(`${block.id}:body`, body || note);
      break;
    }
    case "timeline": {
      const title = clean(String(payload.title ?? ""));
      const items = Array.isArray(payload.items)
        ? (payload.items as Array<Record<string, unknown>>)
        : [];
      const itemText = items
        .map((it) => {
          const when = clean(String(it?.when ?? ""));
          const what = clean(String(it?.event ?? it?.what ?? ""));
          return when ? `${when}，${what}` : what;
        })
        .filter(Boolean)
        .join("。");
      push(`${block.id}:body`, [title, itemText].filter(Boolean).join("。"));
      break;
    }
    case "flash_cards": {
      const cards = Array.isArray(payload.cards)
        ? (payload.cards as Array<Record<string, unknown>>)
        : [];
      cards.forEach((c, idx) => {
        const front = clean(String(c?.front ?? c?.term ?? ""));
        const back = clean(String(c?.back ?? c?.definition ?? ""));
        push(`${block.id}:c${idx}`, front ? `${front}。${back}` : back);
      });
      break;
    }
    // figure / interactive / animation / concept_graph / code → skipped
    default:
      break;
  }
  return out;
}

export function pageToSegments(page: Page | null): Segment[] {
  if (!page) return [];
  const segs: Segment[] = [];
  if (page.title) {
    segs.push({ id: `${page.id}:title`, text: clean(page.title) });
  }
  for (const block of page.blocks) {
    if (block.status !== "ready") continue;
    segs.push(...blockSegments(block));
  }
  return segs;
}
