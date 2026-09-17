/**
 * KbIndexVersionsSection —— 知识库「索引版本」区（全部向量索引版本及激活/失效/旧版状态、
 * 重建索引/重试入口与实时进度日志）。
 * 1:1 复刻自原仓 DeepTutor web/components/knowledge/KbIndexVersionsSection.tsx（314 行）。
 * 复刻来源：Next.js + Tailwind + react-i18next + lucide-react + "@/lib/knowledge-helpers"
 *           + "@/hooks/useKnowledgeProgress" + "@/components/common/ProcessLogs"
 * 替换点：
 *  - "use client" 删除；
 *  - react-i18next（useTranslation/t(key)）→ 中文直出（译文取自原仓 web/locales/zh/app.json）；
 *  - lucide-react → @ant-design/icons 语义就近：Layers→AppstoreOutlined、RefreshCw→SyncOutlined、
 *    Loader2→LoadingOutlined、AlertTriangle→WarningOutlined、Clock→ClockCircleOutlined、
 *    Star(fill)→StarFilled、CheckCircle2→CheckCircleOutlined；
 *  - Tailwind → antd 组件 + 最小内联样式（版本 4 态配色：Active emerald #d1fae5/#059669/#047857、
 *    Stale/phantom amber #fef3c7/#d97706/#b45309 + 标题删除线、Legacy/Inactive muted #f5f5f5/#8c8c8c、
 *    reindex 按钮 error 红 / 常规 amber 双态、分隔线 #f0f0f0）；
 *  - import 契约（并行 Agent 同步产出，按名 import）：helpers（formatKnowledgeTimestamp/kbCanReindex/
 *    kbNeedsReindex/resolveKbStatus/resolveProgressPercent/IndexVersion/KnowledgeBase）
 *    →'./knowledge-helpers'、TaskState→'./useKnowledgeProgress'、ProcessLogs→'./ProcessLogs'。
 *  - 注：源文件并未引用 IndexVersionChip（版本行 4 态徽标由本文件内 IndexVersionRow 实现，
 *    与对拍基准字段清单 §7/§15「IndexVersionChip 无父组件挂载」一致），故本复刻不引入该引用。
 * 不变：props 契约（kb/task?/onReindex）、4 态判定（matchesActive/isActive/isPhantom/isLegacy）、
 *       标题兜底链（legacy→旧版索引；model；signature→未知）、标题删除线仅 phantom、
 *       行 key（signature ?? model-dimension-created_at）、showReindexCta=kbCanReindex、
 *       警示条三分支（isError 红 / needsReindex|mismatch amber）、
 *       最近索引条（暂无记录 + 索引了 N 个文档）、任务日志（reindex/retry 且有 taskId/日志/执行中）、
 *       handleReindex 时序（finally 复位）、进度条 min 4%、task.error 红 pre。
 */
import { useState } from "react";
import type { ReactNode } from "react";
import { Button, Flex, Progress } from "antd";
import {
  AppstoreOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
  StarFilled,
  SyncOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import {
  formatKnowledgeTimestamp,
  kbCanReindex,
  kbNeedsReindex,
  resolveKbStatus,
  resolveProgressPercent,
  type IndexVersion,
  type KnowledgeBase,
} from "./knowledge-helpers";
import type { TaskState } from "./useKnowledgeProgress";
import ProcessLogs from "./ProcessLogs";

const BORDER = "#f0f0f0";
const MUTED = "#8c8c8c";
const MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";

interface KbIndexVersionsSectionProps {
  kb: KnowledgeBase;
  task?: TaskState;
  onReindex: () => Promise<void>;
}

export default function KbIndexVersionsSection({
  kb,
  task,
  onReindex,
}: KbIndexVersionsSectionProps) {
  const [submitting, setSubmitting] = useState(false);
  const versions = kb.statistics?.index_versions ?? [];
  const activeSig = kb.statistics?.active_signature ?? null;
  const needsReindex = kbNeedsReindex(kb);
  const isError = resolveKbStatus(kb) === "error";
  const mismatch = Boolean(kb.metadata?.embedding_mismatch);
  const isReindexingHere =
    (task?.kind === "reindex" || task?.kind === "retry") && task.executing;
  const percent = resolveProgressPercent(kb.progress);
  const lastIndexed = formatKnowledgeTimestamp(kb.metadata?.last_indexed_at);
  const lastIndexedCount = kb.metadata?.last_indexed_count;

  const handleReindex = async () => {
    setSubmitting(true);
    try {
      await onReindex();
    } finally {
      setSubmitting(false);
    }
  };

  const showReindexCta = kbCanReindex(kb);

  return (
    <Flex vertical gap={16}>
      <Flex align="flex-start" justify="space-between" gap={12}>
        <Flex align="center" gap={8}>
          <AppstoreOutlined style={{ fontSize: 14, color: MUTED }} />
          <div>
            <div style={{ fontSize: 12.5, fontWeight: 500 }}>
              索引版本
              <span
                style={{
                  marginLeft: 8,
                  borderRadius: 999,
                  background: "#f5f5f5",
                  padding: "2px 6px",
                  fontSize: 10,
                  fontWeight: 400,
                  color: MUTED,
                }}
              >
                {versions.length}
              </span>
            </div>
            <div style={{ fontSize: 11, color: MUTED }}>
              每个 embedding 配置都对应一个独立存储的向量索引。
            </div>
          </div>
        </Flex>

        {showReindexCta && (
          <Button
            onClick={handleReindex}
            disabled={submitting || isReindexingHere}
            title={
              isError
                ? "使用此知识库中已经保存的文档重试索引。"
                : "点击“重建索引”，使用当前激活的 embedding 模型重建此知识库。已有索引版本会保留。"
            }
            icon={
              submitting || isReindexingHere ? (
                <LoadingOutlined spin />
              ) : (
                <SyncOutlined />
              )
            }
            style={{
              flexShrink: 0,
              fontSize: 12,
              fontWeight: 500,
              ...(isError
                ? {
                    border: "1px solid #fecaca",
                    background: "#fef2f2",
                    color: "#b91c1c",
                  }
                : {
                    border: "1px solid #fcd34d",
                    background: "#fffbeb",
                    color: "#b45309",
                  }),
            }}
          >
            {isReindexingHere
              ? isError
                ? "正在重试…"
                : "正在重建索引…"
              : isError
                ? "重试索引"
                : "重建索引"}
          </Button>
        )}
      </Flex>

      {(isError || needsReindex || mismatch) && (
        <Flex
          align="flex-start"
          gap={8}
          style={{
            borderRadius: 8,
            border: `1px solid ${isError ? "#fecaca" : "#fde68a"}`,
            background: isError
              ? "rgba(254,242,242,0.8)"
              : "rgba(255,251,235,0.8)",
            padding: "8px 12px",
            fontSize: 12,
            color: isError ? "#b91c1c" : "#b45309",
          }}
        >
          <WarningOutlined
            style={{ fontSize: 14, marginTop: 2, flexShrink: 0 }}
          />
          <span>
            {isError
              ? "上一次索引失败。重试会使用现有源文档重新构建索引。"
              : "当前激活的 embedding 配置没有匹配到任何可用的索引版本。请使用当前模型重新索引。"}
          </span>
        </Flex>
      )}

      <Flex
        wrap="wrap"
        align="center"
        style={{
          borderRadius: 8,
          border: `1px solid ${BORDER}`,
          background: "rgba(245,245,245,0.3)",
          padding: "8px 12px",
          fontSize: 11.5,
          color: MUTED,
          columnGap: 8,
          rowGap: 4,
        }}
      >
        <ClockCircleOutlined style={{ fontSize: 14, flexShrink: 0 }} />
        <span>
          最近索引:{" "}
          <span style={{ fontWeight: 500, color: "#1f1f1f" }}>
            {lastIndexed || "暂无记录"}
          </span>
        </span>
        {typeof lastIndexedCount === "number" && (
          <span>· {`索引了 ${lastIndexedCount} 个文档`}</span>
        )}
      </Flex>

      {versions.length > 0 ? (
        <div
          style={{
            border: `1px solid ${BORDER}`,
            borderRadius: 8,
            background: "#ffffff",
            overflow: "hidden",
          }}
        >
          {versions.map((version, index) => (
            <IndexVersionRow
              key={
                version.signature ??
                `${version.model}-${version.dimension}-${version.created_at}`
              }
              version={version}
              activeSignature={activeSig}
              topDivider={index > 0}
            />
          ))}
        </div>
      ) : (
        <div
          style={{
            border: `1px dashed ${BORDER}`,
            borderRadius: 8,
            padding: "24px 16px",
            textAlign: "center",
            fontSize: 12,
            color: MUTED,
          }}
        >
          暂无索引版本。
        </div>
      )}

      {(task?.kind === "reindex" || task?.kind === "retry") &&
        (task.taskId || task.logs.length > 0 || task.executing) && (
          <Flex vertical gap={8}>
            <Flex
              align="center"
              justify="space-between"
              style={{ fontSize: 11, color: MUTED }}
            >
              <span>
                {task.label}
                {task.taskId ? ` · ${task.taskId}` : ""}
              </span>
              {task.executing && percent > 0 && (
                <span style={{ fontWeight: 500, color: "#1f1f1f" }}>
                  {percent}%
                </span>
              )}
            </Flex>
            <ProcessLogs
              logs={task.logs}
              executing={task.executing}
              title="重建索引进度"
            />
            {task.executing && (
              <Progress
                percent={Math.max(percent, 4)}
                showInfo={false}
                strokeWidth={6}
              />
            )}
            {task.error && (
              <div
                style={{
                  borderRadius: 8,
                  border: "1px solid #fecaca",
                  background: "#fef2f2",
                  padding: "8px 12px",
                  fontSize: 12,
                  color: "#b91c1c",
                }}
              >
                <pre
                  style={{
                    margin: 0,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    fontFamily: MONO,
                    fontSize: 11,
                    lineHeight: 1.6,
                  }}
                >
                  {task.error}
                </pre>
              </div>
            )}
          </Flex>
        )}
    </Flex>
  );
}

function IndexVersionRow({
  version,
  activeSignature,
  topDivider,
}: {
  version: IndexVersion;
  activeSignature: string | null;
  topDivider?: boolean;
}) {
  const matchesActive =
    !!version.signature && version.signature === activeSignature;
  const isActive = matchesActive && version.ready === true;
  const isPhantom = matchesActive && version.ready !== true;
  const isLegacy = !!version.legacy;

  const title = isLegacy
    ? "旧版索引"
    : version.model
      ? version.model
      : (version.signature ?? "未知");

  const created = formatKnowledgeTimestamp(version.created_at);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "10px 12px",
        borderTop: topDivider ? `1px solid ${BORDER}` : undefined,
      }}
    >
      <div
        title={
          isActive
            ? "当前激活版本"
            : isPhantom
              ? "已失效（匹配当前配置但存储为空）"
              : isLegacy
                ? "旧版索引格式"
                : "未激活版本"
        }
        style={{
          width: 28,
          height: 28,
          flexShrink: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: 6,
          fontSize: 14,
          background: isActive
            ? "#d1fae5"
            : isPhantom
              ? "#fef3c7"
              : "#f5f5f5",
          color: isActive
            ? "#059669"
            : isPhantom
              ? "#d97706"
              : MUTED,
        }}
      >
        {isActive ? (
          <StarFilled />
        ) : isPhantom ? (
          <WarningOutlined />
        ) : isLegacy ? (
          <ClockCircleOutlined />
        ) : (
          <CheckCircleOutlined />
        )}
      </div>

      <div style={{ minWidth: 0, flex: 1 }}>
        <Flex align="center" gap={8}>
          <span
            style={{
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              fontSize: 12.5,
              fontWeight: 500,
              color: isPhantom ? "#b45309" : "#1f1f1f",
              textDecoration: isPhantom ? "line-through" : undefined,
              textDecorationColor: isPhantom
                ? "rgba(251,191,36,0.7)"
                : undefined,
            }}
          >
            {title}
          </span>
          {isActive && (
            <IndexPill background="#d1fae5" color="#047857">
              已激活
            </IndexPill>
          )}
          {isPhantom && (
            <IndexPill background="#fef3c7" color="#b45309">
              已失效
            </IndexPill>
          )}
          {isLegacy && !isActive && (
            <IndexPill background="#f5f5f5" color={MUTED}>
              旧版
            </IndexPill>
          )}
        </Flex>
        <div
          style={{
            marginTop: 2,
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            columnGap: 8,
            rowGap: 2,
            fontSize: 10.5,
            color: MUTED,
          }}
        >
          {typeof version.dimension === "number" && (
            <span>{version.dimension}维</span>
          )}
          {version.binding && <span>{version.binding}</span>}
          {created && <span>{created}</span>}
          {version.signature && (
            <span style={{ fontFamily: MONO }}>
              {version.signature.slice(0, 10)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function IndexPill({
  children,
  background,
  color,
}: {
  children: ReactNode;
  background: string;
  color: string;
}) {
  return (
    <span
      style={{
        borderRadius: 999,
        background,
        padding: "1px 6px",
        fontSize: 10,
        fontWeight: 500,
        color,
        lineHeight: "16px",
        flexShrink: 0,
      }}
    >
      {children}
    </span>
  );
}
