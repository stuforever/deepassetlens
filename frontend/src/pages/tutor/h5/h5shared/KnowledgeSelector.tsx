/**
 * 桌面同名件 1:1（复刻自 DeepTutor 原仓 web/components/chat/home/KnowledgeSelector.tsx，156 行）。
 * 替换点：删除 "use client"；lucide Check/ChevronDown/Database→CheckOutlined/
 * DownOutlined/DatabaseOutlined（size/strokeWidth→style.fontSize）；Tailwind→内联
 * 样式（token 见 dtStyle.ts）；hover 底色→onMouseEnter/Leave 直写 style（批8 最小
 * 等价物）；active:scale 按压反馈为纯视觉增强，降级省略。状态机/外点关闭/linger
 * 行为逐字未改；t() 译文取 zh/app.json（"Knowledge"→知识库、"knowledge bases"→
 * 个知识库、"Select knowledge bases"→选择知识库、"No knowledge bases available"→
 * 暂无可用的知识库）。
 */
import { useEffect, useRef, useState } from "react";
import { CheckOutlined, DownOutlined, DatabaseOutlined } from "@ant-design/icons";
import { useLingerExpand } from "./use-linger-expand";
import { DT, ellipsis } from "./dtStyle";

/**
 * Knowledge-base scope selector (composer toolbar).
 *
 * Mirrors PersonaSelector's collapse-to-icon chip + dropdown, because a
 * KB selection is the same KIND of state: a SESSION-level retrieval
 * scope that persists across turns (stored in session.preferences),
 * NOT a one-shot reference like an attachment. Surfacing it as a
 * persistent toolbar chip — rather than burying it in the "+" menu —
 * makes that stickiness legible: the active scope sits in the toolbar
 * before every message and is one click away from being changed.
 *
 * Multi-select: rows toggle without closing, so several bases can be
 * picked in one pass. A non-empty selection tints the icon primary so
 * the active scope stays visible even when the chip is collapsed.
 */
export default function KnowledgeSelector({
  knowledgeBases,
  selected,
  onToggle,
  placement = "top",
}: {
  knowledgeBases: { name: string }[];
  selected: string[];
  onToggle: (name: string) => void;
  placement?: "top" | "bottom";
}) {
  const [open, setOpenState] = useState(false);
  const { expanded, linger, triggerProps: lingerProps } = useLingerExpand(open);
  const setOpen = (next: boolean) => {
    setOpenState(next);
    // Keep the label expanded for a beat after close so a just-made
    // change registers before the chip collapses.
    if (!next) linger();
  };
  const rootRef = useRef<HTMLDivElement>(null);

  // Close on outside click.
  useEffect(() => {
    if (!open) return;
    const handler = (event: MouseEvent) => {
      const target = event.target as Node;
      if (rootRef.current && !rootRef.current.contains(target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const count = selected.length;
  const label =
    count === 0
      ? "知识库"
      : count === 1
        ? selected[0]
        : `${count} 个知识库`;
  const menuPosition = placement === "bottom" ? "top" : "bottom";
  const menuOffset = placement === "bottom" ? 6 : 6;

  return (
    <div ref={rootRef} style={{ position: "relative" }}>
      {/* Resting state is just the database icon; hovering (or opening
          the menu) slides the scope label out and lingers ~1.2s after
          leave/selection before collapsing. A non-empty scope tints the
          icon primary. */}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-label={"选择知识库"}
        aria-expanded={open}
        {...lingerProps}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = DT.mutedAlpha(0.55);
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "transparent";
        }}
        style={{
          display: "inline-flex",
          height: 32,
          flexShrink: 0,
          alignItems: "center",
          borderRadius: 8,
          padding: "0 8px",
          fontSize: 14,
          fontWeight: 500,
          border: "none",
          cursor: "pointer",
          background: open ? DT.muted : "transparent",
          color: open
            ? DT.foreground
            : count > 0
              ? DT.primary
              : DT.mutedForeground,
          transition: "background-color 150ms, color 150ms, transform 150ms",
        }}
      >
        <DatabaseOutlined style={{ fontSize: 16, flexShrink: 0 }} />
        <span
          style={{
            display: "flex",
            minWidth: 0,
            alignItems: "center",
            gap: 4,
            overflow: "hidden",
            whiteSpace: "nowrap",
            marginLeft: expanded ? 6 : 0,
            maxWidth: expanded ? 160 : 0,
            opacity: expanded ? 1 : 0,
            transition:
              "max-width 300ms ease-out, opacity 300ms ease-out, margin-left 300ms ease-out",
          }}
        >
          <span style={ellipsis}>{label}</span>
          <DownOutlined
            style={{
              fontSize: 13,
              flexShrink: 0,
              transition: "transform 200ms",
              transform: open ? "rotate(180deg)" : undefined,
            }}
          />
        </span>
      </button>

      {open && (
        <div
          style={{
            position: "absolute",
            right: 0,
            zIndex: 50,
            [menuPosition === "top" ? "bottom" : "top"]: "100%",
            marginBottom: menuPosition === "top" ? menuOffset : undefined,
            marginTop: menuPosition === "bottom" ? menuOffset : undefined,
            width: "min(280px, calc(100vw - 32px))",
            overflow: "hidden",
            borderRadius: 12,
            border: `1px solid ${DT.border}`,
            background: DT.popover,
            boxShadow:
              "0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1)",
          } as React.CSSProperties}
        >
          {knowledgeBases.length === 0 ? (
            <div
              style={{
                padding: "16px 12px",
                textAlign: "center",
                fontSize: 12,
                color: DT.mutedForeground,
              }}
            >
              暂无可用的知识库
            </div>
          ) : (
            <div style={{ maxHeight: 280, overflowY: "auto", padding: "4px 0" }}>
              {knowledgeBases.map((kb) => {
                const active = selected.includes(kb.name);
                const baseBg = active ? DT.primaryAlpha(0.06) : "transparent";
                return (
                  <button
                    key={kb.name}
                    type="button"
                    onClick={() => onToggle(kb.name)}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = active
                        ? DT.primaryAlpha(0.06)
                        : DT.mutedAlpha(0.45);
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = baseBg;
                    }}
                    style={{
                      display: "flex",
                      width: "100%",
                      alignItems: "center",
                      gap: 10,
                      padding: "6px 12px",
                      textAlign: "left",
                      border: "none",
                      cursor: "pointer",
                      background: baseBg,
                      font: "inherit",
                    }}
                  >
                    <DatabaseOutlined
                      style={{
                        fontSize: 15,
                        flexShrink: 0,
                        color: active ? DT.primary : DT.mutedForeground,
                      }}
                    />
                    <span
                      style={{
                        ...ellipsis,
                        flex: 1,
                        fontSize: 12.5,
                        fontWeight: 500,
                        color: DT.foreground,
                      }}
                    >
                      {kb.name}
                    </span>
                    {active && (
                      <CheckOutlined
                        style={{ fontSize: 14, flexShrink: 0, color: DT.primary }}
                      />
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
