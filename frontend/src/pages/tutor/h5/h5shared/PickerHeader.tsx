/**
 * 桌面同名件 1:1（复刻自 DeepTutor 原仓 web/components/common/PickerHeader.tsx，64 行）。
 * 后续批可迁位。替换点：lucide X→CloseOutlined、LucideIcon→antd 图标组件类型
 * （h/w/strokeWidth→style.fontSize）；Tailwind→内联样式（token 见 dtStyle.ts）；
 * t("Close")→zh/app.json 原译文「关闭」（i18next 回退兜底原 key）。
 */
import { CloseOutlined } from "@ant-design/icons";
import type { ComponentType, CSSProperties, ReactNode } from "react";
import { DT } from "./dtStyle";

/**
 * Shared header for the fullscreen context pickers (History, Books, Memory,
 * My Agents, Persona, Question Bank). Every picker used to hand-roll the same
 * three-line header: an all-caps, wide-tracked "eyebrow" kind label, a title,
 * and a subtitle.
 *
 * That eyebrow is a Latin-typography idiom — `uppercase` + `tracking-[0.14em]`
 * reads as refined on English, but on CJK it just spreads the glyphs apart and
 * looks loose/unkempt (uppercase is a no-op for Han characters). So this
 * component drops the eyebrow entirely and conveys the "kind" through a tinted
 * icon chip instead: cleaner, script-agnostic, and consistent across pickers.
 */
export default function PickerHeader({
  icon: Icon,
  titleId,
  title,
  subtitle,
  onClose,
  trailing,
}: {
  icon: ComponentType<{ className?: string; style?: CSSProperties }>;
  /** id wired to the dialog's `aria-labelledby`. */
  titleId: string;
  /** Already-translated title string. */
  title: string;
  /** Already-translated subtitle string. */
  subtitle: string;
  onClose: () => void;
  /** Optional control rendered between the title block and the close button. */
  trailing?: ReactNode;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 14,
        borderBottom: `1px solid ${DT.border}`,
        padding: "16px 20px",
      }}
    >
      <div
        style={{
          marginTop: 2,
          display: "flex",
          height: 36,
          width: 36,
          flexShrink: 0,
          alignItems: "center",
          justifyContent: "center",
          borderRadius: 12,
          background: DT.primaryAlpha(0.1),
          color: DT.primary,
        }}
      >
        <Icon style={{ fontSize: 18 }} />
      </div>
      <div style={{ minWidth: 0, flex: 1 }}>
        <h2
          id={titleId}
          style={{
            margin: 0,
            fontSize: 15,
            fontWeight: 600,
            lineHeight: 1.25,
            color: DT.foreground,
          }}
        >
          {title}
        </h2>
        <p
          style={{
            margin: "4px 0 0",
            fontSize: 13,
            lineHeight: 1.375,
            color: DT.mutedForeground,
          }}
        >
          {subtitle}
        </p>
      </div>
      {trailing}
      <button
        onClick={onClose}
        aria-label={"关闭"}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = DT.muted;
          e.currentTarget.style.color = DT.foreground;
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "transparent";
          e.currentTarget.style.color = DT.mutedForeground;
        }}
        style={{
          marginRight: -4,
          marginTop: -4,
          flexShrink: 0,
          borderRadius: 8,
          padding: 8,
          border: "none",
          cursor: "pointer",
          background: "transparent",
          color: DT.mutedForeground,
          lineHeight: 0,
          transition: "background-color 150ms, color 150ms",
        }}
      >
        <CloseOutlined style={{ fontSize: 18 }} />
      </button>
    </div>
  );
}
