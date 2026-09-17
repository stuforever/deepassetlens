/**
 * 索引版本小徽章 —— 复刻 DeepTutor web/components/knowledge/IndexVersionChip.tsx（antd 重建，1:1）。
 *
 * 三态（与源一致）：激活（signature===activeSignature 且 ready===true）→ success 绿；
 * 失效 phantom（匹配但 ready!==true）→ warning 橙 + 删除线；其他 → 默认描边 + 次要文字。
 * label：legacy→旧版；有 model→{model}{ · {dimension}维}；否则 signature 或 未知。
 * title：phantom → 上次重建索引可能失败提示；否则有 created_at → 创建时间。激活时加 ★ 前缀。
 * 文案对照 dt_baseline/fieldlists/knowledge.md §15 与 web/locales/zh/app.json。
 */
import type { CSSProperties } from "react";
import { Tag } from "antd";
import type { IndexVersion } from "./knowledge-helpers";
import { tokens } from "../../theme/tokens";

interface IndexVersionChipProps {
  version: IndexVersion;
  activeSignature?: string | null;
}

const CHIP: CSSProperties = {
  fontSize: 11,
  lineHeight: "16px",
  paddingBlock: 2,
  paddingInline: 8,
  borderRadius: tokens.radius.pill,
  marginInlineEnd: 0,
};

export default function IndexVersionChip({
  version,
  activeSignature,
}: IndexVersionChipProps) {
  const matchesActive =
    !!version.signature && version.signature === activeSignature;
  const isActive = matchesActive && version.ready === true;
  const isPhantomActive = matchesActive && version.ready !== true;

  const dimensionLabel =
    typeof version.dimension === "number"
      ? ` · ${version.dimension}维`
      : "";
  const label = version.legacy
    ? "旧版"
    : version.model
      ? `${version.model}${dimensionLabel}`
      : (version.signature ?? "未知");

  const style: CSSProperties = isActive
    ? CHIP
    : isPhantomActive
      ? { ...CHIP, textDecoration: "line-through" }
      : {
          ...CHIP,
          background: "transparent",
          color: tokens.colors.textSecondary,
          borderColor: tokens.colors.border,
        };

  const title = isPhantomActive
    ? "当前激活 embedding 的索引版本存在但为空——上次重建索引可能失败了。"
    : version.created_at
      ? `创建时间: ${version.created_at}`
      : undefined;

  return (
    <Tag
      color={isActive ? "success" : isPhantomActive ? "warning" : undefined}
      style={style}
      title={title}
    >
      {isActive ? "★ " : ""}
      {label}
    </Tag>
  );
}
