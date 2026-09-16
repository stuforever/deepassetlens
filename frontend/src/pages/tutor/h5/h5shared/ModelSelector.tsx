/**
 * 桌面同名件 1:1（复刻自 DeepTutor 原仓 web/components/chat/home/ModelSelector.tsx，287 行）。
 * 替换点：删除 "use client"；lucide AlertCircle/Bot/Check/ChevronDown→
 * ExclamationCircleOutlined/RobotOutlined/CheckOutlined/DownOutlined；ProviderIcon →
 * 本目录批9 件；LLMSelection→../../admin/unified-ws、llm-options→./llmOptions
 * （批8/SA-D 同源契约）；Tailwind→内联样式（token 见 dtStyle.ts）；hover→
 * onMouseEnter/Leave 直写 style；t() 译文取 zh/app.json（"System default"→系统默认、
 * "Use the active default model from Settings"→使用设置中的当前默认模型、
 * "Loading models"→模型加载中、"Models unavailable"→模型不可用、"Select model"→
 * 选择模型、"Default"→默认）。逻辑/状态机/截断浮层逐字未改。
 */
import { useEffect, useMemo, useRef, useState } from "react";
import {
  ExclamationCircleOutlined,
  RobotOutlined,
  CheckOutlined,
  DownOutlined,
} from "@ant-design/icons";
import { useLingerExpand } from "./use-linger-expand";
import ProviderIcon from "./ProviderIcon";
import type { LLMSelection } from "../../admin/unified-ws";
import {
  llmSelectionKey,
  sameLLMSelection,
  type LLMOption,
} from "./llmOptions";
import { DT, ellipsis } from "./dtStyle";

function formatContextWindow(value?: number) {
  if (!value) return "";
  if (value >= 1_000_000) return `${Math.round(value / 1_000_000)}M ctx`;
  if (value >= 1_000) return `${Math.round(value / 1_000)}k ctx`;
  return `${value} ctx`;
}

function providerLabel(option: LLMOption) {
  return (
    option.provider_label || option.provider || option.profile_name || "LLM"
  );
}

function ModelOptionRow({
  option,
  selected,
  onSelect,
}: {
  option: LLMOption;
  selected: boolean;
  onSelect: () => void;
}) {
  // Official model ID as the primary label (what gets sent to the API),
  // per design. The user-given nickname and profile live in the tooltip.
  const modelLabel = option.model || option.model_name;
  const contextWindow = formatContextWindow(option.context_window);
  // Long model ids ("google/gemini-3-flash-preview") get ellipsized by the
  // inline layout; hovering the row reveals the full id as an overlay. The
  // scrollWidth check at mouseenter time keeps the overlay away from rows
  // that aren't actually truncated.
  const nameRef = useRef<HTMLSpanElement>(null);
  const [revealFull, setRevealFull] = useState(false);
  return (
    <button
      type="button"
      title={`${option.model_name} | ${option.profile_name}`}
      onClick={onSelect}
      onMouseEnter={() => {
        const el = nameRef.current;
        setRevealFull(!!el && el.scrollWidth > el.clientWidth + 1);
      }}
      onMouseLeave={() => setRevealFull(false)}
      style={{
        position: "relative",
        display: "flex",
        width: "100%",
        alignItems: "center",
        gap: 8,
        padding: "6px 12px",
        textAlign: "left",
        border: "none",
        cursor: "pointer",
        background: selected ? DT.primaryAlpha(0.06) : "transparent",
        font: "inherit",
      }}
    >
      <ProviderIcon
        provider={option.provider}
        size={14}
        className={
          selected ? "text-[var(--primary)]" : "text-[var(--muted-foreground)]"
        }
      />
      <span
        ref={nameRef}
        style={{ ...ellipsis, fontSize: 12.5, fontWeight: 500, color: DT.foreground }}
      >
        {modelLabel}
      </span>
      {option.is_active_default && (
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
          默认
        </span>
      )}
      <span style={{ ...ellipsis, flex: 1, fontSize: 11, color: DT.mutedForeground }}>
        {providerLabel(option)}
      </span>
      {contextWindow ? (
        <span style={{ flexShrink: 0, fontSize: 11, color: DT.mutedForeground }}>
          {contextWindow}
        </span>
      ) : null}
      {selected && (
        <CheckOutlined
          style={{ fontSize: 14, flexShrink: 0, color: DT.primary }}
        />
      )}
      {revealFull && (
        <span
          style={{
            pointerEvents: "none",
            position: "absolute",
            left: 6,
            right: 6,
            top: "50%",
            zIndex: 10,
            transform: "translateY(-50%)",
            wordBreak: "break-all",
            borderRadius: 8,
            border: `1px solid ${DT.border}`,
            background: DT.popover,
            padding: "4px 8px",
            fontSize: 12,
            fontWeight: 500,
            color: DT.foreground,
            boxShadow:
              "0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1)",
          }}
        >
          {modelLabel}
        </span>
      )}
    </button>
  );
}

export default function ModelSelector({
  options,
  activeDefault,
  value,
  loading,
  error,
  allowSystemDefault = false,
  systemDefaultLabel,
  systemDefaultDetail,
  helperText,
  placement = "top",
  onChange,
}: {
  options: LLMOption[];
  activeDefault: LLMSelection | null;
  value: LLMSelection | null;
  loading: boolean;
  error: boolean;
  allowSystemDefault?: boolean;
  systemDefaultLabel?: string;
  systemDefaultDetail?: string;
  helperText?: string;
  placement?: "top" | "bottom";
  onChange: (selection: LLMSelection | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const { expanded, linger, triggerProps: lingerProps } = useLingerExpand(open);

  const selectedSelection = allowSystemDefault
    ? value
    : (value ?? activeDefault);
  const selectedKey = llmSelectionKey(selectedSelection);
  const selectedOption = useMemo(
    () =>
      options.find((option) => sameLLMSelection(option, selectedSelection)) ??
      null,
    [options, selectedSelection],
  );

  useEffect(() => {
    if (!open) return;
    const handler = (event: MouseEvent) => {
      const target = event.target as Node;
      if (rootRef.current && !rootRef.current.contains(target)) {
        setOpen(false);
        linger();
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open, linger]);

  const defaultLabel = systemDefaultLabel || "系统默认";
  const defaultDetail =
    systemDefaultDetail || "使用设置中的当前默认模型";
  const disabled =
    loading || error || (options.length === 0 && !allowSystemDefault);
  const label = loading
    ? "模型加载中"
    : error
      ? "模型不可用"
      : allowSystemDefault && !selectedSelection
        ? defaultLabel
        : // Official model ID, consistent with the dropdown rows.
          selectedOption?.model ||
          selectedOption?.model_name ||
          "选择模型";
  const menuPosition = placement === "bottom" ? "top" : "bottom";

  return (
    <div ref={rootRef} style={{ position: "relative" }}>
      {/* Same resting/expanded treatment as PersonaSelector: the brand
          icon is the whole control at rest; hovering (or opening) slides
          the model name out with a max-width animation and lingers ~1.2s
          after leave/selection before collapsing. */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((current) => !current)}
        aria-label={"选择模型"}
        aria-expanded={open}
        {...lingerProps}
        onMouseEnter={(e) => {
          if (disabled) return;
          e.currentTarget.style.background = DT.mutedAlpha(0.55);
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = open ? DT.muted : "transparent";
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
          cursor: disabled ? "not-allowed" : "pointer",
          background: open && !disabled ? DT.muted : "transparent",
          color: disabled ? DT.border : open ? DT.foreground : DT.mutedForeground,
          transition: "background-color 150ms, color 150ms, transform 150ms",
        }}
      >
        {error ? (
          <ExclamationCircleOutlined style={{ fontSize: 16, flexShrink: 0 }} />
        ) : (
          <ProviderIcon provider={selectedOption?.provider} size={16} />
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
            maxWidth: expanded ? 180 : 0,
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

      {open && !disabled && (
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
          {helperText ? (
            <div
              style={{
                borderBottom: `1px solid ${DT.borderAlpha(0.5)}`,
                padding: "6px 12px",
                fontSize: 11,
                color: DT.mutedForeground,
              }}
            >
              {helperText}
            </div>
          ) : null}
          <div style={{ maxHeight: 280, overflowY: "auto", padding: "4px 0" }}>
            {allowSystemDefault && (
              <button
                type="button"
                title={defaultDetail}
                onClick={() => {
                  onChange(null);
                  setOpen(false);
                  linger();
                }}
                onMouseEnter={(e) => {
                  if (selectedKey !== "") {
                    e.currentTarget.style.background = DT.mutedAlpha(0.45);
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background =
                    selectedKey === "" ? DT.primaryAlpha(0.06) : "transparent";
                }}
                style={{
                  display: "flex",
                  width: "100%",
                  alignItems: "center",
                  gap: 8,
                  padding: "6px 12px",
                  textAlign: "left",
                  border: "none",
                  cursor: "pointer",
                  background:
                    selectedKey === "" ? DT.primaryAlpha(0.06) : "transparent",
                  font: "inherit",
                }}
              >
                <RobotOutlined
                  style={{
                    fontSize: 14,
                    flexShrink: 0,
                    color:
                      selectedKey === "" ? DT.primary : DT.mutedForeground,
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
                  {defaultLabel}
                </span>
                {selectedKey === "" && (
                  <CheckOutlined
                    style={{ fontSize: 14, flexShrink: 0, color: DT.primary }}
                  />
                )}
              </button>
            )}
            {options.map((option) => {
              const optionSelection = {
                profile_id: option.profile_id,
                model_id: option.model_id,
              };
              const optionKey = llmSelectionKey(optionSelection);
              return (
                <ModelOptionRow
                  key={optionKey}
                  option={option}
                  selected={optionKey === selectedKey}
                  onSelect={() => {
                    onChange(optionSelection);
                    setOpen(false);
                    linger();
                  }}
                />
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
