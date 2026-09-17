/**
 * Co-Writer 编辑页专用 MarkdownRenderer——移植自原仓
 * web/components/common/MarkdownRenderer.tsx（113 行）+ 其 Simple/Rich 渲染链中
 * 本页实际消费的能力面（prose/trace 变体、trackSourceLines 行号追踪）。
 *
 * 为什么不直接复用 admin/MarkdownRenderer.tsx：该件是"最小等价 stub"，
 * trackSourceLines 仅接收不生效，而 Co-Writer 编辑器的行锚定滚动同步
 * （editor mirror ↔ preview [data-source-line] 分段线性插值）依赖该属性
 * 真实存在于预览的块级元素上（1:1 复刻纪律，滚动同步属页面核心功能）。
 *
 * 替换点（登记）：
 * - "use client"/next/dynamic 删除（tupu 直接 import，无 SSR 分层）；
 * - Rich 链依赖 katex/mermaid/rehype-raw 等本仓不存在的依赖（禁止新增 npm
 *   依赖），按 admin/MarkdownRenderer.tsx 批8 先例降级为 react-markdown +
 *   remark-gfm 单链；enableMath/enableCode/enableMermaid/allowHtml 保留接收
 *   不生效（数学/mermaid/内嵌 HTML 以源码文本或代码块呈现）；
 * - trackSourceLines 真实生效：与原仓 RichMarkdownRenderer.sourceLineAttr
 *   同语义——块级元素输出 data-source-line=node.position.start.line（remark
 *   AST 起始行）；该模式下不做任何会改变行数的规范化（原仓同决策：
 *   "render the raw"）；
 * - Tailwind prose/trace 变体 → 内联样式逐项对位（CSS 变量带 fallback，
 *   NotebookPage 先例）；urlTransform 用 react-markdown 默认清洗（安全语义
 *   等价，原仓自定义白名单属聊天引用链路，本页不消费）。
 */
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { CSSProperties, ReactNode } from "react";

export interface MarkdownRendererProps {
  content: string;
  className?: string;
  variant?: "default" | "compact" | "prose" | "trace";
  enableMath?: boolean;
  enableCode?: boolean;
  enableMermaid?: boolean;
  allowHtml?: boolean;
  /**
   * When true, top-level block elements receive a `data-source-line` attribute
   * pointing at their starting line in the original markdown source. Useful for
   * editor/preview scroll synchronization.（原仓注释逐字保留）
   */
  trackSourceLines?: boolean;
}

type HastNode = { position?: { start?: { line?: number } } } | null | undefined;

// 原仓 RichMarkdownRenderer.sourceLineAttr 逐字语义。
function sourceLineAttr(node: HastNode): { "data-source-line"?: number } {
  const line = node?.position?.start?.line;
  if (typeof line === "number" && Number.isFinite(line)) {
    return { "data-source-line": line };
  }
  return {};
}

const FG = "var(--foreground, rgba(0, 0, 0, 0.88))";
const MUTED_FG = "var(--muted-foreground, rgba(0, 0, 0, 0.45))";
const BORDER = "var(--border, #d9d9d9)";
const MUTED = "var(--muted, #f5f5f5)";
const PRIMARY = "var(--primary, #1677ff)";
const CARD_BG = "var(--card, #ffffff)";

const MONO_FONT =
  "ui-monospace, SFMono-Regular, Consolas, 'Courier New', monospace";

export default function MarkdownRenderer({
  content,
  className = "",
  variant = "default",
  trackSourceLines = false,
}: MarkdownRendererProps) {
  const isTrace = variant === "trace";
  // 间距对位原仓 gap：trace my-1 / compact my-2 / 其余 my-4。
  const gap = isTrace ? "4px 0" : variant === "compact" ? "8px 0" : "16px 0";

  // ── trace 变体组件集（原仓 traceComponents 逐项对位）──
  const traceComponents = {
    p: ({ children }: { children?: ReactNode }) => (
      <p style={{ margin: "0 0 6px" }}>{children}</p>
    ),
    h1: ({ children }: { children?: ReactNode }) => (
      <p style={{ margin: "0 0 6px", fontWeight: 600 }}>{children}</p>
    ),
    h2: ({ children }: { children?: ReactNode }) => (
      <p style={{ margin: "0 0 6px", fontWeight: 600 }}>{children}</p>
    ),
    h3: ({ children }: { children?: ReactNode }) => (
      <p style={{ margin: "0 0 6px", fontWeight: 600 }}>{children}</p>
    ),
    h4: ({ children }: { children?: ReactNode }) => (
      <p style={{ margin: "0 0 6px", fontWeight: 600 }}>{children}</p>
    ),
    h5: ({ children }: { children?: ReactNode }) => (
      <p style={{ margin: "0 0 6px", fontWeight: 600 }}>{children}</p>
    ),
    h6: ({ children }: { children?: ReactNode }) => (
      <p style={{ margin: "0 0 6px", fontWeight: 600 }}>{children}</p>
    ),
    strong: ({ children }: { children?: ReactNode }) => (
      <strong style={{ fontWeight: 600, color: FG }}>{children}</strong>
    ),
    em: ({ children }: { children?: ReactNode }) => (
      <em style={{ fontStyle: "italic" }}>{children}</em>
    ),
    a: ({ children }: { children?: ReactNode }) => (
      <span style={{ textDecoration: "underline", textUnderlineOffset: 2 }}>
        {children}
      </span>
    ),
    blockquote: ({ children }: { children?: ReactNode }) => (
      <div style={{ borderLeft: "1px solid currentColor", paddingLeft: 12, opacity: 0.8 }}>
        {children}
      </div>
    ),
    pre: ({ children }: { children?: ReactNode }) => <>{children}</>,
    code: ({ children }: { children?: ReactNode }) => (
      <code
        style={{
          borderRadius: 4,
          background: MUTED,
          padding: "1px 4px",
          fontFamily: MONO_FONT,
          fontSize: "0.95em",
          color: FG,
        }}
      >
        {String(children).replace(/\n$/, "")}
      </code>
    ),
    img: () => null,
    hr: () => <div style={{ margin: "4px 0", height: 1, background: "currentColor", opacity: 0.1 }} />,
    ul: ({ children }: { children?: ReactNode }) => (
      <ul style={{ margin: "4px 0", paddingLeft: 16, listStyleType: "disc" }}>{children}</ul>
    ),
    ol: ({ children }: { children?: ReactNode }) => (
      <ol style={{ margin: "4px 0", paddingLeft: 16, listStyleType: "decimal" }}>{children}</ol>
    ),
    li: ({ children }: { children?: ReactNode }) => (
      <li style={{ margin: "2px 0", paddingLeft: 0 }}>{children}</li>
    ),
    table: ({ children }: { children?: ReactNode }) =>
      children != null && children !== false ? (
        <div style={{ margin: "4px 0", overflowX: "auto", borderRadius: 4, border: `1px solid ${BORDER}80` }}>
          <table style={{ minWidth: "100%", fontSize: "inherit", borderCollapse: "collapse" }}>{children}</table>
        </div>
      ) : null,
    thead: ({ children }: { children?: ReactNode }) => (
      <thead style={{ background: `${MUTED}80` }}>{children}</thead>
    ),
    th: ({ children }: { children?: ReactNode }) => (
      <th
        style={{
          borderBottom: `1px solid ${BORDER}80`,
          padding: "2px 6px",
          textAlign: "left",
          fontWeight: 500,
        }}
      >
        {children}
      </th>
    ),
    tbody: ({ children }: { children?: ReactNode }) => <tbody>{children}</tbody>,
    td: ({ children }: { children?: ReactNode }) => (
      <td style={{ borderBottom: `1px solid ${BORDER}4d`, padding: "2px 6px" }}>{children}</td>
    ),
    tr: ({ children }: { children?: ReactNode }) => <tr>{children}</tr>,
    input: ({ type, checked }: { type?: string; checked?: boolean }) =>
      type === "checkbox" ? (
        <input type="checkbox" readOnly checked={checked} style={{ marginRight: 4, verticalAlign: "middle" }} />
      ) : null,
    progress: () => null,
    meter: () => null,
    button: () => null,
    select: () => null,
    option: () => null,
    textarea: () => null,
  };

  // ── 常规/prose 变体组件集（原仓 headingComponents + normalComponents 对位；
  //    trackSourceLines 时块级元素携带 data-source-line）──
  const headingLevel = (level: number) => {
    const sizes: Record<number, number> = { 1: 24, 2: 20, 3: 18, 4: 16, 5: 14, 6: 14 };
    // 间距对位 headingSpacing：prose mt-8 mb-4 / mt-7 mb-3 / mt-6 mb-2.5 / mt-5 mb-2 / mt-4 mb-2
    const spacing: Record<number, [number, number]> = {
      1: [32, 16],
      2: [28, 12],
      3: [24, 10],
      4: [20, 8],
      5: [16, 8],
      6: [16, 8],
    };
    const [mt, mb] = spacing[level];
    return { fontSize: sizes[level], marginTop: mt, marginBottom: mb };
  };

  const lineAttr = (node: HastNode): { "data-source-line"?: number } =>
    trackSourceLines ? sourceLineAttr(node) : {};

  const normalComponents = {
    h1: ({ node, children }: { node?: HastNode; children?: ReactNode }) => (
      <h1 style={{ ...headingLevel(1), fontWeight: 700, letterSpacing: "-0.025em", color: FG, lineHeight: 1.3 }} {...lineAttr(node)}>
        {children}
      </h1>
    ),
    h2: ({ node, children }: { node?: HastNode; children?: ReactNode }) => (
      <h2 style={{ ...headingLevel(2), fontWeight: 600, letterSpacing: "-0.025em", color: FG, lineHeight: 1.3 }} {...lineAttr(node)}>
        {children}
      </h2>
    ),
    h3: ({ node, children }: { node?: HastNode; children?: ReactNode }) => (
      <h3 style={{ ...headingLevel(3), fontWeight: 600, letterSpacing: "-0.025em", color: FG, lineHeight: 1.3 }} {...lineAttr(node)}>
        {children}
      </h3>
    ),
    h4: ({ node, children }: { node?: HastNode; children?: ReactNode }) => (
      <h4 style={{ ...headingLevel(4), fontWeight: 600, color: FG, lineHeight: 1.3 }} {...lineAttr(node)}>
        {children}
      </h4>
    ),
    h5: ({ node, children }: { node?: HastNode; children?: ReactNode }) => (
      <h5 style={{ ...headingLevel(5), fontWeight: 600, color: FG, lineHeight: 1.3 }} {...lineAttr(node)}>
        {children}
      </h5>
    ),
    h6: ({ node, children }: { node?: HastNode; children?: ReactNode }) => (
      <h6
        style={{
          ...headingLevel(6),
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.025em",
          color: MUTED_FG,
          lineHeight: 1.3,
        }}
        {...lineAttr(node)}
      >
        {children}
      </h6>
    ),
    p: ({ node, children }: { node?: HastNode; children?: ReactNode }) => (
      <p style={{ margin: "0 0 16px", color: FG }} {...lineAttr(node)}>
        {children}
      </p>
    ),
    table: ({ node, children }: { node?: HastNode; children?: ReactNode }) =>
      children != null && children !== false ? (
        <div
          style={{ overflowX: "auto", borderRadius: 8, border: `1px solid ${BORDER}`, boxShadow: "0 1px 2px rgba(0,0,0,0.05)", margin: gap }}
          {...lineAttr(node)}
        >
          <table style={{ minWidth: "100%", borderCollapse: "collapse", fontSize: 14, color: FG }}>{children}</table>
        </div>
      ) : null,
    thead: ({ children }: { children?: ReactNode }) => (
      <thead style={{ background: MUTED }}>{children}</thead>
    ),
    th: ({ children }: { children?: ReactNode }) => (
      <th
        style={{
          borderBottom: `1px solid ${BORDER}`,
          textAlign: "left",
          fontWeight: 600,
          color: FG,
          padding: isTrace ? "4px 6px" : "8px 12px",
        }}
      >
        {children}
      </th>
    ),
    tbody: ({ children }: { children?: ReactNode }) => (
      <tbody style={{ borderTop: `1px solid ${BORDER}`, background: CARD_BG }}>{children}</tbody>
    ),
    td: ({ children }: { children?: ReactNode }) => (
      <td style={{ borderBottom: `1px solid ${BORDER}`, color: MUTED_FG, padding: isTrace ? "4px 6px" : "8px 12px" }}>
        {children}
      </td>
    ),
    tr: ({ children }: { children?: ReactNode }) => <tr>{children}</tr>,
    pre: ({ node, children }: { node?: HastNode; children?: ReactNode }) => (
      <div
        style={{
          margin: gap,
          overflow: "hidden",
          borderRadius: 12,
          border: `1px solid ${BORDER}`,
          background: "#1f2937",
        }}
        {...lineAttr(node)}
      >
        <pre style={{ overflowX: "auto", padding: 16, fontSize: 14, lineHeight: 1.625, color: "#e5e7eb", margin: 0 }}>
          {children}
        </pre>
      </div>
    ),
    code: ({ children }: { children?: ReactNode }) => {
      const raw = String(children).replace(/\n$/, "");
      if (raw.includes("\n")) {
        return <code style={{ fontFamily: MONO_FONT }}>{raw}</code>;
      }
      return (
        <code
          style={{
            borderRadius: 4,
            background: MUTED,
            padding: "2px 6px",
            fontFamily: MONO_FONT,
            fontSize: "0.875em",
            color: FG,
          }}
        >
          {children}
        </code>
      );
    },
    a: ({ href, children, title }: { href?: string; children?: ReactNode; title?: string }) => (
      <a
        href={href}
        title={title}
        {...(href && (href.startsWith("http://") || href.startsWith("https://"))
          ? { target: "_blank", rel: "noopener noreferrer" }
          : {})}
        style={{ color: PRIMARY, textDecoration: "underline", textUnderlineOffset: 2 }}
      >
        {children}
      </a>
    ),
    img: ({ src, alt }: { src?: string; alt?: string }) => (
      <img src={src} alt={alt || ""} loading="lazy" style={{ margin: gap, display: "inline-block", maxWidth: "100%", borderRadius: 8, border: `1px solid ${BORDER}` }} />
    ),
    blockquote: ({ node, children }: { node?: HastNode; children?: ReactNode }) => (
      <blockquote
        style={{
          margin: gap,
          borderLeft: `3px solid ${MUTED_FG}`,
          paddingLeft: 16,
          fontStyle: "italic",
          color: MUTED_FG,
        }}
        {...lineAttr(node)}
      >
        {children}
      </blockquote>
    ),
    hr: ({ node }: { node?: HastNode }) => (
      <hr style={{ margin: gap, height: 1, border: "none", background: BORDER }} {...lineAttr(node)} />
    ),
    ul: ({ node, children }: { node?: HastNode; children?: ReactNode }) => (
      <ul style={{ margin: gap, paddingLeft: 24, listStyleType: "disc" }} {...lineAttr(node)}>
        {children}
      </ul>
    ),
    ol: ({ node, children }: { node?: HastNode; children?: ReactNode }) => (
      <ol style={{ margin: gap, paddingLeft: 24, listStyleType: "decimal" }} {...lineAttr(node)}>
        {children}
      </ol>
    ),
    li: ({ node, children }: { node?: HastNode; children?: ReactNode }) => (
      <li style={{ margin: "2px 0", color: FG }} {...lineAttr(node)}>
        {children}
      </li>
    ),
    input: ({ type, checked }: { type?: string; checked?: boolean }) =>
      type === "checkbox" ? (
        <input
          type="checkbox"
          checked={checked}
          readOnly
          style={{ marginRight: 8, width: 16, height: 16, borderRadius: 4, border: `1px solid ${BORDER}`, verticalAlign: "middle", accentColor: PRIMARY }}
        />
      ) : null,
    progress: () => null,
    meter: () => null,
    button: () => null,
    select: () => null,
    option: () => null,
    textarea: () => null,
  };

  const components = isTrace ? traceComponents : normalComponents;

  // trace 变体根样式对位：text-[11px] leading-[1.55] text-[var(--muted-foreground)]；
  // prose 变体：serif 正文（原仓 md-renderer prose max-w-none font-serif）。
  const rootStyle: CSSProperties = isTrace
    ? { maxWidth: "none", fontFamily: "sans-serif", fontSize: 11, lineHeight: 1.55, color: MUTED_FG, minWidth: 0 }
    : variant === "prose"
      ? { maxWidth: "none", fontFamily: "Georgia, 'Times New Roman', serif", fontSize: 15, lineHeight: 1.75, color: FG, minWidth: 0 }
      : { maxWidth: "none", fontFamily: "Georgia, 'Times New Roman', serif", fontSize: 14, lineHeight: 1.7, color: FG, minWidth: 0 };

  return (
    <div className={className} style={rootStyle}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
