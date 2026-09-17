/**
 * 复刻自 DeepTutor 原仓 web/components/settings/shared.tsx（整件 1:1，批5 5.2 壳族）。
 * 替换点（导出名/签名逐字一致）：
 *  - "use client" 去除；react-i18next t() → 文件内查表直出（web/locales/zh/app.json
 *    原译文，插值 {{name}} 语义与 i18next 一致）；
 *  - 原仓 Tailwind class 常量（fieldControlClass/inputClass/nativeSelectClass/
 *    selectClass/selectOptionClass/statusDotClass/labelClass 的返回值）改为本文件
 *    模块加载时注入一次的等价 CSS 类（<style id="dsh-settings-shared-styles">），
 *    导出名与 string 类型逐字保留，消费方式（className={...}）不变；
 *  - 颜色语义一致：var(--foreground/--muted-foreground/--card/--border/--ring/--background)
 *    兜底值取 theme/tokens（textPrimary/textSecondary/bgContent/border/primary/bgPage）。
 */
import React from "react";

import { tokens } from "../../theme/tokens";
import type { CatalogProfile, ServiceName } from "./SettingsContext";

const _FG = tokens.colors.textPrimary; // var(--foreground, #0f172a)
const _MUTED = tokens.colors.textSecondary; // var(--muted-foreground, #64748b)
const _BORDER = tokens.colors.border; // var(--border, #e2e8f0)
const _CARD = tokens.colors.bgContent; // var(--card, #ffffff)
const _BG = tokens.colors.bgPage; // var(--background, #f6f8fc)
const _RING = tokens.colors.primary; // var(--ring, #2563eb)

/** 原仓 class 常量的等价样式表：模块加载时注入一次（CRA 无 SSR，仅浏览器）。 */
const SHARED_STYLE_ID = "dsh-settings-shared-styles";
if (typeof document !== "undefined" && !document.getElementById(SHARED_STYLE_ID)) {
  const styleEl = document.createElement("style");
  styleEl.id = SHARED_STYLE_ID;
  styleEl.textContent = `
.dsh-settings-field-control {
  width: 100%;
  border-radius: 8px;
  border: 1px solid var(--border, ${_BORDER});
  padding: 8px 12px;
  font-size: 14px;
  color: var(--foreground, ${_FG});
  outline: none;
  transition: border-color 150ms;
}
.dsh-settings-field-control:focus {
  border-color: var(--ring, ${_RING});
}
.dsh-settings-input {
  background: transparent;
}
.dsh-settings-input::placeholder {
  color: rgba(100, 116, 139, 0.4);
}
.dsh-settings-native-select {
  background: var(--background, ${_BG});
  cursor: pointer;
}
.dsh-settings-native-select:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
.dsh-settings-select {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
}
.dsh-settings-select-option {
  background: var(--background, ${_BG});
  color: var(--foreground, ${_FG});
}
.dsh-settings-status-dot-error {
  background: #f87171;
}
.dsh-settings-status-dot-ok {
  background: #10b981;
}
.dsh-settings-status-dot-idle {
  background: var(--border, ${_BORDER});
}
.dsh-settings-label-zh-sm { font-size: 10.5px; font-weight: 500; }
.dsh-settings-label-zh-md { font-size: 11px; font-weight: 500; }
.dsh-settings-label-zh-lg { font-size: 12px; font-weight: 500; }
.dsh-settings-label-en-sm { font-size: 9.5px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.16em; }
.dsh-settings-label-en-md { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.16em; }
.dsh-settings-label-en-lg { font-size: 11px; text-transform: uppercase; letter-spacing: 0.16em; }
.dsh-settings-row:first-child { border-top: none !important; }
`;
  document.head.appendChild(styleEl);
}

// 原仓为 Tailwind 类字符串；此处为注入样式的等价类名（见头注），导出契约不变。
export const fieldControlClass = "dsh-settings-field-control";

export const inputClass = `${fieldControlClass} dsh-settings-input`;

export const nativeSelectClass = `${fieldControlClass} dsh-settings-native-select`;

export const selectClass = `${nativeSelectClass} dsh-settings-select`;

export const selectOptionClass = "dsh-settings-select-option";

export const supportedSearchProviders = [
  "brave",
  "tavily",
  "jina",
  "searxng",
  "duckduckgo",
  "perplexity",
] as const;

export const deprecatedSearchProviders = new Set([
  "exa",
  "serper",
  "baidu",
  "openrouter",
]);

export function stringifyExtraHeaders(
  value: CatalogProfile["extra_headers"],
): string {
  if (!value) return "";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value);
  } catch {
    return "";
  }
}

// 原仓返回 Tailwind 类（bg-red-400/bg-emerald-500/bg-[var(--border)]）；
// 等价类见上方注入样式表（颜色语义一致）。
export function statusDotClass(configured: boolean, hasError: boolean): string {
  if (hasError) return "dsh-settings-status-dot-error";
  if (configured) return "dsh-settings-status-dot-ok";
  return "dsh-settings-status-dot-idle";
}

/** i18next 兼容直出（见头注）：web/locales/zh/app.json 原译文。 */
const ZH: Record<string, string> = {
  Manual: "手动",
  Auto: "自动",
  Known: "内置识别",
  Default: "默认",
  Unset: "未设置",
  "No profile": "无配置档",
  "No provider": "无提供商",
  "No endpoint": "未设置端点",
  "No model selected": "未选择模型",
};

function t(key: string): string {
  return Object.prototype.hasOwnProperty.call(ZH, key) ? ZH[key] : key;
}

export function formatContextWindowSource(
  source: string | undefined,
  t: (key: string) => string,
): string {
  if (source === "manual") return t("Manual");
  if (source === "metadata") return t("Auto");
  if (source === "known_model") return t("Known");
  if (source === "default") return t("Default");
  return t("Unset");
}

export function formatContextWindowUpdatedAt(
  value: string | undefined,
  language: "en" | "zh",
): string {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString(language === "zh" ? "zh-CN" : "en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function activeProfileDetail(
  profile: CatalogProfile | null,
  service: ServiceName,
  t: (key: string) => string,
): string {
  if (!profile) return t("No profile");
  if (service === "search") return profile.provider || t("No provider");
  return profile.base_url || t("No endpoint");
}

export function activeModelDetail(
  profile: CatalogProfile | null,
  model: { model?: string; name?: string } | null,
  service: ServiceName,
  t: (key: string) => string,
): string {
  if (service === "search") return profile?.provider || t("No provider");
  return model?.model || model?.name || t("No model selected");
}

// 原仓返回 Tailwind 字体类；等价类见注入样式表（中文不加宽字距/大小写，仅调字号）。
export function labelClass(
  size: "sm" | "md" | "lg",
  language: "en" | "zh",
): string {
  if (language === "zh") {
    if (size === "sm") return "dsh-settings-label-zh-sm";
    if (size === "lg") return "dsh-settings-label-zh-lg";
    return "dsh-settings-label-zh-md";
  }
  if (size === "sm") return "dsh-settings-label-en-sm";
  if (size === "lg") return "dsh-settings-label-en-lg";
  return "dsh-settings-label-en-md";
}

// One-row settings group used on simple pages (Appearance, Status etc.).
// Title + optional description on the left, control flushed right. Matches
// the visual rhythm used on Codex-style preferences pages.
export function SettingRow({
  title,
  description,
  control,
  testId,
}: {
  title: string;
  description?: string;
  control: React.ReactNode;
  /** Optional stable selector for e2e audits (data-testid passthrough). */
  testId?: string;
}) {
  return (
    <div
      data-testid={testId}
      className="dsh-settings-row"
      style={{
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: 24,
        borderTop: `1px solid color-mix(in srgb, var(--border, ${_BORDER}) 50%, transparent)`,
        padding: "16px 4px",
      }}
    >
      <div style={{ minWidth: 0, flex: 1 }}>
        <div style={{ fontSize: 13.5, fontWeight: 500, color: `var(--foreground, ${_FG})` }}>
          {title}
        </div>
        {description && (
          <p
            style={{
              marginTop: 4,
              marginBottom: 0,
              fontSize: 12,
              lineHeight: 1.625,
              color: `var(--muted-foreground, ${_MUTED})`,
            }}
          >
            {description}
          </p>
        )}
      </div>
      <div style={{ flexShrink: 0 }}>{control}</div>
    </div>
  );
}

// Page-level section group. Title + optional description, then children.
export function SettingSection({
  title,
  description,
  children,
  testId,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
  /** Optional stable selector for e2e audits (data-testid passthrough). */
  testId?: string;
}) {
  return (
    <section data-testid={testId} style={{ marginBottom: 40 }}>
      <header style={{ marginBottom: 12 }}>
        <h2
          style={{
            margin: 0,
            fontSize: 15,
            fontWeight: 600,
            letterSpacing: "-0.01em",
            color: `var(--foreground, ${_FG})`,
          }}
        >
          {title}
        </h2>
        {description && (
          <p
            style={{
              marginTop: 4,
              marginBottom: 0,
              fontSize: 12.5,
              lineHeight: 1.625,
              color: `var(--muted-foreground, ${_MUTED})`,
            }}
          >
            {description}
          </p>
        )}
      </header>
      <div
        style={{
          borderRadius: 12,
          border: `1px solid color-mix(in srgb, var(--border, ${_BORDER}) 60%, transparent)`,
          background: `color-mix(in srgb, var(--card, ${_CARD}) 40%, transparent)`,
          padding: "0 20px",
        }}
      >
        {children}
      </div>
    </section>
  );
}

// Page heading shared across settings sub-pages. The global Save Draft / Apply
// toolbar (which also shows where this module persists to) lives above this, so
// each page just owns its title row.
export function SettingsPageHeader({
  title,
  description,
  testId,
}: {
  title: string;
  description?: string;
  /** Optional stable selector for e2e audits (data-testid passthrough). */
  testId?: string;
}) {
  return (
    <header data-testid={testId} style={{ marginBottom: 32 }}>
      <h1
        style={{
          margin: 0,
          fontSize: 22,
          fontWeight: 600,
          letterSpacing: "-0.01em",
          color: `var(--foreground, ${_FG})`,
        }}
      >
        {title}
      </h1>
      {description && (
        <p
          style={{
            marginTop: 6,
            marginBottom: 0,
            fontSize: 13,
            lineHeight: 1.625,
            color: `var(--muted-foreground, ${_MUTED})`,
          }}
        >
          {description}
        </p>
      )}
    </header>
  );
}
