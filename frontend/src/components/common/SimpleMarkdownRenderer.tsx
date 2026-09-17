/**
 * 批6 依赖补件：1:1 移植自 DeepTutor web/components/common/SimpleMarkdownRenderer.tsx
 * （MarkdownRenderer 分发链 Simple 半区）。替换点：
 *  - "use client" 去；
 *  - @/lib/markdown-anchors → ../../lib/markdown-anchors、@/lib/markdown-display →
 *    ../../lib/markdown-display（均为既有/本批 1:1 件）、@/components/common/InlineFileCard →
 *    ./InlineFileCard（本批 1:1 件）；
 *  - Tailwind 类逐项换内联样式；hover/:last-child/divide-y 等选择器态由本文件注入的一次性
 *    <style> 承载（.dtmd-* 作用域类）；间距/字号按 tailwind 数值表逐项换算
 *    （my-1=4px、my-2=8px、my-4=16px、px-1.5=6px、py-1=4px、rounded=4px、rounded-lg=8px、
 *    rounded-xl=12px、text-sm=14px/20px 等）。
 *  - 【降级登记】prose 排版插件（@tailwindcss/typography）不在本仓复刻：根节点保留
 *    md-renderer/prose 类名与 font-serif/max-w-none 内联样式，正文块间距由浏览器 UA
 *    样式承载；chat/home TracePanels 的 variant="trace" 路径不受影响（trace 不走 prose）。
 * 其余逐字一致。
 */

import React, { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { findCitationAnchor } from "../../lib/markdown-anchors";
import {
  citationAnchorIdFor,
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

/* ---- 移植辅助：tailwind 值换算常量与选择器样式注入 ---- */
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

export default function SimpleMarkdownRenderer({
  content,
  className = "",
  variant = "default",
}: MarkdownRendererProps) {
  const normalizedContent = useMemo(
    () => normalizeMarkdownForDisplay(content),
    [content],
  );
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
          color: VAR_FG,
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
          {...props}
        >
          {clean}
        </h6>
      );
    },
  };

  const normalComponents: Components = {
    ...headingComponents,
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
    code: ({ node, children, ...props }) => {
      const raw = String(children).replace(/\n$/, "");

      if (raw.includes("\n")) {
        // Compatibility fallback: keep multiline code readable when rich
        // rendering is unavailable. This intentionally does not consume the
        // code-block theme registry or line-number/wrapping settings; those
        // apply only through RichCodeBlock when rich code rendering is enabled.
        return (
          <div
            className="md-code-block"
            style={{
              overflow: "hidden",
              borderRadius: 12,
              border: `1px solid ${VAR_BORDER}`,
              background: "#1f2937",
              ...gap,
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
          target?.scrollIntoView({ block: "start", behavior: "smooth" });
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
            target?.scrollIntoView({ block: "start", behavior: "smooth" });
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
        {...props}
      />
    ),
    hr: ({ node, ...props }) => (
      <hr
        style={{ height: 1, border: "none", background: VAR_BORDER, ...gap }}
        {...props}
      />
    ),
    input: ({ node, type, checked, ...props }) =>
      type === "checkbox" ? (
        <input
          type="checkbox"
          checked={checked}
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
    // eslint-disable-next-line react-hooks/exhaustive-deps -- components only change with variant
    [isTrace, variant],
  );

  // Linkify exact generated-filename mentions in the assistant's prose into
  // clickable file links (no-op outside a chat message — fileCtx is null).
  const fileCtx = useInlineFileCardContext();
  const fileLinkPlugin = useMemo(
    () => makeFileLinkRemarkPlugin(fileCtx?.files ?? []),
    [fileCtx?.files],
  );
  const remarkPlugins = useMemo(
    () => (fileLinkPlugin ? [remarkGfm, fileLinkPlugin] : [remarkGfm]),
    [fileLinkPlugin],
  );

  // 根样式（原 tailwind rootClasses 的内联等价）。
  const rootStyle: React.CSSProperties = isTrace
    ? {
        maxWidth: "none",
        fontFamily: SANS,
        fontSize: 11,
        lineHeight: 1.55,
        color: VAR_MUTED_FG,
      }
    : { maxWidth: "none", fontFamily: SERIF };

  return (
    <div
      className={`md-renderer ${variant === "prose" ? "prose" : variant === "default" ? "prose prose-sm" : ""} ${className}`}
      style={rootStyle}
    >
      <ReactMarkdown
        remarkPlugins={remarkPlugins}
        components={components}
        urlTransform={markdownUrlTransform}
      >
        {normalizedContent}
      </ReactMarkdown>
    </div>
  );
}
