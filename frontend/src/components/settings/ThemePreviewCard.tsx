/**
 * 复刻自 DeepTutor 原仓 web/components/settings/ThemePreviewCard.tsx（整件 1:1，批5 5.2）。
 * 替换点：
 * - 去 "use client"；本件无 i18n 文案；
 * - Tailwind 类（group relative flex … rounded-xl border …）逐项换为内联样式，
 *   颜色用原仓语义 var(--xxx, 兜底值) 承载（与同批 Toggle.tsx 口径一致）；
 *   原生 <button type="button"> 保留（antd Button 不承载 aria-pressed/data-active
 *   卡片语义，样式全部内联等价实现）；
 * - 仅一处视觉裁剪：源件的 hover 提亮（hover:border / group-hover 文案变色）依赖
 *   Tailwind 伪类，内联样式无法承载，未做 JS 态模拟——静止态视觉与源一致。
 * lucide-react→antd 图标登记：Check → CheckOutlined（选中角标，fontSize 10）。
 */
import React from "react";
import { CheckOutlined } from "@ant-design/icons";

import type { UiSettings } from "./SettingsContext";

type Theme = UiSettings["theme"];

// Explicit palette values lifted from app/globals.css — kept here as plain
// hex/rgba so each preview tile can render its theme's colours even while
// the actual document theme is something else. Keep in sync with globals.css
// when colours change there.
type Palette = {
  bg: string;
  fg: string;
  card: string;
  primary: string;
  muted: string;
  border: string;
  // True for translucent themes — adds a soft gradient/backdrop to convey
  // the "frosted glass" treatment visually.
  glass?: boolean;
};

const PALETTES: Record<Theme, Palette> = {
  // theme id "light" applies no class → :root Cream palette (warm parchment,
  // the default; renamed from generic "Light" to honestly signal its warmth)
  light: {
    bg: "#fdfcf9",
    fg: "#1c1816",
    card: "#ffffff",
    primary: "#b0501e",
    muted: "#f1ede2",
    border: "#e6decc",
  },
  // theme id "snow" applies the .theme-snow class → "Default": pure-white
  // neutral palette, grey surfaces, blue primary (Codex-style chrome)
  snow: {
    bg: "#ffffff",
    fg: "#0d0d0d",
    card: "#ffffff",
    primary: "#2563eb",
    muted: "#f2f2f2",
    border: "#e5e5e5",
  },
  dark: {
    bg: "#1a1918",
    fg: "#e8e4de",
    card: "#242220",
    primary: "#d4734b",
    muted: "#2a2725",
    border: "#3a3634",
  },
  glass: {
    bg: "#0e0d1a",
    fg: "#ffffff",
    card: "rgba(255,255,255,0.06)",
    primary: "#a855f7",
    muted: "rgba(255,255,255,0.06)",
    border: "rgba(255,255,255,0.12)",
    glass: true,
  },
};

// Renders a miniature DeepTutor UI mockup in the given theme's palette —
// a left sidebar with one highlighted nav row, a content area with two
// text lines and an accent button. Pure SVG so it stays crisp at any
// device pixel ratio without leaking real interactive controls.
function MiniPreview({ palette }: { palette: Palette }) {
  const { bg, fg, card, primary, muted, border, glass } = palette;
  return (
    <svg
      viewBox="0 0 160 96"
      style={{ display: "block", height: "100%", width: "100%" }}
      aria-hidden
    >
      {/* Outer frame */}
      <rect x="0" y="0" width="160" height="96" rx="6" fill={bg} />
      {glass && (
        <>
          <defs>
            <radialGradient id="glass-shine" cx="20%" cy="0%" r="80%">
              <stop offset="0%" stopColor="rgba(168,85,247,0.38)" />
              <stop offset="100%" stopColor="rgba(168,85,247,0)" />
            </radialGradient>
          </defs>
          <rect
            x="0"
            y="0"
            width="160"
            height="96"
            rx="6"
            fill="url(#glass-shine)"
          />
        </>
      )}

      {/* Sidebar */}
      <rect x="0" y="0" width="44" height="96" fill={muted} />
      {/* Sidebar nav rows */}
      <rect
        x="8"
        y="14"
        width="28"
        height="3"
        rx="1.5"
        fill={fg}
        opacity="0.45"
      />
      <rect x="6" y="26" width="32" height="10" rx="3" fill={card} />
      <rect
        x="10"
        y="30"
        width="20"
        height="2.5"
        rx="1.25"
        fill={fg}
        opacity="0.9"
      />
      <circle cx="40" cy="31" r="1.5" fill={primary} />
      <rect
        x="8"
        y="44"
        width="24"
        height="2.5"
        rx="1.25"
        fill={fg}
        opacity="0.45"
      />
      <rect
        x="8"
        y="54"
        width="26"
        height="2.5"
        rx="1.25"
        fill={fg}
        opacity="0.45"
      />
      <rect
        x="8"
        y="64"
        width="22"
        height="2.5"
        rx="1.25"
        fill={fg}
        opacity="0.45"
      />

      {/* Sidebar divider */}
      <line x1="44" y1="0" x2="44" y2="96" stroke={border} strokeWidth="0.5" />

      {/* Content card */}
      <rect
        x="54"
        y="14"
        width="96"
        height="68"
        rx="4"
        fill={card}
        stroke={border}
        strokeWidth="0.5"
      />
      {/* Title line */}
      <rect
        x="62"
        y="22"
        width="40"
        height="3.5"
        rx="1.5"
        fill={fg}
        opacity="0.85"
      />
      {/* Body lines */}
      <rect
        x="62"
        y="34"
        width="78"
        height="2.5"
        rx="1.25"
        fill={fg}
        opacity="0.35"
      />
      <rect
        x="62"
        y="42"
        width="64"
        height="2.5"
        rx="1.25"
        fill={fg}
        opacity="0.35"
      />
      <rect
        x="62"
        y="50"
        width="72"
        height="2.5"
        rx="1.25"
        fill={fg}
        opacity="0.35"
      />
      {/* Accent button */}
      <rect x="62" y="64" width="22" height="9" rx="2.5" fill={primary} />
    </svg>
  );
}

export function ThemePreviewCard({
  theme,
  label,
  selected,
  onSelect,
}: {
  theme: Theme;
  label: string;
  selected: boolean;
  onSelect: (theme: Theme) => void;
}) {
  const palette = PALETTES[theme];
  return (
    <button
      type="button"
      onClick={() => onSelect(theme)}
      aria-pressed={selected}
      data-testid={`appearance-theme-${theme}`}
      data-active={selected || undefined}
      style={{
        position: "relative",
        display: "flex",
        flexDirection: "column",
        alignItems: "stretch",
        gap: 8,
        borderRadius: 12,
        border: selected
          ? "1px solid var(--foreground, #0f172a)"
          : "1px solid var(--border, #e5e7eb)",
        background: selected
          ? "var(--card, #ffffff)"
          : "transparent",
        boxShadow: selected ? "0 1px 2px 0 rgba(0, 0, 0, 0.05)" : "none",
        padding: 6,
        textAlign: "left",
        cursor: "pointer",
        transition: "all 150ms",
        outline: "none",
      }}
    >
      <div
        style={{
          position: "relative",
          overflow: "hidden",
          borderRadius: 8,
          aspectRatio: "5 / 3",
          boxShadow: `0 0 0 1px var(--border, #e5e7eb), inset 0 0 0 1px ${palette.border}`,
        }}
      >
        <MiniPreview palette={palette} />
        {selected && (
          <div
            style={{
              position: "absolute",
              right: 6,
              top: 6,
              display: "flex",
              height: 16,
              width: 16,
              alignItems: "center",
              justifyContent: "center",
              borderRadius: 9999,
              background: "var(--foreground, #0f172a)",
              color: "var(--background, #ffffff)",
            }}
          >
            <CheckOutlined style={{ fontSize: 10, fontWeight: 700 }} />
          </div>
        )}
      </div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 4px 2px",
        }}
      >
        <span
          style={{
            fontSize: 12.5,
            letterSpacing: "-0.01em",
            fontWeight: selected ? 500 : 400,
            color: selected
              ? "var(--foreground, #0f172a)"
              : "var(--muted-foreground, #64748b)",
          }}
        >
          {label}
        </span>
        <div style={{ display: "flex" }}>
          {[palette.primary, palette.fg, palette.muted].map((c, i) => (
            <span
              key={i}
              style={{
                height: 10,
                width: 10,
                borderRadius: 9999,
                background: c,
                boxShadow: "0 0 0 1px var(--background, #ffffff)",
                marginLeft: i === 0 ? 0 : -4,
              }}
            />
          ))}
        </div>
      </div>
    </button>
  );
}
