/**
 * 桌面同名件 1:1（复刻自 DeepTutor 原仓 web/components/chat/home/ContextBudgetChip.tsx，335 行）。
 * 替换点：删除 "use client"；Tailwind→内联样式（token 见 dtStyle.ts）；i18n t()
 * → zh/app.json 译文中文直出（contextBudget.* 键全部命中，含 {{percent}}/
 * {{used}}/{{total}}/{{count}} 模板插值，deferredTools 单复数按原语义合并）；
 * segment 键查 SEGMENT_LABELS 表，未知键回退 defaultValue（原仓 i18next 行为）。
 * 颜色表/格式化/环形仪表/键盘 Escape 关闭逐字未改。
 */
import { useEffect, useRef, useState } from "react";
import { DT } from "./dtStyle";

export type ContextBudgetSegment = { key: string; tokens: number };

export type ContextBudget = {
  window: number;
  window_estimated?: boolean;
  used_tokens: number;
  free_tokens: number;
  model?: string;
  counter?: string;
  deferred_tool_count?: number;
  segments: ContextBudgetSegment[];
};

/**
 * Mid-tone hues only. The swatches and the stacked bar sit on --popover,
 * which flips between near-white and near-black, so anything very light or
 * very dark vanishes in one of the two themes. Red is deliberately absent:
 * a segment being large is information, not an error.
 */
const SEGMENT_COLORS: Record<string, string> = {
  messages: "#6366f1",
  system_prompt: "#0ea5e9",
  system_tools: "#14b8a6",
  mcp_tools: "#10b981",
  tool_manifest: "#84cc16",
  extended_tools: "#f59e0b",
  persona_style: "#f97316",
  partner_turn_policy: "#d946ef",
  memory: "#a855f7",
  knowledge_base_note: "#8b5cf6",
  skills: "#06b6d4",
  sources: "#0891b2",
  notebooks: "#e879a3",
  workspace: "#65a30d",
  capability: "#64748b",
};

const FALLBACK_COLORS = [
  "#6366f1",
  "#0ea5e9",
  "#14b8a6",
  "#f59e0b",
  "#a855f7",
  "#64748b",
];

function segmentColor(key: string): string {
  const known = SEGMENT_COLORS[key];
  if (known) return known;
  // An unrecognized key means the backend grew a segment this build doesn't
  // know about; hash it to a stable colour instead of dropping the row.
  let hash = 0;
  for (let i = 0; i < key.length; i += 1) {
    hash = (hash * 31 + key.charCodeAt(i)) >>> 0;
  }
  return FALLBACK_COLORS[hash % FALLBACK_COLORS.length];
}

// zh/app.json "contextBudget.segment.*" 原译文（i18n t() 中文直出替换表）。
const SEGMENT_LABELS: Record<string, string> = {
  capability: "能力",
  extended_tools: "扩展工具清单",
  knowledge_base_note: "知识库说明",
  mcp_tools: "MCP 工具定义",
  memory: "记忆",
  messages: "对话消息",
  notebooks: "笔记本",
  partner_turn_policy: "伙伴轮次策略",
  persona_style: "Persona 风格",
  skills: "技能",
  sources: "来源",
  system_prompt: "系统提示词",
  system_tools: "内置工具定义",
  tool_manifest: "工具清单",
  workspace: "工作区",
};

/**
 * Mirrors formatCompactTokens in components/settings/ServiceConfigEditor.tsx,
 * but keeps one decimal and a lowercase "k" so the header reads like a budget
 * ("895.3k / 1M") rather than a spec sheet. Copied rather than shared because
 * that helper is module-private over there.
 */
function formatTokens(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return "0";
  const compact = (scaled: number) => scaled.toFixed(1).replace(/\.0$/, "");
  if (value >= 1_000_000) return `${compact(value / 1_000_000)}M`;
  if (value >= 1_000) return `${compact(value / 1_000)}k`;
  return String(Math.round(value));
}

function formatPercent(share: number): string {
  if (!Number.isFinite(share) || share <= 0) return "0%";
  if (share < 1) return "<1%";
  if (share < 10) return `${share.toFixed(1).replace(/\.0$/, "")}%`;
  return `${Math.round(share)}%`;
}

/**
 * Tiny ring gauge; inherits the chip's colour so tone changes carry over.
 * Sized 16 to sit level with the lucide icons the neighbouring composer
 * selectors render at `size={16}`.
 */
function UsageRing({ share }: { share: number }) {
  const radius = 6.5;
  const circumference = 2 * Math.PI * radius;
  const filled = Math.min(100, Math.max(0, share)) / 100;
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      aria-hidden="true"
      style={{ transform: "rotate(-90deg)", flexShrink: 0 }}
    >
      <circle
        cx="8"
        cy="8"
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        opacity={0.25}
      />
      <circle
        cx="8"
        cy="8"
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={circumference * (1 - filled)}
      />
    </svg>
  );
}

function SegmentRow({
  color,
  label,
  tokens,
  share,
  bordered = false,
}: {
  color: string;
  label: string;
  tokens: number;
  share: number;
  bordered?: boolean;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span
        style={{
          height: 8,
          width: 8,
          flexShrink: 0,
          borderRadius: 2,
          backgroundColor: color,
          border: bordered ? `1px solid ${DT.border}` : undefined,
        }}
      />
      <span style={{ minWidth: 0, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: 11.5, color: DT.foreground }}>
        {label}
      </span>
      <span style={{ flexShrink: 0, fontSize: 11.5, fontVariantNumeric: "tabular-nums", color: DT.mutedForeground }}>
        {formatTokens(tokens)}
      </span>
      <span style={{ width: 36, flexShrink: 0, textAlign: "right", fontSize: 11, fontVariantNumeric: "tabular-nums", color: DT.mutedForegroundAlpha(0.7) }}>
        {formatPercent(share)}
      </span>
    </div>
  );
}

/**
 * Context-window breakdown for the just-finished turn (composer toolbar).
 *
 * Pure presentation: the numbers are measured server-side from the request
 * that was actually sent, so this component only formats what it is handed.
 * Every number here is an estimate — the footnotes say so explicitly rather
 * than letting a confident-looking bar imply precision we don't have.
 */
export default function ContextBudgetChip({
  budget,
}: {
  budget: ContextBudget;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      const target = event.target as Node;
      if (rootRef.current && !rootRef.current.contains(target)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  // The caller's guard is `typeof === "number"`, which NaN also satisfies, so
  // clamp here rather than let a NaN reach the divisor and print "NaN%".
  const used = Number.isFinite(budget.used_tokens)
    ? Math.max(0, budget.used_tokens)
    : 0;
  // A zero/absent window would make every share NaN; fall back to what we
  // measured so the popover still says something true.
  const total =
    Number.isFinite(budget.window) && budget.window > 0
      ? budget.window
      : Math.max(used, 1);
  const free = Number.isFinite(budget.free_tokens)
    ? Math.max(0, budget.free_tokens)
    : Math.max(0, total - used);
  const usedShare = (used / total) * 100;
  const usedPercentLabel = `${Math.round(usedShare)}%`;
  // Backend already sorts descending and drops empties; filter defensively
  // and keep its order. The key is required for the colour hash and the label
  // lookup, so a row without a usable one is dropped rather than thrown on.
  const segments = (budget.segments ?? []).filter(
    (segment) =>
      segment &&
      typeof segment.key === "string" &&
      segment.key.length > 0 &&
      Number.isFinite(segment.tokens) &&
      segment.tokens > 0,
  );

  const estimatedWindow = budget.window_estimated === true;
  const heuristicCounter = budget.counter === "heuristic";
  const deferredCount = budget.deferred_tool_count ?? 0;
  const hasNotes = estimatedWindow || heuristicCounter || deferredCount > 0;
  const nearFull = usedShare >= 90;

  return (
    <div ref={rootRef} style={{ position: "relative" }}>
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-label={`上下文窗口：已用 ${usedPercentLabel}`}
        aria-expanded={open}
        aria-haspopup="dialog"
        onMouseEnter={(e) => {
          if (!open) {
            e.currentTarget.style.background =
              nearFull ? "rgba(245,158,11,0.1)" : DT.mutedAlpha(0.55);
            if (!nearFull) e.currentTarget.style.color = DT.foreground;
          }
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = open ? DT.muted : "transparent";
          if (!open && !nearFull) e.currentTarget.style.color = DT.mutedForeground;
        }}
        style={{
          display: "inline-flex",
          height: 32,
          flexShrink: 0,
          alignItems: "center",
          gap: 6,
          borderRadius: 8,
          padding: "0 8px",
          fontSize: 14,
          fontWeight: 500,
          fontVariantNumeric: "tabular-nums",
          border: "none",
          cursor: "pointer",
          background: open ? DT.muted : "transparent",
          color: open
            ? DT.foreground
            : nearFull
              ? "#f59e0b"
              : DT.mutedForeground,
          transition: "background-color 150ms, color 150ms, transform 150ms",
        }}
      >
        <UsageRing share={usedShare} />
        <span>{usedPercentLabel}</span>
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="上下文窗口"
          style={{
            transformOrigin: "bottom right",
            position: "absolute",
            bottom: "100%",
            right: 0,
            zIndex: 50,
            marginBottom: 6,
            width: "min(300px, calc(100vw - 32px))",
            overflow: "hidden",
            borderRadius: 12,
            border: `1px solid ${DT.border}`,
            background: DT.popover,
            boxShadow:
              "0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1)",
          }}
        >
          <div style={{ padding: "10px 12px" }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 8 }}>
              <span style={{ flexShrink: 0, fontSize: 10.5, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", color: DT.mutedForeground }}>
                上下文窗口
              </span>
              {budget.model ? (
                <span style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: 10.5, color: DT.mutedForegroundAlpha(0.7) }}>
                  {budget.model}
                </span>
              ) : null}
            </div>
            <div style={{ marginTop: 4, display: "flex", alignItems: "baseline", gap: 6 }}>
              <span style={{ fontSize: 12.5, fontWeight: 600, fontVariantNumeric: "tabular-nums", color: DT.foreground }}>
                {`${formatTokens(used)} / ${formatTokens(total)}（${usedPercentLabel}）`}
              </span>
              {estimatedWindow ? (
                <span
                  style={{
                    flexShrink: 0,
                    borderRadius: 999,
                    background: DT.muted,
                    padding: "1px 6px",
                    fontSize: 9,
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    color: DT.mutedForeground,
                  }}
                >
                  估算
                </span>
              ) : null}
            </div>
            <div
              style={{
                marginTop: 8,
                display: "flex",
                height: 6,
                width: "100%",
                overflow: "hidden",
                borderRadius: 999,
                background: DT.muted,
              }}
            >
              {segments.map((segment) => (
                <div
                  key={segment.key}
                  style={{
                    width: `${Math.min(100, (segment.tokens / total) * 100)}%`,
                    backgroundColor: segmentColor(segment.key),
                  }}
                />
              ))}
            </div>
          </div>

          <div style={{ maxHeight: 240, overflowY: "auto", padding: "0 12px 10px", display: "flex", flexDirection: "column", rowGap: 6 }}>
            {segments.map((segment) => (
              <SegmentRow
                key={segment.key}
                color={segmentColor(segment.key)}
                label={
                  SEGMENT_LABELS[segment.key] ??
                  segment.key.replace(/_/g, " ")
                }
                tokens={segment.tokens}
                share={(segment.tokens / total) * 100}
              />
            ))}
            <SegmentRow
              bordered
              color={DT.muted}
              label="剩余空间"
              tokens={free}
              share={(free / total) * 100}
            />
          </div>

          {hasNotes && (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                rowGap: 4,
                borderTop: `1px solid ${DT.borderAlpha(0.6)}`,
                padding: "8px 12px",
                fontSize: 10.5,
                lineHeight: 1.5,
                color: DT.mutedForegroundAlpha(0.8),
              }}
            >
              {estimatedWindow && (
                <p style={{ margin: 0 }}>窗口大小由模型名推断得出，可在设置中按模型指定。</p>
              )}
              {heuristicCounter && (
                <p style={{ margin: 0 }}>token 数是按字符估算的粗略值。</p>
              )}
              {deferredCount > 0 && (
                <p style={{ margin: 0 }}>
                  {`${deferredCount} 个扩展工具按需加载，未被调用前不占用上下文。`}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
