// 逐行移植自源仓 web/components/chat/preview/previewers/OfficeTextPreview.tsx。
// 差异：去 "use client"；lucide Info/Loader2 → antd 图标；t() → 中文。

import { InfoCircleOutlined, LoadingOutlined } from "@ant-design/icons";
import FallbackPreview from "./FallbackPreview";
import { useTextSource } from "./useTextSource";

/**
 * DOCX / XLSX / PPTX preview using the backend-extracted plain text. Browsers
 * cannot natively render OOXML and we choose not to ship mammoth.js / sheetjs
 * to keep the bundle slim. Showing the extracted text doubles as "see what
 * the LLM read", which is itself useful in a study tool.
 */
export default function OfficeTextPreview({
  filename,
  extractedText,
  extractedTextUrl,
  url,
}: {
  filename: string;
  extractedText: string | undefined;
  extractedTextUrl?: string | null;
  url: string | null;
}) {
  const state = useTextSource(
    extractedText ? null : extractedTextUrl || null,
    extractedText,
  );

  if (!extractedText && !extractedTextUrl) {
    return <FallbackPreview filename={filename} url={url} />;
  }

  if (state.kind === "loading") {
    return (
      <div className="flex h-full items-center justify-center gap-2 text-[12px] text-[var(--muted-foreground)]">
        <LoadingOutlined spin style={{ fontSize: 14 }} />
        <span>正在加载预览…</span>
      </div>
    );
  }

  if (state.kind === "error") {
    return <FallbackPreview filename={filename} url={url} />;
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-start gap-2 border-b border-[var(--border)] bg-[var(--muted)]/40 px-5 py-2.5 text-[11px] text-[var(--muted-foreground)]">
        <InfoCircleOutlined
          style={{ fontSize: 13 }}
          className="mt-px shrink-0"
        />
        <p>
          以下是提取出的纯文本，也是助手实际读取的内容。如需查看完整排版，请下载原文件。
        </p>
      </div>
      <div className="flex-1 overflow-y-auto px-6 py-5">
        <pre className="whitespace-pre-wrap break-words font-sans text-[13px] leading-relaxed text-[var(--foreground)]">
          {state.text}
        </pre>
      </div>
    </div>
  );
}
