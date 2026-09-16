/**
 * M18-B/C 共享：会话收尾卡（C4）+ episodic 上报（C5）+ 阅读回流（C2）+ 题目反馈（C7）。
 * 全部 fire-and-forget，不阻塞 UI；u 缺省时后端落 admin。
 * 原仓 components/h5/session-recap.tsx 1:1 移植（Tailwind → 内联样式，confetti keyframes 原样）。
 */
import { useEffect, useState } from "react";

function qs(u?: string, extra?: Record<string, string>) {
  const p = new URLSearchParams();
  if (u) p.set("u", u);
  for (const [k, v] of Object.entries(extra || {})) if (v) p.set(k, v);
  const s = p.toString();
  return s ? `?${s}` : "";
}

/** C5：会话收尾摘要 -> L1 learning surface（kind=session_summary） */
export function postSessionSummary(
  u: string | undefined,
  payload: {
    topics: string[];
    wins: string[];
    stuck: string;
    questions: number;
    correct: number;
    source: string;
  },
) {
  try {
    void fetch(`/api/v1/learning/session-summary${qs(u)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      keepalive: true,
    }).catch(() => {});
  } catch { /* noop */ }
}

/** C7：生成题反馈三键（太难/太简单/题有误）-> L1（kind=question_feedback） */
export function postQuestionFeedback(
  u: string | undefined,
  payload: { chapter_id: string; tier: string; version: number; question_id: string; tag: "too_hard" | "too_easy" | "wrong"; question_text?: string },
) {
  try {
    void fetch(`/api/v1/learning/question-feedback${qs(u)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).catch(() => {});
  } catch { /* noop */ }
}

/** C2：阅读回流（书翻页/教材翻页）-> L1（kind=book_progress）。
 *  同一 (book,page) 会话内只报一次，避免刷屏。 */
const _reportedPages = new Set<string>();
export function postReadingEvent(
  u: string | undefined,
  bookId: string,
  chapterTitle: string,
  pageIndex: number,
) {
  const key = `${u || ""}|${bookId}|${pageIndex}`;
  if (_reportedPages.has(key)) return;
  _reportedPages.add(key);
  try {
    void fetch(`/api/v1/learning/reading-event${qs(u)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        book_id: bookId,
        chapter_title: chapterTitle,
        page_index: pageIndex,
      }),
      keepalive: true,
    }).catch(() => {});
  } catch { /* noop */ }
}

/** C4 收尾卡：半屏底部弹层 + 简易 confetti。 */
export function SessionRecap({
  open,
  onClose,
  topic,
  questions,
  correct,
  source = "practice",
  u,
}: {
  open: boolean;
  onClose: () => void;
  topic: string;
  questions: number;
  correct: number;
  source?: string;
  u?: string;
}) {
  const [streak, setStreak] = useState<number | null>(null);

  useEffect(() => {
    if (!open) return;
    // 拉最新 streak（刚练完，画像里 streak 已含今天）
    fetch(`/api/v1/learning/today-panel${qs(u)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setStreak(typeof d?.streak_days === "number" ? d.streak_days : null))
      .catch(() => {});
    // C5：episodic 入记忆
    postSessionSummary(u, {
      topics: topic ? [topic] : [],
      wins:
        correct > 0
          ? [`《${topic || "练习"}》答对 ${correct}/${questions}`]
          : [],
      stuck: correct < questions ? `${topic || "练习"} 中还有 ${questions - correct} 题未掌握` : "",
      questions,
      correct,
      source,
    });
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!open) return null;
  const rate = questions ? Math.round((correct / questions) * 100) : 0;
  const praise =
    rate >= 80 ? "太棒了，继续保持！🎉" : rate >= 60 ? "不错哦，再接再厉！💪" : "错题已进错题本，复习一遍就稳了 📖";

  return (
    <div
      style={{ position: "fixed", inset: 0, zIndex: 90, display: "flex", alignItems: "flex-end", justifyContent: "center", background: "rgba(0,0,0,0.4)" }}
      onClick={onClose}
    >
      {/* confetti-lite：12 个彩色小点从上飘落 */}
      <div style={{ pointerEvents: "none", position: "absolute", inset: 0, overflow: "hidden" }}>
        <style>{`@keyframes h5fall{0%{transform:translateY(-10%);opacity:1}100%{transform:translateY(110vh) rotate(300deg);opacity:.2}}`}</style>
        {Array.from({ length: 12 }).map((_, i) => (
          <span
            key={i}
            style={{
              position: "absolute",
              left: `${(i * 8.3 + 4)}%`,
              top: "-4%",
              fontSize: `${12 + (i % 4) * 6}px`,
              animation: `h5fall ${1.6 + (i % 5) * 0.35}s linear ${(i % 3) * 0.25}s forwards`,
            }}
          >
            {["🎉", "⭐", "✨", "🎊"][i % 4]}
          </span>
        ))}
      </div>
      <div
        style={{ width: "100%", maxWidth: 448, background: "#fff", borderRadius: "24px 24px 0 0", padding: 24, paddingBottom: 32, textAlign: "center", position: "relative" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ fontSize: 40 }}>{rate >= 80 ? "🏆" : rate >= 60 ? "🌟" : "📖"}</div>
        <div style={{ marginTop: 4, fontSize: 18, fontWeight: 700, color: "#1e293b" }}>今日收获</div>
        <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8, textAlign: "center" }}>
          <div style={{ borderRadius: 12, background: "#f8fafc", padding: "8px 0" }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: "#4f46e5" }}>{questions}</div>
            <div style={{ fontSize: 11, color: "#64748b" }}>练了 N 题</div>
          </div>
          <div style={{ borderRadius: 12, background: "#f8fafc", padding: "8px 0" }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: "#059669" }}>{rate}%</div>
            <div style={{ fontSize: 11, color: "#64748b" }}>正确率</div>
          </div>
          <div style={{ borderRadius: 12, background: "#f8fafc", padding: "8px 0" }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: "#f97316" }}>{streak ?? "…"}</div>
            <div style={{ fontSize: 11, color: "#64748b" }}>连续天数 🔥</div>
          </div>
        </div>
        <div style={{ marginTop: 12, fontSize: 14, color: "#475569" }}>{praise}</div>
        {topic && <div style={{ marginTop: 4, fontSize: 12, color: "#94a3b8" }}>完成《{topic}》</div>}
        <button
          onClick={onClose}
          style={{ marginTop: 16, width: "100%", padding: "10px 0", borderRadius: 12, background: "#4f46e5", color: "#fff", fontSize: 14, fontWeight: 500, border: "none", cursor: "pointer" }}
        >
          继续学习 →
        </button>
      </div>
    </div>
  );
}
