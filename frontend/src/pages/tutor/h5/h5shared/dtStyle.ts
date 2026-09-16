/**
 * 批9 转换助手（非原仓件）：ChatComposer 全家桶 Tailwind→内联样式转换用的
 * 最小等价物（批8 BookChatPanel "focus-within 高亮与 hover 反馈用状态实现"
 * 同款思路，抽成公共常量避免各件重复）。
 * 颜色 token 映射沿用批8 约定：border→#e4e4e7、foreground→rgba(0,0,0,0.88)、
 * muted→#f4f4f5、muted-foreground→#6b7280、primary→#1677ff、card/popover→#fff、
 * red-500→#ef4444、red-600→#dc2626。
 */
import type { CSSProperties, MouseEvent } from "react";

export const DT = {
  border: "#e4e4e7",
  borderAlpha: (a: number) => `rgba(228,228,231,${a})`,
  foreground: "rgba(0,0,0,0.88)",
  background: "#ffffff",
  card: "#ffffff",
  popover: "#ffffff",
  muted: "#f4f4f5",
  mutedAlpha: (a: number) => `rgba(244,244,245,${a})`,
  mutedForeground: "#6b7280",
  mutedForegroundAlpha: (a: number) => `rgba(107,114,128,${a})`,
  primary: "#1677ff",
  primaryAlpha: (a: number) => `rgba(22,119,255,${a})`,
  primaryForeground: "#ffffff",
  red500: "#ef4444",
  red600: "#dc2626",
} as const;

/** hover 换底色（离开恢复 base）。menu 行/按钮 hover 反馈用。 */
export function hoverBg(
  base: string
): Pick<React.HTMLAttributes<HTMLElement>, "onMouseEnter" | "onMouseLeave"> {
  return {
    onMouseEnter: (e: MouseEvent<HTMLElement>) => {
      e.currentTarget.style.background = DT.mutedAlpha(0.45);
    },
    onMouseLeave: (e: MouseEvent<HTMLElement>) => {
      e.currentTarget.style.background = base;
    },
  };
}

/** hover 换文字色（离开恢复 base）。 */
export function hoverColor(
  base: string
): Pick<React.HTMLAttributes<HTMLElement>, "onMouseEnter" | "onMouseLeave"> {
  return {
    onMouseEnter: (e: MouseEvent<HTMLElement>) => {
      e.currentTarget.style.color = DT.foreground;
    },
    onMouseLeave: (e: MouseEvent<HTMLElement>) => {
      e.currentTarget.style.color = base;
    },
  };
}

/** 组合底色+文字色 hover。 */
export function hoverBgColor(
  baseBg: string,
  baseColor: string
): Pick<React.HTMLAttributes<HTMLElement>, "onMouseEnter" | "onMouseLeave"> {
  return {
    onMouseEnter: (e: MouseEvent<HTMLElement>) => {
      e.currentTarget.style.background = DT.mutedAlpha(0.45);
      e.currentTarget.style.color = baseColor;
    },
    onMouseLeave: (e: MouseEvent<HTMLElement>) => {
      e.currentTarget.style.background = baseBg;
      e.currentTarget.style.color = baseColor;
    },
  };
}

/** 通用省略号截断样式。 */
export const ellipsis: CSSProperties = {
  minWidth: 0,
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
};
