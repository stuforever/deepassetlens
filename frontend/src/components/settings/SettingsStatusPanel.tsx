/**
 * 复刻自 DeepTutor 原仓 web/components/settings/SettingsStatusPanel.tsx（整件 1:1，批5 5.2 壳族）。
 * 替换点：react-i18next t() → 文件内查表直出（zh/app.json 原译文）；Tailwind → 内联样式 +
 * 页内 <style>（hidden sm:block 等响应式规则进样式块）；颜色走 CSS 变量 + theme/tokens 兜底。
 * 结构/data-tour/data-testid/状态点语义（statusDotClass）逐字保留。
 */
import { Fragment } from "react";

import { useSettings } from "./SettingsContext";
import { statusDotClass } from "./shared";

import { tokens } from "../../theme/tokens";

const FG = `var(--foreground, ${tokens.colors.textPrimary})`;
const MUTED = `var(--muted-foreground, ${tokens.colors.textSecondary})`;
const BORDER = `var(--border, ${tokens.colors.border})`;
const CARD = `var(--card, ${tokens.colors.bgContent})`;

/** i18next 兼容直出（见头注）：web/locales/zh/app.json 原译文。 */
const ZH: Record<string, string> = {
  Backend: "后端",
  Online: "在线",
  Checking: "检测中",
  LLM: "LLM",
  Embedding: "嵌入模型",
  Search: "搜索",
  "Not set": "未配置",
};

function t(key: string): string {
  return Object.prototype.hasOwnProperty.call(ZH, key) ? ZH[key] : key;
}

/**
 * Resident status module on the settings hub — the old `/settings/status` page
 * demoted to an always-visible strip. Reads the runtime `/system/status`
 * snapshot (available to every user, unlike the editable catalog), so it
 * reflects what is actually running rather than the draft.
 *
 * Compact, left-aligned, hairline-separated items — no stretched grid or
 * uppercase eyebrow (CJK reads badly with letter-spacing).
 */
export default function SettingsStatusPanel() {
  const { status } = useSettings();

  const items = [
    {
      key: "backend",
      name: t("Backend"),
      configured: status?.backend.status === "online",
      hasError: false,
      value: status
        ? status.backend.status === "online"
          ? t("Online")
          : t("Checking")
        : t("Checking"),
    },
    {
      key: "llm",
      name: t("LLM"),
      configured: Boolean(status?.llm.model),
      hasError: Boolean(status?.llm.error),
      value: status?.llm.model || t("Not set"),
    },
    {
      key: "embedding",
      name: t("Embedding"),
      configured: Boolean(status?.embeddings.model),
      hasError: Boolean(status?.embeddings.error),
      value: status?.embeddings.model || t("Not set"),
    },
    {
      key: "search",
      name: t("Search"),
      configured: Boolean(status?.search.provider),
      hasError: Boolean(status?.search.error),
      value: status?.search.provider || t("Not set"),
    },
  ];

  return (
    <>
      <style>{`
.dsh-set-status-sep { display: none; }
@media (min-width: 640px) {
  .dsh-set-status-sep { display: block; }
}
`}</style>
      <section
        data-tour="tour-status"
        data-testid="settings-status-panel"
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          columnGap: 20,
          rowGap: 10,
          borderRadius: 16,
          border: `1px solid color-mix(in srgb, ${BORDER} 70%, transparent)`,
          background: `color-mix(in srgb, ${CARD} 50%, transparent)`,
          padding: "14px 20px",
        }}
      >
        {items.map((item, i) => (
          <Fragment key={item.key}>
            {i > 0 && (
              <span
                aria-hidden
                className="dsh-set-status-sep"
                style={{
                  height: 28,
                  width: 1,
                  flexShrink: 0,
                  background: `color-mix(in srgb, ${BORDER} 70%, transparent)`,
                }}
              />
            )}
            <div
              data-testid={`settings-status-${item.key}`}
              style={{ display: "flex", alignItems: "center", gap: 10 }}
            >
              <span
                className={statusDotClass(item.configured, item.hasError)}
                style={{ height: 8, width: 8, flexShrink: 0, borderRadius: 9999, display: "inline-block" }}
              />
              <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                <span
                  style={{
                    fontSize: 13,
                    fontWeight: 500,
                    lineHeight: 1,
                    letterSpacing: "-0.01em",
                    color: FG,
                  }}
                >
                  {item.name}
                </span>
                <span
                  title={item.value}
                  style={{
                    maxWidth: 220,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    fontSize: 12,
                    lineHeight: 1,
                    color: MUTED,
                  }}
                >
                  {item.value}
                </span>
              </div>
            </div>
          </Fragment>
        ))}
      </section>
    </>
  );
}
