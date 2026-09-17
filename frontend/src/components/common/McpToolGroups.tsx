/**
 * 批6 依赖补件：1:1 移植自 DeepTutor web/components/common/McpToolGroups.tsx
 * （ToolPicker 依赖）。替换点：
 *  - "use client" 去；
 *  - lucide-react ChevronRight → @ant-design/icons RightOutlined（尺寸经 fontSize 承载，
 *    rotate-90 展开旋转由内联 transform 承载）；
 *  - @/lib/mcp-tool-groups → ../../lib/mcp-tool-groups（本批 1:1 补件）；
 *  - Tailwind 类逐项换内联样式；hover 态由一次性 <style> 承载（.dtmc-row/.dtmc-toggle）；
 *  - rowsClassName prop 按源保留 string 契约（调用方 ToolPicker 传源字符串
 *    "grid grid-cols-1 gap-0.5 sm:grid-cols-2"，本件内部映射为两列 grid/行距 2px；
 *    缺省 "space-y-1.5" → 纵向 flex gap 6px）。
 * 其余逐字一致。
 */

import { useState, type CSSProperties, type ReactNode } from "react";
import { RightOutlined } from "@ant-design/icons";
import {
  groupProviderTools,
  groupCounts,
  selectionFromCounts,
  setGroupSelected,
  toggleToolName,
  type ProviderToolLike,
} from "../../lib/mcp-tool-groups";

/** rowsClassName（源 tailwind 字面量）→ 内联布局样式。 */
function rowsToStyle(cls: string | undefined): CSSProperties {
  if (cls && cls.includes("sm:grid-cols-2")) {
    // 源：grid grid-cols-1 gap-0.5 sm:grid-cols-2（移动单列、桌面两列、行距 2px）
    return {
      display: "grid",
      gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
      rowGap: 2,
      columnGap: 0,
    };
  }
  // 源缺省：space-y-1.5
  return { display: "flex", flexDirection: "column", gap: 6 };
}

/* 一次性样式注入（hover 态）。 */
const STYLE_ID = "dt-mcp-tool-groups-css";
const MCP_TOOL_GROUPS_CSS = `
.dtmc-row:hover { background-color: color-mix(in srgb, var(--muted, #f1ede2) 50%, transparent); }
.dtmc-toggle { color: var(--muted-foreground, #64748b); transition: color 0.15s ease; }
.dtmc-toggle:hover { color: var(--foreground, #1c1816); }
`;
if (typeof document !== "undefined" && !document.getElementById(STYLE_ID)) {
  const styleEl = document.createElement("style");
  styleEl.id = STYLE_ID;
  styleEl.textContent = MCP_TOOL_GROUPS_CSS;
  document.head.appendChild(styleEl);
}

export default function McpToolGroups<T extends ProviderToolLike>({
  tools,
  selected,
  onChange,
  disabled = false,
  rowsClassName,
  renderTool,
}: {
  tools: readonly T[];
  /** Flat tool-name whitelist — exactly what the caller saves. */
  selected: string[];
  onChange: (next: string[]) => void;
  disabled?: boolean;
  /** Container class for an expanded group's rows (callers keep their layout). */
  rowsClassName?: string;
  renderTool: (args: {
    tool: T;
    checked: boolean;
    onToggle: () => void;
  }) => ReactNode;
}) {
  // Expansion overrides keyed by provider id; a group with no override follows
  // its selection state, so a partially granted service opens on its own
  // (including after the options arrive asynchronously).
  const [overrides, setOverrides] = useState<Record<string, boolean>>({});

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {groupProviderTools(tools).map((group) => {
        const counts = groupCounts(group.tools, selected);
        const state = selectionFromCounts(counts);
        const chosen = counts.hits;
        const open = overrides[group.id] ?? state === "partial";
        return (
          <div key={group.id}>
            <div
              className="dtmc-row"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                borderRadius: 8,
                padding: "4px 8px",
              }}
            >
              <label
                style={{
                  display: "flex",
                  minWidth: 0,
                  flex: 1,
                  cursor: "pointer",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <input
                  type="checkbox"
                  checked={state === "all"}
                  disabled={disabled}
                  ref={(el) => {
                    if (el) el.indeterminate = state === "partial";
                  }}
                  onChange={() => {
                    // Pin the current expansion first: without an override the
                    // row follows `state === "partial"`, so ticking a partial
                    // group would flip it to "all" and snap it shut under the
                    // cursor mid-review.
                    setOverrides((current) => ({
                      ...current,
                      [group.id]: open,
                    }));
                    onChange(
                      setGroupSelected(selected, group.tools, state !== "all"),
                    );
                  }}
                />
                <span
                  style={{
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    fontFamily:
                      'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                    fontSize: 11.5,
                    color: "var(--foreground, #1c1816)",
                  }}
                >
                  {group.id}
                </span>
              </label>
              <span
                style={{
                  flexShrink: 0,
                  fontSize: 11,
                  fontVariantNumeric: "tabular-nums",
                  color: "var(--muted-foreground, #64748b)",
                }}
              >
                {chosen}/{group.tools.length}
              </span>
              <button
                type="button"
                aria-label={group.id}
                aria-expanded={open}
                onClick={() =>
                  setOverrides((current) => ({ ...current, [group.id]: !open }))
                }
                className="dtmc-toggle"
                style={{
                  flexShrink: 0,
                  borderRadius: 4,
                  padding: 2,
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  fontSize: 14,
                  display: "flex",
                  alignItems: "center",
                }}
              >
                <RightOutlined
                  style={{
                    transform: open ? "rotate(90deg)" : undefined,
                    transition: "transform 0.2s ease",
                  }}
                />
              </button>
            </div>
            {open && (
              <div style={{ paddingLeft: 16, ...rowsToStyle(rowsClassName) }}>
                {group.tools.map((tool) =>
                  renderTool({
                    tool,
                    checked: selected.includes(tool.name),
                    onToggle: () =>
                      onChange(toggleToolName(selected, tool.name)),
                  }),
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
