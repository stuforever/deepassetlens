"use client";

import { useState, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  Loader2,
  FileText,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  BookOpen,
} from "lucide-react";
import { fetchTextbookPages } from "../../../../../lib/self-learning-api";
import { TabExportToolbar } from "../TabExportToolbar";

interface TextbookPage {
  id: string;
  page_num: number;
  image_url: string | null;
  ocr_text: string | null;
}

interface Props {
  textbookId: string;
  chapterId: string;
  chapterName: string;
  pageStart: number | null;
  pageEnd: number | null;
}

export function OriginalTextTab({ textbookId, chapterId, chapterName, pageStart, pageEnd }: Props) {
  const { t } = useTranslation();
  const [allPages, setAllPages] = useState<TextbookPage[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showOcr, setShowOcr] = useState(false);

  useEffect(() => {
    setLoading(true);
    setCurrentIndex(0);
    fetchTextbookPages(textbookId)
      .then((data) => {
        // API returns { items: [...] }, handle both shapes
        const pages: TextbookPage[] = data?.items || data || [];
        setAllPages(pages);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [textbookId]);

  // Filter pages by chapter page range.
  // A chapter with no page mapping should NOT dump every page of the
  // textbook — show an empty state instead so the user knows it's unmapped.
  const relevantPages = useMemo(() => {
    if (pageStart && pageEnd) {
      return allPages.filter((p) => p.page_num >= pageStart && p.page_num <= pageEnd);
    }
    return [];
  }, [allPages, pageStart, pageEnd]);

  // Reset index when page set changes
  useEffect(() => {
    setCurrentIndex(0);
  }, [pageStart, pageEnd]);

  if (loading) {
    return (
      <div className="p-4 flex items-center gap-2 text-muted-foreground">
        <Loader2 className="w-4 h-4 animate-spin" /> {t("Loading textbook original text...")}
      </div>
    );
  }

  if (relevantPages.length === 0) {
    return (
      <div className="p-4" data-testid="tab-panel-original">
        <div className="p-6 rounded-lg border bg-muted/30 text-center">
          <FileText className="w-10 h-10 mx-auto text-muted-foreground mb-3" />
          <p className="text-sm font-medium mb-1">{t("No textbook original text data")}</p>
          <p className="text-xs text-muted-foreground">
            {pageStart && pageEnd
              ? t("The textbook pages for this chapter (pages {{start}} - {{end}}) have not been imported yet.", { start: pageStart, end: pageEnd })
              : t("This chapter has no page range mapping, so the original text cannot be located.")}
          </p>
        </div>
      </div>
    );
  }

  const currentPage = relevantPages[currentIndex];
  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < relevantPages.length - 1;

  const goToPage = (index: number) => {
    if (index >= 0 && index < relevantPages.length) {
      setCurrentIndex(index);
      setShowOcr(false);
    }
  };

  return (
    <div className="flex flex-col h-full" data-testid="tab-panel-original">
      <div className="px-4 pt-2 print:hidden"><TabExportToolbar chapterId={chapterId} tab="original" /></div>
      {/* Header: chapter name + page indicator */}
      <div className="px-4 py-2 border-b bg-muted/20 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2 text-sm">
          <BookOpen className="w-4 h-4 text-primary" />
          <span className="font-medium">{chapterName}</span>
        </div>
        <span className="text-xs text-muted-foreground">
          {t("Page {{current}} / {{total}}", { current: currentIndex + 1, total: relevantPages.length })}
          {pageStart && pageEnd && (
            <span className="ml-2">{t("(textbook P{{page}})", { page: currentPage?.page_num })}</span>
          )}
        </span>
      </div>

      {/* Page image area */}
      <div className="flex-1 overflow-y-auto flex flex-col items-center p-4">
        {currentPage?.image_url && (
          <img
            src={currentPage.image_url}
            alt={t("Page {{count}}", { count: currentPage.page_num })}
            className="max-w-full max-h-[70vh] object-contain rounded-lg shadow-md border"
            loading="lazy"
          />
        )}

        {/* OCR text - collapsible */}
        {currentPage?.ocr_text && (
          <div className="w-full max-w-3xl mt-3">
            <button
              onClick={() => setShowOcr(!showOcr)}
              data-testid="original-ocr-toggle"
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <ChevronDown
                className={`w-3.5 h-3.5 transition-transform ${showOcr ? "rotate-180" : ""}`}
              />
              {showOcr ? t("Hide text") : t("Show text")}
            </button>
            {showOcr && (
              <div className="mt-2 p-3 rounded-lg border bg-muted/30 text-sm whitespace-pre-wrap leading-relaxed max-h-60 overflow-y-auto">
                {currentPage.ocr_text}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Pager controls */}
      <div className="px-4 py-3 border-t bg-muted/20 flex items-center justify-center gap-4 flex-shrink-0">
        <button
          onClick={() => goToPage(currentIndex - 1)}
          disabled={!hasPrev}
          data-testid="original-prev"
          className={`flex items-center gap-1 px-4 py-1.5 rounded-lg text-sm transition ${
            hasPrev
              ? "bg-background hover:bg-accent border text-foreground"
              : "text-muted-foreground/40 cursor-not-allowed border border-transparent"
          }`}
        >
          <ChevronLeft className="w-4 h-4" /> {t("Previous page")}
        </button>

        {/* Page dots / quick jump */}
        <div className="flex items-center gap-1">
          {relevantPages.map((_, i) => (
            <button
              key={i}
              onClick={() => goToPage(i)}
              className={`w-2 h-2 rounded-full transition ${
                i === currentIndex
                  ? "bg-primary w-6"
                  : "bg-muted-foreground/30 hover:bg-muted-foreground/50"
              }`}
              aria-label={t("Jump to page {{count}}", { count: i + 1 })}
            />
          ))}
        </div>

        <button
          onClick={() => goToPage(currentIndex + 1)}
          disabled={!hasNext}
          data-testid="original-next"
          className={`flex items-center gap-1 px-4 py-1.5 rounded-lg text-sm transition ${
            hasNext
              ? "bg-background hover:bg-accent border text-foreground"
              : "text-muted-foreground/40 cursor-not-allowed border border-transparent"
          }`}
        >
          {t("Next page")} <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
