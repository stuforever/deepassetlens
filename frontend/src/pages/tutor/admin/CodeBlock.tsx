/**
 * 复刻自 DeepTutor：web/app/(workspace)/book/components/blocks/CodeBlock.tsx（平铺到 tupu）。
 * 替换点：删除 "use client"；MarkdownRenderer → LiteMarkdown（'./dtMarkdown'，
 * variant 忽略）；@/lib/book-types → './book-types'；
 * rounded-2xl/border/card/shadow-sm → 内联样式（16px 圆角、1px #e4e4e7 边框、#fff 底）。
 */
import { LiteMarkdown } from './dtMarkdown';
import type { Block } from './book-types';

export interface CodeBlockProps {
  block: Block;
}

export default function CodeBlock({ block }: CodeBlockProps) {
  const language = String(block.payload?.language || "python");
  const code = String(block.payload?.code || "");
  const explanation = String(block.payload?.explanation || "");
  const fenced = `\`\`\`${language}\n${code}\n\`\`\``;
  return (
    <div
      style={{
        borderRadius: 16,
        border: "1px solid #e4e4e7",
        background: "#fff",
        padding: 16,
        boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)",
      }}
    >
      <LiteMarkdown content={fenced} />
      {explanation && (
        <p style={{ marginTop: 8, fontSize: 12, color: "#6b7280" }}>
          {explanation}
        </p>
      )}
    </div>
  );
}
