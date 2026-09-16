/**
 * 桌面同名件 1:1（复刻自 DeepTutor 原仓 web/components/chat/home/ContextReferenceTree.tsx，228 行）。
 * 替换点：删除 "use client"；lucide ChevronDown→DownOutlined、X→CloseOutlined，
 * LucideIcon 类型→ComponentType<{className?;style?}>（size/strokeWidth→
 * style.fontSize）；Tailwind→内联样式（颜色 token 见 dtStyle.ts，token 映射批8 同款）；
 * group-hover 移除钮显隐→行级 hoverKey 状态（批8 最小等价物）；focus-visible 显隐
 * 为纯视觉增强，降级省略。ElbowMark/FoldMark SVG path 逐字未改。
 */
import { memo, useState, type ComponentType, type CSSProperties } from "react";
import { DownOutlined, CloseOutlined } from "@ant-design/icons";
import { DT, ellipsis } from "./dtStyle";

/**
 * One row in the reference tree: an attachment, a Space reference, a
 * persona, etc. All kinds render identically (monochrome icon + kind
 * prefix + label) — visual uniformity is the point.
 */
export interface ContextTreeItem {
  key: string;
  // A lucide icon, or any glyph with the same call signature (brand SVG marks
  // are cast to this at the call site).
  icon: ComponentType<{ className?: string; style?: CSSProperties }>;
  /** Type prefix ("Book", "Notebook", ...), already translated. */
  kind: string;
  /** Item title; truncates. */
  label: string;
  /** 16px thumbnail for image attachments — replaces the icon. */
  thumbnailUrl?: string;
  /** Optional click action (e.g. open attachment preview). */
  onClick?: () => void;
  /** Optional remove action (composer only). */
  onRemove?: () => void;
}

/**
 * Connector glyph: a thin rounded elbow line (NOT a bordered box — that
 * reads as a todo checkbox). Drawn for the "up" flavor (┌: rises from
 * the textarea, turns right); the mirrored/down flavors derive from it
 * via CSS transforms.
 */
function ElbowMark({
  direction,
  mirrored,
}: {
  direction: "up" | "down";
  mirrored: boolean;
}) {
  const flipTransform = [
    direction === "down" ? "scaleY(-1)" : "",
    mirrored ? "scaleX(-1)" : "",
  ]
    .join(" ")
    .trim();
  return (
    <svg
      aria-hidden
      width="12"
      height="12"
      viewBox="0 0 12 12"
      fill="none"
      style={{
        marginTop: 3.5,
        flexShrink: 0,
        alignSelf: "flex-start",
        color: DT.mutedForegroundAlpha(0.45),
        transform: flipTransform || undefined,
      }}
    >
      {/* vertical arm from the box edge, rounded corner, horizontal arm */}
      <path
        d="M2 11 V6 Q2 3 5 3 H11"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
    </svg>
  );
}

/**
 * Folded-content mark for the summary toggle: three quiet dots — the
 * "…" idiom for collapsed lines. The toggle is a control, not a ref,
 * so it gets no elbow; once expanded nothing is hidden anymore and the
 * mark yields to a blank spacer that keeps the text column aligned.
 */
function FoldMark({ visible }: { visible: boolean }) {
  return (
    <svg
      aria-hidden
      width="12"
      height="12"
      viewBox="0 0 12 12"
      fill="none"
      style={{ flexShrink: 0, color: DT.mutedForegroundAlpha(0.55) }}
    >
      {visible && (
        <>
          <circle cx="2.2" cy="6" r="1.1" fill="currentColor" />
          <circle cx="6" cy="6" r="1.1" fill="currentColor" />
          <circle cx="9.8" cy="6" r="1.1" fill="currentColor" />
        </>
      )}
    </svg>
  );
}

/**
 * Claude-Code-style attachment tree: an elbow connector + a quiet
 * collapsed summary ("N references"), expandable to one row per item.
 *
 * direction="up" is the composer flavor — the block sits above the
 * textarea and the elbows read as the input box extending upward.
 * direction="down" + align="right" is the sent-message flavor: ┘
 * elbows hug the bubble's right edge and the rows extend leftward.
 */
export default memo(function ContextReferenceTree({
  items,
  direction,
  align = "left",
  summaryNoun,
}: {
  items: ContextTreeItem[];
  direction: "up" | "down";
  align?: "left" | "right";
  /** Translated noun for the collapsed summary ("attachments" / "references"). */
  summaryNoun: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const [hoverKey, setHoverKey] = useState<string | null>(null);
  if (items.length === 0) return null;

  // A single item needs no collapse ceremony — show it directly.
  const collapsible = items.length > 1;
  const showRows = !collapsible || expanded;
  const mirrored = align === "right";
  const alignItems = mirrored ? "flex-end" : "flex-start";
  // Mirrored rows reverse the flex order so the elbow sits at the right
  // edge (hugging the bubble) and content extends leftward.
  const rowDirection = mirrored ? ("row-reverse" as const) : ("row" as const);

  const rows = showRows
    ? items.map((item) => {
        const hovered = hoverKey === item.key;
        const fg = hovered ? DT.foreground : DT.mutedForeground;
        const Inner = (
          <>
            <ElbowMark direction={direction} mirrored={mirrored} />
            {item.thumbnailUrl ? (
              <img
                src={item.thumbnailUrl}
                alt=""
                aria-hidden
                style={{
                  height: 16,
                  width: 16,
                  flexShrink: 0,
                  borderRadius: 4,
                  border: `1px solid ${DT.borderAlpha(0.6)}`,
                  objectFit: "cover",
                }}
              />
            ) : (
              <item.icon
                style={{ fontSize: 13, color: fg, flexShrink: 0 }}
              />
            )}
            <span style={{ flexShrink: 0, fontWeight: 500, color: fg }}>
              {item.kind}
            </span>
            <span style={{ ...ellipsis, color: DT.mutedForegroundAlpha(0.8) }}>
              {item.label}
            </span>
          </>
        );
        return (
          <span
            key={item.key}
            onMouseEnter={() => setHoverKey(item.key)}
            onMouseLeave={() => setHoverKey(null)}
            style={{
              display: "flex",
              flexDirection: rowDirection,
              maxWidth: "100%",
              alignItems: "center",
              gap: 6,
              fontSize: 12,
              lineHeight: 1.6,
            }}
          >
            {item.onClick ? (
              <button
                type="button"
                onClick={item.onClick}
                style={{
                  display: "flex",
                  flexDirection: rowDirection,
                  minWidth: 0,
                  alignItems: "center",
                  gap: 6,
                  borderRadius: 6,
                  textAlign: "left",
                  color: hovered ? DT.foreground : undefined,
                  background: "none",
                  border: "none",
                  padding: 0,
                  cursor: "pointer",
                  font: "inherit",
                }}
              >
                {Inner}
              </button>
            ) : (
              Inner
            )}
            {item.onRemove ? (
              <button
                type="button"
                onClick={item.onRemove}
                aria-label={"移除"}
                style={{
                  flexShrink: 0,
                  borderRadius: 4,
                  padding: 2,
                  border: "none",
                  background: "none",
                  cursor: "pointer",
                  color: hovered ? DT.foreground : DT.mutedForegroundAlpha(0.6),
                  opacity: hovered ? 1 : 0,
                  transition: "opacity 150ms",
                  lineHeight: 0,
                }}
              >
                <CloseOutlined style={{ fontSize: 11 }} />
              </button>
            ) : null}
          </span>
        );
      })
    : null;

  const summary = collapsible ? (
    <button
      type="button"
      onClick={() => setExpanded((prev) => !prev)}
      aria-expanded={expanded}
      onMouseEnter={(e) => {
        e.currentTarget.style.color = DT.foreground;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.color = DT.mutedForegroundAlpha(0.8);
      }}
      style={{
        display: "flex",
        flexDirection: rowDirection,
        alignItems: "center",
        gap: 6,
        borderRadius: 6,
        fontSize: 12,
        fontWeight: 500,
        lineHeight: 1.6,
        color: DT.mutedForegroundAlpha(0.8),
        border: "none",
        background: "none",
        padding: 0,
        cursor: "pointer",
      }}
    >
      <FoldMark visible={!expanded} />
      <span>
        {items.length} {summaryNoun}
      </span>
      <DownOutlined
        style={{
          fontSize: 11,
          flexShrink: 0,
          transition: "transform 200ms",
          transform: expanded
            ? "rotate(180deg)"
            : direction === "up"
              ? undefined
              : "rotate(-90deg)",
        }}
      />
    </button>
  ) : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", rowGap: 2, alignItems }}>
      {/* "up" reads bottom-to-top: rows stack above the toggle so the
          block grows away from the textarea. "down" is the inverse. */}
      {direction === "up" ? (
        <>
          {rows}
          {summary}
        </>
      ) : (
        <>
          {summary}
          {rows}
        </>
      )}
    </div>
  );
});
