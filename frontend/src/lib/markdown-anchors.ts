// 批6 依赖补件：1:1 移植自 DeepTutor web/lib/markdown-anchors.ts。替换点：@/lib/markdown-display → 相对路径。
// 其余逐字一致。

/**
 * DOM-side citation-anchor resolution shared by RichMarkdownRenderer and
 * SimpleMarkdownRenderer. Deliberately kept out of markdown-display.ts,
 * which is pure string logic exercised by node tests — this helper touches
 * `document`.
 */

import {
  citationAnchorIdFor,
  safeDecodeURIComponent,
} from "./markdown-display";

/**
 * Resolve the element a citation link should scroll to and auto-open its
 * enclosing `<details>` so the target is actually visible. Fallback chain:
 * the citation id's own anchor, then the link's `#hash`, then the
 * `references` section (also the fallback when the resolved id is missing
 * from the DOM). Returns the target, or null when nothing matched; the
 * caller performs its own scroll.
 */
export function findCitationAnchor(
  href: string | undefined,
  id?: string,
): HTMLElement | null {
  const hashTarget =
    id && citationAnchorIdFor(id)
      ? citationAnchorIdFor(id)
      : href?.startsWith("#")
        ? safeDecodeURIComponent(href.slice(1))
        : "references";
  const target =
    document.getElementById(hashTarget || "") ??
    document.getElementById("references");
  const parentDetails = target?.closest("details");
  if (parentDetails instanceof HTMLDetailsElement) {
    parentDetails.open = true;
  }
  return target;
}
