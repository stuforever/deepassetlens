// 逐行移植自源仓 web/components/chat/preview/previewers/MarkdownPreview.tsx。
// 差异：去 "use client"；lucide Loader2 → antd LoadingOutlined；t() → 中文；
// 源仓复用其 MarkdownRenderer，tupu 侧直接用已有 react-markdown + remark-gfm。

import { LoadingOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useTextSource } from "./useTextSource";

/**
 * Markdown preview that reuses the chat's main MarkdownRenderer (math,
 * tables, code highlight, mermaid all auto-detected).
 */
export default function MarkdownPreview({ url }: { url: string }) {
  const state = useTextSource(url);

  if (state.kind === "loading") {
    return (
      <div className="flex h-full items-center justify-center gap-2 text-[12px] text-[var(--muted-foreground)]">
        <LoadingOutlined spin style={{ fontSize: 14 }} />
        <span>正在加载预览…</span>
      </div>
    );
  }

  if (state.kind === "error") {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center text-[12px] text-[var(--muted-foreground)]">
        {state.message}
      </div>
    );
  }

  return (
    <div className="px-6 py-5">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{state.text}</ReactMarkdown>
    </div>
  );
}
