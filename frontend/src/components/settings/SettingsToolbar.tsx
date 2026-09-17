/**
 * 复刻自 DeepTutor 原仓 web/components/settings/SettingsToolbar.tsx（整件 1:1，批5 5.2 壳族）。
 * 替换点：usePathname → useLocation().pathname；lucide（Loader2/Rocket/Save/Wand2）→
 * @ant-design/icons（LoadingOutlined/RocketOutlined/SaveOutlined/ThunderboltOutlined）；
 * react-i18next t() → 文件内查表直出（zh/app.json 原译文）；Tailwind → 内联样式 + 页内
 * <style>（hover/disabled/animate-fade-in 伪类进样式块，amber→tokens.warning）。
 * 导出名（具名 SettingsToolbar）/结构/data-testid/data-tour/逻辑逐字保留。
 */
import {
  LoadingOutlined,
  RocketOutlined,
  SaveOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { useLocation } from "react-router-dom";

import { storagePathFor } from "../../lib/settings-nav";
import { useSettings } from "./SettingsContext";

import { tokens } from "../../theme/tokens";

const FG = `var(--foreground, ${tokens.colors.textPrimary})`;
const BG = `var(--background, ${tokens.colors.bgPage})`;
const MUTED = `var(--muted-foreground, ${tokens.colors.textSecondary})`;
const BORDER = `var(--border, ${tokens.colors.border})`;
const PRIMARY = `var(--primary, ${tokens.colors.primary})`;
const AMBER = tokens.colors.warning; // amber-600 语义

/** i18next 兼容直出（见头注）：web/locales/zh/app.json 原译文。 */
const ZH: Record<string, string> = {
  "Draft has unsaved changes": "草稿有未保存的更改",
  "Saved to": "保存于",
  "All changes saved": "所有更改已保存",
  Tour: "引导",
  "Save Draft": "保存草稿",
  Apply: "应用",
};

function t(key: string): string {
  return Object.prototype.hasOwnProperty.call(ZH, key) ? ZH[key] : key;
}

// Sticky toolbar above the sub-page content. Save Draft / Apply only show
// when there's actually something to save — keeps the bar quiet for the
// majority of sessions that just visit Appearance.
export function SettingsToolbar() {
  const { pathname } = useLocation();
  const storagePath = storagePathFor(pathname ?? "");
  const {
    catalogEditable,
    hasUnsavedChanges,
    saving,
    applying,
    saveCatalog,
    applyCatalog,
    startTour,
    toast,
  } = useSettings();

  if (catalogEditable !== true) {
    if (!toast) return null;
    return (
      <div
        data-testid="settings-toolbar"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-end",
          padding: "8px 4px",
        }}
      >
        <p
          data-testid="settings-toolbar-status"
          style={{ margin: 0, fontSize: 12, color: PRIMARY, animation: "dshSetFadeIn 200ms ease-out" }}
        >
          {toast}
        </p>
      </div>
    );
  }

  return (
    <>
      <style>{`
@keyframes dshSetFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
.dsh-set-tb-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 8px;
  border: 1px solid color-mix(in srgb, ${BORDER} 50%, transparent);
  background: transparent;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  color: ${MUTED};
  cursor: pointer;
  transition: color 150ms, border-color 150ms;
}
.dsh-set-tb-btn:hover {
  border-color: ${BORDER};
  color: ${FG};
}
.dsh-set-tb-btn:disabled {
  opacity: 0.4;
  cursor: default;
}
.dsh-set-tb-btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 8px;
  border: none;
  background: ${FG};
  color: ${BG};
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 150ms;
}
.dsh-set-tb-btn-primary:hover {
  opacity: 0.8;
}
.dsh-set-tb-btn-primary:disabled {
  opacity: 0.4;
  cursor: default;
}
`}</style>
      <div
        data-testid="settings-toolbar"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          padding: "8px 4px",
        }}
      >
        <p
          data-testid="settings-toolbar-status"
          style={{
            margin: 0,
            minWidth: 0,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            fontSize: 12,
            ...(toast
              ? { color: PRIMARY, animation: "dshSetFadeIn 200ms ease-out" }
              : hasUnsavedChanges
                ? { color: AMBER }
                : { color: MUTED }),
          }}
        >
          {toast ? (
            toast
          ) : hasUnsavedChanges ? (
            t("Draft has unsaved changes")
          ) : storagePath ? (
            <>
              {t("Saved to")}{" "}
              <span
                style={{
                  fontFamily:
                    "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
                  color: `color-mix(in srgb, ${FG} 65%, transparent)`,
                }}
              >
                {storagePath}
              </span>
            </>
          ) : (
            t("All changes saved")
          )}
        </p>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button
            type="button"
            onClick={startTour}
            data-testid="settings-toolbar-tour"
            className="dsh-set-tb-btn"
          >
            <RocketOutlined style={{ fontSize: 12 }} />
            {t("Tour")}
          </button>
          <button
            type="button"
            onClick={saveCatalog}
            disabled={saving || !hasUnsavedChanges}
            data-testid="settings-save-btn"
            className="dsh-set-tb-btn"
          >
            {saving ? (
              <LoadingOutlined spin style={{ fontSize: 12 }} />
            ) : (
              <SaveOutlined style={{ fontSize: 12 }} />
            )}
            {t("Save Draft")}
          </button>
          <button
            type="button"
            data-tour="tour-actions"
            onClick={applyCatalog}
            disabled={applying}
            data-testid="settings-apply-btn"
            className="dsh-set-tb-btn-primary"
          >
            {applying ? (
              <LoadingOutlined spin style={{ fontSize: 12 }} />
            ) : (
              <ThunderboltOutlined style={{ fontSize: 12 }} />
            )}
            {t("Apply")}
          </button>
        </div>
      </div>
    </>
  );
}
