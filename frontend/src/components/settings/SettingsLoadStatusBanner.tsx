/**
 * 复刻自 DeepTutor 原仓 web/components/settings/SettingsLoadStatusBanner.tsx（整件 1:1，批5 5.2 壳族）。
 * 替换点：lucide（AlertTriangle/Loader2/RefreshCw）→ @ant-design/icons（WarningOutlined/
 * LoadingOutlined/ReloadOutlined）；react-i18next t() → 文件内查表直出（zh/app.json 原译文）；
 * Tailwind → 内联样式 + 页内 <style>（hover/disabled 伪类进样式块）。tupu 无暗色主题，
 * dark: 前缀变体取亮色值（amber-300/50/100/200/900 语义保持）。导出名/结构/data-testid 逐字保留。
 */
import { useState } from "react";
import {
  LoadingOutlined,
  ReloadOutlined,
  WarningOutlined,
} from "@ant-design/icons";

import { useSettings } from "./SettingsContext";

import { tokens } from "../../theme/tokens";

const BORDER = `var(--border, ${tokens.colors.border})`;

// amber 语义（原仓 Tailwind amber 调色板；tupu 无暗色主题，仅亮色值）。
const AMBER_BORDER = "#fcd34d"; // amber-300
const AMBER_BG = "#fffbeb"; // amber-50
const AMBER_TEXT = "#78350f"; // amber-900
const AMBER_BTN_BG = "#fef3c7"; // amber-100
const AMBER_BTN_BG_HOVER = "#fde68a"; // amber-200

/** i18next 兼容直出（见头注）：web/locales/zh/app.json 原译文。 */
const ZH: Record<string, string> = {
  "Loading settings...": "加载设置中…",
  "Could not load settings from the backend.": "无法从后端加载设置。",
  "Verify the backend is running and NEXT_PUBLIC_API_BASE points to a reachable host. For Docker, see data/user/settings/system.json.":
    "请确认后端正在运行，且 NEXT_PUBLIC_API_BASE 指向可访问的主机。Docker 部署请参考 data/user/settings/system.json。",
  Retry: "重试",
};

function t(key: string): string {
  return Object.prototype.hasOwnProperty.call(ZH, key) ? ZH[key] : key;
}

// Surface the result of the initial /api/v1/settings + /api/v1/system/status
// load so Docker / first-run users know *why* the page is empty when the
// backend is unreachable, instead of seeing a blank screen with the failure
// only in the dev console.
export function SettingsLoadStatusBanner() {
  const { settingsLoading, settingsError, reloadSettings } = useSettings();
  const [retrying, setRetrying] = useState(false);

  if (settingsLoading) {
    return (
      <div
        data-testid="settings-load-banner"
        style={{
          marginTop: 12,
          display: "flex",
          alignItems: "center",
          gap: 8,
          borderRadius: 6,
          border: `1px solid ${BORDER}`,
          background: `var(--surface-soft, ${tokens.colors.bgSubtle})`,
          padding: "8px 12px",
          fontSize: 14,
          color: `var(--foreground-soft, ${tokens.colors.textSecondary})`,
        }}
      >
        <LoadingOutlined spin style={{ fontSize: 16 }} />
        {t("Loading settings...")}
      </div>
    );
  }

  if (!settingsError) return null;

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await reloadSettings();
    } finally {
      setRetrying(false);
    }
  };

  return (
    <>
      <style>{`
.dsh-set-banner-retry {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border-radius: 6px;
  border: 1px solid ${AMBER_BORDER};
  background: ${AMBER_BTN_BG};
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 500;
  color: ${AMBER_TEXT};
  cursor: pointer;
  transition: background-color 150ms;
}
.dsh-set-banner-retry:hover {
  background: ${AMBER_BTN_BG_HOVER};
}
.dsh-set-banner-retry:disabled {
  opacity: 0.6;
  cursor: default;
}
`}</style>
      <div
        role="alert"
        data-testid="settings-load-banner"
        data-state="error"
        style={{
          marginTop: 12,
          display: "flex",
          alignItems: "flex-start",
          gap: 12,
          borderRadius: 6,
          border: `1px solid ${AMBER_BORDER}`,
          background: AMBER_BG,
          padding: "8px 12px",
          fontSize: 14,
          color: AMBER_TEXT,
        }}
      >
        <WarningOutlined
          style={{ marginTop: 2, fontSize: 16, flexShrink: 0 }}
        />
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ fontWeight: 500 }}>
            {t("Could not load settings from the backend.")}
          </div>
          <div style={{ marginTop: 4, fontSize: 12, opacity: 0.9 }}>
            {settingsError}
          </div>
          <div style={{ marginTop: 4, fontSize: 12, opacity: 0.75 }}>
            {t(
              "Verify the backend is running and NEXT_PUBLIC_API_BASE points to a reachable host. For Docker, see data/user/settings/system.json.",
            )}
          </div>
        </div>
        <button
          type="button"
          onClick={handleRetry}
          disabled={retrying}
          data-testid="settings-retry-btn"
          className="dsh-set-banner-retry"
        >
          <ReloadOutlined spin={retrying} style={{ fontSize: 12 }} />
          {t("Retry")}
        </button>
      </div>
    </>
  );
}
