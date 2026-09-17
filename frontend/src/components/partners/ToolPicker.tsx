/**
 * 复刻自 DeepTutor 原仓 web/components/partners/ToolPicker.tsx（整件 1:1，批6 6.3）。
 * 替换点：去 "use client"；t() → 文件内查表直出（zh/app.json 原译文；"Always on and
 * built in — ..." 长句 zh 包未收录，保留英文原文）；Tailwind 类逐项换内联样式
 * （hover 用事件直写；响应式 sm:grid-cols-2 直接取桌面两列）；McpToolGroups 的
 * rowsClassName 参数按源语义换为内联样式对象（见文件尾类型说明）。
 * 无 lucide 图标（源件无图标）。
 *
 * Tool surface configuration: the user-toggleable system tools (same pool as
 * the chat composer) plus configured MCP tools, grouped by server.
 *
 * Semantics mirror the backend config: `null` = everything allowed, an
 * explicit array = whitelist. The picker always hands back an array. System
 * and built-in tools default to `null`, so callers materialise those into "all
 * selected" for editing; MCP tools default to `[]` (off) and are never
 * materialised that way — granting them is an explicit pick.
 */

import { useState } from "react";

import McpToolGroups from "../common/McpToolGroups";
import type { McpToolOption, ToolOptions } from "../../lib/partners-api";

const ZH_MESSAGES: Record<string, string> = {
  "Loading tools…": "正在加载工具…",
  "System tools": "系统工具",
  All: "全部",
  None: "无",
  "Built-in tools": "内置工具",
  "Mounted automatically when the context calls for it — a knowledge base attached, memory available, the sandbox enabled. Deny any you don't want this partner to have.":
    "在上下文需要时自动挂载——挂载了知识库、有可用记忆、开启了沙箱等。不想让这个伙伴拥有的可以关闭。",
  Memory: "记忆",
  "MCP tools": "MCP 工具",
};

function t(key: string, vars?: Record<string, string | number>): string {
  let text = ZH_MESSAGES[key] ?? key;
  if (vars) {
    for (const [name, value] of Object.entries(vars)) {
      text = text.split(`{{${name}}}`).join(String(value));
    }
  }
  return text;
}

/** 原仓 rowsClassName="grid grid-cols-1 gap-0.5 sm:grid-cols-2"——按源字符串逐字
 *  传给 McpToolGroups（并行批次件，其内部自行承载该布局语义）。 */
const MCP_ROWS_CLASS = "grid grid-cols-1 gap-0.5 sm:grid-cols-2";

function ToggleRow({
  name,
  description,
  checked,
  onToggle,
}: {
  name: string;
  description?: string;
  checked: boolean;
  onToggle: () => void;
}) {
  const [hovered, setHovered] = useState(false);
  return (
    <label
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "flex",
        cursor: "pointer",
        alignItems: "flex-start",
        gap: 8,
        borderRadius: 8,
        padding: "6px 8px",
        background: hovered ? "var(--muted, #f1f5f9)" : "transparent",
        transition: "background-color 150ms",
      }}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={onToggle}
        style={{ marginTop: 2 }}
      />
      <span style={{ minWidth: 0 }}>
        <span
          style={{
            display: "block",
            fontSize: 13,
            color: "var(--foreground, #0f172a)",
          }}
        >
          {name}
        </span>
        {description && (
          <span
            style={{
              display: "block",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              fontSize: 11.5,
              color: "var(--muted-foreground, #64748b)",
            }}
          >
            {description}
          </span>
        )}
      </span>
    </label>
  );
}

export default function ToolPicker({
  options,
  enabledTools,
  builtinTools,
  mcpTools,
  onChangeEnabledTools,
  onChangeBuiltinTools,
  onChangeMcpTools,
}: {
  options: ToolOptions | null;
  enabledTools: string[];
  builtinTools: string[];
  mcpTools: string[];
  onChangeEnabledTools: (next: string[]) => void;
  onChangeBuiltinTools: (next: string[]) => void;
  onChangeMcpTools: (next: string[]) => void;
}) {
  if (!options) {
    return (
      <p
        style={{
          fontSize: 13,
          color: "var(--muted-foreground, #64748b)",
          margin: 0,
        }}
      >
        {t("Loading tools…")}
      </p>
    );
  }

  const toggle = (
    list: string[],
    name: string,
    setter: (next: string[]) => void,
  ) => {
    setter(
      list.includes(name) ? list.filter((n) => n !== name) : [...list, name],
    );
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      <div>
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            justifyContent: "space-between",
            marginBottom: 6,
          }}
        >
          <h4
            style={{
              fontSize: 13,
              fontWeight: 500,
              color: "var(--muted-foreground, #64748b)",
              margin: 0,
            }}
          >
            {t("System tools")}
          </h4>
          <div style={{ display: "flex", gap: 8, fontSize: 12 }}>
            <AllNoneButtons
              onAll={() =>
                onChangeEnabledTools(options.tools.map((tl) => tl.name))
              }
              onNone={() => onChangeEnabledTools([])}
            />
          </div>
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
            gap: 2,
          }}
        >
          {options.tools.map((tool) => (
            <ToggleRow
              key={tool.name}
              name={tool.name}
              description={tool.description}
              checked={enabledTools.includes(tool.name)}
              onToggle={() =>
                toggle(enabledTools, tool.name, onChangeEnabledTools)
              }
            />
          ))}
        </div>
      </div>

      {options.builtin_tools.length > 0 && (
        <div>
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              justifyContent: "space-between",
              marginBottom: 6,
            }}
          >
            <h4
              style={{
                fontSize: 13,
                fontWeight: 500,
                color: "var(--muted-foreground, #64748b)",
                margin: 0,
              }}
            >
              {t("Built-in tools")}
            </h4>
            <div style={{ display: "flex", gap: 8, fontSize: 12 }}>
              <AllNoneButtons
                onAll={() =>
                  onChangeBuiltinTools(
                    options.builtin_tools.map((tl) => tl.name),
                  )
                }
                onNone={() => onChangeBuiltinTools([])}
              />
            </div>
          </div>
          <p
            style={{
              marginBottom: 6,
              padding: "0 8px",
              fontSize: 11.5,
              color: "var(--muted-foreground, #64748b)",
              margin: "0 0 6px",
            }}
          >
            {t(
              "Mounted automatically when the context calls for it — a knowledge base attached, memory available, the sandbox enabled. Deny any you don't want this partner to have.",
            )}
          </p>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
              gap: 2,
            }}
          >
            {options.builtin_tools.map((tool) => (
              <ToggleRow
                key={tool.name}
                name={tool.name}
                description={tool.description}
                checked={builtinTools.includes(tool.name)}
                onToggle={() =>
                  toggle(builtinTools, tool.name, onChangeBuiltinTools)
                }
              />
            ))}
          </div>
        </div>
      )}

      <div>
        <h4
          style={{
            fontSize: 13,
            fontWeight: 500,
            color: "var(--muted-foreground, #64748b)",
            margin: "0 0 6px",
          }}
        >
          {t("Memory")}
        </h4>
        <p
          style={{
            padding: "0 8px",
            fontSize: 11.5,
            color: "var(--muted-foreground, #64748b)",
            margin: 0,
          }}
        >
          {t(
            "Always on and built in — not configurable. partner_read sees the owner's shared memory plus the partner's own; partner_memorize writes only the partner's own memory; partner_search keyword-searches past conversations.",
          )}
        </p>
      </div>

      {options.mcp_tools.length > 0 && (
        <div>
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              justifyContent: "space-between",
              marginBottom: 6,
            }}
          >
            <h4
              style={{
                fontSize: 13,
                fontWeight: 500,
                color: "var(--muted-foreground, #64748b)",
                margin: 0,
              }}
            >
              {t("MCP tools")}
            </h4>
            <div style={{ display: "flex", gap: 8, fontSize: 12 }}>
              <AllNoneButtons
                onAll={() => onChangeMcpTools(options.mcp_tools.map((tl) => tl.name))}
                onNone={() => onChangeMcpTools([])}
              />
            </div>
          </div>
          <McpToolGroups
            tools={options.mcp_tools}
            selected={mcpTools}
            onChange={onChangeMcpTools}
            rowsClassName={MCP_ROWS_CLASS}
            renderTool={({
              tool,
              checked,
              onToggle,
            }: {
              tool: McpToolOption;
              checked: boolean;
              onToggle: () => void;
            }) => (
              <ToggleRow
                key={tool.name}
                name={tool.name}
                description={tool.description}
                checked={checked}
                onToggle={onToggle}
              />
            )}
          />
        </div>
      )}
    </div>
  );
}

/** 「全部 / 无」双按钮（源内联重复了 4 次，这里等价抽出，文案/样式逐字一致）。 */
function AllNoneButtons({
  onAll,
  onNone,
}: {
  onAll: () => void;
  onNone: () => void;
}) {
  const [allHovered, setAllHovered] = useState(false);
  const [noneHovered, setNoneHovered] = useState(false);
  return (
    <>
      <button
        type="button"
        onClick={onAll}
        onMouseEnter={() => setAllHovered(true)}
        onMouseLeave={() => setAllHovered(false)}
        style={{
          border: "none",
          background: "transparent",
          padding: 0,
          cursor: "pointer",
          fontSize: 12,
          color: "var(--primary, #2563eb)",
          textDecoration: allHovered ? "underline" : "none",
        }}
      >
        {t("All")}
      </button>
      <button
        type="button"
        onClick={onNone}
        onMouseEnter={() => setNoneHovered(true)}
        onMouseLeave={() => setNoneHovered(false)}
        style={{
          border: "none",
          background: "transparent",
          padding: 0,
          cursor: "pointer",
          fontSize: 12,
          color: "var(--muted-foreground, #64748b)",
          textDecoration: noneHovered ? "underline" : "none",
        }}
      >
        {t("None")}
      </button>
    </>
  );
}
