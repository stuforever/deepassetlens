/**
 * 复刻自 DeepTutor 原仓 web/components/common/ModelThinkingCard.tsx（1:1）。
 * 替换点：
 * - 删除 "use client"；react-i18next → 中文直出（zh/app.json 译文）；
 * - lucide-react → @ant-design/icons（ChevronDown→DownOutlined、
 *   BrainCircuit→RobotOutlined（语义就近：模型思考）、Loader2→LoadingOutlined spin）；
 * - Tailwind → 内联样式：summary 用 display:flex 去除默认 marker（等价于原
 *   [&::-webkit-details-marker]:hidden），chevron 旋转改为按 open 状态内联
 *   transform（等价 group-open/think:rotate-180），hover 文字色用 onMouse 事件保持。
 */
import { useEffect, useRef, useState } from "react";
import type { SyntheticEvent } from "react";
import {
  DownOutlined,
  LoadingOutlined,
  RobotOutlined,
} from "@ant-design/icons";

import MarkdownRenderer from "./MarkdownRenderer";

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

  const handleToggle = (event: SyntheticEvent<HTMLDetailsElement>) => {
    const next = event.currentTarget.open;
    if (next !== open) {
      setUserToggled(next);
    }
  };

  const hasBody = content.trim().length > 0;
  const placeholder = `思考中…`;

  return (
    <details
      ref={detailsRef}
      onToggle={handleToggle}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = "#e4e4e7";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = "rgba(228,228,231,0.6)";
      }}
      style={{
        margin: "12px 0",
        overflow: "hidden",
        borderRadius: 12,
        border: "1px solid rgba(228,228,231,0.6)",
        background: "rgba(255,255,255,0.4)",
        transition: "border-color 0.2s",
      }}
    >
      <summary
        onMouseEnter={(e) => {
          e.currentTarget.style.color = "rgba(0,0,0,0.88)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.color = "#6b7280";
        }}
        style={{
          display: "flex",
          cursor: "pointer",
          alignItems: "center",
          gap: 8,
          padding: "8px 12px",
          fontSize: 12,
          fontWeight: 500,
          color: "#6b7280",
          letterSpacing: "0.025em",
          transition: "color 0.2s",
        }}
      >
        <DownOutlined
          style={{
            fontSize: 12,
            flexShrink: 0,
            opacity: 0.7,
            transform: open ? "rotate(180deg)" : "none",
            transition: "transform 0.2s",
          }}
        />
        <RobotOutlined style={{ fontSize: 12, flexShrink: 0, opacity: 0.8 }} />
        <span>模型思考</span>
        {!closed && (
          <LoadingOutlined
            spin
            style={{ fontSize: 11, marginLeft: 4, color: "rgba(107,114,128,0.7)" }}
          />
        )}
      </summary>
      <div
        style={{
          borderTop: "1px solid rgba(228,228,231,0.4)",
          background: "rgba(255,255,255,0.4)",
          padding: "8px 12px",
        }}
      >
        {hasBody ? (
          <MarkdownRenderer content={content} variant="trace" />
        ) : (
          <div
            style={{
              fontSize: 11,
              color: "rgba(107,114,128,0.7)",
            }}
          >
            {placeholder}
          </div>
        )}
      </div>
    </details>
  );
}
