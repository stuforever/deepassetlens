// 逐行移植自源仓 web/components/chat/preview/previewers/FallbackPreview.tsx。
// 差异：去 "use client"；lucide Download/FileQuestion → antd 图标；t() → 中文；
// docIconFor 改从 '../previewSupport'（antd 图标等价映射）。

import { DownloadOutlined, FileUnknownOutlined } from "@ant-design/icons";
import { docIconFor } from "../previewSupport";

/**
 * Last-resort preview: a centred icon + filename + Download CTA. Used for
 * encrypted PDFs we cannot iframe, exotic binary formats, or attachments
 * predating the storage rollout where the URL is missing.
 */
export default function FallbackPreview({
  filename,
  url,
  reason,
}: {
  filename: string;
  url: string | null;
  reason?: "legacy" | "unsupported";
}) {
  const spec = docIconFor(filename);
  const Icon = url ? spec.Icon : FileUnknownOutlined;
  const tint = url ? spec.tint : "text-[var(--muted-foreground)]";

  return (
    <div className="flex h-full w-full flex-col items-center justify-center gap-4 p-8 text-center">
      <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-[var(--muted)]/60">
        <Icon style={{ fontSize: 40 }} className={tint} />
      </div>
      <div className="space-y-1">
        <div className="text-[14px] font-medium text-[var(--foreground)]">
          {filename}
        </div>
        <div className="text-[12px] text-[var(--muted-foreground)]">
          {reason === "legacy"
            ? "原始文件未保存（消息发送于预览功能上线之前）。"
            : "暂不支持预览此类文件。"}
        </div>
      </div>
      {url && (
        <a
          href={url}
          download={filename}
          className="inline-flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--card)] px-3 py-1.5 text-[12px] font-medium text-[var(--muted-foreground)] transition-colors hover:border-[var(--primary)]/40 hover:text-[var(--primary)]"
        >
          <DownloadOutlined style={{ fontSize: 13 }} />
          下载
        </a>
      )}
    </div>
  );
}
