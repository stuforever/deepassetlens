/**
 * 复刻自 DeepTutor：web/app/(workspace)/book/components/blocks/SectionBlock.tsx（平铺到 tupu）。
 * 替换点：删除 "use client" 与 react-i18next（"Section focus"→章节重点、
 * "Key takeaway:"→关键收获：，取自 zh/app.json）；lucide Sparkles → ThunderboltOutlined；
 * MarkdownRenderer → LiteMarkdown（'./dtMarkdown'，variant 忽略）；
 * @/lib/book-types → './book-types'；Tailwind → 内联样式。
 */
import { ThunderboltOutlined } from "@ant-design/icons";
import { LiteMarkdown } from './dtMarkdown';
import type { Block } from './book-types';

export interface SectionBlockProps {
  block: Block;
}

interface Subsection {
  heading?: string;
  role?: string;
  focus?: string;
  body?: string;
  target_words?: number;
}

export default function SectionBlock({ block }: SectionBlockProps) {
  const payload = block.payload || {};
  const intro = String(payload.intro ?? "").trim();
  const keyTakeaway = String(payload.key_takeaway ?? "").trim();
  const focus = String(payload.focus ?? "").trim();
  const rawSubs = Array.isArray(payload.subsections) ? payload.subsections : [];
  const subsections: Subsection[] = rawSubs as Subsection[];

  return (
    <section style={{ color: "rgba(0,0,0,0.88)" }}>
      {intro && (
        <div style={{ marginBottom: 20, fontSize: "1.02em", lineHeight: 1.625 }}>
          <LiteMarkdown content={intro} />
        </div>
      )}

      {focus && (
        <div
          style={{
            marginBottom: 16,
            fontSize: 11,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            color: "#6b7280",
          }}
        >
          {"章节重点"} · {focus}
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        {subsections.map((sub, idx) => {
          const body = (sub.body || "").trim();
          if (!body) return null;
          return (
            <div key={idx} style={{ lineHeight: 1.625 }}>
              <LiteMarkdown content={body} />
            </div>
          );
        })}
      </div>

      {keyTakeaway && (
        <div
          style={{
            marginTop: 24,
            display: "flex",
            alignItems: "flex-start",
            gap: 8,
            borderRadius: 12,
            border: "1px solid #e4e4e7",
            background: "rgba(244,244,245,0.3)",
            padding: "8px 12px",
            fontSize: 14,
          }}
        >
          <ThunderboltOutlined
            style={{
              fontSize: 16,
              marginTop: 2,
              flexShrink: 0,
              color: "#6b7280",
            }}
          />
          <div style={{ flex: 1 }}>
            <span style={{ marginRight: 4, fontWeight: 500 }}>{"关键收获："}</span>
            <span style={{ color: "rgba(0,0,0,0.88)" }}>{keyTakeaway}</span>
          </div>
        </div>
      )}
    </section>
  );
}
