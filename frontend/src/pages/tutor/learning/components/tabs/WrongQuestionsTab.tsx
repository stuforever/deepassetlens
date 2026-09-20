"use client";

import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Loader2, Plus, XCircle, CheckCircle2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { fetchWrongQuestionsByChapter } from "../../../../../lib/self-learning-api";
import { notify } from "../../../../../lib/notifications";
import { TabExportToolbar } from "../TabExportToolbar";

interface WrongQuestionItem {
  id: string;
  title: string;
  difficulty: number;
  mastery_status?: string;
  question_text?: string;
  tags?: string[];
}

export function WrongQuestionsTab({ chapterId, chapterName }: { chapterId: string; chapterName: string }) {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [items, setItems] = useState<WrongQuestionItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchWrongQuestionsByChapter(chapterId).then((data) => {
      setItems(data.items || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [chapterId]);

  if (loading) return <div className="p-4 flex items-center gap-2 text-muted-foreground"><Loader2 className="w-4 h-4 animate-spin" /> {t("Loading wrong questions...")}</div>;

  return (
    <div className="p-4 space-y-3" data-testid="tab-panel-wrong">
      <TabExportToolbar chapterId={chapterId} tab="wrong" />
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">{t("{{count}} wrong questions total", { count: items.length })}</span>
        <button
          onClick={() => navigate(`/e/sishu/admin/mother-questions/new?chapter_id=${chapterId}`)}
          data-testid="wrong-question-add"
          className="px-3 py-1 rounded border text-sm hover:bg-accent flex items-center gap-1"
        >
          <Plus className="w-3.5 h-3.5" /> {t("Add wrong question")}
        </button>
      </div>
      {items.length === 0 ? (
        <div className="p-4 rounded border bg-muted/30 text-center">
          <XCircle className="w-8 h-8 mx-auto text-muted-foreground mb-2" />
          <p className="text-sm text-muted-foreground">{t("No wrong questions for this chapter yet.")}</p>
          <p className="text-xs text-muted-foreground mt-1">{t("Click \"Add wrong question\" to add wrong questions for this chapter.")}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((m) => (
            <div
              key={m.id}
              className="p-3 rounded-lg border bg-card cursor-pointer hover:bg-accent transition"
              onClick={() => navigate(`/e/sishu/admin/mother-questions/${m.id}`)}
              data-testid="wrong-question-item"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium text-sm">{m.title}</span>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">{"★".repeat(m.difficulty)}</span>
                  {m.mastery_status === "mastered" ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5 text-rose-500" />
                  )}
                </div>
              </div>
              <p className="text-xs text-muted-foreground line-clamp-2">{m.question_text}</p>
              {m.tags && m.tags.length > 0 && (
                <div className="flex gap-1 mt-1">
                  {m.tags.slice(0, 3).map((t, i) => (
                    <span key={i} className="text-xs px-1.5 py-0.5 rounded bg-primary/10 text-primary">{t}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
