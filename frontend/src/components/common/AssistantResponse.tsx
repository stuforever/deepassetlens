/**
 * 批6 依赖补件：1:1 移植自 DeepTutor web/components/common/AssistantResponse.tsx。
 * 替换点：
 *  - "use client" 去；
 *  - @/components/common/MarkdownRenderer、ModelThinkingCard → ./（同目录 1:1 件）；
 *  - @/lib/markdown-display → ../../lib/markdown-display、@/lib/think-segments →
 *    ../../lib/think-segments（既有 1:1 件）、@/hooks/useSmoothStreamText →
 *    ../../hooks/useSmoothStreamText（既有 1:1 件）；
 *  - 默认 className "text-[16px] leading-[1.75]" 为 tailwind 字面量，本仓无 tailwind：
 *    改为「调用方未传 className 时以内联 style 承载 fontSize:16/lineHeight:1.75，
 *    传入时按源语义整体交给 className」（调用方 PartnerChat 未传，行为一致）；
 *    传给 MarkdownRenderer 的 className="text-[var(--foreground)]" 按源逐字保留
 *    （本仓惰性，正文颜色由继承色承载，已登记）。
 * 其余逐字一致（memo/displayName 保留）。
 */

import { Fragment, memo, useMemo } from "react";

import MarkdownRenderer from "./MarkdownRenderer";
import ModelThinkingCard from "./ModelThinkingCard";
import {
  hasVisibleMarkdownContent,
  stripArtifactAnnotations,
} from "../../lib/markdown-display";
import { parseModelThinkingSegments } from "../../lib/think-segments";
import { useSmoothStreamText } from "../../hooks/useSmoothStreamText";

interface AssistantResponseProps {
  content: string;
  className?: string;
  /**
   * When true, the renderer drives the visible text through a rAF
   * typewriter (``useSmoothStreamText``) so the markdown grows at a
   * steady, frame-aligned pace even when the upstream LLM emits
   * uneven chunks. Pass ``false`` for completed turns and any non-
   * streaming surface — the hook short-circuits to a pass-through
   * in that case.
   */
  isStreaming?: boolean;
}

function AssistantResponseImpl({
  content,
  className,
  isStreaming = false,
}: AssistantResponseProps) {
  const displayContent = useSmoothStreamText(content, isStreaming);
  const segments = useMemo(
    () => parseModelThinkingSegments(stripArtifactAnnotations(displayContent)),
    [displayContent],
  );

  // Decide whether the message has anything worth rendering. We consider both
  // ordinary markdown segments and model-thinking blocks: a turn that only
  // ever produced a <think> scratchpad should still render the collapsed card
  // instead of dropping the assistant bubble entirely.
  const hasRenderableSegment = useMemo(() => {
    return segments.some((segment) => {
      if (segment.kind === "think") return segment.content.trim().length > 0;
      return hasVisibleMarkdownContent(segment.content);
    });
  }, [segments]);

  if (!hasRenderableSegment) return null;

  // role="article" lets screen-reader users locate each assistant turn as a
  // structured landmark. aria-live="polite" + aria-atomic="false" announces
  // streamed-in content as the user pauses, without re-reading the whole
  // bubble each token. Together this is the minimal pattern that turns a
  // silent stream into an audible one.
  return (
    <div
      role="article"
      aria-live="polite"
      aria-atomic="false"
      className={className}
      style={className ? undefined : { fontSize: 16, lineHeight: 1.75 }}
    >
      {segments.map((segment, index) => {
        if (segment.kind === "think") {
          return (
            <ModelThinkingCard
              key={`think-${index}`}
              content={segment.content}
              closed={segment.closed}
            />
          );
        }

        if (!hasVisibleMarkdownContent(segment.content)) {
          return <Fragment key={`text-${index}`} />;
        }

        return (
          <MarkdownRenderer
            key={`text-${index}`}
            content={segment.content}
            variant="prose"
            className="text-[var(--foreground)]"
          />
        );
      })}
    </div>
  );
}

// Memoize so completed messages don't re-parse markdown when an
// unrelated streaming sibling updates the parent — the streaming
// message gets a fresh ``msg.content`` per delta and re-renders
// naturally, but every other bubble keeps its previous render output.
const AssistantResponse = memo(AssistantResponseImpl);
AssistantResponse.displayName = "AssistantResponse";
export default AssistantResponse;
