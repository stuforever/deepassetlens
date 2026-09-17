/**
 * 复刻自 DeepTutor 原仓 web/components/settings/SettingsTourOverlay.tsx（整件 1:1，批5 5.2 壳族）。
 * 替换点：usePathname → useLocation().pathname；lucide（ChevronLeft/ChevronRight/Sparkles/X）→
 * @ant-design/icons（LeftOutlined/RightOutlined/StarOutlined/CloseOutlined）；react-i18next t() →
 * 文件内查表直出（zh/app.json 原译文，含 settingsTour.* 七步标题/描述 + {{}} 插值）；
 * Tailwind → 内联样式 + 页内 <style>（ring-2 ring-offset-2 → outline/outlineOffset；
 * bg-[var(--overlay)] → var(--overlay, rgba(0,0,0,0.35))；--primary-rgb 兜底 tupu 主色）。
 * 定位/重试解析/键盘快捷键/导出名/结构/data-testid 逐字保留。
 */
import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import {
  CloseOutlined,
  LeftOutlined,
  RightOutlined,
  StarOutlined,
} from "@ant-design/icons";

import { TOUR_STEPS, useSettings } from "./SettingsContext";

import { tokens } from "../../theme/tokens";

const FG = `var(--foreground, ${tokens.colors.textPrimary})`;
const BG = `var(--background, ${tokens.colors.bgPage})`;
const CARD = `var(--card, ${tokens.colors.bgContent})`;
const BORDER = `var(--border, ${tokens.colors.border})`;
const PRIMARY = `var(--primary, ${tokens.colors.primary})`;
const MUTED = `var(--muted-foreground, ${tokens.colors.textSecondary})`;
const MUTED_BG = `var(--muted, ${tokens.colors.bgSubtle})`;

// Cross-route guided tour. Mounted in the settings layout so the same
// instance survives navigation between sub-pages. After each step
// transition the controller pushes router.push to the step's route;
// here we wait until the pathname matches AND the target ``data-tour``
// element exists before painting, so we never spotlight an empty rect
// mid-transition.
//
// Visual design:
//   • Soft full-screen scrim (no harsh cutout) plus a translucent
//     highlight ring around the target — feels less "modal blocker",
//     more "look here".
//   • Tooltip card carries a step pill (3 / 10), a section title +
//     short description, and Back / Next + Skip controls.
//   • Arrow keys + Esc work as keyboard shortcuts so tour-as-orientation
//     doesn't require mousing.
const TOOLTIP_W = 340;
const TOOLTIP_H_EST = 200;
const SCROLL_PADDING = 80;
const HIGHLIGHT_PAD = 10;

/** i18next 兼容直出（见头注）：web/locales/zh/app.json 原译文。 */
const ZH: Record<string, string> = {
  "Step {{current}} of {{total}}": "第 {{current}} / {{total}} 步",
  "Skip tour": "跳过引导",
  Back: "上一步",
  Next: "下一个",
  "Got it": "知道了",
  "settingsTour.status.title": "状态",
  "settingsTour.status.desc":
    "后端与已配置模型服务的运行状态，常驻主页一目了然。",
  "settingsTour.appearance.title": "外观",
  "settingsTour.appearance.desc": "选择视觉主题和界面语言，改动立即生效。",
  "settingsTour.network.title": "网络",
  "settingsTour.network.desc":
    "端口、浏览器访问后端的 API 地址与 CORS 来源——Docker、局域网、反向代理部署在这里配。",
  "settingsTour.models.title": "模型",
  "settingsTour.models.desc":
    "点进来配置语言、向量、搜索、语音与生成模型——七项服务都在这一组里。",
  "settingsTour.knowledge.title": "知识库",
  "settingsTour.knowledge.desc": "选择文档解析引擎，决定上传文档如何转成文本。",
  "settingsTour.chat.title": "聊天",
  "settingsTour.chat.desc": "工具、MCP 服务器与各能力的运行时参数都在这里。",
  "settingsTour.memory.title": "记忆",
  "settingsTour.memory.desc": "调整记忆整理流程：分块、LLM 预算、去重和引用策略。",
};

function t(key: string, opts?: Record<string, unknown>): string {
  const zh = Object.prototype.hasOwnProperty.call(ZH, key) ? ZH[key] : key;
  if (!opts) return zh;
  return zh.replace(/\{\{(\w+)\}\}/g, (_m, k: string) =>
    opts[k] !== undefined && opts[k] !== null ? String(opts[k]) : `{{${k}}}`,
  );
}

export function SettingsTourOverlay() {
  const { pathname } = useLocation();
  const { tourStepIndex, advanceTour, goBackTour, skipTour } = useSettings();
  const [rect, setRect] = useState<DOMRect | null>(null);

  const guideStep =
    tourStepIndex >= 0 && tourStepIndex < TOUR_STEPS.length
      ? TOUR_STEPS[tourStepIndex]
      : null;
  const totalSteps = TOUR_STEPS.length;
  const isFirst = tourStepIndex <= 0;
  const isLast = tourStepIndex === totalSteps - 1;

  // The "wanted" target identity. When this changes between renders we
  // drop the previously resolved rect during render (React's "store
  // info from previous render" pattern), then the effect below resolves
  // the new one.
  const wantKey = guideStep
    ? `${guideStep.target}@${guideStep.route}@${pathname}`
    : null;
  const [resolvedFor, setResolvedFor] = useState<string | null>(null);
  if (resolvedFor !== wantKey) {
    setResolvedFor(wantKey);
    if (rect !== null) setRect(null);
  }

  // Resolve the target element. We retry briefly because the new
  // sub-page may not have mounted by the time the step changes
  // (Next.js route transitions are async). 8 attempts × 80ms = 640ms
  // ceiling; enough for any normal client-side route swap, well below
  // perceptual budget.
  useEffect(() => {
    if (!guideStep) return;
    if (!pathname.startsWith(guideStep.route)) return;
    let cancelled = false;
    let attempt = 0;
    const tryResolve = () => {
      if (cancelled) return;
      const el = document.querySelector(`[data-tour="${guideStep.target}"]`);
      if (el) {
        // Scroll the target into view BEFORE measuring so a
        // far-down target like the toolbar Apply button isn't
        // painted off-screen.
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        // Defer measurement by one frame so the scroll animation
        // has settled.
        window.requestAnimationFrame(() => {
          if (cancelled) return;
          setRect(el.getBoundingClientRect());
        });
        return;
      }
      attempt += 1;
      if (attempt < 8) {
        window.setTimeout(tryResolve, 80);
      }
    };
    const raf = window.requestAnimationFrame(tryResolve);
    return () => {
      cancelled = true;
      window.cancelAnimationFrame(raf);
    };
  }, [guideStep, pathname]);

  // Keep the highlight in sync as the user resizes the window.
  useEffect(() => {
    if (!guideStep) return;
    const onResize = () => {
      const el = document.querySelector(`[data-tour="${guideStep.target}"]`);
      if (el) setRect(el.getBoundingClientRect());
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [guideStep]);

  // Keyboard shortcuts. Esc skips; ←/→ navigates.
  useEffect(() => {
    if (!guideStep) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        skipTour();
      } else if (e.key === "ArrowRight" || e.key === "Enter") {
        e.preventDefault();
        advanceTour();
      } else if (e.key === "ArrowLeft" && !isFirst) {
        e.preventDefault();
        goBackTour();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [guideStep, advanceTour, goBackTour, skipTour, isFirst]);

  if (!guideStep || !rect) return null;

  const holeLeft = rect.left - HIGHLIGHT_PAD;
  const holeTop = rect.top - HIGHLIGHT_PAD;
  const holeW = rect.width + HIGHLIGHT_PAD * 2;
  const holeH = rect.height + HIGHLIGHT_PAD * 2;

  // Tooltip placement: prefer below the highlight; flip above if it
  // would overflow; clamp horizontally so the card stays on-screen.
  const wouldOverflowBelow =
    holeTop + holeH + 16 + TOOLTIP_H_EST > window.innerHeight - SCROLL_PADDING;
  const tooltipTop = wouldOverflowBelow
    ? Math.max(16, holeTop - TOOLTIP_H_EST - 16)
    : Math.min(holeTop + holeH + 16, window.innerHeight - TOOLTIP_H_EST - 16);
  const tooltipLeft = Math.max(
    16,
    Math.min(holeLeft, window.innerWidth - TOOLTIP_W - 16),
  );

  return (
    <>
      <style>{`
@keyframes dshSetFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
.dsh-set-tour-card { animation: dshSetFadeIn 200ms ease-out; }
.dsh-set-tour-skip-x {
  border: none;
  background: transparent;
  border-radius: 6px;
  padding: 4px;
  color: color-mix(in srgb, ${MUTED} 60%, transparent);
  cursor: pointer;
  transition: color 150ms, background-color 150ms;
}
.dsh-set-tour-skip-x:hover {
  background: color-mix(in srgb, ${MUTED_BG} 40%, transparent);
  color: ${FG};
}
.dsh-set-tour-back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: transparent;
  border-radius: 8px;
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 500;
  color: ${MUTED};
  cursor: pointer;
  transition: color 150ms;
}
.dsh-set-tour-back:hover { color: ${FG}; }
.dsh-set-tour-back:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.dsh-set-tour-skip-text {
  border: none;
  background: transparent;
  padding: 0;
  font-size: 12px;
  color: color-mix(in srgb, ${MUTED} 60%, transparent);
  cursor: pointer;
  transition: color 150ms;
}
.dsh-set-tour-skip-text:hover { color: ${MUTED}; }
.dsh-set-tour-next {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  border-radius: 8px;
  background: ${FG};
  color: ${BG};
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 150ms;
}
.dsh-set-tour-next:hover { opacity: 0.8; }
`}</style>
      <div
        data-testid="settings-tour-overlay"
        style={{
          position: "fixed",
          inset: 0,
          zIndex: 9999,
          pointerEvents: "none",
        }}
      >
        {/* Soft scrim — pointer-events disabled so the user can still
            click highlighted controls if they want to. The click-through
            experience is intentional: the tour describes; it does not
            block. */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: "var(--overlay, rgba(0, 0, 0, 0.35))",
            backdropFilter: "blur(1px)",
            transition: "opacity 200ms",
          }}
        />

        {/* Highlight ring around the target. A soft outer glow + a crisp
            inner outline reads more "spotlight" than a hard cut-out. */}
        <div
          style={{
            position: "absolute",
            borderRadius: 16,
            outline: `2px solid ${PRIMARY}`,
            outlineOffset: 2,
            transition: "all 300ms",
            left: holeLeft,
            top: holeTop,
            width: holeW,
            height: holeH,
            boxShadow:
              "0 0 0 9999px rgba(0,0,0,0.35), 0 0 32px rgba(var(--primary-rgb, 37, 99, 235), 0.45)",
          }}
        />

        {/* Tooltip */}
        <div
          className="dsh-set-tour-card"
          style={{
            pointerEvents: "auto",
            position: "absolute",
            zIndex: 10,
            top: tooltipTop,
            left: tooltipLeft,
            width: 340,
            overflow: "hidden",
            borderRadius: 16,
            border: `1px solid ${BORDER}`,
            background: CARD,
            boxShadow: "0 24px 60px -12px rgba(0, 0, 0, 0.3)",
          }}
          role="dialog"
          aria-labelledby="tour-title"
        >
          {/* Step progress bar — thin strip across the top of the card. */}
          <div
            style={{
              height: 4,
              width: "100%",
              background: `color-mix(in srgb, ${MUTED_BG} 40%, transparent)`,
            }}
          >
            <div
              style={{
                height: "100%",
                background: FG,
                transition: "all 500ms",
                width: `${((tourStepIndex + 1) / totalSteps) * 100}%`,
              }}
            />
          </div>

          <div style={{ padding: "16px 20px 12px" }}>
            {/* Header row: step pill + skip × */}
            <div
              style={{
                marginBottom: 12,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  borderRadius: 9999,
                  background: `color-mix(in srgb, ${MUTED_BG} 50%, transparent)`,
                  padding: "4px 10px",
                  fontSize: 11,
                  fontWeight: 500,
                  color: MUTED,
                }}
              >
                <StarOutlined style={{ fontSize: 12 }} />
                <span>
                  {t("Step {{current}} of {{total}}", {
                    current: tourStepIndex + 1,
                    total: totalSteps,
                  })}
                </span>
              </div>
              <button
                type="button"
                onClick={skipTour}
                aria-label={t("Skip tour")}
                data-testid="settings-tour-skip"
                className="dsh-set-tour-skip-x"
              >
                <CloseOutlined style={{ fontSize: 14 }} />
              </button>
            </div>

            <h2
              id="tour-title"
              style={{
                margin: "0 0 6px",
                fontSize: 14,
                fontWeight: 600,
                color: FG,
              }}
            >
              {t(guideStep.titleKey)}
            </h2>
            <p
              style={{
                margin: 0,
                fontSize: 12.5,
                lineHeight: 1.625,
                color: MUTED,
              }}
            >
              {t(guideStep.descKey)}
            </p>
          </div>

          {/* Footer: Back / Next */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 8,
              borderTop: `1px solid color-mix(in srgb, ${BORDER} 60%, transparent)`,
              background: `color-mix(in srgb, ${BG} 30%, transparent)`,
              padding: "12px 20px",
            }}
          >
            <button
              type="button"
              onClick={goBackTour}
              disabled={isFirst}
              data-testid="settings-tour-back"
              className="dsh-set-tour-back"
            >
              <LeftOutlined style={{ fontSize: 12 }} />
              {t("Back")}
            </button>
            <button
              type="button"
              onClick={skipTour}
              data-testid="settings-tour-skip-text"
              className="dsh-set-tour-skip-text"
            >
              {t("Skip tour")}
            </button>
            <button
              type="button"
              onClick={advanceTour}
              data-testid="settings-tour-next"
              className="dsh-set-tour-next"
            >
              {isLast ? t("Got it") : t("Next")}
              <RightOutlined style={{ fontSize: 12 }} />
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
