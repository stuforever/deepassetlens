/**
 * 复刻自 DeepTutor 原仓 web/components/partners/PartnerAvatar.tsx（整件 1:1，批6 6.3）。
 * 替换点：去 "use client"；Tailwind 类逐项换为内联样式（颜色 var(--x, 兜底)）。
 * className prop 保留（源签名逐字一致）；本仓无 tailwind，外部传入的工具类
 * （如 FaceEditor 的 shadow-sm）不生效，见 FaceEditor 登记说明。
 * 无 lucide 图标。
 *
 * Round partner avatar. Precedence: uploaded image (data URL) → emoji on a
 * colored disc → name initial on a colored disc. Emoji and background color
 * compose (iOS-contacts style) instead of being mutually exclusive.
 */

export const PARTNER_COLORS = [
  "#b0501e", // ember (primary-adjacent)
  "#8c6a2f", // ochre
  "#4f7a5b", // moss
  "#3d6b8a", // lake
  "#6d5a8c", // plum
  "#8a4f5f", // rose
  "#a8763e", // amber
  "#5b8a8a", // teal
] as const;

export default function PartnerAvatar({
  name,
  emoji,
  color,
  image,
  size = 40,
  className = "",
}: {
  name: string;
  emoji?: string;
  color?: string;
  /** Custom avatar as a data URL — wins over emoji/color when set. */
  image?: string;
  size?: number;
  className?: string;
}) {
  if (image) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={image}
        alt=""
        aria-hidden
        className={className}
        style={{
          flexShrink: 0,
          userSelect: "none",
          borderRadius: 9999,
          objectFit: "cover",
          width: size,
          height: size,
        }}
      />
    );
  }

  const initial = (name || "?").trim().charAt(0).toUpperCase();
  // Emoji discs default to a soft neutral so an un-colored emoji keeps the
  // familiar look; a chosen color becomes the disc behind the emoji.
  const background = color || (emoji ? "var(--muted, #f1f5f9)" : PARTNER_COLORS[0]);
  return (
    <span
      aria-hidden
      className={className}
      style={{
        display: "flex",
        flexShrink: 0,
        userSelect: "none",
        alignItems: "center",
        justifyContent: "center",
        borderRadius: 9999,
        color: "#ffffff",
        width: size,
        height: size,
        background,
        fontSize: emoji ? size * 0.55 : size * 0.42,
        fontWeight: 600,
      }}
    >
      {emoji || initial}
    </span>
  );
}
