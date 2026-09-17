/**
 * 复刻自 DeepTutor 原仓 web/components/partners/PartnerModelSelect.tsx（整件 1:1，批6 6.3）。
 * 替换点：去 "use client"；t() → 文件内查表直出（zh/app.json 原译文）；Tailwind 类
 * 逐项换内联样式（hover 用事件直写）。lucide-react→antd 图标登记：
 * Check → CheckOutlined；ChevronDown → DownOutlined；Loader2 → LoadingOutlined(spin)。
 *
 * Click-to-open model dropdown that always shows the full current choice as
 * text (no collapse-to-icon, no hover-expand). Used for the partner's
 * primary/backup model rows; `noneLabel` names the null choice ("System
 * default" for primary, "No backup" for backup).
 */

import { useEffect, useRef, useState } from "react";
import { CheckOutlined, DownOutlined, LoadingOutlined } from "@ant-design/icons";
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

export default function PartnerModelSelect({
  options,
  activeDefault,
  value,
  loading,
  error,
  noneLabel,
  noneDetail,
  onChange,
}: {
  options: LLMOption[];
  activeDefault: LLMSelection | null;
  value: LLMSelection | null;
  loading: boolean;
  error: boolean;
  noneLabel: string;
  noneDetail?: string;
  onChange: (selection: LLMSelection | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          borderRadius: 12,
          border: "1px solid var(--border, #e2e8f0)",
          padding: "10px 14px",
          fontSize: 13.5,
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

  const current = value
    ? options.find((option) => sameLLMSelection(option, value))
    : undefined;
  const defaultOption = activeDefault
    ? options.find((option) => sameLLMSelection(option, activeDefault))
    : undefined;

  const currentTitle = value
    ? current
      ? current.model_name || current.model
      : value.model_id
    : noneLabel;
  const currentSubtitle = value
    ? current
      ? `${current.provider_label || current.provider} · ${current.profile_name}`
      : ""
    : (noneDetail ??
      (defaultOption
        ? `${defaultOption.model_name || defaultOption.model} · ${defaultOption.provider_label || defaultOption.provider}`
        : ""));

  const select = (next: LLMSelection | null) => {
    onChange(next);
    setOpen(false);
  };

  return (
    <div ref={rootRef} style={{ position: "relative" }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        style={{
          display: "flex",
          width: "100%",
          alignItems: "center",
          gap: 12,
          borderRadius: 12,
          border: `1px solid ${
            open ? "var(--ring, #2563eb)" : "var(--border, #e2e8f0)"
          }`,
          padding: "10px 14px",
          textAlign: "left",
          background: "transparent",
          cursor: "pointer",
          transition: "border-color 150ms",
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
            {currentTitle}
          </span>
          {currentSubtitle && (
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
              {currentSubtitle}
            </span>
          )}
        </span>
        <DownOutlined
          style={{
            flexShrink: 0,
            fontSize: 14,
            color: "var(--muted-foreground, #64748b)",
            transform: open ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform 200ms",
          }}
        />
      </button>

      {open && (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            zIndex: 30,
            marginTop: 4,
            maxHeight: 300,
            overflowY: "auto",
            borderRadius: 12,
            border: "1px solid var(--border, #e2e8f0)",
            background: "var(--popover, #ffffff)",
            padding: 4,
            boxShadow:
              "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)",
          }}
        >
          <DropdownRow
            title={noneLabel}
            subtitle={noneDetail}
            selected={value === null}
            onClick={() => select(null)}
          />
          {options.map((option) => (
            <DropdownRow
              key={llmSelectionKey(option)}
              title={option.model_name || option.model}
              subtitle={`${option.provider_label || option.provider} · ${option.profile_name}`}
              trailing={formatContext(option.context_window)}
              selected={value !== null && sameLLMSelection(option, value)}
              onClick={() =>
                select({
                  profile_id: option.profile_id,
                  model_id: option.model_id,
                })
              }
            />
          ))}
          {options.length === 0 && (
            <p
              style={{
                padding: "8px 12px",
                fontSize: 13,
                color: "var(--muted-foreground, #64748b)",
                margin: 0,
              }}
            >
              {t("No models configured yet — add providers in Settings → LLM.")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function DropdownRow({
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
        padding: "8px 10px",
        textAlign: "left",
        border: "none",
        background: selected
          ? "var(--secondary, #f1f5f9)"
          : hovered
            ? "var(--muted, #f1f5f9)"
            : "transparent",
        cursor: "pointer",
        transition: "background-color 150ms",
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
      {selected && (
        <CheckOutlined
          style={{
            flexShrink: 0,
            fontSize: 14,
            color: "var(--primary, #2563eb)",
          }}
        />
      )}
    </button>
  );
}
