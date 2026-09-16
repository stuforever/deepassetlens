/**
 * 复刻自 DeepTutor：web/app/(workspace)/book/components/blocks/TimelineBlock.tsx（平铺到 tupu）。
 * 替换点：删除 "use client"；@/lib/book-types → './book-types'；
 * Tailwind（rounded-2xl/card/border-l 圆点/border→#e4e4e7、primary→#1677ff、
 * muted-foreground→#6b7280、font-mono 等宽字体栈）→ 最小内联样式。
 */
import type { Block } from './book-types';

const monoFont =
  'SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace';

interface TimelineEvent {
  date?: string;
  title?: string;
  description?: string;
}

export interface TimelineBlockProps {
  block: Block;
}

export default function TimelineBlock({ block }: TimelineBlockProps) {
  const events = (block.payload?.events as TimelineEvent[] | undefined) || [];
  if (events.length === 0) return null;
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
      <ol
        style={{
          position: "relative",
          margin: "0 0 0 12px",
          padding: 0,
          listStyle: "none",
          display: "flex",
          flexDirection: "column",
          gap: 16,
          borderLeft: "1px solid #e4e4e7",
          paddingLeft: 16,
        }}
      >
        {events.map((ev, idx) => (
          <li key={idx} style={{ position: "relative" }}>
            <span
              style={{
                position: "absolute",
                left: -19,
                top: 4,
                display: "inline-flex",
                width: 12,
                height: 12,
                borderRadius: 999,
                border: "2px solid #fff",
                background: "#1677ff",
                boxSizing: "border-box",
              }}
            />
            <div
              style={{
                fontSize: 12,
                fontFamily: monoFont,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                color: "#6b7280",
              }}
            >
              {ev.date || ""}
            </div>
            <div
              style={{
                fontSize: 14,
                fontWeight: 600,
                color: "rgba(0,0,0,0.88)",
              }}
            >
              {ev.title}
            </div>
            {ev.description && (
              <div
                style={{
                  marginTop: 2,
                  fontSize: 12,
                  lineHeight: 1.625,
                  color: "#6b7280",
                }}
              >
                {ev.description}
              </div>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
