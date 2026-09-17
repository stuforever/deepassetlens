// 逐行移植自源仓 web/components/chat/preview/previewers/PdfPreview.tsx。
// 差异：去 "use client"；lucide Loader2 → antd LoadingOutlined；t() → 中文。

import { useState } from "react";
import { LoadingOutlined } from "@ant-design/icons";
import type { FilePreviewSource } from "../previewSupport";

/**
 * PDF preview powered by the browser's built-in viewer (PDF.js in Chrome /
 * Firefox, Preview in Safari). Loads the original file from /api/attachments
 * via an <iframe> — zero extra bundle weight.
 *
 * The "load" event sometimes fires twice in WebKit because of the inline
 * UA toolbar; we only flip the loading flag on the first one.
 */
export default function PdfPreview({
  url,
  filename,
}: {
  url: string;
  filename: FilePreviewSource["filename"];
}) {
  const [loading, setLoading] = useState(true);

  return (
    <div className="relative h-full w-full bg-[var(--muted)]/30">
      {loading && (
        <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center">
          <div className="flex items-center gap-2 text-[12px] text-[var(--muted-foreground)]">
            <LoadingOutlined spin style={{ fontSize: 14 }} />
            <span>正在加载预览…</span>
          </div>
        </div>
      )}
      <iframe
        title={filename}
        src={url}
        className="h-full w-full border-0 bg-[var(--background)]"
        onLoad={() => setLoading(false)}
      />
    </div>
  );
}
