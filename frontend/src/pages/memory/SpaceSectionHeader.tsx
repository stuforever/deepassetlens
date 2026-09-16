/**
 * 桌面同名件 1:1（复制自 DeepTutor 原仓 web/components/space/SpaceSectionHeader.tsx，47 行）。
 * 随 MemorySection 随行移植（组内私有落位，仅 MemorySection 消费）。
 * 替换点：删除 "use client"；lucide LucideIcon 类型 → 本组 IconType
 * （antd 图标组件均接受 className/style）；size/strokeWidth → fontSize 内联；
 * Tailwind → 内联样式。
 * 交互逐字未改。
 */
import type { CSSProperties, ComponentType, ReactNode } from "react";

/** antd 图标组件通用类型（等价 lucide LucideIcon 在本组的用法）。 */
export type IconType = ComponentType<{
  className?: string;
  style?: CSSProperties;
}>;

interface SpaceSectionHeaderProps {
  icon: IconType;
  title: string;
  description: string;
  action?: ReactNode;
  meta?: ReactNode;
}

const FG = "var(--foreground, rgba(0, 0, 0, 0.88))";
const MUTED_FG = "var(--muted-foreground, rgba(0, 0, 0, 0.45))";
const BORDER = "var(--border, #d9d9d9)";
const CARD = "var(--card, #ffffff)";

export function SpaceSectionHeader({
  icon: Icon,
  title,
  description,
  action,
  meta,
}: SpaceSectionHeaderProps) {
  return (
    <header
      style={{
        marginBottom: 24,
        display: "flex",
        flexDirection: "column",
        gap: 16,
        borderBottom: `1px solid color-mix(in srgb, ${BORDER} 60%, transparent)`,
        paddingBottom: 20,
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
        <span
          aria-hidden
          style={{
            marginTop: 2,
            display: "flex",
            height: 36,
            width: 36,
            flexShrink: 0,
            alignItems: "center",
            justifyContent: "center",
            borderRadius: 12,
            border: `1px solid color-mix(in srgb, ${BORDER} 60%, transparent)`,
            background: CARD,
            color: FG,
            boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
          }}
        >
          <Icon style={{ fontSize: 16 }} />
        </span>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 8 }}>
            <h1
              style={{
                fontSize: 19,
                fontWeight: 600,
                lineHeight: 1.25,
                letterSpacing: "-0.01em",
                color: FG,
                margin: 0,
                fontFamily: "Georgia, 'Times New Roman', serif",
              }}
            >
              {title}
            </h1>
            {meta}
          </div>
          <p
            style={{
              marginTop: 4,
              maxWidth: 576,
              fontSize: 13,
              lineHeight: 1.625,
              color: MUTED_FG,
              marginBottom: 0,
            }}
          >
            {description}
          </p>
        </div>
      </div>
      {action && (
        <div style={{ flexShrink: 0, alignSelf: "flex-start" }}>{action}</div>
      )}
    </header>
  );
}

export default SpaceSectionHeader;
