"use client";

import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Loader2 } from "lucide-react";
import type { ChapterOverview, ChapterNode, TextbookNode } from "../../../../lib/self-learning-api";
import { fetchChapterOverview } from "../../../../lib/self-learning-api";
import { OriginalTextTab } from "./tabs/OriginalTextTab";
import { KnowledgePointsTab } from "./tabs/KnowledgePointsTab";
import { InternalBooksTab } from "./tabs/InternalBooksTab";
import { WrongQuestionsTab } from "./tabs/WrongQuestionsTab";
import { CoursewareTab } from "./tabs/CoursewareTab";
import { ExerciseTab } from "./tabs/ExerciseTab";
import { NotesTab } from "./tabs/NotesTab";
import { MemoryTab } from "./tabs/MemoryTab";
import { AIResourceTab } from "./tabs/AIResourceTab";
import { VoiceVideoTab } from "./tabs/VoiceVideoTab";
import { ReciteTab } from "./tabs/ReciteTab";

const TABS = [
  { id: "original", labelKey: "tab.original", icon: "📄" },
  { id: "internal_books", labelKey: "tab.internal_books", icon: "📖" },
  { id: "courseware", labelKey: "tab.courseware", icon: "📚" },
  { id: "voice", labelKey: "tab.voice", icon: "📣" },
  { id: "recite", labelKey: "tab.recite", icon: "🎙" },
  { id: "knowledge", labelKey: "tab.knowledge", icon: "💡" },
  { id: "exercise", labelKey: "tab.exercise", icon: "🎯" },
  { id: "wrong", labelKey: "tab.wrong", icon: "❌" },
  { id: "notes", labelKey: "tab.notes", icon: "📝" },
  { id: "memory", labelKey: "tab.memory", icon: "🧠" },
  { id: "ai", labelKey: "tab.ai", icon: "✨" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export function ChapterTabs({
  chapter,
  textbook,
  initialTab,
}: {
  chapter: ChapterNode;
  textbook: TextbookNode;
  initialTab?: string;
}) {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<TabId>("original");
  const [overview, setOverview] = useState<ChapterOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setActiveTab((initialTab as TabId) || "original");
    fetchChapterOverview(chapter.id)
      .then((data) => { setOverview(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [chapter.id, initialTab]);

  // Badge counts for tab labels
  const badges: Partial<Record<TabId, number>> = {};
  if (overview) {
    badges.knowledge = overview.knowledge_points?.length || 0;
    badges.wrong = overview.wrong_questions?.count || 0;
    badges.courseware = overview.related_books?.length || 0;
  }

  return (
    <div className="flex flex-col h-full">
      {/* Tab Bar */}
      <div className="flex items-center gap-1 px-2 border-b overflow-x-auto flex-shrink-0" data-testid="chapter-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            data-testid={`chapter-tab-${tab.id}`}
            data-active={activeTab === tab.id ? "true" : "false"}
            className={`px-3 py-2 text-sm rounded-t border-b-2 transition whitespace-nowrap ${
              activeTab === tab.id
                ? "border-primary text-primary font-medium bg-primary/5"
                : "border-transparent text-muted-foreground hover:text-foreground hover:bg-accent"
            }`}
          >
            <span className="mr-1">{tab.icon}</span>
            {t(tab.labelKey)}
            {badges[tab.id] !== undefined && badges[tab.id]! > 0 && (
              <span className="ml-1 text-xs px-1.5 py-0.5 rounded-full bg-primary/10 text-primary">
                {badges[tab.id]}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto" data-testid="chapter-tab-content">
        {loading ? (
          <div className="p-8 flex items-center justify-center text-muted-foreground" data-testid="chapter-tab-loading">
            <Loader2 className="w-5 h-5 animate-spin mr-2" /> {t("Loading chapter data...")}
          </div>
        ) : (
          <>
            {activeTab === "original" && (
              <OriginalTextTab
                textbookId={chapter.textbook_id}
                chapterId={chapter.id}
                chapterName={chapter.name}
                pageStart={chapter.page_start}
                pageEnd={chapter.page_end}
              />
            )}
            {activeTab === "knowledge" && overview && (
              <KnowledgePointsTab overview={overview} chapterId={chapter.id} />
            )}
            {activeTab === "internal_books" && (
              <InternalBooksTab chapterId={chapter.id} chapterName={chapter.name} />
            )}
            {activeTab === "wrong" && (
              <WrongQuestionsTab chapterId={chapter.id} chapterName={chapter.name} />
            )}
            {activeTab === "courseware" && overview && (
              <CoursewareTab overview={overview} chapterId={chapter.id} chapterName={chapter.name} />
            )}
            {activeTab === "exercise" && overview && (
              <ExerciseTab overview={overview} chapterId={chapter.id} />
            )}
            {activeTab === "voice" && (
              <VoiceVideoTab chapterId={chapter.id} chapterName={chapter.name} />
            )}
            {activeTab === "recite" && (
              <ReciteTab
                textbookId={chapter.textbook_id}
                chapterId={chapter.id}
                chapterName={chapter.name}
              />
            )}
            {activeTab === "notes" && (
              <NotesTab chapterId={chapter.id} chapterName={chapter.name} />
            )}
            {activeTab === "memory" && (
              <MemoryTab chapterId={chapter.id} chapterName={chapter.name} textbookName={textbook.name} />
            )}
            {activeTab === "ai" && (
              <AIResourceTab chapterId={chapter.id} chapterName={chapter.name} textbookName={textbook.name} />
            )}
          </>
        )}
      </div>
    </div>
  );
}
