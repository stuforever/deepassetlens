/**
 * 复刻自 DeepTutor 原仓 web/components/partners/PartnerModelPicker.tsx（整件 1:1，批6 6.3）。
 * 替换点：去 "use client"；t() → 文件内查表直出（zh/app.json 原译文）；Tailwind 类
 * 逐项换内联样式（hover 用事件直写）。lucide-react→antd 图标登记：
 * Check → CheckOutlined（strokeWidth 3 语义由图标自身承载）；Loader2 → LoadingOutlined(spin)。
 *
 * Always-expanded model picker for the partner wizard — a plain radio list
 * (system default + every catalog option), no hover-to-expand animation.
 */

import { useState } from "react";
import { CheckOutlined, LoadingOutlined } from "@ant-design/icons";
import {
  llmSelectionKey,
  sameLLMSelection,
  type LLMOption,
} from "../../lib/llm-options";
import type { LLMSelection } from "../../lib/unified-ws";

const ZH_MESSAGES: Record<string, string> = {
  "Loading models…": "正在加载模型…",
  "Could not load the model catalog — the partner will use the system default.":
    "无法加载模型目录——该伙伴将使用系统默认模型。",
  "System default": "系统默认",
  "Follows whatever the system default model is.": "始终跟随系统默认模型。",
  "No models configured yet — add providers in Settings → LLM.":
    "还没有配置模型——请在 设置 → LLM 中添加。",
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

function formatContext(tokens?: number): string {
  if (!tokens || tokens <= 0) return "";
  if (tokens >= 1_000_000) return `${Math.round(tokens / 100_000) / 10}M`;
  if (tokens >= 1_000) return `${Math.round(tokens / 1_000)}K`;
  return String(tokens);
}

function Row({
  title,
  subtitle,
  trailing,
  selected,
  onClick,
}: {
  title: string;
  subtitle?: string;
  trailing?: string;
  selected: boolean;
  onClick: () => void;
}) {
  const [hovered, setHovered] = useState(false);
  return (
    <button
      type="button"
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "flex",
        width: "100%",
        alignItems: "center",
        gap: 12,
        borderRadius: 8,
        border: `1px solid ${
          selected
            ? "var(--primary, #2563eb)"
            : hovered
              ? "var(--ring, #2563eb)"
              : "var(--border, #e2e8f0)"
        }`,
        padding: "8px 12px",
        textAlign: "left",
        background: selected ? "var(--secondary, #f1f5f9)" : "transparent",
        cursor: "pointer",
        transition: "border-color 150ms, background-color 150ms",
      }}
    >
      <span style={{ minWidth: 0, flex: 1 }}>
        <span
          style={{
            display: "block",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            fontSize: 13.5,
            fontWeight: 500,
            color: "var(--foreground, #0f172a)",
          }}
        >
          {title}
        </span>
        {subtitle && (
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
            {subtitle}
          </span>
        )}
      </span>
      {trailing && (
        <span
          style={{
            flexShrink: 0,
            fontSize: 11.5,
            color: "var(--muted-foreground, #64748b)",
          }}
        >
          {trailing}
        </span>
      )}
      <span
        style={{
          display: "flex",
          height: 16,
          width: 16,
          flexShrink: 0,
          alignItems: "center",
          justifyContent: "center",
          borderRadius: 9999,
          border: `1px solid ${
            selected ? "var(--primary, #2563eb)" : "var(--border, #e2e8f0)"
          }`,
          background: selected ? "var(--primary, #2563eb)" : "transparent",
          color: "var(--primary-foreground, #ffffff)",
        }}
      >
        {selected && <CheckOutlined style={{ fontSize: 12 }} />}
      </span>
    </button>
  );
}

export default function PartnerModelPicker({
  options,
  activeDefault,
  value,
  loading,
  error,
  onChange,
}: {
  options: LLMOption[];
  activeDefault: LLMSelection | null;
  value: LLMSelection | null;
  loading: boolean;
  error: boolean;
  onChange: (selection: LLMSelection | null) => void;
}) {
  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "8px 0",
          fontSize: 13,
          color: "var(--muted-foreground, #64748b)",
        }}
      >
        <LoadingOutlined spin style={{ fontSize: 14 }} />
        {t("Loading models…")}
      </div>
    );
  }
  if (error) {
    return (
      <p
        style={{
          fontSize: 13,
          color: "var(--muted-foreground, #64748b)",
          margin: 0,
        }}
      >
        {t(
          "Could not load the model catalog — the partner will use the system default.",
        )}
      </p>
    );
  }

  const defaultOption = activeDefault
    ? options.find((option) => sameLLMSelection(option, activeDefault))
    : undefined;
  const defaultDetail = defaultOption
    ? `${defaultOption.model_name || defaultOption.model} · ${defaultOption.provider_label || defaultOption.provider}`
    : undefined;

  return (
    <div
      style={{
        maxHeight: 340,
        overflowY: "auto",
        paddingRight: 4,
        display: "flex",
        flexDirection: "column",
        gap: 6,
      }}
    >
      <Row
        title={t("System default")}
        subtitle={
          defaultDetail ?? t("Follows whatever the system default model is.")
        }
        selected={value === null}
        onClick={() => onChange(null)}
      />
      {options.map((option) => (
        <Row
          key={llmSelectionKey(option)}
          title={option.model_name || option.model}
          subtitle={`${option.provider_label || option.provider} · ${option.profile_name}`}
          trailing={formatContext(option.context_window)}
          selected={value !== null && sameLLMSelection(option, value)}
          onClick={() =>
            onChange({
              profile_id: option.profile_id,
              model_id: option.model_id,
            })
          }
        />
      ))}
      {options.length === 0 && (
        <p
          style={{
            padding: "4px 0",
            fontSize: 13,
            color: "var(--muted-foreground, #64748b)",
            margin: 0,
          }}
        >
          {t("No models configured yet — add providers in Settings → LLM.")}
        </p>
      )}
    </div>
  );
}
