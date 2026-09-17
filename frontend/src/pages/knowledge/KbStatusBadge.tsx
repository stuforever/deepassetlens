/**
 * 知识库状态徽标 —— 复刻 DeepTutor web/components/knowledge/KbStatusBadge.tsx（antd 重建，1:1）。
 *
 * 判定优先级（与源一致）：needsReindex > error > live（含本地重建中）> ready > 其他（状态原值下划线转空格）。
 * lucide → @ant-design/icons：AlertTriangle→WarningOutlined、CheckCircle2→CheckCircleOutlined、Clock3→ClockCircleOutlined。
 * 颜色语义（antd）：需要重新索引=warning 橙 / 错误=error 红 / 实时处理中=processing 蓝 / 就绪=success 绿；
 * 其他状态沿用源的 emerald 配色 → success 绿。
 * 文案对照 dt_baseline/fieldlists/knowledge.md §16 与 web/locales/zh/app.json。
 */
import type { CSSProperties } from "react";
import { Tag } from "antd";
import { CheckCircleOutlined, ClockCircleOutlined, WarningOutlined } from "@ant-design/icons";
import {
  kbHasLiveProgress,
  kbNeedsReindex,
  resolveKbStatus,
  type KnowledgeBase,
} from "./knowledge-helpers";

interface KbStatusBadgeProps {
  kb: KnowledgeBase;
  isReindexingLocally?: boolean;
}

const PILL: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 4,
  fontSize: 10,
  fontWeight: 500,
  lineHeight: "14px",
  paddingBlock: 2,
  paddingInline: 8,
  borderRadius: 999,
  marginInlineEnd: 0,
};

export default function KbStatusBadge({
  kb,
  isReindexingLocally = false,
}: KbStatusBadgeProps) {
  const status = resolveKbStatus(kb);
  const needsReindex = kbNeedsReindex(kb);
  const isLive = kbHasLiveProgress(kb) || isReindexingLocally;
  const isError = status === "error";
  const isReady = status === "ready" && !needsReindex;

  const Icon = isLive ? ClockCircleOutlined : isReady ? CheckCircleOutlined : WarningOutlined;

  const label = needsReindex
    ? "需要重新索引"
    : isError
      ? "错误"
      : isLive
        ? "实时处理中"
        : isReady
          ? "就绪"
          : status.replaceAll("_", " ");

  const color = needsReindex
    ? "warning"
    : isError
      ? "error"
      : isLive
        ? "processing"
        : "success";

  return (
    <Tag color={color} style={PILL}>
      <Icon style={{ fontSize: 12 }} />
      {label}
    </Tag>
  );
}
