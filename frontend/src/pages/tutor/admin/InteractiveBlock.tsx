/**
 * 复刻自 DeepTutor：web/app/(workspace)/book/components/blocks/InteractiveBlock.tsx（平铺到 tupu）。
 * 替换点：删除 "use client" 与 react-i18next（"(Interactive payload is empty)"→（交互内容为空），
 * 取自 zh/app.json）；VisualizationViewer → './VisualizationViewer'；
 * MarkdownRenderer → LiteMarkdown（'./dtMarkdown'，variant 忽略）；
 * @/lib/book-types → './book-types'、@/lib/visualize-types → './visualize-types'；
 * Tailwind → 内联样式。
 */
import VisualizationViewer from './VisualizationViewer';
import { LiteMarkdown } from './dtMarkdown';
import type { Block } from './book-types';
import type { VisualizeResult } from './visualize-types';

export interface InteractiveBlockProps {
  block: Block;
}

export default function InteractiveBlock({ block }: InteractiveBlockProps) {
  const code =
    (block.payload?.code as
      | { language?: string; content?: string }
      | undefined) || {};
  const content = String(code.content || "");
  const description = block.payload?.description
    ? String(block.payload.description)
    : "";
  const chartType = block.payload?.chart_type
    ? String(block.payload.chart_type)
    : "interactive";

  if (!content.trim()) {
    return (
      <div
        style={{
          borderRadius: 16,
          border: "1px dashed #e4e4e7",
          background: "rgba(255,255,255,0.4)",
          padding: 16,
          fontSize: 12,
          fontStyle: "italic",
          color: "#6b7280",
        }}
      >
        （交互内容为空）
      </div>
    );
  }

  const result: VisualizeResult = {
    response: description,
    render_type: "html",
    code: { language: "html", content },
    analysis: {
      render_type: "html",
      description,
      data_description: "",
      chart_type: chartType,
      visual_elements: [],
      rationale: "",
    },
    review: {
      optimized_code: "",
      changed: false,
      review_notes: "",
    },
  };

  return (
    <figure
      style={{
        borderRadius: 16,
        border: "1px solid #e4e4e7",
        background: "#fff",
        padding: 12,
        boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)",
        margin: 0,
      }}
    >
      <VisualizationViewer result={result} />
      {description && (
        <figcaption
          style={{ marginTop: 12, fontSize: 12, lineHeight: 1.375, color: "#6b7280" }}
        >
          <LiteMarkdown content={description} />
        </figcaption>
      )}
    </figure>
  );
}
