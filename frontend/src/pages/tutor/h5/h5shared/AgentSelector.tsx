/**
 * 桌面同名件 1:1（复刻自 DeepTutor 原仓 web/components/chat/home/AgentSelector.tsx，183 行）。
 * 替换点：删除 "use client"；lucide Bot/Check/ChevronDown/Minus/Plus→RobotOutlined/
 * CheckOutlined/DownOutlined/MinusOutlined/PlusOutlined；agentGlyph 来自本目录
 * agent-icons.tsx（纯 SVG 逐字）；Tailwind→内联样式（token 见 dtStyle.ts）；hover→
 * onMouseEnter/Leave 直写 style；active:scale 降级省略；t() 译文取 zh/app.json。
 * 状态机/外点关闭/预算加减逐字未改。
 */
import { useEffect, useRef, useState } from "react";
import {
  RobotOutlined,
  CheckOutlined,
  DownOutlined,
  MinusOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import { agentGlyph } from "./agent-icons";
import { useLingerExpand } from "./use-linger-expand";
import { DT, ellipsis } from "./dtStyle";

const BUDGET_MIN = 1;
const BUDGET_MAX = 12;

/**
 * Connected-agent selector (composer toolbar).
 *
 * Sibling of KnowledgeSelector, but single-select: a turn consults at most one
 * connected agent (Claude Code / Codex). Picking one routes the whole turn
 * through the subagent capability — the chat model consults the live local
 * agent instead of retrieving from a KB. Selecting the active one again clears
 * it. A selection tints the bot icon primary so the active agent stays visible
 * when collapsed.
 */
export default function AgentSelector({
  agents,
  selected,
  onSelect,
  budget = null,
  onBudgetChange,
  placement = "top",
}: {
  agents: { name: string; kind?: string }[];
  selected: string | null;
  onSelect: (name: string | null) => void;
  /** Max times DeepTutor may consult the agent this turn. */
  budget?: number | null;
  onBudgetChange?: (budget: number) => void;
  placement?: "top" | "bottom";
}) {
  const [open, setOpenState] = useState(false);
  const { expanded, linger, triggerProps: lingerProps } = useLingerExpand(open);
  const setOpen = (next: boolean) => {
    setOpenState(next);
    if (!next) linger();
  };
  const rootRef = useRef<HTMLDivElement>(null);

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

  const label = selected ?? "智能体";
  const menuPosition = placement === "bottom" ? "top" : "bottom";
  const SelectedGlyph = agentGlyph(
    agents.find((a) => a.name === selected)?.kind,
  );

  return (
    <div ref={rootRef} style={{ position: "relative" }}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-label={"选择已连接的智能体"}
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
            : selected
              ? DT.primary
              : DT.mutedForeground,
          transition: "background-color 150ms, color 150ms, transform 150ms",
        }}
      >
        {SelectedGlyph ? (
          <SelectedGlyph size={16} style={{ flexShrink: 0 }} />
        ) : (
          <RobotOutlined style={{ fontSize: 16, flexShrink: 0 }} />
        )}
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
            marginBottom: menuPosition === "top" ? 6 : undefined,
            marginTop: menuPosition === "bottom" ? 6 : undefined,
            width: "min(280px, calc(100vw - 32px))",
            overflow: "hidden",
            borderRadius: 12,
            border: `1px solid ${DT.border}`,
            background: DT.popover,
            boxShadow:
              "0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1)",
          } as React.CSSProperties}
        >
          <div style={{ maxHeight: 280, overflowY: "auto", padding: "4px 0" }}>
            {agents.map((agent) => {
              const active = selected === agent.name;
              const RowGlyph = agentGlyph(agent.kind);
              const baseBg = active ? DT.primaryAlpha(0.06) : "transparent";
              return (
                <button
                  key={agent.name}
                  type="button"
                  onClick={() => {
                    onSelect(active ? null : agent.name);
                    setOpen(false);
                  }}
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
                  {RowGlyph ? (
                    <RowGlyph size={15} style={{ flexShrink: 0 }} />
                  ) : (
                    <RobotOutlined style={{ fontSize: 15, flexShrink: 0 }} />
                  )}
                  <span
                    style={{
                      ...ellipsis,
                      flex: 1,
                      fontSize: 12.5,
                      fontWeight: 500,
                      color: DT.foreground,
                    }}
                  >
                    {agent.name}
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

          {onBudgetChange && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 8,
                borderTop: `1px solid ${DT.border}`,
                padding: "8px 12px",
              }}
            >
              <span style={{ minWidth: 0, fontSize: 11.5, color: DT.mutedForeground }}>
                DeepTutor 最多提问轮数
              </span>
              <div style={{ display: "flex", flexShrink: 0, alignItems: "center", gap: 4 }}>
                <button
                  type="button"
                  aria-label={"减少"}
                  disabled={(budget ?? BUDGET_MIN) <= BUDGET_MIN}
                  onClick={() =>
                    onBudgetChange(
                      Math.max(BUDGET_MIN, (budget ?? BUDGET_MIN) - 1),
                    )
                  }
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = DT.mutedAlpha(0.6);
                    e.currentTarget.style.color = DT.foreground;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "transparent";
                    e.currentTarget.style.color = DT.mutedForeground;
                  }}
                  style={{
                    display: "flex",
                    height: 20,
                    width: 20,
                    alignItems: "center",
                    justifyContent: "center",
                    borderRadius: 6,
                    border: "none",
                    cursor: "pointer",
                    color: DT.mutedForeground,
                    opacity: (budget ?? BUDGET_MIN) <= BUDGET_MIN ? 0.4 : 1,
                    background: "transparent",
                  }}
                >
                  <MinusOutlined style={{ fontSize: 12 }} />
                </button>
                <span
                  style={{
                    width: 20,
                    textAlign: "center",
                    fontSize: 12.5,
                    fontWeight: 600,
                    fontVariantNumeric: "tabular-nums",
                    color: DT.foreground,
                  }}
                >
                  {budget ?? "–"}
                </span>
                <button
                  type="button"
                  aria-label={"增加"}
                  disabled={(budget ?? BUDGET_MAX) >= BUDGET_MAX}
                  onClick={() =>
                    onBudgetChange(
                      Math.min(BUDGET_MAX, (budget ?? BUDGET_MIN) + 1),
                    )
                  }
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = DT.mutedAlpha(0.6);
                    e.currentTarget.style.color = DT.foreground;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "transparent";
                    e.currentTarget.style.color = DT.mutedForeground;
                  }}
                  style={{
                    display: "flex",
                    height: 20,
                    width: 20,
                    alignItems: "center",
                    justifyContent: "center",
                    borderRadius: 6,
                    border: "none",
                    cursor: "pointer",
                    color: DT.mutedForeground,
                    opacity: (budget ?? BUDGET_MAX) >= BUDGET_MAX ? 0.4 : 1,
                    background: "transparent",
                  }}
                >
                  <PlusOutlined style={{ fontSize: 12 }} />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
