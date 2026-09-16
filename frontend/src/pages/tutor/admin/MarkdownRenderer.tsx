/**
 * 等价替换 stub（非 1:1）：原仓 web/components/common/MarkdownRenderer.tsx 走
 * Simple/Rich 双渲染器链，Rich 链依赖 katex / mermaid / rehype-raw / next/dynamic
 * 等本仓不存在的依赖（禁止新增 npm 依赖），故按"最小等价"用本仓已有的
 * react-markdown + remark-gfm 实现（与 frontend/src/components/conversation/
 * AssistantCanvas.tsx 同一套约定）。
 * 保留原 props 契约：content/className/variant/enableMath/enableCode/
 * enableMermaid/allowHtml/trackSourceLines 全部可传；富渲染开关在 stub 中仅
 * 接收不生效（数学/mermaid/内嵌 HTML 以源码文本或代码块呈现）。tupu 使用面
 * （BookChatPanel → AssistantResponse → prose/trace 变体）覆盖普通 markdown、
 * 表格、代码块，视觉与原仓 Simple 变体一致。
 */
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export interface MarkdownRendererProps {
  content: string;
  className?: string;
  variant?: "default" | "compact" | "prose" | "trace";
  enableMath?: boolean;
  enableCode?: boolean;
  enableMermaid?: boolean;
  allowHtml?: boolean;
  /** 见原仓说明：编辑器滚动同步用；stub 中仅接收不生效。 */
  trackSourceLines?: boolean;
}

export default function MarkdownRenderer({
  content,
  className = "",
}: MarkdownRendererProps) {
  return (
    <div className={className} style={{ minWidth: 0 }}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          pre: ({ children }) => (
            <pre
              style={{
                background: "#f4f4f5",
                border: "1px solid #e4e4e7",
                borderRadius: 8,
                padding: "8px 12px",
                overflowX: "auto",
                fontSize: 13,
                lineHeight: 1.6,
                margin: "8px 0",
              }}
            >
              {children}
            </pre>
          ),
          code: ({ children }) => (
            <code
              style={{
                fontFamily:
                  "ui-monospace, SFMono-Regular, Consolas, 'Courier New', monospace",
              }}
            >
              {children}
            </code>
          ),
          a: ({ children, href }) => (
            <a href={href} target="_blank" rel="noreferrer">
              {children}
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
