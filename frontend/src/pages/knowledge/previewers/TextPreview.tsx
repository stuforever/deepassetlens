// 逐行移植自源仓 web/components/chat/preview/previewers/TextPreview.tsx。
// 差异：去 "use client"；lucide Loader2 → antd LoadingOutlined；t() → 中文；
// 源仓 next/dynamic 动态加载 @/components/common/RichCodeBlock —— tupu 侧无该
// 组件，按同等 props（raw/lang）内联最小等宽渲染块。

import { LoadingOutlined } from "@ant-design/icons";
import { langForFilename } from "../previewSupport";
import { useTextSource } from "./useTextSource";

/**
 * Plain text + code preview. Files with a recognised code extension render
 * inside RichCodeBlock with one-dark syntax highlighting; everything else
 * falls back to a tidy monospace block.
 *
 * Language mapping lives in ``@/lib/code-languages`` — adding a new
 * highlight target is a one-line edit there.
 */
export default function TextPreview({
  url,
  filename,
}: {
  url: string;
  filename: string;
}) {
  const state = useTextSource(url);
  const lang = langForFilename(filename) ?? "text";

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
    <div className="px-4 py-4">
      <RichCodeBlock raw={state.text} lang={lang} />
    </div>
  );
}

/** tupu 内联等价：源仓 RichCodeBlock 的最小形态（等宽块 + 语言标注）。 */
function RichCodeBlock({ raw, lang }: { raw: string; lang: string }) {
  return (
    <pre
      className="overflow-auto rounded-lg border border-[var(--border)] bg-[var(--muted)]/40 p-3 font-mono text-[12px] leading-[1.7] text-[var(--foreground)]"
      data-language={lang}
    >
      {raw}
    </pre>
  );
}
