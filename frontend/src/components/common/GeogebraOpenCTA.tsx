/**
 * 批6 依赖补件：1:1 移植自 DeepTutor web/components/common/GeogebraOpenCTA.tsx
 * （RichMarkdownRenderer 级联依赖，lazy 加载）。替换点：
 *  - "use client" 去；react-i18next → 文件内查表直出（zh/app.json 原译文）；
 *  - lucide-react Compass → @ant-design/icons CompassOutlined（strokeWidth 忽略）；
 *  - @/context/GeogebraTabContext → ../../context/GeogebraTabContext（本批 1:1 补件）；
 *  - Tailwind 类逐项换内联样式；hover 态由一次性 <style> 承载（.dtggb-btn）；
 *    调用侧 gap 由 className 字符串改为 style 对象（prop 更名 className → style）。
 * 其余逐字一致。
 */

import { CompassOutlined } from "@ant-design/icons";
import { useCallback, useMemo } from "react";
import type { CSSProperties } from "react";
import { useGeogebraTabOpener } from "../../context/GeogebraTabContext";

const ZH_MESSAGES: Record<string, string> = {
  "GeoGebra figure": "GeoGebra 图形",
  "GeoGebra viewer is not available in this surface":
    "此界面不支持 GeoGebra 查看器",
  "Interactive GeoGebra figure": "交互式 GeoGebra 图形",
  "Click to open an interactive GeoGebra canvas in the side viewer.":
    "点击在侧边查看器中打开交互式 GeoGebra 画布。",
};

function t(key: string, vars?: Record<string, string | number>): string {
  let text = ZH_MESSAGES[key] ?? key;
  if (vars) {
    for (const [name, value] of Object.entries(vars)) {
      text = text.split(`{{${name}}}`).join(String(value));
    }
  }
  return text;
}

/* 一次性样式注入（hover 态）。 */
const STYLE_ID = "dt-geogebra-cta-css";
const GEOGEBRA_CTA_CSS = `
.dtggb-btn { transition: border-color 0.15s ease, background-color 0.15s ease; }
.dtggb-btn:not(:disabled):hover {
  border-color: color-mix(in srgb, var(--primary, #b0501e) 60%, transparent);
  background-color: color-mix(in srgb, var(--muted, #f1ede2) 30%, transparent);
}
`;
if (typeof document !== "undefined" && !document.getElementById(STYLE_ID)) {
  const styleEl = document.createElement("style");
  styleEl.id = STYLE_ID;
  styleEl.textContent = GEOGEBRA_CTA_CSS;
  document.head.appendChild(styleEl);
}

interface GeogebraOpenCTAProps {
  /** Raw ggbscript body. */
  script: string;
  /** Stable id from the ```ggbscript[id;title] fence — used for tab dedupe. */
  payloadId?: string;
  /** Title to show on the CTA + the resulting tab. */
  title?: string;
  style?: CSSProperties;
}

/**
 * Card-style CTA shown in-place of a ```ggbscript fence in chat answers.
 * Clicking expands the right-hand SessionViewerPanel and opens (or
 * focuses) a GeoGebra tab carrying this script.
 *
 * When no GeogebraTabProvider is mounted (e.g. preview surfaces), the
 * button is disabled with a tooltip — we don't want a click to silently
 * no-op.
 */
export default function GeogebraOpenCTA({
  script,
  payloadId,
  title,
  style,
}: GeogebraOpenCTAProps) {
  const controller = useGeogebraTabOpener();

  // A stable id keyed on the script content. This makes the tab dedupe
  // robust even if the assistant doesn't bother emitting an explicit
  // page_id in the fence info (older outputs).
  const id = useMemo(() => {
    if (payloadId) return payloadId;
    let hash = 0;
    for (let i = 0; i < script.length; i += 1) {
      hash = (hash * 31 + script.charCodeAt(i)) | 0;
    }
    return `script-${(hash >>> 0).toString(36)}`;
  }, [payloadId, script]);

  const onClick = useCallback(() => {
    if (!controller) return;
    controller.openTab({ id, title: title || t("GeoGebra figure"), script });
  }, [controller, id, script, title]);

  const disabled = !controller;

  return (
    <div style={{ margin: "12px 0", ...(style || {}) }}>
      <button
        type="button"
        onClick={onClick}
        disabled={disabled}
        title={
          disabled
            ? t("GeoGebra viewer is not available in this surface")
            : undefined
        }
        className="dtggb-btn"
        style={{
          display: "flex",
          width: "100%",
          alignItems: "center",
          gap: 12,
          borderRadius: 12,
          border: "1px solid var(--border, #e2e8f0)",
          background: "var(--card, #ffffff)",
          padding: "12px 16px",
          textAlign: "left",
          cursor: disabled ? "not-allowed" : "pointer",
          opacity: disabled ? 0.6 : 1,
          font: "inherit",
        }}
      >
        <span
          style={{
            display: "flex",
            width: 36,
            height: 36,
            flexShrink: 0,
            alignItems: "center",
            justifyContent: "center",
            borderRadius: 8,
            background:
              "color-mix(in srgb, var(--primary, #b0501e) 10%, transparent)",
            color: "var(--primary, #b0501e)",
            fontSize: 18,
          }}
        >
          <CompassOutlined />
        </span>
        <span style={{ minWidth: 0, flex: 1 }}>
          <span
            style={{
              display: "block",
              fontSize: 14,
              fontWeight: 500,
              color: "var(--foreground, #1c1816)",
            }}
          >
            {title || t("Interactive GeoGebra figure")}
          </span>
          <span
            style={{
              display: "block",
              fontSize: 12,
              lineHeight: "16px",
              color: "var(--muted-foreground, #64748b)",
            }}
          >
            {t(
              "Click to open an interactive GeoGebra canvas in the side viewer.",
            )}
          </span>
        </span>
      </button>
    </div>
  );
}
