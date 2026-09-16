/**
 * 复刻自 DeepTutor：web/app/(workspace)/book/components/blocks/UserNoteBlock.tsx（平铺到 tupu）。
 * 替换点：删除 "use client" 与 react-i18next（"Your note"→你的笔记、
 * "Empty note – start writing your own annotation."→空笔记——开始写下你的批注吧。，
 * 均取自 zh/app.json）；lucide StickyNote → HighlightOutlined；
 * MarkdownRenderer → LiteMarkdown（'./dtMarkdown'，variant 忽略）；
 * Tailwind（primary/50 虚线左边框、primary/[0.04] 底色）→ 内联样式。
 */
import { HighlightOutlined } from "@ant-design/icons";
import { LiteMarkdown } from './dtMarkdown';
import type { Block } from './book-types';

export interface UserNoteBlockProps {
  block: Block;
}

export default function UserNoteBlock({ block }: UserNoteBlockProps) {
  const body = String(block.payload?.body || "");
  return (
    <aside
      style={{
        display: "flex",
        gap: 12,
        borderLeft: "3px dashed rgba(22,119,255,0.5)",
        background: "rgba(22,119,255,0.04)",
        padding: "8px 12px 8px 16px",
      }}
    >
      <HighlightOutlined
        style={{ fontSize: 16, marginTop: 3, flexShrink: 0, color: "#1677ff" }}
      />
      <div style={{ minWidth: 0, display: "flex", flexDirection: "column", gap: 4 }}>
        <div
          style={{
            fontSize: 11,
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.16em",
            color: "#1677ff",
          }}
        >
          你的笔记
        </div>
        {body ? (
          <LiteMarkdown content={body} />
        ) : (
          <div style={{ fontSize: 12, color: "#6b7280" }}>
            空笔记——开始写下你的批注吧。
          </div>
        )}
      </div>
    </aside>
  );
}
