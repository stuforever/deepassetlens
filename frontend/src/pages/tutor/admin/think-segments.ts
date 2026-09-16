/**
 * 复刻自 DeepTutor 原仓 web/lib/think-segments.ts（整件 1:1，纯 TS 无外部依赖）。
 * 将助手原始回复切分为普通 markdown 段与 <think>/<thinking> 模型思考段。
 */

export interface TextSegment {
  kind: "text";
  content: string;
}

export interface ThinkSegment {
  kind: "think";
  content: string;
  /** False while the model is still streaming inside the open tag. */
  closed: boolean;
}

export type ContentSegment = TextSegment | ThinkSegment;

const FENCED_CODE_REGEX = /```[\s\S]*?```/g;
const FENCED_PLACEHOLDER_REGEX = /\u0000FENCED_(\d+)\u0000/g;

// `?<\s*think(?:ing)?\b[^>]*>`?
//   leading/trailing backtick is optional so we match both the raw streaming
//   form and the post-`escapeUnknownHtmlTags` form. The `[^>]*` swallows any
//   stray attributes some providers emit (e.g. `<thinking duration="3s">`).
const OPEN_TAG_REGEX = /`?<\s*(think(?:ing)?)\b[^>]*>`?/i;

function closeTagRegex(tag: string): RegExp {
  return new RegExp(`\`?<\\s*/\\s*${tag}\\s*>\`?`, "i");
}

function maskFencedCode(input: string): { masked: string; blocks: string[] } {
  const blocks: string[] = [];
  const masked = input.replace(FENCED_CODE_REGEX, (match) => {
    blocks.push(match);
    return `\u0000FENCED_${blocks.length - 1}\u0000`;
  });
  return { masked, blocks };
}

function restoreFencedCode(input: string, blocks: string[]): string {
  if (blocks.length === 0) return input;
  return input.replace(FENCED_PLACEHOLDER_REGEX, (_, idx: string) => {
    const i = Number(idx);
    return Number.isFinite(i) ? (blocks[i] ?? "") : "";
  });
}

/**
 * Strip the leading newlines that typically follow `<think>` and the
 * trailing newlines that precede `</think>`, so the collapsible card
 * does not render a top/bottom gap.
 */
function trimThinkContent(content: string): string {
  return content.replace(/^\s+/, "").replace(/\s+$/, "");
}

export function parseModelThinkingSegments(input: string): ContentSegment[] {
  if (!input) return [];
  if (!/<\s*think(?:ing)?\b/i.test(input)) {
    return [{ kind: "text", content: input }];
  }

  const { masked, blocks } = maskFencedCode(input);
  const segments: ContentSegment[] = [];
  let cursor = 0;

  while (cursor < masked.length) {
    const tail = masked.slice(cursor);
    const open = OPEN_TAG_REGEX.exec(tail);
    if (!open) {
      const text = restoreFencedCode(tail, blocks);
      if (text.length > 0) segments.push({ kind: "text", content: text });
      break;
    }

    if (open.index > 0) {
      const prefix = restoreFencedCode(tail.slice(0, open.index), blocks);
      if (prefix.length > 0) segments.push({ kind: "text", content: prefix });
    }

    const tag = open[1].toLowerCase();
    const afterOpen = tail.slice(open.index + open[0].length);
    const close = closeTagRegex(tag).exec(afterOpen);

    if (!close) {
      const body = restoreFencedCode(afterOpen, blocks);
      segments.push({
        kind: "think",
        content: trimThinkContent(body),
        closed: false,
      });
      break;
    }

    const body = restoreFencedCode(afterOpen.slice(0, close.index), blocks);
    segments.push({
      kind: "think",
      content: trimThinkContent(body),
      closed: true,
    });
    cursor += open.index + open[0].length + close.index + close[0].length;
  }

  return segments;
}

/** True when `input` contains at least one model-thinking block. */
export function hasModelThinking(input: string): boolean {
  if (!input) return false;
  return /<\s*think(?:ing)?\b/i.test(input);
}
