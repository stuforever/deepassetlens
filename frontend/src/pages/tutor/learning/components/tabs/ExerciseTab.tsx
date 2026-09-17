"use client";

import { useEffect, useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { GraduationCap, Target, Swords, Loader2, CheckCircle2, XCircle, AlertTriangle } from "lucide-react";
import type { ChapterOverview, Grade7Resource } from "../../../../../lib/self-learning-api";
import { fetchChapterResources } from "../../../../../lib/self-learning-api";
import { apiUrl } from "../../../../../lib/api";
import { TabExportToolbar } from "../TabExportToolbar";

/** 闯关练习：该章节的结构化题目（可作答，即时反馈）。 */
function PracticeSet({ set }: { set: Grade7Resource }) {
  const { t } = useTranslation();
  const [idx, setIdx] = useState(0);
  const [answered, setAnswered] = useState<Record<number, boolean>>({});
  const [result, setResult] = useState<Record<number, boolean>>({});
  const questions = set.questions || [];
  const total = questions.length;
  if (total === 0) return null;
  const q = questions[idx];

  const check = (userAnswer: string | number) => {
    if (answered[idx]) return;
    const correct = Array.isArray(q.answer)
      ? q.answer.map(String).includes(String(userAnswer))
      : String(q.answer) === String(userAnswer);
    setResult((r) => ({ ...r, [idx]: correct }));
    setAnswered((a) => ({ ...a, [idx]: true }));
  };

  return (
    <div className="rounded-lg border bg-card p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium text-sm">
          {set.title}
          {set.adaptive_reason === "weak" && (
            <span className="ml-2 px-1.5 py-0.5 rounded bg-rose-100 text-rose-600 dark:bg-rose-900/40 dark:text-rose-300 text-[11px] font-medium">薄弱优先</span>
          )}
          {set.adaptive_reason === "due" && (
            <span className="ml-2 px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300 text-[11px] font-medium">到期复习</span>
          )}
        </span>
        <span className="text-xs text-muted-foreground">{t("Question {{current}}/{{total}}", { current: idx + 1, total })}</span>
      </div>
      <p className="text-sm mb-3">{q.ask}</p>
      {q.type === "choice" && (q.options || []).map((opt, i) => (
        <button
          key={i}
          onClick={() => check(i)}
          disabled={!!answered[idx]}
          className={`w-full text-left px-3 py-2 mb-1 rounded border text-sm transition ${
            answered[idx] && String(i) === String(q.answer)
              ? "border-emerald-400 bg-emerald-50 dark:bg-emerald-950/30"
              : answered[idx]
                ? "border-muted bg-muted/30"
                : "bg-card hover:bg-accent"
          }`}
        >
          {String.fromCharCode(65 + i)}. {opt}
        </button>
      ))}
      {q.type !== "choice" && (
        <div className="flex gap-2">
          <input
            className="flex-1 px-3 py-2 rounded border bg-transparent text-sm"
            placeholder={t("Enter answer")}
            onKeyDown={(e) => {
              if (e.key === "Enter") check((e.target as HTMLInputElement).value);
            }}
          />
          <button onClick={() => check("")} className="px-3 py-2 rounded border text-sm hover:bg-accent">
            {t("Submit")}
          </button>
        </div>
      )}
      {answered[idx] && (
        <div className={`mt-2 text-sm flex items-center gap-1 ${result[idx] ? "text-emerald-600" : "text-rose-500"}`}>
          {result[idx] ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
          {result[idx] ? t("Correct!") : t("Correct answer: {{answer}}", { answer: Array.isArray(q.answer) ? q.answer.join(" / ") : q.answer })}
          <span className="text-muted-foreground ml-2">{q.why}</span>
        </div>
      )}
      <div className="mt-3 flex justify-between">
        <button
          onClick={() => setIdx((i) => Math.max(0, i - 1))}
          disabled={idx === 0}
          className="px-3 py-1.5 rounded border text-sm disabled:opacity-40 hover:bg-accent"
        >
          {t("Previous")}
        </button>
        <span className="text-xs text-muted-foreground self-center">
          {t("Answered {{count}}/{{total}}", { count: Object.keys(answered).filter((k) => result[+k]).length, total })}
        </span>
        <button
          onClick={() => setIdx((i) => Math.min(total - 1, i + 1))}
          disabled={idx === total - 1}
          className="px-3 py-1.5 rounded border text-sm disabled:opacity-40 hover:bg-accent"
        >
          {t("Next question")}
        </button>
      </div>
    </div>
  );
}

export function ExerciseTab({ overview, chapterId }: { overview: ChapterOverview; chapterId: string }) {
  const { t } = useTranslation();
  const progress = overview.mastery_progress;
  const [exercises, setExercises] = useState<Grade7Resource[]>([]);
  const [loading, setLoading] = useState(true);
  const [adaptive, setAdaptive] = useState<{ adapted: boolean; summary: string[] } | null>(null);
  const [weakHint, setWeakHint] = useState<{ weak_relevant: boolean; matched_kp?: { kp_name: string; mastery: number }[] } | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    fetchChapterResources(chapterId)
      .then((d) => {
        setExercises(d.exercises || []);
        setAdaptive(d.adaptive ?? null);
      })
      .catch(() => setExercises([]))
      .finally(() => setLoading(false));
  }, [chapterId]);

  useEffect(() => { load(); }, [load]);

  // 自适应薄弱提示（design §3.7）
  useEffect(() => {
    const chapterTitle = overview.chapter?.name || "";
    if (!chapterTitle) return;
    fetch(`${apiUrl("/api/v1/learning/exercise-hint")}?chapter_title=${encodeURIComponent(chapterTitle)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setWeakHint(d))
      .catch(() => setWeakHint(null));
  }, [overview]);

  const structured = exercises.filter((e) => (e.questions || []).length > 0);
  const games = exercises.filter((e) => e.game_html);

  return (
    <div className="p-4 space-y-4" data-testid="tab-panel-exercise">
      <TabExportToolbar chapterId={chapterId} tab="exercise" />
      {/* 闯关练习 */}
      <section data-testid="exercise-levelup">
        <div className="flex items-center gap-2 mb-2">
          <Swords className="w-4 h-4 text-rose-500" />
          <h3 className="font-semibold text-sm">{t("Level-up Practice")}</h3>
        </div>
        {weakHint?.weak_relevant && (
          <div className="mb-3 p-3 rounded-lg border border-amber-200 bg-amber-50/60 text-sm flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
            <div>
              <span className="font-medium text-amber-700">本章命中你的薄弱知识点：</span>
              <span className="text-amber-700">
                {weakHint.matched_kp?.map((k) => `${k.kp_name}（掌握 ${Math.round(k.mastery * 100)}%）`).join("、")}
              </span>
              <div className="text-xs text-amber-600/80 mt-0.5">建议优先完成本章闯关，巩固薄弱点。</div>
            </div>
          </div>
        )}
        {adaptive?.adapted && (adaptive.summary || []).length > 0 && (
          <div className="mb-3 p-3 rounded-lg border border-sky-200 bg-sky-50/60 text-sm flex items-start gap-2">
            <Target className="w-4 h-4 text-sky-600 mt-0.5 shrink-0" />
            <div className="text-sky-700">
              <span className="font-medium">闯关已按学情排序：</span>
              <span>{adaptive.summary.join("；")}</span>
            </div>
          </div>
        )}
        {loading ? (
          <div className="p-4 flex items-center justify-center text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin mr-2" /> {t("Loading...")}
          </div>
        ) : structured.length === 0 && games.length === 0 ? (
          <div className="p-4 rounded border bg-muted/30 text-center">
            <p className="text-sm text-muted-foreground">{t("No level-up practice for this chapter yet.")}</p>
          </div>
        ) : (
          <>
            {structured.map((e) => <PracticeSet key={e.id} set={e} />)}
            {games.map((g) => (
              <div key={g.id} className="rounded-lg border overflow-hidden">
                <div className="px-3 py-2 border-b bg-muted/30 text-sm font-medium">{g.title}</div>
                <iframe
                  src={g.game_html}
                  title={g.title}
                  className="w-full h-[480px] bg-white"
                  sandbox="allow-scripts allow-same-origin allow-modals allow-forms allow-pointer-lock"
                />
              </div>
            ))}
          </>
        )}
      </section>

      {/* 精通之路进度 */}
      <div className="p-4 rounded-lg border bg-card">
        <div className="flex items-center gap-2 mb-3">
          <GraduationCap className="w-4 h-4 text-primary" />
          <h3 className="font-semibold text-sm">{t("Mastery Path")}</h3>
        </div>
        {progress ? (
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("Total modules")}</span>
              <span>{progress.total_modules}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("Matched in this chapter")}</span>
              <span>{progress.matched_modules}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">{t("Completed")}</span>
              <span className="text-emerald-600">{progress.completed}</span>
            </div>
            <div className="pt-2">
              <div className="h-2 rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all"
                  style={{ width: `${progress.total_modules > 0 ? (progress.completed / progress.total_modules * 100) : 0}%` }}
                />
              </div>
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">
            {t("No mastery path progress yet. You can initialize the mastery path in the learning space.")}
          </p>
        )}
      </div>

      {/* 测验题 */}
      <div className="p-4 rounded-lg border bg-card">
        <div className="flex items-center gap-2 mb-3">
          <Target className="w-4 h-4 text-amber-500" />
          <h3 className="font-semibold text-sm">{t("Quiz Questions")}</h3>
        </div>
        <p className="text-sm text-muted-foreground">
          {t("Quiz questions come from the quiz blocks in the courseware. If a courseware is linked, quizzes will appear here.")}
        </p>
      </div>
    </div>
  );
}
