/**
 * H5ExportButtons — H5 导出按钮（M25 三年级上批次 T20，验收判例 5）。
 * 原仓 app/h5/learn/export-buttons.tsx 1:1 移植。
 * 等价替换：删除 "use client"；apiUrl(x) 脱壳为 x 相对路径；
 * lucide（Download/FileText）→ @ant-design/icons（DownloadOutlined/FileTextOutlined）；
 * Tailwind → 内联样式逐项对位（print:hidden / active:* 伪类无法内联，已省略）。
 *
 * 双按钮 PDF/Word 触达 T16 导出端点（GET /self-learning/chapter/{id}/export），
 * 复用 withU 组装 u 参数（验收判例 6 门禁语义）。章节级传 chapterId；
 * 教材级（原文页）传 textbookId（端点 textbook_id 直通全书页导出）。
 */

import { DownloadOutlined, FileTextOutlined } from "@ant-design/icons";
import { withU } from "../h5shared/h5Utils";

// P3-B：会话解锁的访问码只在 H5Shell 的 fetch 补丁里注入 X-Access-Code，
// <a download> 导航不经 fetch → 必须显式拼 code 参数（审查 R1-必修3：
// 设码用户三处导出曾全 401）。
function getH5Code(): string {
  try {
    return sessionStorage.getItem("dsh_h5_code") || "";
  } catch {
    return "";
  }
}

export function H5ExportButtons({ chapterId, textbookId, tab }: {
  chapterId?: string;
  textbookId?: string;
  tab: string;
}) {
  const mk = (format: "pdf" | "docx") => {
    const params = new URLSearchParams({ tab, format });
    if (tab === "exercise") params.set("answer_sheet", "0");
    if (textbookId) params.set("textbook_id", textbookId);
    const code = getH5Code();
    if (code) params.set("code", code);
    const cid = encodeURIComponent(chapterId || "-");
    return withU(`/api/v1/self-learning/chapter/${cid}/export?${params.toString()}`);
  };

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }} data-testid="h5-export-buttons">
      <a
        href={mk("pdf")}
        download
        data-testid="export-pdf"
        style={{
          display: "inline-flex", alignItems: "center", gap: 4, padding: "4px 10px",
          borderRadius: 9999, border: "1px solid #e2e8f0", background: "#fff",
          fontSize: 12, color: "#475569", textDecoration: "none",
        }}
      >
        <FileTextOutlined style={{ fontSize: 14 }} /> PDF
      </a>
      <a
        href={mk("docx")}
        download
        data-testid="export-docx"
        style={{
          display: "inline-flex", alignItems: "center", gap: 4, padding: "4px 10px",
          borderRadius: 9999, border: "1px solid #e2e8f0", background: "#fff",
          fontSize: 12, color: "#475569", textDecoration: "none",
        }}
      >
        <DownloadOutlined style={{ fontSize: 14 }} /> Word
      </a>
    </div>
  );
}
