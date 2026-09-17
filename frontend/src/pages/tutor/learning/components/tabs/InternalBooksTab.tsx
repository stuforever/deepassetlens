"use client";

import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { BookOpen, Loader2, Sparkles, ExternalLink } from "lucide-react";
import { fetchChapterBooksInherited, createChapterBook } from "../../../../../lib/self-learning-api";
import { TabExportToolbar } from "../TabExportToolbar";

interface ChapterBook {
  id: string;
  title: string;
  status: string;
  chapter_count: number;
  page_count: number;
  metadata?: Record<string, unknown>;
}

/** 内部书籍：本章已生成/可一键生成的课件书。 */
export function InternalBooksTab({ chapterId, chapterName }: {
  chapterId: string;
  chapterName: string;
}) {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [books, setBooks] = useState<ChapterBook[]>([]);
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(true);

  const refreshBooks = useCallback(() => {
    setLoading(true);
    fetchChapterBooksInherited(chapterId)
      .then((data) => setBooks(data || []))
      .catch(() => setBooks([]))
      .finally(() => setLoading(false));
  }, [chapterId]);

  useEffect(() => {
    refreshBooks();
  }, [refreshBooks]);

  const openBook = (bookId: string, pageId?: string) => {
    // Deep-link straight into the book reader (not the library list).
    const q = pageId ? `book=${bookId}&page=${pageId}` : `book=${bookId}`;
    navigate(`/e/tutor/book?${q}`);
  };

  const handleGenerate = async () => {
    if (creating) return;
    setCreating(true);
    try {
      const result = await createChapterBook(chapterId);
      // Enter the book reader directly — it polls compile status live.
      openBook(result.book_id);
    } catch (err) {
      console.error("createChapterBook failed", err);
      setCreating(false);
    }
  };

  const statusLabel = (s: string) => {
    if (s === "ready") return t("Ready");
    if (s === "compiling") return t("Compiling…");
    if (s === "error") return t("Error");
    return s;
  };

  return (
    <div className="p-4 space-y-3" data-testid="tab-panel-internal_books">
      <TabExportToolbar chapterId={chapterId} tab="internal_books" />
      {/* Header */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <BookOpen className="w-4 h-4 text-primary" />
          <span>{t("Chapter courseware book (generated from knowledge points + textbook text + wrong questions)")}</span>
        </div>
        <button
          onClick={handleGenerate}
          disabled={creating}
          data-testid="internal-book-generate"
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition shrink-0 ${
            creating
              ? "bg-muted text-muted-foreground cursor-not-allowed"
              : "bg-primary text-primary-foreground hover:opacity-90"
          }`}
        >
          {creating ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" /> {t("Generating…")}
            </>
          ) : (
            <>
              <Sparkles className="w-3.5 h-3.5" /> {t("Generate courseware book")}
            </>
          )}
        </button>
      </div>
      {creating && (
        <p className="text-xs text-muted-foreground">
          {t("Generation started in the background (about 5-10 minutes). You'll enter the book reader to view progress.")}
        </p>
      )}

      {/* Book list */}
      {loading ? (
        <div className="p-6 flex items-center justify-center text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin mr-2" /> {t("Loading...")}
        </div>
      ) : books.length === 0 ? (
        <div className="p-6 rounded-lg border bg-muted/30 text-center">
          <BookOpen className="w-10 h-10 mx-auto text-muted-foreground mb-3" />
          <p className="text-sm font-medium mb-1">{t("No courseware book for this chapter yet")}</p>
          <p className="text-xs text-muted-foreground">
            {t("Click \"Generate courseware book\" in the top-right to auto-generate from this chapter's knowledge points, textbook text, and wrong questions.")}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {books.map((b) => (
            <div
              key={b.id}
              onClick={() => openBook(b.id)}
              data-testid="internal-book-item"
              className="p-3 rounded-lg border bg-card cursor-pointer hover:bg-accent transition flex items-center gap-3"
            >
              <BookOpen className="w-5 h-5 text-primary shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="font-medium text-sm truncate">{b.title}</p>
                <p className="text-xs text-muted-foreground">
                  {statusLabel(b.status)} · {t("{{count}} chapters", { count: b.chapter_count })} · {t("{{count}} pages", { count: b.page_count })}
                </p>
              </div>
              <ExternalLink className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
