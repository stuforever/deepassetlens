/**
 * KbUpdateHistory —— 知识库更新历史列表（本地持久化任务记录，可展开查看错误与日志尾段，可清空）。
 * 1:1 复刻自原仓 DeepTutor web/components/knowledge/KbUpdateHistory.tsx（147 行）。
 * 复刻来源：Next.js + Tailwind + react-i18next + lucide-react + "@/hooks/useKnowledgeHistory"
 * 替换点：
 *  - "use client" 删除；
 *  - react-i18next（useTranslation/t(key)）→ 中文直出（译文取自原仓 web/locales/zh/app.json：
 *    "Update history"→更新历史、"Clear history"→清空历史、"No logs captured."→没有日志记录。）；
 *  - lucide-react → @ant-design/icons 语义就近：AlertCircle→ExclamationCircleOutlined、
 *    CheckCircle2→CheckCircleOutlined、ChevronDown→DownOutlined、ChevronRight→RightOutlined、
 *    History→HistoryOutlined、Trash2→DeleteOutlined、Upload→UploadOutlined、
 *    RefreshCw→SyncOutlined、Wand2→ThunderboltOutlined；
 *  - Tailwind → antd 组件 + 最小内联样式（行 hover 用 onMouseEnter/Leave 置背景、
 *    completed 绿 #d1fae5/#047857、error 红 #fee2e2/#b91c1c、muted #8c8c8c、分隔线 #f0f0f0）；
 *  - import 契约：HistoryEntry 类型 → './useKnowledgeHistory'（并行 Agent 同步产出，
 *    结构按源 hook：id/taskId/kind/label/status/startedAt/completedAt/fileCount?/error?/logTail）。
 * 不变：props 契约（entries/onClear）、entries 为空整个组件不渲染（return null）、
 *       expandedId 单条展开状态机、formatDuration 硬编码英文（Xms/X.Xs/Xm Ys，不经翻译）、
 *       entry.label 后端侧英文原样（Create {kb}/Upload to {kb}/Re-index {kb}/Retry {kb}）、
 *       iconForKind(kind) 映射（upload→Upload/reindex→RefreshCw/create 与默认→Wand2）、
 *       完成时间 toLocaleString、localStorage 语义 key knowledge:history:v1（读写经并行 hook，本组件只读展示）。
 */
import { useState } from "react";
import {
  CheckCircleOutlined,
  DeleteOutlined,
  DownOutlined,
  ExclamationCircleOutlined,
  HistoryOutlined,
  RightOutlined,
  SyncOutlined,
  ThunderboltOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import { Button, Typography } from "antd";
import type { HistoryEntry } from "./useKnowledgeHistory";

const BORDER = "#f0f0f0";
const MUTED = "#8c8c8c";
const MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";

interface KbUpdateHistoryProps {
  entries: HistoryEntry[];
  onClear: () => void;
}

export default function KbUpdateHistory({
  entries,
  onClear,
}: KbUpdateHistoryProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  if (entries.length === 0) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            fontSize: 11.5,
            fontWeight: 500,
            textTransform: "uppercase",
            letterSpacing: "0.12em",
            color: MUTED,
          }}
        >
          <HistoryOutlined style={{ fontSize: 12 }} />
          <span>更新历史</span>
          <span
            style={{
              borderRadius: 999,
              background: "#f5f5f5",
              padding: "0 6px",
              fontSize: 10,
              letterSpacing: "normal",
            }}
          >
            {entries.length}
          </span>
        </div>
        <Button
          type="text"
          size="small"
          icon={<DeleteOutlined />}
          onClick={onClear}
          title="清空历史"
          aria-label="清空历史"
          style={{ width: 24, height: 24, color: MUTED }}
        />
      </div>

      <div
        style={{
          border: `1px solid ${BORDER}`,
          borderRadius: 8,
          overflow: "hidden",
        }}
      >
        {entries.map((entry, index) => {
          const expanded = expandedId === entry.id;
          const isError = entry.status === "error";
          const KindIcon = iconForKind(entry.kind);
          const durationMs = Math.max(0, entry.completedAt - entry.startedAt);

          return (
            <div
              key={entry.id}
              style={{
                borderTop: index > 0 ? `1px solid ${BORDER}` : undefined,
                fontSize: 12.5,
              }}
            >
              <div
                onClick={() => setExpandedId(expanded ? null : entry.id)}
                onMouseEnter={() => setHoveredId(entry.id)}
                onMouseLeave={() => setHoveredId(null)}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 10,
                  padding: "10px 12px",
                  cursor: "pointer",
                  textAlign: "left",
                  background:
                    hoveredId === entry.id ? "rgba(0,0,0,0.028)" : undefined,
                }}
              >
                <span
                  style={{
                    marginTop: 2,
                    flexShrink: 0,
                    color: MUTED,
                    lineHeight: 1,
                  }}
                >
                  {expanded ? (
                    <DownOutlined style={{ fontSize: 13 }} />
                  ) : (
                    <RightOutlined style={{ fontSize: 13 }} />
                  )}
                </span>

                <span
                  style={{
                    marginTop: 2,
                    flexShrink: 0,
                    display: "inline-flex",
                    borderRadius: 6,
                    padding: 4,
                    fontSize: 12,
                    lineHeight: 1,
                    background: isError ? "#fee2e2" : "#d1fae5",
                    color: isError ? "#b91c1c" : "#047857",
                  }}
                >
                  {isError ? (
                    <ExclamationCircleOutlined />
                  ) : (
                    <CheckCircleOutlined />
                  )}
                </span>

                <span
                  style={{
                    minWidth: 0,
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                  }}
                >
                  <span
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 6,
                      fontSize: 12.5,
                      fontWeight: 500,
                    }}
                  >
                    <KindIcon style={{ fontSize: 12, color: MUTED }} />
                    {entry.label}
                  </span>
                  <span style={{ marginTop: 2, fontSize: 11, color: MUTED }}>
                    {new Date(entry.completedAt).toLocaleString()}
                    {durationMs > 0 && ` · ${formatDuration(durationMs)}`}
                  </span>
                </span>
              </div>

              {expanded && (
                <div
                  style={{
                    borderTop: `1px solid ${BORDER}`,
                    background: "rgba(245,245,245,0.3)",
                    padding: "8px 12px",
                  }}
                >
                  {entry.error && (
                    <pre
                      style={{
                        margin: "0 0 8px",
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                        border: "1px solid #fecaca",
                        background: "#fef2f2",
                        color: "#b91c1c",
                        borderRadius: 6,
                        padding: "6px 8px",
                        fontFamily: MONO,
                        fontSize: 11,
                        lineHeight: 1.6,
                      }}
                    >
                      {entry.error}
                    </pre>
                  )}
                  {entry.logTail.length > 0 ? (
                    <pre
                      style={{
                        maxHeight: 240,
                        overflow: "auto",
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                        margin: 0,
                        border: `1px solid ${BORDER}`,
                        background: "#ffffff",
                        color: MUTED,
                        borderRadius: 6,
                        padding: "6px 8px",
                        fontFamily: MONO,
                        fontSize: 10.5,
                        lineHeight: 1.6,
                      }}
                    >
                      {entry.logTail.join("\n")}
                    </pre>
                  ) : (
                    !entry.error && (
                      <Typography.Text
                        type="secondary"
                        style={{ fontSize: 11 }}
                      >
                        没有日志记录。
                      </Typography.Text>
                    )
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function iconForKind(kind: HistoryEntry["kind"]) {
  switch (kind) {
    case "upload":
      return UploadOutlined;
    case "reindex":
      return SyncOutlined;
    case "create":
    default:
      return ThunderboltOutlined;
  }
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  const minutes = Math.floor(ms / 60_000);
  const seconds = Math.round((ms % 60_000) / 1000);
  return `${minutes}m ${seconds}s`;
}
