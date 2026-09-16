/**
 * 复刻自 DeepTutor：web/app/(workspace)/book/components/blocks/CalloutBlock.tsx（平铺到 tupu）。
 * 替换点：删除 "use client"；@/lib/book-types → './book-types'；
 * lucide-react → @ant-design/icons（Lightbulb→BulbOutlined、AlertTriangle→WarningOutlined、
 * BookmarkCheck→FileDoneOutlined、Sparkles→ThunderboltOutlined）；
 * Tailwind 变体样式 → 内联样式（仅取亮色主题值，dark: 前缀丢弃；
 * border-l-[3px]→borderLeft，amber/rose/sky/emerald 按 Tailwind 色值）。
 */
import type { ComponentType, CSSProperties } from "react";
import {
  BulbOutlined,
  WarningOutlined,
  FileDoneOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import type { Block } from './book-types';

type IconComponent = ComponentType<{ style?: CSSProperties }>;

const VARIANT_STYLES: Record<
  string,
  { icon: IconComponent; rule: string; tintBg: string; tintText: string; accent: string }
> = {
  key_idea: {
    icon: BulbOutlined,
    rule: "rgba(251,191,36,0.7)",
    tintBg: "rgba(255,251,235,0.6)",
    tintText: "#451a03",
    accent: "#b45309",
  },
  common_pitfall: {
    icon: WarningOutlined,
    rule: "rgba(251,113,133,0.7)",
    tintBg: "rgba(255,241,242,0.6)",
    tintText: "#881337",
    accent: "#be123c",
  },
  summary: {
    icon: FileDoneOutlined,
    rule: "rgba(56,189,248,0.7)",
    tintBg: "rgba(240,249,255,0.6)",
    tintText: "#082f49",
    accent: "#0369a1",
  },
  tip: {
    icon: ThunderboltOutlined,
    rule: "rgba(52,211,153,0.7)",
    tintBg: "rgba(236,253,245,0.6)",
    tintText: "#022c22",
    accent: "#047857",
  },
};

export interface CalloutBlockProps {
  block: Block;
}

export default function CalloutBlock({ block }: CalloutBlockProps) {
  const variant = String(block.payload?.variant || "key_idea");
  const label = String(block.payload?.label || variant.replace(/_/g, " "));
  const body = String(block.payload?.body || "");
  const style = VARIANT_STYLES[variant] || VARIANT_STYLES.key_idea;
  const Icon = style.icon;
  return (
    <aside
      style={{
        position: "relative",
        display: "flex",
        gap: 12,
        borderLeft: `3px solid ${style.rule}`,
        background: style.tintBg,
        color: style.tintText,
        padding: "8px 12px 8px 16px",
      }}
    >
      <Icon
        style={{
          fontSize: 16,
          marginTop: 3,
          flexShrink: 0,
          color: style.accent,
        }}
      />
      <div style={{ minWidth: 0, display: "flex", flexDirection: "column", gap: 4 }}>
        <div
          style={{
            fontSize: 11,
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.16em",
            color: style.accent,
          }}
        >
          {label}
        </div>
        <div style={{ fontSize: 14.5, lineHeight: 1.625 }}>{body}</div>
      </div>
    </aside>
  );
}
