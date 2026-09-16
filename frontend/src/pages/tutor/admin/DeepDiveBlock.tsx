/**
 * 复刻自 DeepTutor：web/app/(workspace)/book/components/blocks/DeepDiveBlock.tsx（平铺到 tupu）。
 * 替换点：删除 "use client" 与 react-i18next，i18n 中文直出（zh/app.json）：
 *   "Go Deeper"→深入学习、"Linked sub-page already exists."→关联子页面已存在.。
 * lucide：ChevronRight→RightOutlined、Sparkles→ThunderboltOutlined、Loader2→LoadingOutlined(spin)。
 * Tailwind → antd Button + 内联样式（primary 渐变底/主色 30% 边框等）；
 * 深潜条目 hover 主色边框由 antd Button 自带（对应原 hover:border-primary/40）。
 * props 契约不变：onDeepDive(topic, blockId)、pendingTopic。
 */
import { useState } from "react";
import {
  RightOutlined,
  ThunderboltOutlined,
  LoadingOutlined,
} from "@ant-design/icons";
import { Button } from "antd";
import type { Block } from './book-types';

const borderColor = "#e4e4e7";
const foreground = "rgba(0,0,0,0.88)";
const mutedForeground = "#6b7280";

interface Suggestion {
  topic?: string;
  rationale?: string;
}

export interface DeepDiveBlockProps {
  block: Block;
  onDeepDive?: (topic: string, blockId: string) => Promise<void> | void;
  pendingTopic?: string | null;
}

export default function DeepDiveBlock({
  block,
  onDeepDive,
  pendingTopic,
}: DeepDiveBlockProps) {
  const suggestions =
    (block.payload?.suggestions as Suggestion[] | undefined) || [];
  const linkedPageId = block.metadata?.deep_dive_page_id as string | undefined;
  const [busy, setBusy] = useState<string | null>(null);

  if (suggestions.length === 0) return null;

  return (
    <div
      style={{
        borderRadius: 16,
        border: "1px solid rgba(22,119,255,0.3)",
        background:
          "linear-gradient(to bottom right, rgba(22,119,255,0.05), transparent)",
        padding: 16,
        boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)",
      }}
    >
      <div style={{ marginBottom: 12, display: "flex", alignItems: "center", gap: 8 }}>
        <ThunderboltOutlined style={{ fontSize: 16, color: "#1677ff" }} />
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.16em",
            color: "#1677ff",
          }}
        >
          {"深入学习"}
        </span>
      </div>
      <ul
        style={{
          listStyle: "none",
          margin: 0,
          padding: 0,
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        {suggestions.map((s, i) => {
          const topic = s.topic || "";
          const isPending = busy === topic || pendingTopic === topic;
          return (
            <li key={i}>
              <Button
                block
                onClick={async () => {
                  if (!onDeepDive || !topic) return;
                  setBusy(topic);
                  try {
                    await onDeepDive(topic, block.id);
                  } finally {
                    setBusy(null);
                  }
                }}
                disabled={isPending || !!linkedPageId}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "flex-start",
                  justifyContent: "space-between",
                  gap: 12,
                  borderRadius: 12,
                  border: `1px solid ${borderColor}`,
                  background: "#fff",
                  padding: "8px 12px",
                  textAlign: "left",
                  height: "auto",
                }}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, fontWeight: 500, color: foreground }}>
                    {topic}
                  </div>
                  {s.rationale && (
                    <div
                      style={{
                        marginTop: 2,
                        fontSize: 12,
                        lineHeight: 1.625,
                        color: mutedForeground,
                      }}
                    >
                      {s.rationale}
                    </div>
                  )}
                </div>
                {isPending ? (
                  <LoadingOutlined
                    spin
                    style={{ fontSize: 16, flexShrink: 0, color: "#1677ff" }}
                  />
                ) : (
                  <RightOutlined
                    style={{ fontSize: 16, flexShrink: 0, color: mutedForeground }}
                  />
                )}
              </Button>
            </li>
          );
        })}
      </ul>
      {linkedPageId && (
        <p style={{ marginTop: 8, fontSize: 11, color: mutedForeground }}>
          {"关联子页面已存在。"}
        </p>
      )}
    </div>
  );
}
