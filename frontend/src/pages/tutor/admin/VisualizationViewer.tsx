/**
 * 复刻自 DeepTutor：web/components/visualize/VisualizationViewer.tsx（整件平铺到 tupu）。
 * 替换点：
 *  - 删除 "use client" 与 react-i18next；文案按 zh/app.json 中文直出
 *    （全屏/显示代码/隐藏代码/复制代码/已复制/审阅/关闭/在新标签页打开/打开/
 *    图表渲染失败/图表渲染错误/SVG 渲染错误/无效的 SVG：不是以 <svg 开头；
 *    "SVG could not be safely rendered" 在 app.json 无对应 key，按规则语义中文→"SVG 无法安全渲染"）。
 *  - next/dynamic → React.lazy + Suspense（客户端无 SSR，等价代码分割）。
 *  - 原仓动态 import("chart.js/auto")：tupu 未安装 chart.js 且禁止新增依赖，改为
 *    运行时探测宿主全局 window.Chart（若由外部脚本加载则复用），缺失时走与原仓
 *    catch 相同的错误分支（"图表渲染错误"卡片）。mermaid 分支同理见 ./Mermaid。
 *  - lucide-react → @ant-design/icons：Code2→CodeOutlined、Copy→CopyOutlined、
 *    Check→CheckOutlined、ExternalLink→ExportOutlined、Maximize2→FullscreenOutlined、
 *    X→CloseOutlined（size={n} → fontSize:n）。
 *  - @/components/Mermaid → './Mermaid'（本目录产出）；@/lib/iframe-html → './iframe-html'；
 *    @/lib/visualize-types → './visualize-types'（并行 Agent 产出，导出名一致）。
 *  - Tailwind → antd Button + 最小内联样式；色值按任务映射（border→#e4e4e7、
 *    background→#f5f5f5、card→#fff、muted-foreground→#6b7280、red-200→#fecaca、
 *    red-50→#fef2f2、red-600→#dc2626、red-500→#ef4444）。
 *  - 交互逻辑（Escape 关闭全屏、iframe postMessage 桥、复制、portal 全屏）逐字保留。
 */
import {
  lazy,
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type MouseEvent as ReactMouseEvent,
} from "react";
import { createPortal } from "react-dom";
import {
  CodeOutlined,
  CopyOutlined,
  CheckOutlined,
  ExportOutlined,
  FullscreenOutlined,
  CloseOutlined,
} from "@ant-design/icons";
import { Button } from "antd";
import { Mermaid } from "./Mermaid";
import { prepareIframeHtml } from "./iframe-html";
import { isManimResult, type VisualizeResult } from "./visualize-types";
import "./svg-theme.css";

const MathAnimatorViewer = lazy(() => import("./MathAnimatorViewer"));

const borderColor = "#e4e4e7";
const mutedForeground = "#6b7280";
const foreground = "rgba(0,0,0,0.88)";
const iconStyle = (size: number): CSSProperties => ({ fontSize: size });

// 工具栏小按钮（原仓：border+bg+10~11px 文案的细边框按钮），antd hover 自带主色变化。
const toolbarBtnStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  borderRadius: 6,
  border: `1px solid ${borderColor}`,
  background: "#f5f5f5",
  padding: "4px 10px",
  fontSize: 11,
  fontWeight: 500,
  color: mutedForeground,
  height: "auto",
  boxShadow: "none",
};

function stripCodeFence(source: string): string {
  const trimmed = source.trim();
  const fenced = trimmed.match(
    /^```(?:json|javascript|js)?\s*([\s\S]*?)\s*```$/i,
  );
  return fenced ? fenced[1].trim() : trimmed;
}

function parseChartConfig(source: string): unknown {
  const raw = stripCodeFence(source);
  try {
    return JSON.parse(raw);
  } catch {
    const jsonish = raw
      .replace(/([{,]\s*)([A-Za-z_$][\w$]*)\s*:/g, '$1"$2":')
      .replace(/'([^'\\]*(?:\\.[^'\\]*)*)'/g, (_match, value: string) =>
        JSON.stringify(value.replace(/\\'/g, "'")),
      )
      .replace(/,\s*([}\]])/g, "$1");
    return JSON.parse(jsonish);
  }
}

type ChartCtor = new (
  ctx: HTMLCanvasElement,
  config: unknown,
) => { destroy: () => void };

// 原仓：const ChartModule = await import("chart.js/auto")。tupu 无 chart.js 依赖
// （禁止新增），改为全局探测；缺失时向上抛错走 catch 分支。
async function loadChartCtor(): Promise<ChartCtor | null> {
  const w = window as unknown as { Chart?: ChartCtor };
  return w.Chart ?? null;
}

function ChartJsRenderer({ config }: { config: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<unknown>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function render() {
      if (!canvasRef.current) return;

      try {
        const Chart = await loadChartCtor();
        if (!Chart) {
          throw new Error("图表渲染失败");
        }

        if (chartRef.current) {
          (chartRef.current as { destroy: () => void }).destroy();
          chartRef.current = null;
        }

        const parsedConfig = parseChartConfig(config);

        if (cancelled) return;

        chartRef.current = new Chart(canvasRef.current, parsedConfig);
        setError(null);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "图表渲染失败");
        }
      }
    }

    void render();

    return () => {
      cancelled = true;
      if (chartRef.current) {
        (chartRef.current as { destroy: () => void }).destroy();
        chartRef.current = null;
      }
    };
  }, [config]);

  if (error) {
    return (
      <div
        style={{
          borderRadius: 8,
          border: "1px solid #fecaca",
          background: "#fef2f2",
          padding: 16,
        }}
      >
        <p style={{ fontSize: 14, fontWeight: 500, color: "#dc2626" }}>
          {"图表渲染错误"}
        </p>
        <pre
          style={{
            marginTop: 8,
            whiteSpace: "pre-wrap",
            fontSize: 12,
            color: "#ef4444",
          }}
        >
          {error}
        </pre>
      </div>
    );
  }

  return (
    <div
      className="dt-chart-wrap"
      style={{ position: "relative", width: "100%" }}
    >
      <canvas ref={canvasRef} />
    </div>
  );
}

function HtmlRenderer({ html }: { html: string }) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [height, setHeight] = useState(560);

  const prepared = useMemo(() => prepareIframeHtml(html || ""), [html]);

  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;
    iframe.srcdoc = prepared;
  }, [prepared]);

  // Listen for the iframe bridge: a sendPrompt() call (mirror into the composer
  // via the shared window event) or a height report (grow to fit, no clipping).
  useEffect(() => {
    const onMessage = (e: MessageEvent) => {
      const iframe = iframeRef.current;
      if (!iframe || e.source !== iframe.contentWindow) return;
      const data = e.data as { type?: string; text?: string; height?: number };
      if (!data || typeof data !== "object") return;
      if (data.type === "dt:visualize-prompt" && data.text) {
        window.dispatchEvent(
          new CustomEvent("dt:visualize-prompt", { detail: data.text }),
        );
      } else if (
        data.type === "dt:visualize-height" &&
        typeof data.height === "number"
      ) {
        setHeight(Math.min(2400, Math.max(240, Math.ceil(data.height) + 8)));
      }
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  const handleOpenInNewTab = () => {
    try {
      const contentUrl = URL.createObjectURL(
        new Blob([prepared], { type: "text/html" }),
      );
      const wrapper = `<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Visualization</title><style>html,body,iframe{height:100%;width:100%;margin:0;border:0;}</style></head><body><iframe sandbox="allow-scripts" src="${contentUrl}"></iframe></body></html>`;
      const url = URL.createObjectURL(
        new Blob([wrapper], { type: "text/html" }),
      );
      window.open(url, "_blank", "noopener,noreferrer");
      setTimeout(() => {
        URL.revokeObjectURL(url);
        URL.revokeObjectURL(contentUrl);
      }, 60_000);
    } catch {
      /* no-op */
    }
  };

  return (
    <div style={{ position: "relative", width: "100%" }}>
      <Button
        type="default"
        size="small"
        onClick={handleOpenInNewTab}
        style={{
          ...toolbarBtnStyle,
          position: "absolute",
          right: 8,
          top: 8,
          zIndex: 10,
          background: "rgba(245,245,245,0.9)",
        }}
        title={"在新标签页打开"}
      >
        <ExportOutlined style={iconStyle(10)} />
        {"打开"}
      </Button>
      <iframe
        ref={iframeRef}
        title={"HTML 可视化"}
        sandbox="allow-scripts"
        style={{
          width: "100%",
          borderRadius: 8,
          border: `1px solid ${borderColor}`,
          background: "#fff",
          minHeight: 320,
          height,
        }}
      />
    </div>
  );
}

// Per-page sequence used to scope SVG ids (see the scoping block below).
let svgScopeSeq = 0;

// Sanitize an SVG string for safe inline rendering: parse as XML, strip
// script/foreign-object/event-handler vectors, then reserialize. SVGs come from
// our own LLM and already pass a backend well-formedness check, but we still
// defend against prompt-injected <script>/on* handlers. Kept dependency-free
// (same sanitize→string contract as DOMPurify, so it can be swapped later).
function sanitizeSvg(raw: string): string {
  const trimmed = raw.trim();
  if (typeof DOMParser === "undefined") return "";
  const doc = new DOMParser().parseFromString(trimmed, "image/svg+xml");
  const root = doc.documentElement;
  if (!root || root.nodeName.toLowerCase() !== "svg") return "";
  if (root.getElementsByTagName("parsererror").length > 0) return "";

  const STRIP = [
    "script",
    "foreignObject",
    "iframe",
    "object",
    "embed",
    "audio",
    "video",
    "handler",
  ];
  root.querySelectorAll(STRIP.join(",")).forEach((n) => n.remove());

  const walk = (el: Element) => {
    const tag = el.nodeName.toLowerCase();
    for (const attr of Array.from(el.attributes)) {
      const name = attr.name.toLowerCase();
      const val = attr.value.replace(/\s+/g, "").toLowerCase();
      if (name.startsWith("on")) {
        el.removeAttribute(attr.name);
      } else if (
        (name === "href" || name === "xlink:href") &&
        (val.startsWith("javascript:") ||
          (val.startsWith("data:") && !val.startsWith("data:image/")))
      ) {
        el.removeAttribute(attr.name);
      } else if (name === "style" && val.includes("javascript:")) {
        el.removeAttribute(attr.name);
      } else if (
        (tag === "set" || tag === "animate") &&
        name === "attributename" &&
        val.startsWith("on")
      ) {
        // <set attributeName="onclick" .../> can inject a handler — drop it.
        el.remove();
        return;
      }
    }
    Array.from(el.children).forEach((child) => walk(child));
  };
  walk(root);

  // Scope ids so multiple inlined SVGs on one page don't collide: marker /
  // clipPath / gradient defs are referenced via url(#id) or href="#id". A bare
  // <img> kept each SVG in its own document; inline DOM shares one namespace,
  // so without this the 2nd+ figure's arrows/gradients break.
  const ids = new Set<string>();
  root.querySelectorAll("[id]").forEach((el) => {
    const id = el.getAttribute("id");
    if (id) ids.add(id);
  });
  if (ids.size) {
    const prefix = `dtsvg${svgScopeSeq++}-`;
    const rescope = (el: Element) => {
      const ownId = el.getAttribute("id");
      if (ownId && ids.has(ownId)) el.setAttribute("id", prefix + ownId);
      for (const attr of Array.from(el.attributes)) {
        const lname = attr.name.toLowerCase();
        let v = attr.value.replace(
          /url\(\s*(['"]?)#([^)'"\s]+)\1\s*\)/g,
          (m, q, id) => (ids.has(id) ? `url(${q}#${prefix}${id}${q})` : m),
        );
        if (
          (lname === "href" || lname.endsWith(":href")) &&
          v.charAt(0) === "#" &&
          ids.has(v.slice(1))
        ) {
          v = `#${prefix}${v.slice(1)}`;
        } else if (
          lname === "aria-labelledby" ||
          lname === "aria-describedby"
        ) {
          v = v
            .split(/\s+/)
            .map((token) => (ids.has(token) ? prefix + token : token))
            .join(" ");
        }
        if (v !== attr.value) el.setAttribute(attr.name, v);
      }
      Array.from(el.children).forEach((child) => rescope(child));
    };
    rescope(root);
  }

  return root.outerHTML;
}

function SvgFigure({ svg }: { svg: string }) {
  const trimmed = svg.trim();
  const looksSvg = trimmed.startsWith("<svg") || trimmed.startsWith("<?xml");

  // Sanitize in useMemo (原仓经 dynamic ssr:false 保证客户端挂载，DOMParser 可用).
  const safe = useMemo(
    () => (looksSvg ? sanitizeSvg(trimmed) : ""),
    [looksSvg, trimmed],
  );

  if (!looksSvg || !safe) {
    return (
      <div
        style={{
          borderRadius: 8,
          border: "1px solid #fecaca",
          background: "#fef2f2",
          padding: 16,
        }}
      >
        <p style={{ fontSize: 14, fontWeight: 500, color: "#dc2626" }}>
          {"SVG 渲染错误"}
        </p>
        <pre
          style={{
            marginTop: 8,
            whiteSpace: "pre-wrap",
            fontSize: 12,
            color: "#ef4444",
          }}
        >
          {looksSvg ? "SVG 无法安全渲染" : "无效的 SVG：不是以 <svg 开头"}
        </pre>
      </div>
    );
  }

  // Inline (not <img>) so host CSS and the SVG's own <style> apply. Clicking a
  // node carrying data-prompt drops a follow-up question into the composer (via
  // a window event the chat page listens for) — prefilled, not auto-sent.
  const onSvgClick = (e: ReactMouseEvent<HTMLDivElement>) => {
    const node = (e.target as Element).closest?.("[data-prompt]");
    const prompt = node?.getAttribute("data-prompt")?.trim();
    if (prompt) {
      window.dispatchEvent(
        new CustomEvent("dt:visualize-prompt", { detail: prompt }),
      );
    }
  };

  return (
    <div
      className="dt-svg-root"
      style={{
        display: "flex",
        justifyContent: "center",
        overflowX: "auto",
      }}
      onClick={onSvgClick}
      dangerouslySetInnerHTML={{ __html: safe }}
    />
  );
}

// A model occasionally emits several <svg> blocks in one response, and the
// backend extractor concatenates everything from the first <svg to the last
// </svg> — so one code.content can hold multiple svgs with colliding ids
// (marker/gradient/clipPath). Split them and render each as its own figure,
// independently sanitized and id-scoped, instead of one malformed multi-root
// document where only the last svg's defs win.
function splitSvgBlocks(raw: string): string[] {
  const blocks = raw.match(/<svg[\s\S]*?<\/svg>/gi);
  return blocks && blocks.length ? blocks : [raw.trim()];
}

function SvgRenderer({ svg }: { svg: string }) {
  const blocks = useMemo(() => splitSvgBlocks(svg.trim()), [svg]);
  if (blocks.length <= 1) {
    return <SvgFigure svg={blocks[0] ?? svg} />;
  }
  return (
    <div style={{ display: "flex", width: "100%", flexDirection: "column", gap: 16 }}>
      {blocks.map((block, i) => (
        <SvgFigure key={i} svg={block} />
      ))}
    </div>
  );
}

type TextResult = Extract<
  VisualizeResult,
  { render_type: "svg" | "chartjs" | "mermaid" | "html" }
>;

function renderTextVisualization(result: TextResult) {
  if (result.render_type === "svg") {
    return <SvgRenderer svg={result.code.content} />;
  }
  if (result.render_type === "mermaid") {
    return <Mermaid chart={result.code.content} />;
  }
  if (result.render_type === "html") {
    return <HtmlRenderer html={result.code.content} />;
  }
  return <ChartJsRenderer config={result.code.content} />;
}

export default function VisualizationViewer({
  result,
}: {
  result: VisualizeResult;
}) {
  // All hooks must run unconditionally before any early return — React
  // requires a stable hook order across renders. The text-path body below
  // is the only consumer of these states; the manim path returns earlier
  // and ignores them.
  const [showCode, setShowCode] = useState(false);
  const [copied, setCopied] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);

  useEffect(() => {
    if (!fullscreen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setFullscreen(false);
    };
    document.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [fullscreen]);

  if (isManimResult(result)) {
    return (
      <Suspense fallback={null}>
        <MathAnimatorViewer result={result.manim} />
      </Suspense>
    );
  }

  // TypeScript narrows ``result`` to the text-only variant from here on.
  // HTML iframe already provides its own "Open in new tab" affordance; the
  // sandboxed iframe also doesn't behave well inside a re-rendered modal.
  const supportsFullscreen = result.render_type !== "html";

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(result.code.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard API may be unavailable */
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Visualization area */}
      <div
        style={{
          position: "relative",
          overflow: "hidden",
          borderRadius: 12,
          border: `1px solid ${borderColor}`,
          background: "#f5f5f5",
          ...(result.render_type === "html" ? {} : { padding: 16 }),
        }}
      >
        {supportsFullscreen && (
          <Button
            type="default"
            size="small"
            onClick={() => setFullscreen(true)}
            title={"全屏"}
            style={{
              ...toolbarBtnStyle,
              position: "absolute",
              right: 8,
              top: 8,
              zIndex: 10,
              background: "rgba(245,245,245,0.9)",
            }}
          >
            <FullscreenOutlined style={iconStyle(10)} />
            {"全屏"}
          </Button>
        )}
        {renderTextVisualization(result)}
      </div>

      {/* Toolbar */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <Button
          type="default"
          size="small"
          onClick={() => setShowCode((prev) => !prev)}
          style={toolbarBtnStyle}
        >
          <CodeOutlined style={iconStyle(12)} />
          {showCode ? "隐藏代码" : "显示代码"}
        </Button>

        <Button
          type="default"
          size="small"
          onClick={handleCopy}
          style={toolbarBtnStyle}
        >
          {copied ? (
            <CheckOutlined style={iconStyle(12)} />
          ) : (
            <CopyOutlined style={iconStyle(12)} />
          )}
          {copied ? "已复制" : "复制代码"}
        </Button>

        <span
          style={{
            marginLeft: "auto",
            fontSize: 10,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            color: "rgba(107,114,128,0.5)",
          }}
        >
          {result.render_type === "svg"
            ? "SVG"
            : result.render_type === "mermaid"
              ? `Mermaid · ${result.analysis.chart_type || "diagram"}`
              : result.render_type === "html"
                ? `HTML · ${result.analysis.chart_type || "interactive"}`
                : `Chart.js · ${result.analysis.chart_type || "chart"}`}
        </span>
      </div>

      {/* Code panel — matches the always-dark .md-code-block style used by the
          markdown renderers so a "Show code" toggle inside a chart message
          looks identical to a fenced code block in the assistant response. */}
      {showCode && (
        <div
          className="md-code-block"
          style={{
            overflow: "hidden",
            borderRadius: 12,
            border: `1px solid ${borderColor}`,
            background: "#1f2937",
          }}
        >
          <div
            style={{
              borderBottom: "1px solid rgba(255,255,255,0.1)",
              padding: "8px 12px",
              fontSize: 11,
              fontWeight: 500,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              color: "#9ca3af",
            }}
          >
            {result.code.language}
          </div>
          <pre
            style={{
              maxHeight: 320,
              overflow: "auto",
              padding: 16,
              fontSize: 13,
              lineHeight: 1.625,
              color: "#e5e7eb",
              margin: 0,
            }}
          >
            <code>{result.code.content}</code>
          </pre>
        </div>
      )}

      {/* Review notes */}
      {result.review.changed && result.review.review_notes && (
        <p style={{ fontSize: 11, color: mutedForeground }}>
          {"审阅"}: {result.review.review_notes}
        </p>
      )}

      {/* Fullscreen overlay — rendered via portal: the message bubble sits
          inside transformed/overflow ancestors (streaming animations, chat
          scroll root), which break position:fixed and put the composer above
          the overlay. document.body has neither problem. */}
      {fullscreen &&
        supportsFullscreen &&
        createPortal(
          <div
            style={{
              position: "fixed",
              inset: 0,
              zIndex: 120,
              display: "flex",
              flexDirection: "column",
              background: "rgba(0,0,0,0.85)",
              padding: 16,
              backdropFilter: "blur(4px)",
            }}
            onClick={() => setFullscreen(false)}
          >
            <div
              style={{
                marginBottom: 8,
                flexShrink: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                color: "#fff",
              }}
            >
              <div
                style={{
                  fontSize: 12,
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  opacity: 0.8,
                }}
              >
                {result.render_type === "svg"
                  ? "SVG"
                  : result.render_type === "mermaid"
                    ? `Mermaid · ${result.analysis.chart_type || "diagram"}`
                    : `Chart.js · ${result.analysis.chart_type || "chart"}`}
              </div>
              <Button
                type="default"
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  setFullscreen(false);
                }}
                title={"关闭"}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 4,
                  borderRadius: 6,
                  background: "rgba(255,255,255,0.1)",
                  borderColor: "transparent",
                  padding: "6px 10px",
                  fontSize: 11,
                  fontWeight: 500,
                  color: "#fff",
                  height: "auto",
                  boxShadow: "none",
                }}
              >
                <CloseOutlined style={iconStyle(12)} />
                {"关闭"}
              </Button>
            </div>
            {/* m-auto (not items-center/justify-center) so oversized content
                stays scrollable from its start edge instead of clipping. */}
            <div
              style={{
                display: "flex",
                flex: 1,
                overflow: "auto",
                borderRadius: 12,
                background: "#fff",
                padding: 24,
                boxShadow: "0 25px 50px -12px rgba(0,0,0,0.25)",
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div
                className="dt-viz-fullscreen"
                style={{ margin: "auto", width: "100%", maxWidth: 1600 }}
              >
                {renderTextVisualization(result)}
              </div>
            </div>
          </div>,
          document.body,
        )}
    </div>
  );
}
