/**
 * 批6 依赖补件：1:1 移植自 DeepTutor web/components/common/RichMarkdownRenderer.tsx
 * （MarkdownRenderer 分发链 Rich 半区）。替换点：
 *  - "use client" 去；next/dynamic(ssr:false) → React.lazy + <Suspense>（CRA 无 SSR，
 *    等价语义；loading → Suspense fallback）；
 *  - react-i18next → 文件内查表直出（zh/app.json 原译文）；
 *  - 依赖包已由父级安装（IA批6 N-16：react-syntax-highlighter/mermaid/remark-math/rehype-katex/rehype-raw/katex）；@ts-ignore 保留：
 *      katex（import "katex/dist/katex.min.css"）、remark-math@^6、rehype-katex@^7、
 *      rehype-raw@^7（动态 import）；
 *  - @/lib/latex → ../../lib/latex（本批 1:1 件）、@/lib/markdown-anchors →
 *    ../../lib/markdown-anchors、@/lib/markdown-display → ../../lib/markdown-display、
 *    @/components/common/InlineFileCard → ./InlineFileCard、@/components/Mermaid →
 *    ../../Mermaid、./RichCodeBlock、@/components/common/GeogebraOpenCTA → ./GeogebraOpenCTA
 *    （均本批 1:1 件；三个 lazy 子件的 gap 入参由 className 字符串改为 style 对象）；
 *  - Tailwind 类逐项换内联样式；hover/divide-y 选择器态复用与 SimpleMarkdownRenderer
 *    同名同内容的一次性 <style>（.dtmd-*，按 id 去重）；prose 排版插件降级登记同 Simple。
 * 其余逐字一致。
 */

import React, { Suspense, useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
// @ts-ignore 缺包登记：katex 未安装（见文件头）
import "katex/dist/katex.min.css";
import {
  convertFlowFenceToMermaid,
  convertSequenceFenceToMermaid,
  processMarkdownContent,
} from "../../lib/latex";
import { findCitationAnchor } from "../../lib/markdown-anchors";
import {
  citationAnchorIdFor,
  escapeUnknownHtmlTagsForDisplay,
  markdownUrlTransform,
  normalizeMarkdownForDisplay,
  safeDecodeURIComponent,
} from "../../lib/markdown-display";
import {
  InlineFileCard,
  makeFileLinkRemarkPlugin,
  parseAttachmentHref,
  useInlineFileCardContext,
} from "./InlineFileCard";
import type { MarkdownRendererProps } from "./MarkdownRenderer";
import type { Components } from "react-markdown";
import type { PluggableList } from "unified";
import type { Element } from "hast";

const SANS =
  'ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif';
const SERIF =
  'ui-serif, Georgia, Cambria, "Times New Roman", Times, serif';
const MONO =
  'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace';
const VAR_FG = "var(--foreground, #1c1816)";
const VAR_MUTED_FG = "var(--muted-foreground, #64748b)";
const VAR_BORDER = "var(--border, #e2e8f0)";
const VAR_MUTED = "var(--muted, #f1ede2)";
const VAR_CARD = "var(--card, #ffffff)";
const VAR_PRIMARY = "var(--primary, #b0501e)";
const borderMix = (pct: number) =>
  `1px solid color-mix(in srgb, ${VAR_BORDER} ${pct}%, transparent)`;

/* 一次性样式注入（与 SimpleMarkdownRenderer 同 id 同内容，加载去重）。 */
const STYLE_ID = "dt-md-renderer-css";
const MD_RENDERER_CSS = `
.dtmd-trace-p { margin: 0 0 6px; }
.dtmd-trace-p:last-child { margin-bottom: 0; }
.dtmd-divide > :not([hidden]) ~ :not([hidden]) { border-top: 1px solid ${VAR_BORDER}; }
.dtmd-tr { transition: color 0.15s ease, background-color 0.15s ease, border-color 0.15s ease, text-decoration-color 0.15s ease, fill 0.15s ease, stroke 0.15s ease; }
.dtmd-tr:hover { background: color-mix(in srgb, ${VAR_MUTED} 60%, transparent); }
.dtmd-cite { cursor: pointer; color: ${VAR_PRIMARY}; text-decoration: none; transition: color 0.15s ease; }
.dtmd-cite:hover { color: color-mix(in srgb, ${VAR_PRIMARY} 70%, transparent); text-decoration: underline; }
.dtmd-link { color: ${VAR_PRIMARY}; text-decoration: underline; text-decoration-color: color-mix(in srgb, ${VAR_PRIMARY} 40%, transparent); text-underline-offset: 2px; transition: color 0.15s ease, text-decoration-color 0.15s ease; }
.dtmd-link:hover { text-decoration-color: ${VAR_PRIMARY}; }
.dtmd-bq > p { margin-bottom: 4px; }
`;
if (typeof document !== "undefined" && !document.getElementById(STYLE_ID)) {
  const styleEl = document.createElement("style");
  styleEl.id = STYLE_ID;
  styleEl.textContent = MD_RENDERER_CSS;
  document.head.appendChild(styleEl);
}

const ZH_MESSAGES: Record<string, string> = {
  "Rendering diagram...": "正在渲染图表…",
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

function MermaidLoading() {
  return (
    <div
      style={{
        margin: "16px 0",
        borderRadius: 12,
        border: `1px solid ${VAR_BORDER}`,
        background: `color-mix(in srgb, ${VAR_MUTED} 50%, transparent)`,
        padding: "12px 16px",
        fontSize: 14,
        color: VAR_MUTED_FG,
      }}
    >
      {t("Rendering diagram...")}
    </div>
  );
}

const LazyMermaid = React.lazy(() => import("../Mermaid"));

const LazyCodeBlock = React.lazy(() => import("./RichCodeBlock"));

const GeogebraOpenCTA = React.lazy(() => import("./GeogebraOpenCTA"));

type PluginBundle = {
  remarkMath?: unknown;
  rehypeKatex?: unknown;
  rehypeRaw?: unknown;
};

function extractText(children: React.ReactNode): string {
  return React.Children.toArray(children)
    .map((child) => {
      if (typeof child === "string" || typeof child === "number") {
        return String(child);
      }

      if (React.isValidElement<{ children?: React.ReactNode }>(child)) {
        return extractText(child.props.children);
      }

      return "";
    })
    .join("");
}

function headingId(children: React.ReactNode): string | undefined {
  const text = extractText(children)
    .toLowerCase()
    .replace(/[^\w\s-]/g, "")
    .replace(/\s+/g, "-");
  return text || undefined;
}

function hasRenderableChildren(children: React.ReactNode): boolean {
  return (
    extractText(children).replace(/[\s\u200B-\u200D\uFEFF]/g, "").length > 0
  );
}

function hasRenderableDetailsBody(children: React.ReactNode): boolean {
  return React.Children.toArray(children).some((child) => {
    if (typeof child === "string" || typeof child === "number") {
      return String(child).replace(/[\s\u200B-\u200D\uFEFF]/g, "").length > 0;
    }

    if (!React.isValidElement(child)) return false;
    if (
      typeof child.type === "string" &&
      child.type.toLowerCase() === "summary"
    ) {
      return false;
    }

    return true;
  });
}

function stripLeadingHashes(children: React.ReactNode): React.ReactNode {
  const arr = React.Children.toArray(children);
  if (arr.length > 0 && typeof arr[0] === "string") {
    const cleaned = arr[0].replace(/^#{1,6}\s+/, "");
    if (cleaned !== arr[0]) return [cleaned, ...arr.slice(1)];
  }
  return children;
}

function sourceLineAttr(node: Element | undefined): { "data-source-line"?: number } {
  const line = node?.position?.start?.line;
  if (typeof line === "number" && Number.isFinite(line)) {
    return { "data-source-line": line };
  }
  return {};
}

// Scrolls only the nearest scrollable ancestor instead of every scrollable
// ancestor up to the viewport. Using `Element.scrollIntoView` here walks the
// ancestor chain and can shift outer panes that happen to be scrollable
// (e.g. when the preview container sits inside a flex layout that briefly
// gains scroll height), which manifests as the whole page jumping after a
// citation click.
function scrollAnchorIntoView(target: HTMLElement): void {
  let container: HTMLElement | null = target.parentElement;
  while (container) {
    const style = window.getComputedStyle(container);
    const overflowY = style.overflowY;
    if (
      (overflowY === "auto" || overflowY === "scroll") &&
      container.scrollHeight > container.clientHeight
    ) {
      break;
    }
    container = container.parentElement;
  }
  if (!container) {
    target.scrollIntoView({ block: "start", behavior: "smooth" });
    return;
  }
  const containerRect = container.getBoundingClientRect();
  const targetRect = target.getBoundingClientRect();
  const top = targetRect.top - containerRect.top + container.scrollTop;
  container.scrollTo({ top, behavior: "smooth" });
}

export default function RichMarkdownRenderer({
  content,
  className = "",
  variant = "default",
  enableMath = false,
  enableCode = false,
  enableMermaid = false,
  allowHtml = false,
  trackSourceLines = false,
}: MarkdownRendererProps) {
  // When `trackSourceLines` is on the consumer wants `data-source-line`
  // attributes that map back to the *original* markdown lines (e.g. for
  // editor/preview scroll sync). `normalizeMarkdownForDisplay` strips empty
  // blocks, collapses runs of blank lines, etc, all of which shift line
  // numbers and break that contract. In that mode we only escape unknown
  // pseudo-HTML tags (preserving line count) so AST positions stay faithful.
  const normalizedContent = useMemo(
    () =>
      trackSourceLines
        ? escapeUnknownHtmlTagsForDisplay(content)
        : normalizeMarkdownForDisplay(content),
    [content, trackSourceLines],
  );
  const [plugins, setPlugins] = useState<PluginBundle>({});
  const isTrace = variant === "trace";
  const gap = isTrace
    ? { margin: "4px 0" }
    : variant === "compact"
      ? { margin: "8px 0" }
      : { margin: "16px 0" };
  const cellPad = isTrace
    ? { padding: "2px 6px" }
    : variant === "compact"
      ? { padding: "6px 8px" }
      : { padding: "8px 12px" };
  const headingSpacing = variant === "compact" ? "mt-4 mb-2" : "mt-6 mb-3";
  const textColor = VAR_FG;

  useEffect(() => {
    let cancelled = false;

    async function loadPlugins() {
      const nextPlugins: PluginBundle = {};

      if (enableMath) {
        const [remarkMathModule, rehypeKatexModule] = await Promise.all([
          // @ts-ignore 缺包登记：remark-math 未安装（见文件头）
          import("remark-math"),
          // @ts-ignore 缺包登记：rehype-katex 未安装（见文件头）
          import("rehype-katex"),
        ]);
        nextPlugins.remarkMath = remarkMathModule.default;
        nextPlugins.rehypeKatex = rehypeKatexModule.default;
      }

      if (allowHtml) {
        // @ts-ignore 缺包登记：rehype-raw 未安装（见文件头）
        const rehypeRawModule = await import("rehype-raw");
        nextPlugins.rehypeRaw = rehypeRawModule.default;
      }

      if (!cancelled) {
        setPlugins(nextPlugins);
      }
    }

    void loadPlugins();

    return () => {
      cancelled = true;
    };
  }, [allowHtml, enableMath]);

  const processedContent = useMemo(() => {
    // `processMarkdownContent` aggressively rewrites the source: it expands
    // `[TOC]`, converts `flow`/`seq` fences into multi-line mermaid blocks,
    // turns `\(...\)` / `\[...\]` into multi-line `$$...$$`, and collapses
    // runs of blank lines. Every one of those transformations changes line
    // numbers, which would invalidate the source line attributes we expose
    // for scroll sync. So when `trackSourceLines` is on we render the raw
    // markdown verbatim and rely on standard fences (` ```mermaid `, `$$`).
    if (trackSourceLines) return normalizedContent;
    return enableMath || enableMermaid
      ? processMarkdownContent(normalizedContent)
      : normalizedContent;
  }, [enableMath, enableMermaid, normalizedContent, trackSourceLines]);

  const traceComponents: Components = {
    p: ({ node, ...props }) => (
      <p className="dtmd-trace-p" {...props} />
    ),
    h1: ({ node, children }) => (
      <p style={{ marginBottom: 6, fontWeight: 600 }}>{children}</p>
    ),
    h2: ({ node, children }) => (
      <p style={{ marginBottom: 6, fontWeight: 600 }}>{children}</p>
    ),
    h3: ({ node, children }) => (
      <p style={{ marginBottom: 6, fontWeight: 600 }}>{children}</p>
    ),
    h4: ({ node, children }) => (
      <p style={{ marginBottom: 6, fontWeight: 600 }}>{children}</p>
    ),
    h5: ({ node, children }) => (
      <p style={{ marginBottom: 6, fontWeight: 600 }}>{children}</p>
    ),
    h6: ({ node, children }) => (
      <p style={{ marginBottom: 6, fontWeight: 600 }}>{children}</p>
    ),
    strong: ({ node, children }) => (
      <strong style={{ fontWeight: 600, color: VAR_FG }}>
        {children}
      </strong>
    ),
    em: ({ node, children }) => <em style={{ fontStyle: "italic" }}>{children}</em>,
    a: ({ node, children }) => (
      <span style={{ textDecoration: "underline", textUnderlineOffset: 2 }}>{children}</span>
    ),
    blockquote: ({ node, children }) => (
      <div
        style={{
          borderLeft:
            "1px solid color-mix(in srgb, currentColor 20%, transparent)",
          paddingLeft: 12,
          opacity: 0.8,
        }}
      >
        {children}
      </div>
    ),
    pre: ({ children }) => <>{children}</>,
    code: ({ node, children }) => (
      <code
        style={{
          borderRadius: 4,
          background: VAR_MUTED,
          padding: "2px 4px",
          fontFamily: MONO,
          fontSize: "0.95em",
          color: `color-mix(in srgb, ${VAR_FG} 90%, transparent)`,
        }}
      >
        {String(children).replace(/\n$/, "")}
      </code>
    ),
    img: () => null,
    hr: () => <div style={{ margin: "4px 0", height: 1, background: "currentColor", opacity: 0.1 }} />,
    ul: ({ node, ...props }) => (
      <ul
        style={{
          margin: "4px 0",
          marginLeft: 16,
          paddingLeft: 0,
          listStyleType: "disc",
        }}
        {...props}
      />
    ),
    ol: ({ node, ...props }) => (
      <ol
        style={{
          margin: "4px 0",
          marginLeft: 16,
          paddingLeft: 0,
          listStyleType: "decimal",
        }}
        {...props}
      />
    ),
    li: ({ node, ...props }) => (
      <li style={{ marginTop: 2, marginBottom: 2, paddingLeft: 0 }} {...props} />
    ),
    table: ({ node, children, ...props }) =>
      hasRenderableChildren(children) ? (
        <div
          style={{
            margin: "4px 0",
            overflowX: "auto",
            borderRadius: 4,
            border: borderMix(50),
          }}
        >
          <table
            style={{ minWidth: "100%", fontSize: "inherit", borderCollapse: "collapse" }}
            {...props}
          >
            {children}
          </table>
        </div>
      ) : null,
    thead: ({ node, ...props }) => (
      <thead
        style={{
          background: `color-mix(in srgb, ${VAR_MUTED} 50%, transparent)`,
        }}
        {...props}
      />
    ),
    th: ({ node, ...props }) => (
      <th
        style={{
          borderBottom: borderMix(50),
          padding: "2px 6px",
          textAlign: "left",
          fontWeight: 500,
        }}
        {...props}
      />
    ),
    tbody: ({ node, ...props }) => <tbody {...props} />,
    td: ({ node, ...props }) => (
      <td style={{ borderBottom: borderMix(30), padding: "2px 6px" }} {...props} />
    ),
    tr: ({ node, ...props }) => <tr {...props} />,
    input: ({ node, type, ...props }) =>
      type === "checkbox" ? (
        <input
          type="checkbox"
          readOnly
          style={{ marginRight: 4, verticalAlign: "middle" }}
          {...props}
        />
      ) : null,
    progress: () => null,
    meter: () => null,
    button: () => null,
    select: () => null,
    option: () => null,
    textarea: () => null,
    details: ({ node, children }) =>
      hasRenderableDetailsBody(children) ? <div>{children}</div> : null,
    summary: ({ node, children }) =>
      hasRenderableChildren(children) ? <span>{children}</span> : null,
  };

  const lineAttr = (node: Element | undefined) =>
    trackSourceLines ? sourceLineAttr(node) : {};

  const headingComponents: Components = {
    h1: ({ node, children, className: headingClassName, ...props }) => {
      const clean = stripLeadingHashes(children);
      return (
        <h1
          id={headingId(clean)}
          className={headingClassName || undefined}
          style={{
            scrollMarginTop: 80,
            fontFamily: SANS,
            fontSize: 24,
            lineHeight: "32px",
            fontWeight: 700,
            letterSpacing: "-0.025em",
            color: textColor,
            marginTop: variant === "compact" ? 20 : 32,
            marginBottom: variant === "compact" ? 8 : 16,
          }}
          {...lineAttr(node)}
          {...props}
        >
          {clean}
        </h1>
      );
    },
    h2: ({ node, children, className: headingClassName, ...props }) => {
      const clean = stripLeadingHashes(children);
      return (
        <h2
          id={headingId(clean)}
          className={headingClassName || undefined}
          style={{
            scrollMarginTop: 80,
            fontFamily: SANS,
            fontSize: 20,
            lineHeight: "28px",
            fontWeight: 600,
            letterSpacing: "-0.025em",
            color: textColor,
            marginTop: variant === "compact" ? 16 : 28,
            marginBottom: variant === "compact" ? 8 : 12,
          }}
          {...lineAttr(node)}
          {...props}
        >
          {clean}
        </h2>
      );
    },
    h3: ({ node, children, className: headingClassName, ...props }) => {
      const clean = stripLeadingHashes(children);
      return (
        <h3
          id={headingId(clean)}
          className={headingClassName || undefined}
          style={{
            scrollMarginTop: 80,
            fontFamily: SANS,
            fontSize: 18,
            lineHeight: "28px",
            fontWeight: 600,
            letterSpacing: "-0.025em",
            color: textColor,
            marginTop: variant === "compact" ? 16 : 24,
            marginBottom: variant === "compact" ? 6 : 10,
          }}
          {...lineAttr(node)}
          {...props}
        >
          {clean}
        </h3>
      );
    },
    h4: ({ node, children, className: headingClassName, ...props }) => {
      const clean = stripLeadingHashes(children);
      return (
        <h4
          id={headingId(clean)}
          className={headingClassName || undefined}
          style={{
            scrollMarginTop: 80,
            fontFamily: SANS,
            fontSize: 16,
            lineHeight: "24px",
            fontWeight: 600,
            color: textColor,
            marginTop: variant === "compact" ? 12 : 20,
            marginBottom: variant === "compact" ? 6 : 8,
          }}
          {...lineAttr(node)}
          {...props}
        >
          {clean}
        </h4>
      );
    },
    h5: ({ node, children, className: headingClassName, ...props }) => {
      const clean = stripLeadingHashes(children);
      return (
        <h5
          id={headingId(clean)}
          className={headingClassName || undefined}
          style={{
            scrollMarginTop: 80,
            fontFamily: SANS,
            fontSize: 14,
            lineHeight: "20px",
            fontWeight: 600,
            color: textColor,
            marginTop: variant === "compact" ? 12 : 16,
            marginBottom: variant === "compact" ? 6 : 8,
          }}
          {...lineAttr(node)}
          {...props}
        >
          {clean}
        </h5>
      );
    },
    h6: ({ node, children, className: headingClassName, ...props }) => {
      const clean = stripLeadingHashes(children);
      return (
        <h6
          id={headingId(clean)}
          className={headingClassName || undefined}
          style={{
            scrollMarginTop: 80,
            fontFamily: SANS,
            fontSize: 14,
            lineHeight: "20px",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.025em",
            color: VAR_MUTED_FG,
            marginTop: variant === "compact" ? 12 : 16,
            marginBottom: variant === "compact" ? 6 : 8,
          }}
          {...lineAttr(node)}
          {...props}
        >
          {clean}
        </h6>
      );
    },
  };

  const normalComponents: Components = {
    ...headingComponents,
    p: ({ node, ...props }) => <p {...lineAttr(node)} {...props} />,
    ul: ({ node, ...props }) => <ul {...lineAttr(node)} {...props} />,
    ol: ({ node, ...props }) => <ol {...lineAttr(node)} {...props} />,
    table: ({ node, children, ...props }) =>
      hasRenderableChildren(children) ? (
        <div
          className="dtmd-divide"
          style={{
            overflowX: "auto",
            borderRadius: 8,
            border: `1px solid ${VAR_BORDER}`,
            boxShadow: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
            ...gap,
          }}
          {...lineAttr(node)}
        >
          <table
            style={{
              minWidth: "100%",
              fontSize: 14,
              lineHeight: "20px",
              borderCollapse: "collapse",
            }}
            {...props}
          >
            {children}
          </table>
        </div>
      ) : null,
    thead: ({ node, ...props }) => (
      <thead style={{ background: VAR_MUTED }} {...props} />
    ),
    th: ({ node, ...props }) => (
      <th
        style={{
          borderBottom: `1px solid ${VAR_BORDER}`,
          textAlign: "left",
          fontWeight: 600,
          color: VAR_FG,
          ...cellPad,
        }}
        {...props}
      />
    ),
    tbody: ({ node, ...props }) => (
      <tbody className="dtmd-divide" style={{ background: VAR_CARD }} {...props} />
    ),
    td: ({ node, ...props }) => (
      <td
        style={{
          borderBottom: `1px solid ${VAR_BORDER}`,
          color: VAR_MUTED_FG,
          ...cellPad,
        }}
        {...props}
      />
    ),
    tr: ({ node, ...props }) => <tr className="dtmd-tr" {...props} />,
    pre: ({ children }) => <>{children}</>,
    code: ({ node, className: blockClassName, children, ...props }) => {
      const raw = String(children).replace(/\n$/, "");
      const langMatch = /language-([A-Za-z0-9_+#.-]+)/.exec(
        blockClassName || "",
      );
      const lang = langMatch?.[1]?.toLowerCase() || "";
      const isMultiline = raw.includes("\n");
      const lineProps = isMultiline ? lineAttr(node) : {};

      if (lang === "mermaid" && enableMermaid) {
        return (
          <div {...lineProps}>
            <Suspense fallback={<MermaidLoading />}>
              <LazyMermaid chart={raw} style={gap} />
            </Suspense>
          </div>
        );
      }

      // editor.md style fences. With `trackSourceLines` the preprocess
      // pipeline is bypassed (it would shift line numbers), so the raw
      // fence reaches us here and we convert at render time instead.
      if (
        (lang === "flow" || lang === "seq" || lang === "sequence") &&
        enableMermaid
      ) {
        const converted =
          lang === "flow"
            ? convertFlowFenceToMermaid(raw)
            : convertSequenceFenceToMermaid(raw);
        if (converted) {
          return (
            <div {...lineProps}>
              <Suspense fallback={<MermaidLoading />}>
                <LazyMermaid chart={converted} style={gap} />
              </Suspense>
            </div>
          );
        }
      }

      if (lang === "ggbscript" && enableCode) {
        // Backend emits ```ggbscript[page_id;title]. We don't render the
        // applet inline anymore — the chat answer stays text-only and we
        // surface a CTA card. Clicking it opens (or focuses) a GeoGebra
        // tab inside the right-hand SessionViewerPanel where the user can
        // interact with the figure without the chat scroll fighting it.
        const metaMatch = /language-ggbscript\[([^;\]]*)(?:;([^\]]*))?\]/.exec(
          blockClassName || "",
        );
        const ggbPayloadId = metaMatch?.[1]?.trim() || undefined;
        const ggbTitle = metaMatch?.[2]?.trim() || undefined;
        return (
          <div {...lineProps}>
            <Suspense fallback={null}>
              <GeogebraOpenCTA
                script={raw}
                payloadId={ggbPayloadId}
                title={ggbTitle}
                style={gap}
              />
            </Suspense>
          </div>
        );
      }

      // Route every multi-line block through the rich code block so the
      // indented (no-language) variant still gets a polished, consistent
      // theme instead of the washed-out fallback panel.
      if (isMultiline && enableCode) {
        return (
          <div {...lineProps}>
            <Suspense fallback={null}>
              <LazyCodeBlock raw={raw} lang={lang || "text"} style={gap} />
            </Suspense>
          </div>
        );
      }

      if (lang && enableCode) {
        return (
          <Suspense fallback={null}>
            <LazyCodeBlock raw={raw} lang={lang} style={gap} />
          </Suspense>
        );
      }

      if (isMultiline) {
        // Code-block appearance settings apply only when rich code rendering is enabled.
        // This static fallback keeps disabled-code surfaces readable without
        // silently applying syntax theme, line-number, or wrapping preferences.
        return (
          <div
            className="md-code-block"
            style={{
              overflow: "hidden",
              borderRadius: 12,
              border: `1px solid ${VAR_BORDER}`,
              background: "#1f2937",
              ...gap,
              ...lineProps,
            }}
          >
            <pre
              style={{
                overflowX: "auto",
                padding: 16,
                fontSize: 14,
                lineHeight: 1.625,
                color: "#e5e7eb",
                margin: 0,
              }}
            >
              <code className="md-code-block__code" {...props}>
                {raw}
              </code>
            </pre>
          </div>
        );
      }

      return (
        <code
          className="md-inline-code"
          style={{
            borderRadius: 4,
            background: VAR_MUTED,
            padding: "2px 6px",
            fontFamily: MONO,
            fontSize: "0.875em",
            color: VAR_FG,
          }}
          {...props}
        >
          {children}
        </code>
      );
    },
    a: ({ node, href, children, title, ...props }) => {
      const attachmentName = parseAttachmentHref(href);
      if (attachmentName) {
        return <InlineFileCard name={attachmentName} fallback={children} />;
      }
      const isCitation = title === "citation";
      const isHashLink = href?.startsWith("#");
      const external =
        href?.startsWith("http://") || href?.startsWith("https://");

      if (isCitation) {
        const label = extractText(children);
        const ids = label.split(/\s*,\s*/);
        const scrollToRef = (event: React.MouseEvent, id?: string) => {
          event.preventDefault();
          const target = findCitationAnchor(href, id);
          if (target) scrollAnchorIntoView(target);
        };
        return (
          <span
            className="citation-group"
            style={{
              margin: "0 2px",
              fontSize: "0.78em",
              lineHeight: 1.375,
              color: VAR_MUTED_FG,
            }}
            {...props}
          >
            [
            {ids.map((id, idx) => {
              const prefixMatch = id.match(/^(web|rag|code|src)-/);
              const prefix = prefixMatch?.[1] ?? "";
              const num =
                prefix && prefixMatch ? id.slice(prefixMatch[0].length) : id;
              const citationAnchor = citationAnchorIdFor(id);
              return (
                <React.Fragment key={`${id}-${idx}`}>
                  {idx > 0 && ", "}
                  <a
                    href={citationAnchor ? `#${citationAnchor}` : href}
                    onClick={(event) => scrollToRef(event, id)}
                    className="dtmd-cite"
                  >
                    {prefix ? (
                      <>
                        <span
                          style={{
                            fontSize: "0.85em",
                            fontWeight: 600,
                            textTransform: "uppercase",
                            letterSpacing: "0.025em",
                          }}
                        >
                          {prefix}
                        </span>
                        {num}
                      </>
                    ) : (
                      num
                    )}
                  </a>
                </React.Fragment>
              );
            })}
            ]
          </span>
        );
      }

      return (
        <a
          href={href}
          {...(external
            ? { target: "_blank", rel: "noopener noreferrer" }
            : {})}
          onClick={(event) => {
            if (!isHashLink || !href) return;

            event.preventDefault();
            const targetId = safeDecodeURIComponent(href.slice(1));
            const target = document.getElementById(targetId);
            if (target) scrollAnchorIntoView(target);
          }}
          className="dtmd-link"
          {...props}
        >
          {children}
        </a>
      );
    },
    img: ({ node, src, alt, ...props }) => (
      <img
        src={src}
        alt={alt || ""}
        loading="lazy"
        style={{
          display: "inline-block",
          maxWidth: "100%",
          borderRadius: 8,
          border: `1px solid ${VAR_BORDER}`,
          ...gap,
        }}
        {...lineAttr(node)}
        {...props}
      />
    ),
    blockquote: ({ node, ...props }) => (
      <blockquote
        className="dtmd-bq"
        style={{
          borderLeft: `3px solid ${VAR_MUTED_FG}`,
          paddingLeft: 16,
          fontStyle: "italic",
          color: VAR_MUTED_FG,
          ...gap,
        }}
        {...lineAttr(node)}
        {...props}
      />
    ),
    hr: ({ node, ...props }) => (
      <hr
        style={{ height: 1, border: "none", background: VAR_BORDER, ...gap }}
        {...lineAttr(node)}
        {...props}
      />
    ),
    input: ({ node, type, checked, ...props }) =>
      type === "checkbox" ? (
        <input
          type="checkbox"
          checked={checked ?? false}
          readOnly
          style={{
            marginRight: 8,
            width: 16,
            height: 16,
            borderRadius: 4,
            border: `1px solid ${VAR_BORDER}`,
            verticalAlign: "middle",
            accentColor: VAR_PRIMARY,
          }}
          {...props}
        />
      ) : null,
    progress: () => null,
    meter: () => null,
    button: () => null,
    select: () => null,
    option: () => null,
    textarea: () => null,
    details: ({ node, children, ...props }) =>
      hasRenderableDetailsBody(children) ? (
        <details
          style={{
            borderRadius: 8,
            border: `1px solid ${VAR_BORDER}`,
            background: VAR_CARD,
            padding: "8px 16px",
            ...gap,
          }}
          {...props}
        >
          {children}
        </details>
      ) : null,
    summary: ({ node, children, ...props }) =>
      hasRenderableChildren(children) ? (
        <summary
          style={{
            cursor: "pointer",
            userSelect: "none",
            fontWeight: 500,
            color: VAR_FG,
          }}
          {...props}
        >
          {children}
        </summary>
      ) : null,
  };

  const components = useMemo(
    () => (isTrace ? traceComponents : normalComponents),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- components only change with variant/feature flags
    [isTrace, variant, enableMermaid, enableCode, trackSourceLines],
  );

  // 根样式（原 tailwind rootClasses 的内联等价；prose 排版插件降级登记见文件头）。
  const rootStyle: React.CSSProperties = isTrace
    ? {
        maxWidth: "none",
        fontFamily: SANS,
        fontSize: 11,
        lineHeight: 1.55,
        color: VAR_MUTED_FG,
      }
    : { maxWidth: "none", fontFamily: SERIF };

  // Linkify exact generated-filename mentions in the assistant's prose into
  // clickable file links (no-op outside a chat message — fileCtx is null).
  const fileCtx = useInlineFileCardContext();
  const fileLinkPlugin = useMemo(
    () => makeFileLinkRemarkPlugin(fileCtx?.files ?? []),
    [fileCtx?.files],
  );
  const remarkPlugins = useMemo(() => {
    const p: PluggableList = [remarkGfm];
    if (plugins.remarkMath) p.push(plugins.remarkMath as never);
    if (fileLinkPlugin) p.push(fileLinkPlugin as never);
    return p;
  }, [plugins.remarkMath, fileLinkPlugin]);

  const rehypePlugins = useMemo(() => {
    const p: PluggableList = [];
    if (allowHtml && plugins.rehypeRaw) p.push(plugins.rehypeRaw as never);
    if (enableMath && plugins.rehypeKatex) p.push(plugins.rehypeKatex as never);
    return p;
  }, [allowHtml, enableMath, plugins.rehypeRaw, plugins.rehypeKatex]);

  return (
    <div
      className={`md-renderer ${variant === "prose" ? "prose" : variant === "default" ? "prose prose-sm" : ""} ${className}`}
      style={rootStyle}
    >
      <ReactMarkdown
        remarkPlugins={remarkPlugins}
        rehypePlugins={rehypePlugins}
        components={components}
        urlTransform={markdownUrlTransform}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  );
}
