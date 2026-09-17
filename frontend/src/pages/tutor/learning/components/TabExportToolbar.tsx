"use client";

/**
 * TabExportToolbar — 桌面 10 tab 通用导出工具栏（M25 三年级上批次 T19）。
 *
 * 三按钮：🖨 window.print()（配合 globals.css @media print 只渲染当前
 * tab 内容——h5 share 打印卡片先例）；PDF/Word 走 <a download> 触达
 * T16 导出端点 GET /self-learning/chapter/{cid}/export。
 * exercise tab 另有答题卡版式切换（学生版/家长版，answer_sheet=0/1，
 * 验收判例 3）；其他 tab 不展示切换（端点忽略该参数）。
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Download, FileText, Printer } from "lucide-react";
import { apiUrl } from "../../../../lib/api";
import { getH5User } from "../../../../lib/h5-utils";

export function TabExportToolbar({ chapterId, tab }: {
  chapterId: string;
  tab: string;
}) {
  const { t } = useTranslation();
  const [answerSheet, setAnswerSheet] = useState(false);
  const u = getH5User();

  const exportUrl = (format: "pdf" | "docx") => {
    const params = new URLSearchParams({ tab, format });
    if (tab === "exercise") params.set("answer_sheet", answerSheet ? "1" : "0");
    if (u) params.set("u", u);
    return apiUrl(
      `/api/v1/self-learning/chapter/${encodeURIComponent(chapterId)}/export?${params.toString()}`,
    );
  };

  return (
    <div
      className="flex items-center gap-2 print:hidden"
      data-testid="tab-export-toolbar"
    >
      <button
        onClick={() => window.print()}
        data-testid="print-btn"
        className="px-2.5 py-1 text-xs rounded border hover:bg-accent inline-flex items-center gap-1 text-muted-foreground"
        title={t("Print current tab")}
      >
        <Printer className="w-3.5 h-3.5" /> {t("Print")}
      </button>
      <a
        href={exportUrl("pdf")}
        download
        data-testid="export-pdf"
        className="px-2.5 py-1 text-xs rounded border hover:bg-accent inline-flex items-center gap-1 text-muted-foreground"
        title={t("Export as PDF")}
      >
        <FileText className="w-3.5 h-3.5" /> PDF
      </a>
      <a
        href={exportUrl("docx")}
        download
        data-testid="export-docx"
        className="px-2.5 py-1 text-xs rounded border hover:bg-accent inline-flex items-center gap-1 text-muted-foreground"
        title={t("Export as Word")}
      >
        <Download className="w-3.5 h-3.5" /> Word
      </a>
      {tab === "exercise" && (
        <button
          onClick={() => setAnswerSheet((v) => !v)}
          data-testid="answer-sheet-toggle"
          className="px-2.5 py-1 text-xs rounded border border-primary/40 bg-primary/5 text-primary inline-flex items-center gap-1"
          title={t("Toggle answer sheet edition")}
        >
          {answerSheet ? t("Parent edition") : t("Student edition")}
        </button>
      )}
    </div>
  );
}
