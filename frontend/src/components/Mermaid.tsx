/**
 * 批6 依赖补件：1:1 移植自 DeepTutor web/components/Mermaid.tsx（RichMarkdownRenderer
 * 级联依赖，lazy 加载）。替换点：
 *  - "use client" 去；react-i18next → 文件内查表直出（zh/app.json 原译文，{{x}} 插值语义一致）；
 *  - @/lib/theme → ../../lib/theme（本批 1:1 补件）；
 *  - 依赖包已安装（IA批6 N-16 mermaid）——`import("mermaid")` 两处以 @ts-ignore 承载类型；
 *    运行时渲染 mermaid 图需安装 mermaid@^11 后由 webpack 解析；
 *  - Tailwind 类逐项换内联样式（red-50=#fef2f2、red-200=#fecaca、red-600=#dc2626、
 *    red-500=#ef4444）；调用侧 gap 由 className 字符串改为 style 对象（prop 更名
 *    className → style，见 RichMarkdownRenderer 调用点登记）。
 * 其余逐字一致。
 */

import React, { useEffect, useRef, useState } from "react";

// @ts-ignore 缺包登记：mermaid 未安装（见文件头）
type MermaidApi = (typeof import("mermaid"))["default"];

const ZH_MESSAGES: Record<string, string> = {
  "Rendering diagram...": "正在渲染图表…",
  "Failed to render diagram": "示意图渲染失败",
  "Diagram rendering error": "图表渲染出错",
  "Show source": "显示源码",
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

import { subscribeToThemeChanges } from "../lib/theme";

interface MermaidProps {
  chart: string;
  style?: React.CSSProperties;
}

let mermaidLoader: Promise<MermaidApi> | null = null;

// Read a CSS custom property from :root. We re-derive these on every render
// so the diagram colors track the active theme rather than freezing to the
// first-render palette.
function cssVar(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  return value || fallback;
}

function themeVariablesFromCss() {
  // Mermaid expects opaque colors; we pull from the theme's --foreground /
  // --card / --border / --primary tokens so diagrams blend with the chat
  // surface in every theme (light, dark, snow, glass).
  return {
    primaryColor: cssVar("--card", "#ffffff"),
    primaryTextColor: cssVar("--foreground", "#1f1d1b"),
    primaryBorderColor: cssVar("--border", "#dbd4c8"),
    lineColor: cssVar("--muted-foreground", "#6b655f"),
    secondaryColor: cssVar("--muted", "#ece7dd"),
    tertiaryColor: cssVar("--background", "#faf9f6"),
    textColor: cssVar("--foreground", "#1f1d1b"),
    mainBkg: cssVar("--card", "#ffffff"),
  };
}

async function loadMermaid() {
  if (!mermaidLoader) {
    // @ts-ignore 缺包登记：mermaid 未安装（见文件头）
    mermaidLoader = import("mermaid").then((module) => module.default);
  }
  return mermaidLoader;
}

// Re-applied on every render so theme changes pick up. mermaid.initialize()
// is idempotent and cheap; the heavy work is the dynamic import which the
// loader above only runs once.
function applyMermaidTheme(mermaid: MermaidApi) {
  mermaid.initialize({
    startOnLoad: false,
    theme: "base",
    securityLevel: "strict",
    fontFamily: "ui-sans-serif, system-ui, sans-serif",
    flowchart: {
      useMaxWidth: true,
      htmlLabels: false,
      curve: "basis",
    },
    themeVariables: themeVariablesFromCss(),
  });
}

function cleanupMermaidOrphans(id: string) {
  try {
    document.getElementById(id)?.remove();
    document.getElementById(`d${id}`)?.remove();
  } catch {
    /* ignore */
  }
}

let mermaidIdCounter = 0;

const DEBOUNCE_MS = 600;

export const Mermaid: React.FC<MermaidProps> = ({ chart, style }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [stable, setStable] = useState(false);
  const [id] = useState(() => `mermaid-${++mermaidIdCounter}`);
  const [themeToken, setThemeToken] = useState(0);
  const lastChartRef = useRef(chart);

  useEffect(() => {
    lastChartRef.current = chart;
    setStable(false);

    const timer = window.setTimeout(() => {
      if (lastChartRef.current === chart) setStable(true);
    }, DEBOUNCE_MS);

    return () => window.clearTimeout(timer);
  }, [chart]);

  // Bump a token whenever the app's theme changes so the render effect below
  // re-runs with fresh theme variables. Without this the diagram would keep
  // its initial palette across light/dark/glass/snow switches.
  useEffect(() => {
    return subscribeToThemeChanges(() => setThemeToken((t) => t + 1));
  }, []);

  useEffect(() => {
    if (!stable) return;

    let cancelled = false;
    const renderChart = async () => {
      if (!chart.trim() || !containerRef.current) return;

      try {
        const mermaid = await loadMermaid();
        applyMermaidTheme(mermaid);
        cleanupMermaidOrphans(id);
        const { svg: renderedSvg } = await mermaid.render(id, chart.trim());
        if (!cancelled) {
          setSvg(renderedSvg);
          setError(null);
        }
      } catch (err) {
        cleanupMermaidOrphans(id);
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : t("Failed to render diagram"),
          );
        }
      }
    };

    void renderChart();
    return () => {
      cancelled = true;
    };
  }, [stable, chart, id, t, themeToken]);

  if (error) {
    return (
      <div
        style={{
          margin: "16px 0",
          padding: 16,
          background: "#fef2f2",
          border: "1px solid #fecaca",
          borderRadius: 8,
          ...(style || {}),
        }}
      >
        <p style={{ color: "#dc2626", fontSize: 14, fontWeight: 500, marginBottom: 8 }}>
          {t("Diagram rendering error")}
        </p>
        <pre style={{ fontSize: 12, color: "#ef4444", whiteSpace: "pre-wrap" }}>{error}</pre>
        <details style={{ marginTop: 8 }}>
          <summary
            style={{
              fontSize: 12,
              color: "var(--muted-foreground, #64748b)",
              cursor: "pointer",
            }}
          >
            {t("Show source")}
          </summary>
          <pre
            style={{
              marginTop: 8,
              padding: 8,
              background: "var(--muted, #f1ede2)",
              borderRadius: 4,
              fontSize: 12,
              overflowX: "auto",
              color: "var(--foreground, #1c1816)",
            }}
          >
            {chart}
          </pre>
        </details>
      </div>
    );
  }

  if (!stable && !svg) {
    return (
      <div
        style={{
          margin: "16px 0",
          borderRadius: 12,
          border: "1px solid var(--border, #e2e8f0)",
          background: "color-mix(in srgb, var(--muted, #f1ede2) 50%, transparent)",
          padding: "12px 16px",
          fontSize: 14,
          color: "var(--muted-foreground, #64748b)",
          ...(style || {}),
        }}
      >
        {t("Rendering diagram...")}
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      style={{
        margin: "24px 0",
        display: "flex",
        justifyContent: "center",
        overflowX: "auto",
        ...(style || {}),
      }}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
};

export default Mermaid;
