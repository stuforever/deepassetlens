"use client";

import { Suspense, useState, useEffect, useCallback } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { BookOpen, Loader2, GraduationCap } from "lucide-react";
import { fetchTextbookTree, type TextbookNode, type ChapterNode } from "../../../lib/self-learning-api";
import { ChapterTree } from "./components/ChapterTree";
import { ChapterTabs } from "./components/ChapterTabs";

function SelfLearningContent() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { t } = useTranslation();
  const [textbooks, setTextbooks] = useState<TextbookNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedChapter, setSelectedChapter] = useState<ChapterNode | null>(null);
  const [selectedTextbook, setSelectedTextbook] = useState<TextbookNode | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const initialTab = searchParams.get("tab") || undefined;

  // Load textbooks
  useEffect(() => {
    fetchTextbookTree()
      .then((data) => {
        setTextbooks(data || []);
        setLoading(false);

        // Auto-select from URL params
        const chapterId = searchParams.get("chapter_id");
        const textbookId = searchParams.get("textbook_id");
        const requestedTab = searchParams.get("tab");
        if (chapterId) {
          for (const tb of data || []) {
            const findInTree = (chapters: ChapterNode[]): ChapterNode | null => {
              for (const ch of chapters) {
                if (ch.id === chapterId) return ch;
                if (ch.children) {
                  const found = findInTree(ch.children);
                  if (found) return found;
                }
              }
              return null;
            };
            const found = findInTree(tb.chapters || []);
            if (found) {
              setSelectedChapter(found);
              setSelectedTextbook(tb);
              return;
            }
          }
        } else if (textbookId) {
          const tb = (data || []).find((t) => t.id === textbookId);
          if (tb) setSelectedTextbook(tb);
        } else if (requestedTab) {
          // H5 入口（拍错题/学情）未指定章节时自动选第一个可用章节
          for (const tb of data || []) {
            const findFirst = (chapters: ChapterNode[]): ChapterNode | null => {
              if (!chapters.length) return null;
              const first = chapters[0];
              if (first.children && first.children.length) return findFirst(first.children);
              return first;
            };
            const first = findFirst(tb.chapters || []);
            if (first) {
              setSelectedChapter(first);
              setSelectedTextbook(tb);
              return;
            }
          }
        }
      })
      .catch(() => setLoading(false));
  }, [searchParams]);

  const onSelectChapter = useCallback((chapter: ChapterNode, textbook: TextbookNode) => {
    setSelectedChapter(chapter);
    setSelectedTextbook(textbook);
    // Update URL without full navigation
    const params = new URLSearchParams();
    params.set("chapter_id", chapter.id);
    params.set("textbook_id", textbook.id);
    navigate(`/e/tutor/self-learning?${params.toString()}`, { replace: true });
  }, [navigate]);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        <Loader2 className="w-6 h-6 animate-spin mr-2" /> {t("Loading textbook data...")}
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b flex-shrink-0">
        <div className="flex items-center gap-3">
          <GraduationCap className="w-5 h-5 text-primary" />
          <h1 className="text-lg font-semibold">{t("Self-directed Learning")}</h1>
          <span className="text-xs text-muted-foreground">
            {t("{{count}} textbooks · chapter-centric organization of all learning content", { count: textbooks.length })}
          </span>
        </div>
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          data-testid="self-learning-sidebar-toggle"
          className="px-2 py-1 rounded border text-sm hover:bg-accent"
        >
          {sidebarOpen ? t("◀ Collapse") : t("▶ Expand")}
        </button>
      </div>

      {/* Main: sidebar + content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Chapter Tree */}
        {sidebarOpen && (
          <aside className="w-72 shrink-0 border-r overflow-y-auto bg-card/50" data-testid="chapter-tree">
            <ChapterTree
              textbooks={textbooks}
              selectedChapterId={selectedChapter?.id || null}
              onSelectChapter={onSelectChapter}
            />
          </aside>
        )}

        {/* Right: Tab Content */}
        <main className="flex-1 overflow-hidden flex flex-col" data-testid="self-learning-main">
          {selectedChapter && selectedTextbook ? (
            <>
              {/* Chapter Header */}
              <div className="px-4 py-2 border-b flex-shrink-0 bg-muted/20">
                <div className="flex items-center gap-2 text-sm">
                  <BookOpen className="w-4 h-4 text-primary" />
                  <span className="text-muted-foreground">{selectedTextbook.name}</span>
                  <span className="text-muted-foreground">/</span>
                  <span className="font-medium">{selectedChapter.name}</span>
                </div>
              </div>
              {/* Tabs */}
              <div className="flex-1 overflow-hidden">
                <ChapterTabs chapter={selectedChapter} textbook={selectedTextbook} initialTab={initialTab} />
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center" data-testid="self-learning-empty">
              <div className="text-center max-w-md">
                <BookOpen className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                <h2 className="text-lg font-semibold mb-2">{t("Select a chapter to start learning")}</h2>
                <p className="text-sm text-muted-foreground">
                  {t("Select a textbook and chapter from the left directory; the system will show the chapter's original text, internal books, courseware, voice/video, knowledge point summary, practice, wrong questions, notes, memory, and AI resources.")}
                </p>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default function SelfLearningPage() {
  const { t } = useTranslation();
  return (
    <Suspense fallback={<div className="h-full flex items-center justify-center text-muted-foreground"><Loader2 className="w-5 h-5 animate-spin mr-2" /> {t("Loading...")}</div>}>
      <SelfLearningContent />
    </Suspense>
  );
}
