/**
 * 批6 依赖补件：1:1 移植自 DeepTutor web/components/common/ModelThinkingCard.tsx。
 * 替换点：
 *  - "use client" 去；react-i18next → 文件内查表直出（zh/app.json 原译文）；
 *  - lucide-react → @ant-design/icons（登记：BrainCircuit → ExperimentOutlined；
 *    ChevronDown → DownOutlined（旋转由内联 transform 承载，展开态经 <style> 的
 *    details[open] 选择器）；Loader2 → LoadingOutlined（animate-spin → spin 属性））；
 *  - Tailwind 类逐项换内联样式；summary 的 list-none/[&::-webkit-details-marker]:hidden
 *    与 group-open/think:rotate-180 由一次性 <style> 承载（.dt-think-*）；
 *  - 颜色回退沿用 PartnerChat 先例：--border→#e2e8f0、--card→#ffffff、--background→#fdfcf9、
 *    --muted-foreground→#64748b、--foreground→#1c1816。
 * 其余逐字一致。
 */

import { useEffect, useRef, useState } from "react";
import {
  DownOutlined,
  ExperimentOutlined,
  LoadingOutlined,
} from "@ant-design/icons";

import MarkdownRenderer from "./MarkdownRenderer";

/* 一次性样式注入（details 展开态旋转 + marker 隐藏）。 */
const STYLE_ID = "dt-model-thinking-card-css";
const THINK_CARD_CSS = `
.dt-think-summary { list-style: none; }
.dt-think-summary::-webkit-details-marker { display: none; }
.dt-think-chevron { transition: transform 0.2s ease; }
.dt-think-card[open] .dt-think-chevron { transform: rotate(180deg); }
`;
if (typeof document !== "undefined" && !document.getElementById(STYLE_ID)) {
  const styleEl = document.createElement("style");
  styleEl.id = STYLE_ID;
  styleEl.textContent = THINK_CARD_CSS;
  document.head.appendChild(styleEl);
}

const ZH_MESSAGES: Record<string, string> = {
  "Thinking...": "思考中…",
  "Model thinking": "模型思考",
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

interface ModelThinkingCardProps {
  /** Inner text of a single <think>...</think> block (already trimmed). */
  content: string;
  /**
   * False while the model is still streaming inside the open <think> tag, so
   * the card stays expanded and shows a spinner. Once the closing tag arrives
   * the card auto-collapses (default-folded) unless the user has pinned it
   * open or closed manually.
   */
  closed: boolean;
}

/**
 * Collapsible card that surfaces a reasoning model's raw <think> scratchpad
 * in a way that visually echoes the system trace panels (subtle border,
 * muted typography) without being mistaken for one.
 *
 * Behaviour:
 *  - Default-open while the model is still writing the scratchpad so the
 *    user can watch reasoning happen live.
 *  - Auto-collapses the moment the closing tag arrives.
 *  - Once the user toggles the card themselves, their preference wins for
 *    the rest of the message lifetime.
 */
export default function ModelThinkingCard({
  content,
  closed,
}: ModelThinkingCardProps) {
  const [userToggled, setUserToggled] = useState<boolean | null>(null);
  const detailsRef = useRef<HTMLDetailsElement>(null);

  const open = userToggled !== null ? userToggled : !closed;

  // Keep the underlying <details> element in sync with our derived `open`
  // state. We do not bind `open` as a controlled prop because React strips
  // the boolean attribute on `false`, which races with the browser's
  // built-in toggle handling and produces a flicker the first time `closed`
  // flips during streaming.
  useEffect(() => {
    const el = detailsRef.current;
    if (el && el.open !== open) {
      el.open = open;
    }
  }, [open]);

  const handleToggle = (event: React.SyntheticEvent<HTMLDetailsElement>) => {
    const next = event.currentTarget.open;
    if (next !== open) {
      setUserToggled(next);
    }
  };

  const hasBody = content.trim().length > 0;
  const placeholder = `${t("Thinking...")}`;

  return (
    <details
      ref={detailsRef}
      onToggle={handleToggle}
      className="dt-think-card"
      style={{
        margin: "12px 0",
        overflow: "hidden",
        borderRadius: 12,
        border:
          "1px solid color-mix(in srgb, var(--border, #e2e8f0) 60%, transparent)",
        background:
          "color-mix(in srgb, var(--card, #ffffff) 40%, transparent)",
        transition: "border-color 0.15s ease",
      }}
    >
      <summary
        className="dt-think-summary"
        style={{
          display: "flex",
          cursor: "pointer",
          alignItems: "center",
          gap: 8,
          padding: "8px 12px",
          fontSize: 12,
          fontWeight: 500,
          color: "var(--muted-foreground, #64748b)",
          transition: "color 0.15s ease",
        }}
      >
        <DownOutlined
          className="dt-think-chevron"
          style={{ fontSize: 12, flexShrink: 0, opacity: 0.7 }}
        />
        <ExperimentOutlined style={{ fontSize: 12, flexShrink: 0, opacity: 0.8 }} />
        <span style={{ letterSpacing: "0.025em" }}>{t("Model thinking")}</span>
        {!closed && (
          <LoadingOutlined
            spin
            style={{
              fontSize: 11,
              marginLeft: 4,
              color: "color-mix(in srgb, var(--muted-foreground, #64748b) 70%, transparent)",
            }}
          />
        )}
      </summary>
      <div
        style={{
          borderTop:
            "1px solid color-mix(in srgb, var(--border, #e2e8f0) 40%, transparent)",
          background:
            "color-mix(in srgb, var(--background, #fdfcf9) 40%, transparent)",
          padding: "8px 12px",
        }}
      >
        {hasBody ? (
          <MarkdownRenderer content={content} variant="trace" />
        ) : (
          <div
            style={{
              fontSize: 11,
              color:
                "color-mix(in srgb, var(--muted-foreground, #64748b) 70%, transparent)",
            }}
          >
            {placeholder}
          </div>
        )}
      </div>
    </details>
  );
}
