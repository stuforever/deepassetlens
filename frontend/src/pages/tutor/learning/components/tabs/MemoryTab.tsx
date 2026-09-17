"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Brain, Loader2, RefreshCw, AlertTriangle, CheckCircle2, CalendarClock } from "lucide-react";
import { fetchLearnerProfile, type LearnerProfileDto } from "../../../../../lib/self-learning-api";
import { apiUrl } from "../../../../../lib/api";
import { TabExportToolbar } from "../TabExportToolbar";

const STATUS_META: Record<string, { label: string; cls: string; icon: string }> = {
  mastered: { label: "已掌握", cls: "text-emerald-600 bg-emerald-50 border-emerald-200", icon: "✅" },
  learning: { label: "学习中", cls: "text-sky-600 bg-sky-50 border-sky-200", icon: "📖" },
  weak: { label: "薄弱", cls: "text-rose-600 bg-rose-50 border-rose-200", icon: "⚠️" },
  new: { label: "未学", cls: "text-muted-foreground bg-muted/40 border-border", icon: "○" },
};

const SUBJECT_LABEL: Record<string, string> = {
  math: "数学",
  chinese: "语文",
  english: "英语",
};

/** 章节学情：真实 LearnerProfile 展示（design §3.6 改动点 C）。 */
export function MemoryTab({ chapterId, chapterName, textbookName }: { chapterId: string; chapterName: string; textbookName: string }) {
  const { t } = useTranslation();
  const [profile, setProfile] = useState<LearnerProfileDto | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    const data = await fetchLearnerProfile();
    setProfile(data);
    setLoading(false);
  }, []);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await fetch(apiUrl("/api/v1/learning/learner-profile/refresh"), { method: "POST" });
      await load();
    } finally {
      setRefreshing(false);
    }
  }, [load]);

  if (loading)
    return (
      <div className="p-4 flex items-center gap-2 text-muted-foreground">
        <Loader2 className="w-4 h-4 animate-spin" /> {t("Loading learning profile...")}
      </div>
    );

  if (!profile || Object.keys(profile.kp_mastery || {}).length === 0) {
    return (
      <div className="p-4 space-y-3" data-testid="tab-panel-memory">
        <div className="p-6 rounded-lg border bg-card text-center">
          <Brain className="w-10 h-10 mx-auto text-muted-foreground mb-2" />
          <p className="text-sm font-medium">还没有学情数据</p>
          <p className="text-xs text-muted-foreground mt-1">
            完成一次答题 / 错题复习后，这里会自动生成你的掌握度画像。
          </p>
        </div>
        <a
          href="/memory/l2"
          className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
        >
          <RefreshCw className="w-3.5 h-3.5" /> {t("Go to the memory page to update")}
        </a>
      </div>
    );
  }

  const kps = Object.values(profile.kp_mastery);
  const bySubject = kps.reduce<Record<string, typeof kps>>((acc, kp) => {
    (acc[kp.subject] = acc[kp.subject] || []).push(kp);
    return acc;
  }, {});

  return (
    <div className="p-4 space-y-4" data-testid="tab-panel-memory">
      <TabExportToolbar chapterId={chapterId} tab="memory" />
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2" data-testid="memory-profile">
          <Brain className="w-4 h-4 text-purple-600" />
          <h3 className="font-semibold text-sm">学情画像</h3>
          <span className="text-xs text-muted-foreground">
            {Object.keys(profile.kp_mastery).length} 个知识点
          </span>
        </div>
        <button
          onClick={onRefresh}
          disabled={refreshing}
          data-testid="memory-refresh"
          className="px-2 py-1 rounded border text-xs hover:bg-accent flex items-center gap-1"
        >
          <RefreshCw className={`w-3 h-3 ${refreshing ? "animate-spin" : ""}`} /> 刷新
        </button>
      </div>

      {/* 概览统计 */}
      <div className="grid grid-cols-3 gap-2">
        <div className="p-2 rounded border bg-card text-center">
          <CheckCircle2 className="w-4 h-4 mx-auto text-emerald-600 mb-1" />
          <div className="text-lg font-semibold">{profile.strong_points.length}</div>
          <div className="text-[10px] text-muted-foreground">已掌握</div>
        </div>
        <div className="p-2 rounded border bg-card text-center">
          <AlertTriangle className="w-4 h-4 mx-auto text-rose-500 mb-1" />
          <div className="text-lg font-semibold">{profile.weak_points.length}</div>
          <div className="text-[10px] text-muted-foreground">薄弱</div>
        </div>
        <div className="p-2 rounded border bg-card text-center">
          <CalendarClock className="w-4 h-4 mx-auto text-amber-500 mb-1" />
          <div className="text-lg font-semibold">{profile.due_reviews.length}</div>
          <div className="text-[10px] text-muted-foreground">待复习</div>
        </div>
      </div>

      {/* 学习节奏 + 徽章（design §5.3 游戏化） */}
      <div className="grid grid-cols-2 gap-2">
        <div className="p-2 rounded border bg-card text-center">
          <div className="text-lg font-semibold text-orange-600">🔥 {profile.streak_days}</div>
          <div className="text-[10px] text-muted-foreground">连续学习（天）</div>
        </div>
        <div className="p-2 rounded border bg-card text-center">
          <div className="text-lg font-semibold text-sky-600">
            ⏱️ {Math.round(profile.total_study_minutes || 0)}
          </div>
          <div className="text-[10px] text-muted-foreground">累计学习（分钟）</div>
        </div>
      </div>

      {profile.badges && profile.badges.length > 0 && (
        <div className="p-3 rounded-lg border bg-card">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-base">🏅</span>
            <h4 className="font-semibold text-sm">我的徽章</h4>
            <span className="text-xs text-muted-foreground">{profile.badges.length} 枚</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {profile.badges.map((b) => (
              <div
                key={b.id}
                title={b.desc}
                className="flex items-center gap-1 px-2 py-1 rounded-full border bg-amber-50/60 text-xs text-amber-700"
              >
                <span>{b.icon}</span>
                {b.name}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 按学科掌握度 */}
      {Object.entries(bySubject).map(([subject, list]) => (
        <div key={subject} className="p-3 rounded-lg border bg-card">
          <div className="flex items-center gap-2 mb-2">
            <span className="font-semibold text-sm">
              {SUBJECT_LABEL[subject] || subject}
            </span>
            <span className="text-xs text-muted-foreground">{list.length} 个知识点</span>
          </div>
          <div className="space-y-2">
            {list
              .sort((a, b) => a.mastery - b.mastery)
              .map((kp) => {
                const meta = STATUS_META[kp.status] || STATUS_META.new;
                return (
                  <div key={kp.kp_id} className="flex items-center gap-2">
                    <span className="w-2.5 text-center text-xs">{meta.icon}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-center mb-0.5">
                        <span className="text-xs truncate">{kp.kp_name}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${meta.cls}`}>
                          {meta.label} {Math.round(kp.mastery * 100)}%
                        </span>
                      </div>
                      <div className="h-1.5 rounded-full bg-muted/50 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            kp.status === "mastered"
                              ? "bg-emerald-500"
                              : kp.status === "weak"
                                ? "bg-rose-500"
                                : "bg-sky-500"
                          }`}
                          style={{ width: `${Math.max(4, kp.mastery * 100)}%` }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      ))}

      {/* 到期复习 */}
      {profile.due_reviews.length > 0 && (
        <div className="p-3 rounded-lg border border-amber-200 bg-amber-50/60">
          <div className="flex items-center gap-2 mb-2">
            <CalendarClock className="w-4 h-4 text-amber-600" />
            <h4 className="font-semibold text-sm">待复习</h4>
            <span className="text-xs text-muted-foreground">{profile.due_reviews.length} 项到期</span>
          </div>
          <ul className="space-y-1">
            {profile.due_reviews.slice(0, 8).map((r) => (
              <li key={r.kp_id} className="text-xs flex items-center justify-between">
                <span>{r.kp_name}</span>
                <span className="text-muted-foreground">{r.reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <a
        href="/memory/l2"
        className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
      >
        <RefreshCw className="w-3.5 h-3.5" /> {t("Go to the memory page to update")}
      </a>
    </div>
  );
}
