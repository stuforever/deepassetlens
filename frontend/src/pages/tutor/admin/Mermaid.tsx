/**
 * 复刻自 DeepTutor：web/components/Mermaid.tsx（平铺到 tupu 目标目录）。
 * 替换点：
 *  - 删除 "use client" 与 react-i18next；文案按 zh/app.json 中文直出
 *    （"Diagram rendering error"→图表渲染出错、"Show source"→显示源码、
 *    "Rendering diagram..."→正在渲染图表…、"Failed to render diagram"→示意图渲染失败）。
 *  - 原仓动态 import("mermaid")：tupu 未安装 mermaid 且禁止新增依赖，改为运行时
 *    探测宿主全局 window.mermaid（若由外部脚本按需加载则复用），缺失时走与原仓
 *    catch 相同的错误分支（错误提示 + 显示源码）。
 *  - 原仓 @/lib/theme subscribeToThemeChanges：tupu 无主题系统（固定亮色），
 *    themeToken 恒为 0，仅保留渲染 effect 的依赖形状。
 *  - Tailwind 样式 → 最小内联样式（muted-foreground→#6b7280、muted→#f4f4f5、
 *    border→#e4e4e7、rose/red 色按 Tailwind 色值）。
 */
import React, { useEffect, useRef, useState } from "react";

interface MermaidProps {
  chart: string;
  className?: string;
}

type MermaidApi = {
  initialize: (config: Record<string, unknown>) => void;
  render: (id: string, chart: string) => Promise<{ svg: string }>;
};

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

// 原仓：动态 import("mermaid") 并缓存 promise。tupu 无该依赖，改为全局探测。
async function loadMermaid(): Promise<MermaidApi | null> {
  const w = window as unknown as { mermaid?: MermaidApi };
  return w.mermaid ?? null;
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

const errorBoxStyle: React.CSSProperties = {
  margin: "16px 0",
  padding: 16,
  background: "#fef2f2",
  border: "1px solid #fecaca",
  borderRadius: 8,
};

export const Mermaid: React.FC<MermaidProps> = ({ chart, className = "" }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [stable, setStable] = useState(false);
  const [id] = useState(() => `mermaid-${++mermaidIdCounter}`);
  // 原仓订阅主题变化重渲染；tupu 无主题系统，恒为 0（保留依赖形状）。
  const [themeToken] = useState(0);
  const lastChartRef = useRef(chart);

  useEffect(() => {
    lastChartRef.current = chart;
    setStable(false);

    const timer = window.setTimeout(() => {
      if (lastChartRef.current === chart) setStable(true);
    }, DEBOUNCE_MS);

    return () => window.clearTimeout(timer);
  }, [chart]);

  useEffect(() => {
    if (!stable) return;

    let cancelled = false;
    const renderChart = async () => {
      if (!chart.trim() || !containerRef.current) return;

      try {
        const mermaid = await loadMermaid();
        if (!mermaid) {
          throw new Error("示意图渲染失败");
        }
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
            err instanceof Error ? err.message : "示意图渲染失败",
          );
        }
      }
    };

    void renderChart();
    return () => {
      cancelled = true;
    };
  }, [stable, chart, id, themeToken]);

  if (error) {
    return (
      <div
        className={className}
        style={errorBoxStyle}
      >
        <p
          style={{
            color: "#dc2626",
            fontSize: 14,
            fontWeight: 500,
            marginBottom: 8,
          }}
        >
          图表渲染出错
        </p>
        <pre style={{ fontSize: 12, color: "#ef4444", whiteSpace: "pre-wrap" }}>
          {error}
        </pre>
        <details style={{ marginTop: 8 }}>
          <summary
            style={{ fontSize: 12, color: "#6b7280", cursor: "pointer" }}
          >
            显示源码
          </summary>
          <pre
            style={{
              marginTop: 8,
              padding: 8,
              background: "#f4f4f5",
              borderRadius: 4,
              fontSize: 12,
              overflowX: "auto",
              color: "rgba(0,0,0,0.88)",
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
        className={className}
        style={{
          margin: "16px 0",
          borderRadius: 12,
          border: "1px solid #e4e4e7",
          background: "rgba(244,244,245,0.5)",
          padding: "12px 16px",
          fontSize: 14,
          color: "#6b7280",
        }}
      >
        正在渲染图表…
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        margin: "24px 0",
        display: "flex",
        justifyContent: "center",
        overflowX: "auto",
      }}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
};

export default Mermaid;
