/**
 * H5 学习主页（learn）——原仓 xiaobaohaohao/DeepTutor web/app/h5/learn/page.tsx 1:1 移植（批9 F2 / SA-B3）。
 *
 * 等价替换（与批8 F1/H5WrongBook 同口径）：
 *  - "use client" 删除；next/link → react-router-dom Link（href→to）；
 *    next/navigation useSearchParams/useRouter → react-router-dom useSearchParams/useNavigate（router.push→navigate）；
 *  - 路由前缀映射：原 /h5/* → tupu /e/tutor-h5/*（withU 拼参语义不变）；
 *  - fetch(apiUrl(x)) / fetch(backendUrl(x)) → fetch(x) 逐字路径（h5shared 无 api.ts，直接相对路径）；
 *  - lucide-react → @ant-design/icons 语义就近：BookOpen→ReadOutlined、ChevronRight→RightOutlined、
 *    ChevronDown→DownOutlined、Loader2→LoadingOutlined(spin)、CheckCircle2→CheckCircleOutlined、
 *    XCircle→CloseCircleOutlined、Target→AimOutlined、FileText→FileTextOutlined、
 *    MessageCircle→MessageOutlined、RefreshCw→ReloadOutlined、Sparkles→ThunderboltOutlined；
 *    （原 import 中的 ChevronLeft/Brain 为死导入——原文件正文未使用，不带）；
 *  - Tailwind → 内联样式逐项对位（active:/focus:/hover: 伪类随 h5shared 先例略去；
 *    [&_p]/[&_code] 任意变体与 line-clamp-3 语义注入 <style> / WebkitLineClamp）；
 *  - alert()（收藏/409 文案）原样保留；confirm 无此页；
 *  - data-testid / aria-label / aria-expanded / h5-current-chapter DOM 钩子逐字保留；
 *  - 离线 outbox 动态 import("@/lib/h5-outbox") → import("./h5shared/h5Outbox")（调用点语义原样）；
 *  - ReciteTab/H5ExportButtons/SessionRecap/H5Sheet/H5Shell/h5LearnMemory/selfLearningApi 均为
 *    h5shared + learn 组已落盘移植件，签名已按实际文件核对。
 *
 * 功能面（零裁剪）：教材树 → 章节抽屉（两级手风琴+最近3章+深链 ?chapter_id=&tab=）→
 * 九 Tab（课件/闯关/知识点/语音视频/背诵默写/笔记/章节错题/章节记忆/AI 资源）+
 * 题库闯关 H5PracticeSet + 三档 AI 生成练习 H5TierPractice + 本章错题重练 H5WrongReview +
 * 一键生成本章课件书 + 课件内嵌阅读 overlay + H5NotesTab + 会话收尾卡 + 题目反馈三键 +
 * 答题上报 grade-exercise（失败入 outbox）+ 错题收藏 mother-questions。
 */
import React, { Suspense, useEffect, useState, useCallback, useMemo } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  ReadOutlined,
  RightOutlined,
  DownOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  AimOutlined,
  FileTextOutlined,
  MessageOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import {
  fetchTextbookTree,
  fetchChapterResources,
  fetchChapterOverview,
  fetchChapterBooksInherited,
  createChapterBook,
  fetchWrongQuestionsByChapter,
  fetchLearnerProfile,
} from "./h5shared/selfLearningApi";
import type {
  LearnerProfileDto,
  TextbookNode,
  ChapterNode,
  ChapterResources,
} from "./h5shared/selfLearningApi";
import { withU } from "./h5shared/h5Utils";
import {
  readLastChapter,
  readRecentChapters,
  rememberChapter as memRememberChapter,
} from "./h5shared/h5LearnMemory";
import type { H5RecentChapter } from "./h5shared/h5LearnMemory";
import MarkdownRenderer from "../admin/MarkdownRenderer";
import { MathWidget } from "../admin/MathWidget";
import { ReciteTab } from "./learn/ReciteTab";
import { H5ExportButtons } from "./learn/H5ExportButtons";
import { SessionRecap, postQuestionFeedback, postSessionSummary } from "./h5shared/sessionRecap";
import { H5Shell } from "./h5shared/H5Shell";
import { H5Sheet } from "./h5shared/H5Sheet";

/** Tailwind 调色板对位（slate 系，取 tailwind v3 标准色值）。 */
const SLATE = {
  50: "#f8fafc",
  100: "#f1f5f9",
  200: "#e2e8f0",
  300: "#cbd5e1",
  400: "#94a3b8",
  500: "#64748b",
  600: "#475569",
  700: "#334155",
  800: "#1e293b",
} as const;
const BORDER = "#e5e7eb";
const SHADOW = "0 1px 3px rgba(0,0,0,.1), 0 1px 2px rgba(0,0,0,.06)";
const CARD_WHITE: React.CSSProperties = {
  background: "#fff",
  borderRadius: 16,
  boxShadow: SHADOW,
  border: `1px solid ${BORDER}`,
};
/** 原 line-clamp-3 */
const CLAMP3: React.CSSProperties = {
  display: "-webkit-box",
  WebkitLineClamp: 3,
  WebkitBoxOrient: "vertical",
  overflow: "hidden",
};
/** 原 "mt-6 text-center text-slate-400 text-sm py-10"（个别处 marginTop 覆写为 0）。 */
const EMPTY_CENTER: React.CSSProperties = {
  marginTop: 24,
  textAlign: "center",
  color: SLATE[400],
  fontSize: 14,
  padding: "40px 0",
};
/** 原 "flex items-center justify-center py-10 text-slate-400"（LoadingOutlined 另加）。 */
const LOAD_CENTER: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "40px 0",
  color: SLATE[400],
};

/**
 * H5 自包含学习页（design: H5 自包含闭环，不跳桌面工作台）。
 *
 * 教材树 → 章节 → 课件（PDF/HTML 链接）+ 闯关练习（即时反馈）。
 * 用户标识 u 透传（?u=小明）。
 */

/** 闯关题组（H5 精简版，即时反馈 + 答题上报学习引擎，总纲 G1）。 */
function H5PracticeSet({ set, u, chapterId }: {
  set: { title: string; priority?: number; adaptive_reason?: string; questions: any[] };
  u?: string;
  chapterId?: string;
}) {
  const [idx, setIdx] = useState(0);
  const [answered, setAnswered] = useState<Record<number, boolean>>({});
  const [result, setResult] = useState<Record<number, boolean>>({});
  // W2（第八篇 M16-B）：答对手动收藏到错题本（答错已由后端自动沉淀）
  const [favSaved, setFavSaved] = useState<Record<number, boolean>>({});
  const [favSaving, setFavSaving] = useState(false);
  // C4（M18-B）：整组完成 → 会话收尾卡
  const [recapOpen, setRecapOpen] = useState(false);
  const [recapDone, setRecapDone] = useState(false);
  const questions = set.questions || [];
  const total = questions.length;
  const q = questions[idx];
  const answeredCount = Object.keys(answered).length;
  const correctCount = Object.keys(answered).filter((k) => result[+k]).length;

  useEffect(() => {
    if (!recapDone && total > 0 && answeredCount === total) {
      setRecapOpen(true);
      setRecapDone(true);
    }
  }, [answeredCount, total, recapDone]);

  if (total === 0) return null;

  // 答题进引擎（总纲 G1）：fire-and-forget 上报，不阻塞即时反馈。
  // 复用 POST /api/v1/learning/grade-exercise -> 判题/掌握度/FSRS/错题/记忆。
  // E3（M12）：带 attempt_id（后端幂等）；断网/失败时入 outbox，联网后重放。
  const reportToEngine = (userAnswer: string | number) => {
    if (!chapterId || !set.title) return;
    try {
      const exId = set.title;
      const qIndex = questions.findIndex((x) => x === q);
      const questionId = `${exId}#${Math.max(0, qIndex)}`;
      const expected = Array.isArray(q.answer) ? q.answer.join(";") : String(q.answer ?? "");
      const qs = u ? `?u=${encodeURIComponent(u)}` : "";
      const attemptId =
        (typeof crypto !== "undefined" && crypto.randomUUID
          ? crypto.randomUUID()
          : `a${Date.now()}-${Math.random().toString(36).slice(2, 8)}`);
      const body = {
        attempt_id: attemptId,
        chapter_id: chapterId,
        question_id: questionId,
        question_type: q.type === "choice" ? "choice" : "fill",
        question_text: q.ask || "",
        user_answer: String(userAnswer),
        expected_answer: expected,
        kp_id: q.kp_id || "",
        u: u || "",
      };
      void fetch(
        `/api/v1/learning/grade-exercise${qs}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      )
        .then(async (r) => {
          if (!r.ok) throw new Error(`http ${r.status}`);
          return r.json();
        })
        .catch(() => {
          // E3 离线/失败：暂存 outbox，联网后自动重放（副作用由后端幂等去重）
          import("./h5shared/h5Outbox")
            .then((m) =>
              m.enqueue({
                attempt_id: attemptId,
                url: `/api/v1/learning/grade-exercise${qs}`,
                body,
                ts: Date.now(),
                retries: 0,
              }),
            )
            .catch(() => { /* noop */ });
        });
    } catch { /* noop */ }
  };

  const check = (userAnswer: string | number) => {
    if (answered[idx]) return;
    const correct = Array.isArray(q.answer)
      ? q.answer.map(String).includes(String(userAnswer))
      : String(q.answer) === String(userAnswer);
    setResult((r) => ({ ...r, [idx]: correct }));
    setAnswered((a) => ({ ...a, [idx]: true }));
    reportToEngine(userAnswer);
  };

  // W2：答对但想收藏 -> 手动入库（带 u 隔离 + src:practice）
  const saveFav = async () => {
    if (favSaved[idx] || favSaving) return;
    setFavSaving(true);
    try {
      const qs = u ? `?u=${encodeURIComponent(u)}` : "";
      const res = await fetch(`/api/v1/mother-questions${qs}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: (q.ask || "").slice(0, 20),
          question_text: q.ask || "",
          standard_answer: Array.isArray(q.answer) ? q.answer.join(" / ") : String(q.answer ?? ""),
          tags: ["h5", "manual", "src:practice", ...(u ? [`u:${u}`] : [])],
          subject: "math",
        }),
      });
      if (res.status === 409) alert("这道题已在错题本 📖");
      else if (res.ok) {
        setFavSaved((s) => ({ ...s, [idx]: true }));
        alert("已收藏到错题本 📖，系统会安排复习");
      } else alert("收藏失败，请重试");
    } catch {
      alert("网络错误，请重试");
    } finally {
      setFavSaving(false);
    }
  };

  return (
    <div style={{ ...CARD_WHITE, padding: 12, marginBottom: 12 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
        <span style={{ fontWeight: 500, fontSize: 14 }}>
          {set.title}
          {set.adaptive_reason === "weak" && (
            <span style={{ marginLeft: 8, padding: "2px 6px", borderRadius: 4, background: "#ffe4e6", color: "#e11d48", fontSize: 11, fontWeight: 500 }}>薄弱优先</span>
          )}
          {set.adaptive_reason === "due" && (
            <span style={{ marginLeft: 8, padding: "2px 6px", borderRadius: 4, background: "#fef3c7", color: "#b45309", fontSize: 11, fontWeight: 500 }}>到期复习</span>
          )}
        </span>
        <span style={{ fontSize: 12, color: SLATE[400] }}>
          第 {idx + 1}/{total} 题
        </span>
      </div>
      <p style={{ fontSize: 14, margin: "0 0 12px" }}>{q.ask}</p>
      {q.type === "choice" && (q.options || []).map((opt: string, i: number) => (
        <button
          key={i}
          onClick={() => check(i)}
          disabled={!!answered[idx]}
          style={{
            width: "100%", textAlign: "left", padding: "8px 12px", marginBottom: 4,
            borderRadius: 8, fontSize: 14, transition: "all .15s",
            ...(answered[idx] && String(i) === String(q.answer)
              ? { border: "1px solid #34d399", background: "#ecfdf5" }
              : answered[idx]
                ? { border: `1px solid ${SLATE[200]}`, background: SLATE[50] }
                : { border: `1px solid ${SLATE[200]}`, background: "#fff" }),
          }}
        >
          {String.fromCharCode(65 + i)}. {opt}
        </button>
      ))}
      {q.type !== "choice" && (
        <div style={{ display: "flex", gap: 8 }}>
          <input
            style={{ flex: 1, minWidth: 0, padding: "8px 12px", borderRadius: 8, border: `1px solid ${BORDER}`, background: "transparent", fontSize: 14 }}
            placeholder="输入答案"
            onKeyDown={(e) => {
              if (e.key === "Enter") check((e.target as HTMLInputElement).value);
            }}
          />
          <button onClick={() => check("")} style={{ padding: "8px 12px", borderRadius: 8, border: `1px solid ${BORDER}`, fontSize: 14, background: "transparent" }}>
            提交
          </button>
        </div>
      )}
      {answered[idx] && (
        <div style={{ marginTop: 8, fontSize: 14, display: "flex", alignItems: "flex-start", gap: 4, color: result[idx] ? "#059669" : "#f43f5e" }}>
          {result[idx] ? <CheckCircleOutlined style={{ fontSize: 16, flexShrink: 0, marginTop: 2 }} /> : <CloseCircleOutlined style={{ fontSize: 16, flexShrink: 0, marginTop: 2 }} />}
          <div>
            {result[idx] ? "答对啦！" : `正确答案：${Array.isArray(q.answer) ? q.answer.join(" / ") : q.answer}`}
            {q.why && <div style={{ fontSize: 12, color: SLATE[500], marginTop: 2 }}>{q.why}</div>}
            {/* W2（第八篇）：答错自动入库提示 / 答对可手动收藏 */}
            {!result[idx] && (
              <div style={{ marginTop: 4, display: "flex", flexWrap: "wrap", alignItems: "center", columnGap: 8, rowGap: 4 }}>
                <span style={{ fontSize: 12, color: "#059669", display: "flex", alignItems: "center", gap: 4 }}>
                  📖 已自动加入错题本（含章节归属）
                </span>
                {/* W4（第八篇 M16-C）：练习答错一键问 AI */}
                <Link
                  to={withU(
                    `/e/tutor-h5/chat?text=${encodeURIComponent(`这道题我不会，帮我讲讲：\n${q.ask || ""}`)}`,
                    u,
                  )}
                  style={{ fontSize: 12, color: "#0284c7", textDecoration: "underline", display: "inline-flex", alignItems: "center", gap: 2 }}
                >
                  <MessageOutlined style={{ fontSize: 12 }} /> 问 AI 为什么
                </Link>
              </div>
            )}
            {result[idx] && !favSaved[idx] && (
              <button
                onClick={() => void saveFav()}
                disabled={favSaving}
                style={{ marginTop: 4, display: "inline-flex", alignItems: "center", gap: 4, fontSize: 12, padding: "4px 10px", borderRadius: 8, background: "#fffbeb", border: "1px solid #fde68a", color: "#b45309", opacity: favSaving ? 0.5 : 1 }}
              >
                {favSaving ? "收藏中…" : "＋ 收藏到错题本"}
              </button>
            )}
            {result[idx] && favSaved[idx] && (
              <div style={{ fontSize: 12, color: "#059669", marginTop: 2 }}>已收藏到错题本 ✓</div>
            )}
          </div>
        </div>
      )}
      <div style={{ marginTop: 12, display: "flex", justifyContent: "space-between" }}>
        <button
          onClick={() => setIdx((i) => Math.max(0, i - 1))}
          disabled={idx === 0}
          style={{ padding: "6px 12px", borderRadius: 8, border: `1px solid ${BORDER}`, fontSize: 14, background: "transparent", opacity: idx === 0 ? 0.4 : 1 }}
        >
          上一题
        </button>
        <span style={{ fontSize: 12, color: SLATE[400], alignSelf: "center" }}>
          答对 {Object.keys(answered).filter((k) => result[+k]).length}/{total}
        </span>
        <button
          onClick={() => setIdx((i) => Math.min(total - 1, i + 1))}
          disabled={idx === total - 1}
          style={{ padding: "6px 12px", borderRadius: 8, border: `1px solid ${BORDER}`, fontSize: 14, background: "transparent", opacity: idx === total - 1 ? 0.4 : 1 }}
        >
          下一题
        </button>
      </div>
      {/* C4（M18-B）：整组答完 → 会话收尾卡（C5 episodic 同步入记忆） */}
      <SessionRecap
        open={recapOpen}
        onClose={() => setRecapOpen(false)}
        topic={set.title}
        questions={total}
        correct={correctCount}
        source="practice"
        u={u}
      />
    </div>
  );
}

/**
 * PG-3（M15）：三档难度 AI 生成练习（第七篇 §一/PG-1~PG-3）。
 *
 * 闯关区保留题库闯关（下方「⚔️ 闯关」原样），此区为 AI 生成练习：
 * segmented 三档（默认=画像推荐档）→ 读缓存题组（GET practice）→
 * 无题时「✨ 生成新题」（POST generate-practice，60s 冷却）。
 * 作答上报 grade-exercise 带 kp_id/expected_answer_pg（PG-2 直填，
 * 掌握度落在题目声明的真实 KP，非 ex_ 占位）。
 */
function H5TierPractice({ u, chapterId }: { u?: string; chapterId?: string }) {
  const TIER_META: Record<string, { label: string; icon: string }> = {
    basic: { label: "🌱 基础", icon: "🌱" },
    intermediate: { label: "🌲 提高", icon: "🌲" },
    advanced: { label: "🔥 挑战", icon: "🔥" },
  };
  const TIER_ORDER = ["basic", "intermediate", "advanced"];

  const [tier, setTier] = useState<string>("basic");
  const [recommended, setRecommended] = useState<string>("intermediate");
  const [questions, setQuestions] = useState<any[]>([]);
  const [version, setVersion] = useState(0);
  const [versionCount, setVersionCount] = useState(0);
  const [cooldown, setCooldown] = useState(0);
  const [generating, setGenerating] = useState(false);
  const [loading, setLoading] = useState(false);
  const [initDone, setInitDone] = useState(false);
  const [err, setErr] = useState("");
  const [idx, setIdx] = useState(0);
  const [answered, setAnswered] = useState<Record<number, boolean>>({});
  const [result, setResult] = useState<Record<number, boolean>>({});
  const [favSaved, setFavSaved] = useState<Record<number, boolean>>({});
  const [favSaving, setFavSaving] = useState(false);
  // C4（M18-B）：整组完成 → 收尾卡；C7：题目反馈三键（每题一次）
  const [recapOpen, setRecapOpen] = useState(false);
  const [recapDone, setRecapDone] = useState(false);
  const [fbGiven, setFbGiven] = useState<Record<number, string>>({});
  const answeredCount = Object.keys(answered).length;
  const correctCount = Object.keys(answered).filter((k) => result[+k]).length;

  useEffect(() => {
    if (!recapDone && questions.length > 0 && answeredCount === questions.length) {
      setRecapOpen(true);
      setRecapDone(true);
    }
  }, [answeredCount, questions.length, recapDone]);

  const giveFeedback = (tag: "too_hard" | "too_easy" | "wrong") => {
    if (fbGiven[idx]) return;
    setFbGiven((s) => ({ ...s, [idx]: tag }));
    postQuestionFeedback(u, {
      chapter_id: chapterId || "",
      tier,
      version,
      question_id: `gen:${chapterId}:${tier}:${version}#${idx}`,
      tag,
      question_text: questions[idx]?.ask || "",
    });
  };

  const qs = u ? `&u=${encodeURIComponent(u)}` : "";
  const qsClean = qs ? qs.slice(1) : "";

  const loadTier = useCallback(
    async (targetTier: string) => {
      if (!chapterId) return;
      setLoading(true);
      setErr("");
      try {
        const res = await fetch(
          `/api/v1/learning/practice?chapter_id=${encodeURIComponent(chapterId)}&tier=${encodeURIComponent(targetTier)}${qs}`,
        );
        if (!res.ok) throw new Error(`http ${res.status}`);
        const data = await res.json();
        setTier(targetTier);
        setRecommended(data.recommended_tier || "intermediate");
        setQuestions(data.questions || []);
        setVersion(data.version ?? 0);
        setVersionCount(data.version_count ?? 0);
        setCooldown(data.cooldown ?? 0);
        setIdx(0);
        setAnswered({});
        setResult({});
        setFavSaved({});
      } catch {
        setErr("加载生成练习失败");
      } finally {
        setLoading(false);
      }
    },
    [chapterId, u],
  );

  // 初次进入：取推荐档并加载
  useEffect(() => {
    if (!chapterId || initDone) return;
    let alive = true;
    void (async () => {
      try {
        const res = await fetch(
          `/api/v1/learning/practice?chapter_id=${encodeURIComponent(chapterId)}&tier=basic${qs}`,
        );
        if (!res.ok) return;
        const data = await res.json();
        if (!alive) return;
        const rec = data.recommended_tier || "basic";
        setRecommended(rec);
        setTier(rec);
        // 推荐档可能已有缓存题；没有则先展示 basic 档（空态提示生成）
        if (rec !== "basic" && !(data.questions || []).length) {
          const res2 = await fetch(
            `/api/v1/learning/practice?chapter_id=${encodeURIComponent(chapterId)}&tier=${encodeURIComponent(rec)}${qs}`,
          );
          if (res2.ok) {
            const d2 = await res2.json();
            if (!alive) return;
            setQuestions(d2.questions || []);
            setVersion(d2.version ?? 0);
            setVersionCount(d2.version_count ?? 0);
            setCooldown(d2.cooldown ?? 0);
            return;
          }
        }
        setQuestions(data.questions || []);
        setVersion(data.version ?? 0);
        setVersionCount(data.version_count ?? 0);
        setCooldown(data.cooldown ?? 0);
      } catch {
        /* noop */
      } finally {
        if (alive) setInitDone(true);
      }
    })();
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapterId, u]);

  // 冷却倒计时
  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setInterval(() => setCooldown((c) => Math.max(0, c - 1)), 1000);
    return () => clearInterval(t);
  }, [cooldown > 0]);

  const generate = async () => {
    if (!chapterId || generating) return;
    setGenerating(true);
    setErr("");
    try {
      // 生成耗时 20-30s+，直连后端绕过 Next proxy 30s 超时（同批量 OCR 处理）
      // （tupu 无 Next proxy，backendUrl(x) 脱壳为同字面相对路径）
      const res = await fetch(
        `/api/v1/learning/generate-practice?${qsClean}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ chapter_id: chapterId, tier, count: 5, u: u || "" }),
        },
      );
      if (res.status === 409) {
        const d = await res.json().catch(() => ({}));
        const m = String(d.detail || "");
        const s = m.match(/\d+/);
        setCooldown(s ? parseInt(s[0], 10) : 60);
        setErr(m || "生成太频繁，请稍后再试");
        return;
      }
      if (res.status === 503) {
        setErr("AI 未配置，暂不能生成新题");
        return;
      }
      if (!res.ok) throw new Error(`http ${res.status}`);
      const data = await res.json();
      setQuestions(data.questions || []);
      setVersion(data.version ?? 0);
      setVersionCount(data.version_count ?? 0);
      setCooldown(data.cooldown ?? 60);
      setIdx(0);
      setAnswered({});
      setResult({});
      setFavSaved({});
    } catch {
      setErr("生成失败，请重试");
    } finally {
      setGenerating(false);
    }
  };

  const rotate = async () => {
    if (!chapterId || versionCount <= 1) return;
    try {
      const res = await fetch(
        `/api/v1/learning/practice/rotate?chapter_id=${encodeURIComponent(chapterId)}&tier=${encodeURIComponent(tier)}${qs}`,
      );
      if (!res.ok) return;
      const data = await res.json();
      setQuestions(data.questions || []);
      setVersion(data.version ?? 0);
      setVersionCount(data.version_count ?? 0);
      setIdx(0);
      setAnswered({});
      setResult({});
      setFavSaved({});
    } catch {
      /* noop */
    }
  };

  // PG-2 作答上报：带 kp_id + expected_answer_pg 直填
  const report = (userAnswer: string) => {
    if (!chapterId) return;
    const q = questions[idx];
    if (!q) return;
    const attemptId =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `a${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const body = {
      attempt_id: attemptId,
      chapter_id: chapterId,
      question_id: `gen:${chapterId}:${tier}:${version}#${idx}`,
      question_type: q.type === "choice" ? "choice" : "fill",
      question_text: q.ask || "",
      user_answer: String(userAnswer),
      expected_answer_pg: String(q.answer ?? ""),
      kp_id: q.kp_id || "",
      u: u || "",
    };
    void fetch(`/api/v1/learning/grade-exercise${qsClean ? `?${qsClean}` : ""}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).catch(() => { /* noop */ });
  };

  const check = (userAnswer: string | number) => {
    if (answered[idx] || !questions[idx]) return;
    const q = questions[idx];
    const correct =
      q.type === "choice"
        ? String(q.answer).toUpperCase() ===
          (typeof userAnswer === "number" ? String.fromCharCode(65 + userAnswer) : String(userAnswer).toUpperCase())
        : String(q.answer) === String(userAnswer);
    setResult((r) => ({ ...r, [idx]: correct }));
    setAnswered((a) => ({ ...a, [idx]: true }));
    report(typeof userAnswer === "number" ? String.fromCharCode(65 + userAnswer) : userAnswer);
  };

  const saveFav = async () => {
    if (favSaved[idx] || favSaving || !questions[idx]) return;
    setFavSaving(true);
    const q = questions[idx];
    try {
      const res = await fetch(`/api/v1/mother-questions${qsClean ? `?${qsClean}` : ""}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: (q.ask || "").slice(0, 20),
          question_text: q.ask || "",
          standard_answer: String(q.answer ?? ""),
          kp_id: q.kp_id || undefined,
          tags: ["h5", "manual", "src:practice", ...(u ? [`u:${u}`] : [])],
          subject: "math",
        }),
      });
      if (res.status === 409) alert("这道题已在错题本 📖");
      else if (res.ok) {
        setFavSaved((s) => ({ ...s, [idx]: true }));
        alert("已收藏到错题本 📖，系统会安排复习");
      } else alert("收藏失败，请重试");
    } catch {
      alert("网络错误，请重试");
    } finally {
      setFavSaving(false);
    }
  };

  if (!chapterId) return null;
  const q = questions[idx];
  const total = questions.length;

  return (
    <div style={{ ...CARD_WHITE, padding: 12, marginBottom: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
        <ThunderboltOutlined style={{ fontSize: 16, color: "#8b5cf6" }} />
        <span style={{ fontWeight: 500, fontSize: 14 }}>AI 生成练习</span>
        <span style={{ fontSize: 10, color: SLATE[400] }}>（三档难度 · 自动归入本章知识点）</span>
      </div>

      {/* 三档 segmented（默认=推荐档） */}
      <div style={{ display: "flex", borderRadius: 12, background: SLATE[100], padding: 4, marginBottom: 12 }}>
        {TIER_ORDER.map((k) => (
          <button
            key={k}
            onClick={() => void loadTier(k)}
            style={{
              flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 4,
              padding: "6px 0", borderRadius: 8, fontSize: 14, transition: "all .15s", border: "none",
              ...(tier === k ? { background: "#fff", boxShadow: SHADOW, color: SLATE[800], fontWeight: 500 } : { background: "transparent", color: SLATE[500] }),
            }}
          >
            <span>{TIER_META[k].icon}</span>
            <span>{TIER_META[k].label}</span>
            {k === recommended && (
              <span style={{ padding: "2px 4px", borderRadius: 4, background: "#ede9fe", color: "#7c3aed", fontSize: 10, fontWeight: 500 }}>推荐</span>
            )}
          </button>
        ))}
      </div>

      {loading ? (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "32px 0", color: SLATE[400], fontSize: 14 }}>
          <LoadingOutlined spin style={{ fontSize: 16, marginRight: 8 }} /> 加载中…
        </div>
      ) : total === 0 ? (
        <div style={{ textAlign: "center", padding: "24px 0" }}>
          <div style={{ fontSize: 14, color: SLATE[500], marginBottom: 12 }}>
            {tier === "advanced"
              ? "挑战档以本章错题为种子出变式"
              : "还没有该档练习，点击生成一组新题"}
          </div>
          <button
            onClick={() => void generate()}
            disabled={generating || cooldown > 0}
            style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "10px 16px", borderRadius: 16, background: "#7c3aed", color: "#fff", fontSize: 14, fontWeight: 500, border: "none", opacity: generating || cooldown > 0 ? 0.5 : 1 }}
          >
            {generating ? (
              <>
                <LoadingOutlined spin style={{ fontSize: 16 }} /> 生成中（约 15 秒）…
              </>
            ) : cooldown > 0 ? (
              <>{cooldown}s 后可再次生成</>
            ) : (
              <>
                <ThunderboltOutlined style={{ fontSize: 16 }} /> ✨ 生成新题
              </>
            )}
          </button>
          {err && <div style={{ fontSize: 12, color: "#f43f5e", marginTop: 8 }}>{err}</div>}
        </div>
      ) : (
        <>
          {/* 题组操作：换一批 / 生成新题 */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 8, marginBottom: 8 }}>
            {versionCount > 1 && (
              <button
                onClick={() => void rotate()}
                style={{ display: "inline-flex", alignItems: "center", gap: 4, padding: "4px 10px", borderRadius: 8, border: `1px solid ${BORDER}`, fontSize: 12, color: SLATE[600], background: "transparent" }}
              >
                <ReloadOutlined style={{ fontSize: 12 }} /> 换一批
              </button>
            )}
            <button
              onClick={() => void generate()}
              disabled={generating || cooldown > 0}
              style={{ display: "inline-flex", alignItems: "center", gap: 4, padding: "4px 10px", borderRadius: 8, border: "1px solid #ddd6fe", color: "#7c3aed", fontSize: 12, background: "transparent", opacity: generating || cooldown > 0 ? 0.5 : 1 }}
            >
              {generating ? (
                <LoadingOutlined spin style={{ fontSize: 12 }} />
              ) : cooldown > 0 ? (
                <>{cooldown}s</>
              ) : (
                <ThunderboltOutlined style={{ fontSize: 12 }} />
              )}
              {cooldown > 0 ? "生成冷却" : "生成新题"}
            </button>
          </div>

          <p style={{ fontSize: 14, margin: "0 0 12px" }}>{q.ask}</p>
          {q.type === "choice" && (q.options || []).map((opt: string, i: number) => (
            <button
              key={i}
              onClick={() => check(i)}
              disabled={!!answered[idx]}
              style={{
                width: "100%", textAlign: "left", padding: "8px 12px", marginBottom: 4,
                borderRadius: 8, fontSize: 14, transition: "all .15s",
                ...(answered[idx] && String.fromCharCode(65 + i) === String(q.answer).toUpperCase()
                  ? { border: "1px solid #34d399", background: "#ecfdf5" }
                  : answered[idx]
                    ? { border: `1px solid ${SLATE[200]}`, background: SLATE[50] }
                    : { border: `1px solid ${SLATE[200]}`, background: "#fff" }),
              }}
            >
              {String.fromCharCode(65 + i)}. {opt}
            </button>
          ))}
          {q.type !== "choice" && (
            <div style={{ display: "flex", gap: 8 }}>
              <input
                style={{ flex: 1, minWidth: 0, padding: "8px 12px", borderRadius: 8, border: `1px solid ${BORDER}`, background: "transparent", fontSize: 14 }}
                placeholder="输入答案"
                onKeyDown={(e) => {
                  if (e.key === "Enter") check((e.target as HTMLInputElement).value);
                }}
              />
              <button onClick={() => check("")} style={{ padding: "8px 12px", borderRadius: 8, border: `1px solid ${BORDER}`, fontSize: 14, background: "transparent" }}>
                提交
              </button>
            </div>
          )}
          {answered[idx] && (
            <div style={{ marginTop: 8, fontSize: 14, display: "flex", alignItems: "flex-start", gap: 4, color: result[idx] ? "#059669" : "#f43f5e" }}>
              {result[idx] ? (
                <CheckCircleOutlined style={{ fontSize: 16, flexShrink: 0, marginTop: 2 }} />
              ) : (
                <CloseCircleOutlined style={{ fontSize: 16, flexShrink: 0, marginTop: 2 }} />
              )}
              <div>
                {result[idx] ? "答对啦！" : `正确答案：${q.answer}`}
                {!result[idx] && (
                  <div style={{ marginTop: 4, display: "flex", flexWrap: "wrap", alignItems: "center", columnGap: 8, rowGap: 4 }}>
                    <span style={{ fontSize: 12, color: "#059669", display: "flex", alignItems: "center", gap: 4 }}>
                      📖 已自动加入错题本（含章节归属）
                    </span>
                    <Link
                      to={withU(
                        `/e/tutor-h5/chat?text=${encodeURIComponent(`这道题我不会，帮我讲讲：\n${q.ask || ""}`)}`,
                        u,
                      )}
                      style={{ fontSize: 12, color: "#0284c7", textDecoration: "underline", display: "inline-flex", alignItems: "center", gap: 2 }}
                    >
                      <MessageOutlined style={{ fontSize: 12 }} /> 问 AI 为什么
                    </Link>
                  </div>
                )}
                {result[idx] && !favSaved[idx] && (
                  <button
                    onClick={() => void saveFav()}
                    disabled={favSaving}
                    style={{ marginTop: 4, display: "inline-flex", alignItems: "center", gap: 4, fontSize: 12, padding: "4px 10px", borderRadius: 8, background: "#fffbeb", border: "1px solid #fde68a", color: "#b45309", opacity: favSaving ? 0.5 : 1 }}
                  >
                    {favSaving ? "收藏中…" : "＋ 收藏到错题本"}
                  </button>
                )}
                {result[idx] && favSaved[idx] && (
                  <div style={{ fontSize: 12, color: "#059669", marginTop: 2 }}>已收藏到错题本 ✓</div>
                )}
                {/* C7（M18-C）：生成题反馈三键（每题一次，入库供 PG 调优） */}
                <div style={{ marginTop: 6, display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 10, color: SLATE[400] }}>这道题：</span>
                  {([["too_hard", "太难"], ["too_easy", "太简单"], ["wrong", "题有误"]] as const).map(([tag, label]) => (
                    fbGiven[idx] ? (
                      fbGiven[idx] === tag ? (
                        <span key={tag} style={{ fontSize: 11, padding: "2px 8px", borderRadius: 8, background: "#ede9fe", color: "#7c3aed" }}>
                          已反馈「{label}」✓
                        </span>
                      ) : null
                    ) : (
                      <button
                        key={tag}
                        onClick={() => giveFeedback(tag)}
                        style={{ fontSize: 11, padding: "2px 8px", borderRadius: 8, border: `1px solid ${SLATE[200]}`, color: SLATE[500], background: "transparent" }}
                      >
                        {label}
                      </button>
                    )
                  ))}
                </div>
              </div>
            </div>
          )}
          <div style={{ marginTop: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <button
              onClick={() => setIdx((i) => Math.max(0, i - 1))}
              disabled={idx === 0}
              style={{ padding: "6px 12px", borderRadius: 8, border: `1px solid ${BORDER}`, fontSize: 14, background: "transparent", opacity: idx === 0 ? 0.4 : 1 }}
            >
              上一题
            </button>
            <span style={{ fontSize: 12, color: SLATE[400], alignSelf: "center" }}>
              第 {idx + 1}/{total} 题 · 答对 {Object.keys(answered).filter((k) => result[+k]).length}
            </span>
            <button
              onClick={() => setIdx((i) => Math.min(total - 1, i + 1))}
              disabled={idx === total - 1}
              style={{ padding: "6px 12px", borderRadius: 8, border: `1px solid ${BORDER}`, fontSize: 14, background: "transparent", opacity: idx === total - 1 ? 0.4 : 1 }}
            >
              下一题
            </button>
          </div>
          {/* C4（M18-B）：整组答完 → 会话收尾卡 */}
          <SessionRecap
            open={recapOpen}
            onClose={() => setRecapOpen(false)}
            topic={`AI 生成练习 · ${TIER_META[tier]?.label || tier}`}
            questions={total}
            correct={correctCount}
            source="practice"
            u={u}
          />
        </>
      )}
    </div>
  );
}

/**
 * PG-4（M15）：本章错题重练底部弹层（第七篇 §五）。
 * 自评流：题面 -> 「忘记/模糊/记住」-> POST review/submit（FSRS 推进）-> 下一题。
 * 与 wrongbook 复习同一状态机，数据零复制（items 复用 F2 章节错题列表）。
 */
function H5WrongReview({
  u,
  items,
  open,
  onClose,
}: {
  u?: string;
  items: any[];
  open: boolean;
  onClose: () => void;
}) {
  const [idx, setIdx] = useState(0);
  const [rated, setRated] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [nextReview, setNextReview] = useState("");

  useEffect(() => {
    if (!open) return;
    setIdx(0);
    setRated(false);
    setDone(false);
    setNextReview("");
  }, [open]);

  if (!open) return null;
  const total = items.length;
  const q = items[idx];

  const submit = async (rating: number) => {
    if (submitting || !q) return;
    setSubmitting(true);
    try {
      const qs = u ? `?u=${encodeURIComponent(u)}` : "";
      const res = await fetch(
        `/api/v1/mother-questions/${q.id}/review/submit${qs}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ rating }),
        },
      );
      if (res.ok) {
        const d = await res.json();
        const due = d?.new_state?.due || d?.card?.due || d?.next_review_at || "";
        setNextReview(due ? new Date(Number(due) * 1000).toLocaleString("zh-CN") : "");
        setRated(true);
      }
    } catch {
      /* noop */
    } finally {
      setSubmitting(false);
    }
  };

  const next = () => {
    if (idx + 1 < total) {
      setIdx(idx + 1);
      setRated(false);
      setNextReview("");
    } else {
      setDone(true);
      // C5（M18-B）：复习收尾入 episodic 记忆
      postSessionSummary(u, {
        topics: [],
        wins: [`完成 ${total} 道错题重练`],
        stuck: "",
        questions: total,
        correct: total,
        source: "review",
      });
    }
  };

  return (
    // S1（M23）：H5Sheet 统一基座（max-h + 内滚 + Esc 关）
    <H5Sheet open={open} onClose={onClose} title="❌ 本章错题重练">
      <div style={{ padding: "0 20px", paddingBottom: "max(1rem, env(safe-area-inset-bottom))" }}>
        {done ? (
          <div style={{ textAlign: "center", padding: "32px 0" }}>
            <CheckCircleOutlined style={{ fontSize: 32, color: "#10b981", display: "block", margin: "0 auto 8px" }} />
            <div style={{ fontSize: 14, fontWeight: 500 }}>✅ 完成 {total} 道错题复习</div>
            <div style={{ fontSize: 12, color: SLATE[500], marginTop: 4 }}>FSRS 已更新，系统会按遗忘曲线安排下次复习</div>
            <button
              onClick={onClose}
              style={{ marginTop: 16, padding: "8px 16px", borderRadius: 12, background: "#7c3aed", color: "#fff", fontSize: 14, border: "none" }}
            >
              完成
            </button>
          </div>
        ) : total === 0 ? (
          <div style={{ textAlign: "center", padding: "40px 0", color: SLATE[400], fontSize: 14 }}>本章还没有错题，去闯关吧</div>
        ) : !q ? (
          <div style={{ textAlign: "center", padding: "40px 0", color: SLATE[400], fontSize: 14 }}>加载中…</div>
        ) : (
          <>
            <div style={{ fontSize: 12, color: SLATE[400], marginBottom: 8 }}>第 {idx + 1}/{total} 题</div>
            <div style={{ background: SLATE[50], borderRadius: 12, border: `1px solid ${BORDER}`, padding: 12, marginBottom: 12 }}>
              <p style={{ fontSize: 14, margin: 0 }}>{q.question_text || q.title}</p>
              {q.wrong_answer && (
                <div style={{ marginTop: 8, fontSize: 12, color: "#f43f5e" }}>我的错答：{q.wrong_answer}</div>
              )}
              {q.wrong_reason && (
                <div style={{ marginTop: 4, fontSize: 12, color: "#d97706" }}>错因：{q.wrong_reason}</div>
              )}
            </div>
            {!rated ? (
              // G4（M24-A）：与桌面 4 档 FSRS 对齐（1 忘记 / 2 困难 / 3 良好 / 4 简单）
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 6 }}>
                <button
                  onClick={() => void submit(1)}
                  disabled={submitting}
                  style={{ padding: "12px 4px", borderRadius: 12, border: "1px solid #fecdd3", color: "#e11d48", fontSize: 14, background: "transparent", opacity: submitting ? 0.5 : 1 }}
                >
                  😵 忘记
                </button>
                <button
                  onClick={() => void submit(2)}
                  disabled={submitting}
                  style={{ padding: "12px 4px", borderRadius: 12, border: "1px solid #fde68a", color: "#b45309", fontSize: 14, background: "transparent", opacity: submitting ? 0.5 : 1 }}
                >
                  🤔 模糊
                </button>
                <button
                  onClick={() => void submit(3)}
                  disabled={submitting}
                  style={{ padding: "12px 4px", borderRadius: 12, border: "1px solid #bae6fd", color: "#0284c7", fontSize: 14, background: "transparent", opacity: submitting ? 0.5 : 1 }}
                >
                  🙂 记住
                </button>
                <button
                  onClick={() => void submit(4)}
                  disabled={submitting}
                  style={{ padding: "12px 4px", borderRadius: 12, border: "1px solid #a7f3d0", color: "#059669", fontSize: 14, background: "transparent", opacity: submitting ? 0.5 : 1 }}
                >
                  😄 简单
                </button>
              </div>
            ) : (
              <div>
                <div style={{ fontSize: 12, color: "#059669", marginBottom: 12 }}>
                  FSRS 已更新{nextReview ? `，下次复习：${nextReview}` : ""}
                </div>
                <button
                  onClick={next}
                  style={{ width: "100%", padding: "10px 0", borderRadius: 12, background: "#7c3aed", color: "#fff", fontSize: 14, border: "none" }}
                >
                  {idx + 1 < total ? "下一题" : "完成全部"}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </H5Sheet>
  );
}

// T3（第十二篇）：语音资源音频报错兜底——onError 时给出可见提示而非静默失效
function VoiceAudio({ src }: { src: string }) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <div style={{ fontSize: 12, color: "#d97706", background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 12, padding: "8px 12px" }}>
        ⚠️ 音频加载失败（资源缺失或格式不支持），请联系老师重新上传
      </div>
    );
  }
  return (
    <audio
      controls
      preload="none"
      src={src}
      onError={() => setFailed(true)}
      style={{ width: "100%", height: 36 }}
    />
  );
}

function H5LearnContent() {
  const [searchParams] = useSearchParams();
  const u = searchParams.get("u") || searchParams.get("openid") || "";
  // N1（第十一篇）：下拉刷新 tick——递增触发全部章节数据重拉
  const [refreshTick, setRefreshTick] = useState(0);
  const [textbooks, setTextbooks] = useState<TextbookNode[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedChapter, setSelectedChapter] = useState<ChapterNode | null>(null);
  const [resources, setResources] = useState<ChapterResources | null>(null);
  const [resLoading, setResLoading] = useState(false);
  const [books, setBooks] = useState<any[]>([]);
  const [booksLoading, setBooksLoading] = useState(false);
  const [chapterPicker, setChapterPicker] = useState(false);
  // 内容 Tab（design T2 六 Tab + F2/F3 章节错题/记忆）：课件 / 闯关 / 知识点 / 语音视频 / 笔记 / AI 资源 / 章节错题 / 章节记忆
  const [tab, setTab] = useState<"course" | "practice" | "kp" | "voice" | "recite" | "note" | "ai" | "wrong" | "memory">("course");
  // PG-4（M15）：本章错题重练底部弹层
  const [wrongReviewOpen, setWrongReviewOpen] = useState(false);
  // U4（第六篇）：Tab 横滚渐隐指示——滚动到头渐隐消失
  const [tabScrolledEnd, setTabScrolledEnd] = useState(false);
  const [overview, setOverview] = useState<any>(null);
  // F2（M14-B）：本用户章节错题（?u= 隔离）
  const [chapterWrongs, setChapterWrongs] = useState<any[]>([]);
  const [wrongLoading, setWrongLoading] = useState(false);
  // F3（M14-B）：本用户章节记忆（KP 掌握状态 + 掌握度）
  const [learnerProfile, setLearnerProfile] = useState<LearnerProfileDto | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  // P1-A 课件内嵌阅读（页内全屏 overlay，盖住 TabBar）
  const [viewer, setViewer] = useState<{ title: string; src: string } | null>(null);
  // 课件下拉选择（精简：一行选择，选中即打开，避免课件列表占空间）
  const [selectedCourse, setSelectedCourse] = useState("");
  // R3-b 知识点卡折叠：默认收起，点击展开讲解/公式
  const [expandedKps, setExpandedKps] = useState<Set<string>>(new Set());
  // U3（第六篇）：章节抽屉——两级手风琴 + 最近 3 章 + 大触点
  const [openChapterId, setOpenChapterId] = useState<string | null>(null);
  const [recentChapters, setRecentChapters] = useState<H5RecentChapter[]>([]);

  useEffect(() => {
    // S5（M23-E）：per-u 最近章节（首次读取自动收编旧全局键）
    setRecentChapters(readRecentChapters(u || ""));
  }, [u]);

  // S5：记忆统一走 lib（三键同步：上次章节/最近3章/首页继续上次）
  const rememberChapter = (id: string, name: string, tbId?: string, tbName?: string) => {
    memRememberChapter(u || "", id, name, tbId, tbName);
    setRecentChapters(readRecentChapters(u || ""));
  };

  const findChapterById = useCallback(
    (id: string): ChapterNode | null => {
      const walk = (list: ChapterNode[]): ChapterNode | null => {
        for (const c of list) {
          if (c.id === id) return c;
          const hit = walk(c.children || []);
          if (hit) return hit;
        }
        return null;
      };
      for (const tb of textbooks) {
        const hit = walk(tb.chapters || []);
        if (hit) return hit;
      }
      return null;
    },
    [textbooks],
  );

  const pickChapter = (ch: ChapterNode) => {
    setSelectedChapter(ch);
    // S5：连同所属教材一起记忆（抽屉标签/续学条可显示「教材 · 章节」）
    const has = (chapters: ChapterNode[]): boolean =>
      chapters.some((c) => c.id === ch.id || (c.children?.length ? has(c.children || []) : false));
    const tb = textbooks.find((t) => has(t.chapters || []));
    rememberChapter(ch.id, ch.name, tb?.id, tb?.name);
    setChapterPicker(false);
  };

  // 抽屉打开时自动滚动到当前章节（可见即可达）
  useEffect(() => {
    if (chapterPicker) {
      setTimeout(() => {
        document
          .querySelector(".h5-current-chapter")
          ?.scrollIntoView({ block: "center", behavior: "smooth" });
      }, 60);
    }
  }, [chapterPicker]);

  useEffect(() => {
    fetchTextbookTree()
      .then((data) => {
        const list = data || [];
        setTextbooks(list);
        setLoading(false);
        const walk = (chapters: ChapterNode[], targetId: string): ChapterNode | null => {
          for (const c of chapters) {
            if (c.id === targetId) return c;
            const hit = walk(c.children || [], targetId);
            if (hit) return hit;
          }
          return null;
        };
        // C2（M18-C）：?chapter_id= 深链（书内活动块跳转用），命中则优先选它
        const deepChapterId = searchParams.get("chapter_id") || "";
        if (deepChapterId) {
          for (const tb of list) {
            const hit = walk(tb.chapters || [], deepChapterId);
            if (hit) {
              setSelectedChapter(hit);
              rememberChapter(hit.id, hit.name, tb.id, tb.name);
              // 配合 ?tab=practice 等深链直达目标 Tab
              const t = searchParams.get("tab");
              if (t === "practice" || t === "course" || t === "kp" || t === "voice" || t === "recite" || t === "note" || t === "wrong" || t === "ai" || t === "memory") {
                setTab(t);
              }
              return;
            }
          }
        }
        // S5（M23-E）：per-u 上次章节——在教材树里验证存在，被删/树变则继续回退
        const last = readLastChapter(u || "");
        if (last?.chapter_id) {
          for (const tb of list) {
            const hit = walk(tb.chapters || [], last.chapter_id);
            if (hit) {
              setSelectedChapter(hit);
              rememberChapter(hit.id, hit.name, tb.id, tb.name);
              return;
            }
          }
        }
        // 自动选第一个可学章节 + 同步写记忆（S5 一致性修复：首页「继续上次」恒与学习页当前章节一致）
        for (const tb of list) {
          const findFirst = (chapters: ChapterNode[]): ChapterNode | null => {
            if (!chapters.length) return null;
            const first = chapters[0];
            if (first.children && first.children.length) return findFirst(first.children);
            return first;
          };
          const first = findFirst(tb.chapters || []);
          if (first) {
            setSelectedChapter(first);
            rememberChapter(first.id, first.name, tb.id, tb.name);
            return;
          }
        }
      })
      .catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedChapter) return;
    setResLoading(true);
    fetchChapterResources(selectedChapter.id, u || undefined)
      .then((d) => setResources(d))
      .catch(() => setResources(null))
      .finally(() => setResLoading(false));
  }, [selectedChapter, u, refreshTick]);

  // 章节总览（知识点 Tab 数据，design T2；F2 起带 u 读本用户错题/精通之路）
  useEffect(() => {
    if (!selectedChapter) return;
    fetchChapterOverview(selectedChapter.id, u || undefined)
      .then((d) => setOverview(d))
      .catch(() => setOverview(null));
  }, [selectedChapter, u, refreshTick]);

  // F2（M14-B）：本用户章节错题（?u= 隔离，不再是 admin 数据）
  useEffect(() => {
    if (!selectedChapter) return;
    setWrongLoading(true);
    fetchWrongQuestionsByChapter(selectedChapter.id, u || undefined)
      .then((d) => setChapterWrongs(d?.items || []))
      .catch(() => setChapterWrongs([]))
      .finally(() => setWrongLoading(false));
  }, [selectedChapter, u, refreshTick]);

  // F3（M14-B）：本用户学习画像（章节记忆：KP 状态 + 掌握度 + 到期复习）
  useEffect(() => {
    if (!selectedChapter) return;
    setProfileLoading(true);
    fetchLearnerProfile(u || undefined)
      .then((d) => setLearnerProfile(d))
      .catch(() => setLearnerProfile(null))
      .finally(() => setProfileLoading(false));
  }, [selectedChapter, u, refreshTick]);

  // 内部书（M3-T3）：展示本章继承的内部书列表
  useEffect(() => {
    if (!selectedChapter) return;
    setBooksLoading(true);
    fetchChapterBooksInherited(selectedChapter.id)
      .then((data) => setBooks(Array.isArray(data) ? data : []))
      .catch(() => setBooks([]))
      .finally(() => setBooksLoading(false));
  }, [selectedChapter, refreshTick]);

  // G3（M24-A）：一键生成本章课件书（桌面 InternalBooksTab 同款端点；后台编译，书阅读器轮询进度）
  const navigate = useNavigate();
  const [creatingBook, setCreatingBook] = useState(false);
  const [bookErr, setBookErr] = useState("");
  const handleGenerateBook = async () => {
    if (!selectedChapter || creatingBook) return;
    setCreatingBook(true);
    setBookErr("");
    try {
      const r = await createChapterBook(selectedChapter.id);
      navigate(withU(`/e/tutor-h5/book/${r.book_id}`, u || undefined));
    } catch {
      setBookErr("生成失败，请稍后重试");
    } finally {
      setCreatingBook(false);
    }
  };

  const courseware = resources?.courseware || [];
  const structured = (resources?.exercises || []).filter((e) => (e.questions || []).length > 0);
  const adaptive = resources?.adaptive;
  // 当前章节所属教材名（AI 资源 Tab prompt 用，递归找）
  const textbookName = useMemo(() => {
    if (!selectedChapter) return "";
    const find = (chapters: ChapterNode[]): boolean =>
      chapters.some((c) => c.id === selectedChapter.id || (c.children?.length ? find(c.children || []) : false));
    return textbooks.find((tb) => find(tb.chapters || []))?.name || "";
  }, [textbooks, selectedChapter]);

  return (
    <H5Shell
      active="learn"
      onRefresh={() => {
        setRefreshTick((t) => t + 1);
      }}
    >
      {/* [&_p]/[&_code] 任意变体注入（知识点讲解容器 .h5-learn-kpmd 专用） */}
      <style>{".h5-learn-kpmd p{margin:4px 0}.h5-learn-kpmd code{background:#f1f5f9;padding:0 4px;border-radius:4px}"}</style>
      {/* 顶栏 */}
      <div style={{ background: "linear-gradient(to right, #2563eb, #4f46e5)", color: "#fff", padding: 16, borderBottomLeftRadius: 24, borderBottomRightRadius: 24 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ width: 56 }} />
          <div style={{ fontSize: 18, fontWeight: 700 }}>📚 学习</div>
          <div style={{ width: 56 }} />
        </div>
        {/* U3：整条当前章节横幅 = 大触点（44px+），点按换章节 */}
        <button
          onClick={() => setChapterPicker(true)}
          style={{ marginTop: 12, width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between", background: "rgba(255,255,255,0.15)", borderRadius: 16, padding: "12px 16px", border: "none", cursor: "pointer" }}
        >
          <span style={{ fontSize: 14, color: "#eff6ff", textAlign: "left" }}>
            {selectedChapter
              ? `当前章节：${textbookName ? `${textbookName} · ` : ""}${selectedChapter.name}`
              : "选择章节开始学习"}
          </span>
          <RightOutlined style={{ fontSize: 20, color: "#dbeafe", flexShrink: 0 }} />
        </button>
      </div>

      {/* 章节选择抽屉（U3：两级手风琴 + 最近 3 章 + 44px 触点；S1/M23 H5Sheet 基座） */}
      <H5Sheet open={chapterPicker} onClose={() => setChapterPicker(false)} title="选择章节" testId="chapter-drawer">
        <div style={{ padding: "0 20px", paddingBottom: "max(1rem, env(safe-area-inset-bottom))" }}>
          {recentChapters.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: SLATE[500], marginBottom: 4 }}>最近</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                {recentChapters.map((rc) => (
                  <button
                    key={rc.id}
                    onClick={() => {
                      const found = findChapterById(rc.id);
                      if (found) pickChapter(found);
                      else setChapterPicker(false);
                    }}
                    style={{ width: "100%", textAlign: "left", minHeight: 44, padding: "10px 12px", borderRadius: 8, fontSize: 14, background: SLATE[50], border: "none", cursor: "pointer", display: "block" }}
                  >
                    🕘 {rc.textbook_name ? `${rc.textbook_name} · ` : ""}
                    {rc.name}
                  </button>
                ))}
              </div>
            </div>
          )}
            {textbooks.map((tb) => (
              <div key={tb.id} style={{ marginBottom: 12 }} data-testid={`tb-block-${tb.id}`}>
                <div style={{ fontSize: 12, fontWeight: 600, color: SLATE[500], marginBottom: 4, display: "flex", alignItems: "center", gap: 4 }}>
                  <ReadOutlined style={{ fontSize: 14 }} /> {tb.name}
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  {(tb.chapters || [])
                    .sort((a, b) => a.order - b.order)
                    .map((ch) => {
                      const kids = (ch.children || []).sort((a, b) => a.order - b.order);
                      const hasKids = kids.length > 0;
                      const open = openChapterId === ch.id;
                      const isCur = selectedChapter?.id === ch.id;
                      return (
                        <div key={ch.id}>
                          <button
                            onClick={() => {
                              if (hasKids) setOpenChapterId(open ? null : ch.id);
                              else pickChapter(ch);
                            }}
                            style={{
                              width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
                              textAlign: "left", padding: "10px 12px", borderRadius: 8, fontSize: 14,
                              border: "none", cursor: "pointer",
                              ...(isCur
                                ? { background: "#eef2ff", color: "#4338ca", fontWeight: 500 }
                                : { background: "transparent", color: "inherit" }),
                            }}
                            className={isCur ? "h5-current-chapter" : undefined}
                          >
                            <span>
                              <FileTextOutlined style={{ fontSize: 14, marginRight: 4, verticalAlign: "-2px" }} />
                              {ch.name}
                            </span>
                            {hasKids && (
                              <DownOutlined
                                style={{ fontSize: 16, color: SLATE[400], flexShrink: 0, transition: "transform .15s", transform: open ? "rotate(180deg)" : "none" }}
                              />
                            )}
                          </button>
                          {hasKids && open && (
                            <div style={{ marginLeft: 16, borderLeft: `1px solid ${SLATE[200]}`, paddingLeft: 8, display: "flex", flexDirection: "column", gap: 2 }}>
                              {kids.map((kid) => {
                                const kidCur = selectedChapter?.id === kid.id;
                                return (
                                  <button
                                    key={kid.id}
                                    onClick={() => pickChapter(kid)}
                                    style={{
                                      width: "100%", textAlign: "left", padding: "10px 12px", borderRadius: 8,
                                      fontSize: 14, border: "none", cursor: "pointer",
                                      ...(kidCur
                                        ? { background: "#eef2ff", color: "#4338ca", fontWeight: 500 }
                                        : { background: "transparent", color: "inherit" }),
                                    }}
                                    className={kidCur ? "h5-current-chapter" : undefined}
                                  >
                                    {kid.name}
                                  </button>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      );
                    })}
                </div>
              </div>
            ))}
        </div>
      </H5Sheet>

      {/* 内容（design T2：五 Tab + 原文入口） */}
      <div style={{ padding: "0 16px", marginTop: 16, paddingBottom: 32 }}>
        {loading ? (
          <div style={LOAD_CENTER}>
            <LoadingOutlined spin style={{ fontSize: 20, marginRight: 8 }} /> 加载教材…
          </div>
        ) : (
          <>
            {/* 自适应排序提示 */}
            {adaptive?.adapted && (adaptive.summary || []).length > 0 && (
              <div style={{ padding: 12, borderRadius: 16, border: "1px solid #bae6fd", background: "rgba(240,249,255,0.7)", fontSize: 14, display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 12 }}>
                <AimOutlined style={{ fontSize: 16, color: "#0284c7", marginTop: 2, flexShrink: 0 }} />
                <span style={{ color: "#0369a1" }}>{adaptive.summary.join("；")}</span>
              </div>
            )}

            {/* Tab 栏（design T2 六 Tab） */}
            <div style={{ position: "sticky", top: 0, zIndex: 20, background: "rgba(248,250,252,0.95)", backdropFilter: "blur(8px)", paddingBottom: 8 }}>
              {/* U4：横滚渐隐指示——第 6 个 Tab 被裁切时右侧有渐隐，滑到头消失 */}
              <div style={{ position: "relative" }}>
                <div
                  style={{ display: "flex", gap: 4, overflowX: "auto" }}
                  onScroll={(e) => {
                    const el = e.currentTarget;
                    setTabScrolledEnd(el.scrollWidth - el.scrollLeft - el.clientWidth < 8);
                  }}
                >
                  {([
                    ["course", "📖 课件"],
                    ["practice", "⚔️ 闯关"],
                    ["kp", "💡 知识点"],
                    ["voice", "📣 语音视频"],
                    ["recite", "🎙 背诵默写"],
                    ["note", "📝 笔记"],
                    ["wrong", "❌ 章节错题"],
                    ["memory", "🧠 章节记忆"],
                    ["ai", "✨ AI 资源"],
                  ] as const).map(([key, label]) => (
                    <button
                      key={key}
                      onClick={() => setTab(key)}
                      style={{
                        flexShrink: 0, padding: "6px 12px", borderRadius: 9999, fontSize: 12,
                        fontWeight: 500, transition: "all .15s", cursor: "pointer",
                        ...(tab === key
                          ? { background: "#2563eb", color: "#fff", border: "none" }
                          : { background: "#fff", color: SLATE[500], border: `1px solid ${SLATE[200]}` }),
                      }}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                {!tabScrolledEnd && (
                  <div style={{ pointerEvents: "none", position: "absolute", top: 0, bottom: 0, right: 0, width: 32, background: "linear-gradient(to right, rgba(248,250,252,0), #f8fafc)" }} />
                )}
              </div>
              {/* 阅读入口（design T3 原文 + T4 内部书） */}
              <div style={{ marginTop: 8, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                <Link
                  to={withU("/e/tutor-h5/learn/textbook", u)}
                  style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 12px", borderRadius: 12, border: `1px solid ${SLATE[200]}`, background: "#fff", fontSize: 14, textDecoration: "none" }}
                >
                  <span style={{ color: SLATE[600] }}>📄 教材原文</span>
                  <RightOutlined style={{ fontSize: 14, color: SLATE[300] }} />
                </Link>
                {booksLoading ? (
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 12px", borderRadius: 12, border: `1px solid ${SLATE[200]}`, background: "#fff", fontSize: 14, color: SLATE[400] }}>
                    <span>📕 加载内部书…</span>
                  </div>
                ) : books.length > 0 ? (
                  <Link
                    to={withU(`/e/tutor-h5/book/${books[0].id}`, u)}
                    style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 12px", borderRadius: 12, border: `1px solid ${SLATE[200]}`, background: "#fff", fontSize: 14, textDecoration: "none" }}
                  >
                    <span style={{ color: SLATE[600] }}>📕 内部书</span>
                    <RightOutlined style={{ fontSize: 14, color: SLATE[300] }} />
                  </Link>
                ) : (
                  <button
                    onClick={() => void handleGenerateBook()}
                    disabled={creatingBook}
                    data-testid="gen-book-btn"
                    style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 12px", borderRadius: 12, border: "1px solid #c7d2fe", background: "rgba(238,242,255,0.6)", fontSize: 14, cursor: "pointer", opacity: creatingBook ? 0.6 : 1 }}
                  >
                    <span style={{ color: "#4338ca" }}>
                      {creatingBook ? (
                        <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                          <LoadingOutlined spin style={{ fontSize: 14 }} /> 生成中…
                        </span>
                      ) : (
                        "✨ 生成本章课件书"
                      )}
                    </span>
                    {bookErr ? <span style={{ fontSize: 10, color: "#f43f5e", marginLeft: 4 }}>{bookErr}</span> : <RightOutlined style={{ fontSize: 14, color: "#a5b4fc" }} />}
                  </button>
                )}
              </div>
            </div>

            {/* 课件 Tab */}
            {tab === "course" &&
              (resLoading ? (
                <div style={LOAD_CENTER}>
                  <LoadingOutlined spin style={{ fontSize: 20, marginRight: 8 }} /> 加载课件…
                </div>
              ) : courseware.length > 0 ? (
                <div style={{ marginTop: 12 }}>
                  <select
                    value={selectedCourse}
                    onChange={(e) => {
                      setSelectedCourse(e.target.value);
                      const c = courseware.find((x) => (x.html || x.title) === e.target.value);
                      if (!c) return;
                      if (c.html) setViewer({ title: c.title, src: c.html });
                      else if (c.page && c.page.endsWith(".mp4")) setViewer({ title: c.title, src: c.page });
                      else if (c.page) window.open(c.page, "_blank");
                    }}
                    style={{ width: "100%", padding: "10px 12px", borderRadius: 12, border: `1px solid ${BORDER}`, background: "#fff", fontSize: 14 }}
                  >
                    <option value="">选择课件…</option>
                    {courseware.map((c) => (
                      <option key={c.id} value={c.html || c.title}>
                        {c.title}
                      </option>
                    ))}
                  </select>
                </div>
              ) : (
                <div style={EMPTY_CENTER}>本章暂无课件</div>
              ))}

            {/* 闯关 Tab */}
            {tab === "practice" &&
              (resLoading ? (
                <div style={LOAD_CENTER}>
                  <LoadingOutlined spin style={{ fontSize: 20, marginRight: 8 }} /> 加载练习…
                </div>
              ) : (
                <div style={{ marginTop: 12 }}>
                  {/* PG-3（M15）：三档 AI 生成练习（第七篇）——闯关区保留题库闯关 */}
                  <H5TierPractice u={u || undefined} chapterId={selectedChapter?.id} />
                  {/* PG-4（M15）：本章错题重练入口（第四入口） */}
                  {(chapterWrongs?.length ?? 0) > 0 && (
                    <button
                      onClick={() => setWrongReviewOpen(true)}
                      style={{ width: "100%", marginBottom: 12, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 12px", borderRadius: 16, border: "1px solid #fde68a", background: "rgba(255,251,235,0.5)", color: "#b45309", fontSize: 14, fontWeight: 500, cursor: "pointer" }}
                    >
                      <span>❌ 本章错题重练（{chapterWrongs.length}）</span>
                      <span>→</span>
                    </button>
                  )}
                  {structured.length > 0 ? (
                    <>
                      <div style={{ fontSize: 11, color: SLATE[400], padding: "0 4px", marginBottom: 8 }}>— 题库闯关（人工精选）—</div>
                      {structured.map((e) => (
                        <H5PracticeSet
                          key={e.id}
                          set={{ title: e.title, priority: e.priority, adaptive_reason: e.adaptive_reason, questions: e.questions || [] }}
                          u={u || undefined}
                          chapterId={selectedChapter?.id}
                        />
                      ))}
                    </>
                  ) : null}
                  {/* W4（第八篇 M16-C）：闯关区拍照入口——不会的题拍下来问 AI */}
                  <Link
                    to={withU("/e/tutor-h5/wrong", u)}
                    style={{ marginTop: 12, display: "flex", alignItems: "center", justifyContent: "center", gap: 6, padding: "10px 12px", borderRadius: 16, border: "1px dashed #fda4af", background: "rgba(255,241,242,0.5)", color: "#f43f5e", fontSize: 14, fontWeight: 500, textDecoration: "none" }}
                  >
                    📷 拍照问 AI（不会的题拍下来）
                  </Link>
                </div>
              ))}

            {/* 语音 Tab（design T2 voices） */}
            {tab === "voice" && (
              <div style={{ marginTop: 12 }}>
                {(resources?.voices || []).length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {(resources?.voices || []).map((v) => (
                      <div key={v.id} style={{ ...CARD_WHITE, padding: 12 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                          <ReadOutlined style={{ fontSize: 16, color: "#0ea5e9", flexShrink: 0 }} />
                          <span style={{ fontSize: 14, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{v.title}</span>
                        </div>
                        {v.html ? (
                          <button
                            onClick={() => setViewer({ title: v.title, src: v.html! })}
                            style={{ width: "100%", padding: "8px 12px", borderRadius: 12, background: "#0284c7", color: "#fff", fontSize: 14, fontWeight: 500, border: "none", cursor: "pointer" }}
                          >
                            📹 打开领读视频（跟读 · 中文谐音）
                          </button>
                        ) : null}
                        {v.page ? (
                          <VoiceAudio src={v.page} />
                        ) : null}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={EMPTY_CENTER}>
                    本章暂无语音领读
                    <div style={{ fontSize: 12, marginTop: 6 }}>支持口语跟读的资源会显示在这里</div>
                  </div>
                )}
              </div>
            )}

            {/* 背诵默写 Tab（M25 T13：复用桌面 ReciteTab，双端 1:1 同端点同 testid） */}
            {tab === "recite" && selectedChapter && (
              <div style={{ ...CARD_WHITE, marginTop: 12, overflow: "hidden" }}>
                <ReciteTab
                  textbookId={selectedChapter.textbook_id}
                  chapterId={selectedChapter.id}
                  chapterName={selectedChapter.name}
                />
              </div>
            )}

            {/* 知识点 Tab（design T2 overview.knowledge_points） */}
            {tab === "kp" && (
              <div style={{ marginTop: 12 }}>
                <H5ExportButtons chapterId={selectedChapter?.id || ""} tab="knowledge" />
                {(overview?.knowledge_points || []).length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {(overview?.knowledge_points || []).map((kp: any) => {
                      const expanded = expandedKps.has(kp.id);
                      return (
                        <div key={kp.id} style={{ ...CARD_WHITE, padding: 12 }} data-testid={`kp-card-${kp.id}`}>
                          <button
                            onClick={() =>
                              setExpandedKps((prev) => {
                                const next = new Set(prev);
                                if (next.has(kp.id)) next.delete(kp.id);
                                else next.add(kp.id);
                                return next;
                              })
                            }
                            style={{ width: "100%", display: "flex", alignItems: "center", gap: 6, textAlign: "left", background: "transparent", border: "none", padding: 0, cursor: "pointer" }}
                            aria-expanded={expanded}
                          >
                            <AimOutlined style={{ fontSize: 16, color: "#6366f1", flexShrink: 0 }} />
                            <span style={{ fontWeight: 600, fontSize: 14 }}>{kp.name}</span>
                            {kp.difficulty ? (
                              <span style={{ fontSize: 10, color: SLATE[400] }}>难度 {kp.difficulty}</span>
                            ) : null}
                            <DownOutlined
                              style={{ fontSize: 16, color: SLATE[400], marginLeft: "auto", transition: "transform .15s", flexShrink: 0, transform: expanded ? "rotate(180deg)" : "none" }}
                            />
                          </button>
                          {expanded && (
                            <>
                              {kp.description && (
                                <div style={{ fontSize: 14, color: SLATE[600], marginTop: 6 }}>{kp.description}</div>
                              )}
                              {kp.explanation && (
                                <div className="h5-learn-kpmd" style={{ fontSize: 14, marginTop: 6, background: SLATE[50], borderRadius: 12, padding: 10 }}>
                                  <MarkdownRenderer content={kp.explanation} />
                                </div>
                              )}
                              {kp.formula?.latex && (
                                <details style={{ marginTop: 6, borderRadius: 12, border: "1px solid #e0e7ff", background: "rgba(238,242,255,0.5)", padding: 10 }}>
                                  <summary style={{ fontSize: 14, fontWeight: 500, color: "#4338ca", cursor: "pointer" }}>
                                    📐 公式
                                  </summary>
                                  <div style={{ marginTop: 8, overflowX: "auto", fontSize: 16 }}>
                                    <MarkdownRenderer content={`$$${kp.formula.latex}$$`} />
                                  </div>
                                  {kp.formula.derivation && (
                                    <div style={{ marginTop: 8, fontSize: 12, color: SLATE[500], whiteSpace: "pre-wrap", borderTop: "1px solid #e0e7ff", paddingTop: 8 }}>
                                      <div style={{ fontWeight: 500, color: SLATE[600], marginBottom: 4 }}>推导过程</div>
                                      <MarkdownRenderer content={kp.formula.derivation} />
                                    </div>
                                  )}
                                </details>
                              )}
                              {/* G2（M24-A）：可拖拽数学图形——桌面 KnowledgePointsTab 同款共享组件 */}
                              {overview?.textbook?.subject === "math" && kp.figure?.type && (
                                <div style={{ marginTop: 8, borderRadius: 12, border: "1px solid #ccfbf1", background: "rgba(240,253,250,0.5)", padding: 10 }}>
                                  <div style={{ fontSize: 12, fontWeight: 500, color: "#0f766e", marginBottom: 4 }}>✋ 可拖拽演示（拖一拖就懂）</div>
                                  <MathWidget figure={kp.figure} />
                                </div>
                              )}
                              {(kp.examples || []).slice(0, 2).map((ex: any, i: number) => (
                                <div key={i} style={{ marginTop: 6, fontSize: 14, color: SLATE[600] }}>
                                  <span style={{ fontWeight: 500, color: "#4f46e5" }}>例{i + 1}：</span>
                                  {ex.content || ex.title}
                                </div>
                              ))}
                              {(kp.related || []).length > 0 && (
                                <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 6 }}>
                                  {(kp.related || []).slice(0, 6).map((r: any, i: number) => (
                                    <span key={i} style={{ fontSize: 10, padding: "2px 8px", borderRadius: 9999, background: "#eef2ff", color: "#4f46e5", border: "1px solid #e0e7ff" }}>
                                      {r.name} · {r.relation}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div style={EMPTY_CENTER}>本章暂无知识点数据</div>
                )}
              </div>
            )}

            {/* 笔记 Tab（design T2 /api/v1/notebook 序列） */}
            {tab === "note" && <H5NotesTab chapterId={selectedChapter?.id || ""} chapterName={selectedChapter?.name || ""} u={u || ""} />}

            {/* F2（M14-B）：章节错题——本用户数据（?u= 隔离），点击进错题本复习流 */}
            {tab === "wrong" && (
              <div style={{ marginTop: 12 }}>
                <H5ExportButtons chapterId={selectedChapter?.id || ""} tab="wrong" />
                {wrongLoading ? (
                  <div style={LOAD_CENTER}>
                    <LoadingOutlined spin style={{ fontSize: 16, marginRight: 8 }} /> 加载中…
                  </div>
                ) : chapterWrongs.length === 0 ? (
                  <div style={{ ...EMPTY_CENTER, marginTop: 0 }}>本章暂无错题，继续加油 💪</div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {chapterWrongs.map((w: any) => (
                      <Link
                        key={w.id}
                        to={withU(`/e/tutor-h5/wrongbook?mid=${encodeURIComponent(w.id)}`, u)}
                        style={{ display: "block", background: "#fff", borderRadius: 16, border: `1px solid ${SLATE[200]}`, padding: "12px 14px", textDecoration: "none" }}
                      >
                        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 8 }}>
                          <div style={{ fontSize: 14, color: SLATE[800], lineHeight: 1.625, flex: 1, minWidth: 0, ...CLAMP3 }}>
                            {w.title || w.question_text || "（无标题）"}
                          </div>
                          <RightOutlined style={{ fontSize: 14, color: SLATE[300], flexShrink: 0, marginTop: 4 }} />
                        </div>
                        <div style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 8, fontSize: 11, color: SLATE[400] }}>
                          {w.difficulty ? <span>难度 {w.difficulty}</span> : null}
                          {(w.tags || []).slice(0, 3).map((t: string) => (
                            <span key={t} style={{ background: SLATE[100], borderRadius: 9999, padding: "2px 8px" }}>
                              {t}
                            </span>
                          ))}
                        </div>
                      </Link>
                    ))}
                    <Link
                      to={withU("/e/tutor-h5/wrongbook", u)}
                      style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 14px", borderRadius: 16, border: "1px solid #c7d2fe", background: "#eef2ff", fontSize: 14, fontWeight: 500, color: "#4338ca", textDecoration: "none" }}
                    >
                      <span>📚 进错题本复习（共 {chapterWrongs.length} 题）</span>
                      <RightOutlined style={{ fontSize: 16 }} />
                    </Link>
                  </div>
                )}
              </div>
            )}

            {/* F3（M14-B）：章节记忆——KP 状态徽章 + 掌握度条 + 去复习 */}
            {tab === "memory" && (
              <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 8 }}>
                {profileLoading ? (
                  <div style={LOAD_CENTER}>
                    <LoadingOutlined spin style={{ fontSize: 16, marginRight: 8 }} /> 加载中…
                  </div>
                ) : (
                  (() => {
                    const kps = (overview?.knowledge_points || []) as any[];
                    const kpMastery = learnerProfile?.kp_mastery || {};
                    const dueMap = new Map((learnerProfile?.due_reviews || []).map((d) => [d.kp_id, d]));
                    const rows = kps.map((kp) => ({ kp, m: kpMastery[kp.id] }));
                    const mastered = rows.filter((r) => r.m?.status === "mastered").length;
                    const stMap: Record<string, { label: string; cls: React.CSSProperties; bar: string }> = {
                      mastered: { label: "已掌握", cls: { background: "#d1fae5", color: "#047857" }, bar: "#10b981" },
                      weak: { label: "薄弱", cls: { background: "#ffe4e6", color: "#be123c" }, bar: "#fb7185" },
                      learning: { label: "学习中", cls: { background: "#fef3c7", color: "#b45309" }, bar: "#fbbf24" },
                      new: { label: "未学习", cls: { background: "#f1f5f9", color: "#64748b" }, bar: "#cbd5e1" },
                    };
                    return (
                      <>
                        <div style={{ background: "#fff", borderRadius: 16, border: `1px solid ${SLATE[200]}`, padding: "12px 14px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                          <div style={{ fontSize: 14, color: SLATE[700] }}>
                            🧠 本章知识点 {kps.length} 个，已掌握 {mastered} 个
                          </div>
                          <span style={{ fontSize: 12, color: SLATE[400] }}>
                            {kps.length ? Math.round((mastered / kps.length) * 100) : 0}%
                          </span>
                        </div>
                        {kps.length === 0 ? (
                          <div style={{ ...EMPTY_CENTER, marginTop: 0 }}>本章暂无知识点数据</div>
                        ) : (
                          rows.map(({ kp, m }) => {
                            const status = m?.status || "new";
                            const mastery = m?.mastery ?? 0;
                            const due = dueMap.get(kp.id);
                            const st = stMap[status] || stMap.new;
                            return (
                              <div key={kp.id} style={{ background: "#fff", borderRadius: 16, border: `1px solid ${SLATE[200]}`, padding: "12px 14px" }}>
                                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                                  <div style={{ fontSize: 14, fontWeight: 500, color: SLATE[800], flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{kp.name}</div>
                                  <span style={{ flexShrink: 0, fontSize: 11, fontWeight: 500, padding: "2px 8px", borderRadius: 9999, ...st.cls }}>
                                    {st.label}
                                  </span>
                                </div>
                                <div style={{ marginTop: 8, height: 6, borderRadius: 9999, background: SLATE[100], overflow: "hidden" }}>
                                  <div
                                    style={{ height: "100%", borderRadius: 9999, background: st.bar, width: `${Math.max(4, Math.min(100, mastery))}%` }}
                                  />
                                </div>
                                <div style={{ marginTop: 6, display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 11, color: SLATE[400] }}>
                                  <span>掌握度 {Math.round(mastery)}%</span>
                                  {due ? (
                                    <span style={{ color: "#d97706" }}>⏰ 到期复习</span>
                                  ) : m?.attempts ? (
                                    <span>已练 {m.attempts} 次</span>
                                  ) : (
                                    <span>未练习</span>
                                  )}
                                </div>
                                {due && (
                                  <Link
                                    to={withU("/e/tutor-h5/wrongbook", u)}
                                    style={{ marginTop: 8, display: "block", textAlign: "center", padding: "8px 0", borderRadius: 12, background: "#fffbeb", border: "1px solid #fde68a", fontSize: 14, fontWeight: 500, color: "#b45309", textDecoration: "none" }}
                                  >
                                    📚 去复习
                                  </Link>
                                )}
                              </div>
                            );
                          })
                        )}
                      </>
                    );
                  })()
                )}
              </div>
            )}

            {/* AI 资源 Tab（design T2 → /h5/chat 发 prompt） */}
            {tab === "ai" && (
              <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 12 }}>
                {[
                  {
                    icon: "🗺️",
                    title: "生成概念图",
                    desc: "用思维导图呈现本章知识结构",
                    color: { background: "#eff6ff", border: "1px solid #bfdbfe" },
                    prompt: `根据《${textbookName}》的「${selectedChapter?.name}」生成一张概念图，展示核心知识点的关系。`,
                  },
                  {
                    icon: "🎬",
                    title: "生成讲解动画",
                    desc: "演示本章核心概念的动态过程",
                    color: { background: "#faf5ff", border: "1px solid #e9d5ff" },
                    prompt: `为「${selectedChapter?.name}」创建一段动画，演示核心概念的动态过程。`,
                  },
                  {
                    icon: "🧩",
                    title: "生成互动练习页",
                    desc: "带即时反馈的 HTML 互动练习",
                    color: { background: "#ecfdf5", border: "1px solid #a7f3d0" },
                    prompt: `为「${selectedChapter?.name}」创建一个带练习和即时反馈的互动学习页。`,
                  },
                  {
                    icon: "✍️",
                    title: "AI 精讲本章",
                    desc: "讲解本章核心知识与解题方法",
                    color: { background: "#fffbeb", border: "1px solid #fde68a" },
                    prompt: `讲解「${selectedChapter?.name}」的核心知识点和解题方法。`,
                  },
                ].map((tool) => (
                  <Link
                    key={tool.title}
                    to={withU(`/e/tutor-h5/chat?prompt=${encodeURIComponent(tool.prompt)}`, u)}
                    style={{ display: "flex", alignItems: "flex-start", gap: 12, padding: 14, borderRadius: 16, border: `1px solid ${BORDER}`, background: "#fff", fontSize: 14, textDecoration: "none" }}
                  >
                    <div style={{ width: 36, height: 36, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, flexShrink: 0, ...tool.color }}>
                      {tool.icon}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 600, color: SLATE[800] }}>{tool.title}</div>
                      <div style={{ fontSize: 12, color: SLATE[500], marginTop: 2 }}>{tool.desc}</div>
                    </div>
                    <RightOutlined style={{ fontSize: 14, color: SLATE[300], flexShrink: 0, marginTop: 4 }} />
                  </Link>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {/* P1-A 课件内嵌阅读：页内全屏 overlay，盖住 TabBar */}
      {viewer && (
        <div style={{ position: "fixed", inset: 0, zIndex: 50, background: "#fff", display: "flex", flexDirection: "column" }}>
          <div style={{ height: 48, display: "flex", alignItems: "center", padding: "0 12px", borderBottom: `1px solid ${BORDER}`, background: "#fff", flexShrink: 0 }}>
            <button
              onClick={() => setViewer(null)}
              style={{ padding: "6px 12px", borderRadius: 8, background: SLATE[100], fontSize: 14, fontWeight: 500, border: "none", cursor: "pointer" }}
            >
              ✕ 关闭
            </button>
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", margin: "0 8px", fontSize: 14, color: SLATE[700] }}>{viewer.title}</span>
            <a
              href={viewer.src}
              target="_blank"
              rel="noreferrer"
              style={{ marginLeft: "auto", fontSize: 12, color: "#3b82f6", flexShrink: 0 }}
            >
              外部打开
            </a>
          </div>
          {viewer.src.endsWith(".mp4") ? (
            <video src={viewer.src} controls autoPlay style={{ flex: 1, width: "100%" }} />
          ) : (
            <iframe src={viewer.src} style={{ flex: 1, width: "100%" }} title={viewer.title} />
          )}
        </div>
      )}

      {/* PG-4（M15）：本章错题重练底部弹层 */}
      <H5WrongReview
        u={u || undefined}
        items={chapterWrongs || []}
        open={wrongReviewOpen}
        onClose={() => setWrongReviewOpen(false)}
      />
    </H5Shell>
  );
}

/** H5 章节笔记（design T2）：基于工程 Notebook 模块，按章节归档。
 *  C1（M18-A）：全部请求带 ?u=，后端按用户隔离笔记本。 */
function H5NotesTab({ chapterId, chapterName, u }: { chapterId: string; chapterName: string; u?: string }) {
  const [notes, setNotes] = useState<
    { id: string; notebook: string; title: string; content: string }[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [newNote, setNewNote] = useState("");
  const [saving, setSaving] = useState(false);

  const nbUrl = useCallback(
    (path: string) => {
      const qs = u ? (path.includes("?") ? "&" : "?") + `u=${encodeURIComponent(u)}` : "";
      return `/api/v1/notebook${path}${qs}`;
    },
    [u]
  );

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(nbUrl("/list"));
      if (!res.ok) {
        setNotes([]);
        return;
      }
      const list = (await res.json()).notebooks || [];
      const mine = list.filter((n: any) => n.name.includes(chapterName));
      const others = list.filter((n: any) => !n.name.includes(chapterName));
      const targets = [...mine, ...others.slice(0, 5)];
      const views: { id: string; notebook: string; title: string; content: string }[] = [];
      for (const nb of targets) {
        try {
          const detailRes = await fetch(nbUrl(`/${nb.id}`));
          if (!detailRes.ok) continue;
          const detail = await detailRes.json();
          for (const r of detail.records || []) {
            const content = r.summary || r.output || r.user_query || "";
            if (content) {
              views.push({
                id: r.id || `${nb.id}-${views.length}`,
                notebook: detail.name,
                title: r.title || detail.name,
                content,
              });
            }
          }
        } catch {
          /* 跳过打不开的笔记本 */
        }
      }
      setNotes(views);
    } catch {
      setNotes([]);
    } finally {
      setLoading(false);
    }
  }, [chapterName, nbUrl]);

  useEffect(() => {
    void load();
  }, [load]);

  const save = async () => {
    if (!newNote.trim() || saving) return;
    setSaving(true);
    try {
      let nbId: string | null = null;
      try {
        const listRes = await fetch(nbUrl("/list"));
        const list = listRes.ok ? (await listRes.json()).notebooks || [] : [];
        nbId = list.find((n: any) => n.name === chapterName)?.id || null;
      } catch {
        nbId = null;
      }
      if (!nbId) {
        const created = await fetch(nbUrl("/create"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: chapterName,
            description: `学习笔记（${chapterName}）`,
            color: "#3B82F6",
            icon: "book",
          }),
        });
        const createdData = created.ok ? await created.json() : {};
        nbId = createdData.notebook?.id || null;
      }
      if (!nbId) return;
      await fetch(nbUrl("/add_record"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          notebook_ids: [nbId],
          record_type: "chat",
          title: `${chapterName} - 学习笔记`,
          summary: "",
          user_query: "",
          output: newNote,
          metadata: { chapter_id: chapterId, chapter_name: chapterName },
        }),
      });
      setNewNote("");
      await load();
    } catch {
      /* 保存失败忽略 */
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 12 }}>
      {/* 快速记笔记 */}
      <div style={{ ...CARD_WHITE, padding: 12 }}>
        <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 8 }}>📝 快速记笔记</div>
        <textarea
          value={newNote}
          onChange={(e) => setNewNote(e.target.value)}
          placeholder={`记录关于「${chapterName}」的学习笔记…`}
          style={{ width: "100%", boxSizing: "border-box", minHeight: 90, padding: 10, borderRadius: 12, border: `1px solid ${BORDER}`, fontSize: 14, background: "transparent", resize: "vertical", outline: "none" }}
        />
        <button
          onClick={() => void save()}
          disabled={saving || !newNote.trim()}
          style={{ marginTop: 8, padding: "8px 16px", borderRadius: 12, background: "#2563eb", color: "#fff", fontSize: 14, fontWeight: 500, border: "none", cursor: "pointer", opacity: saving || !newNote.trim() ? 0.5 : 1 }}
        >
          {saving ? "保存中…" : "保存笔记"}
        </button>
      </div>

      {/* 笔记列表 */}
      {loading ? (
        <div style={LOAD_CENTER}>
          <LoadingOutlined spin style={{ fontSize: 20, marginRight: 8 }} /> 加载笔记…
        </div>
      ) : notes.length === 0 ? (
        <div style={{ textAlign: "center", padding: "40px 0", color: SLATE[400] }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>📝</div>
          还没有笔记，在上方记录一条吧
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {notes.map((n) => (
            <div key={n.id} style={{ ...CARD_WHITE, padding: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                <span style={{ fontWeight: 500, fontSize: 14, color: SLATE[800], overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{n.title}</span>
                <span style={{ fontSize: 10, color: SLATE[400], marginLeft: "auto", flexShrink: 0 }}>{n.notebook}</span>
              </div>
              <p style={{ fontSize: 12, color: SLATE[600], whiteSpace: "pre-wrap", margin: 0 }}>{n.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function H5LearnPage() {
  return (
    <Suspense fallback={<div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", color: SLATE[400] }}><LoadingOutlined spin style={{ fontSize: 20, marginRight: 8 }} /> 加载中…</div>}>
      <H5LearnContent />
    </Suspense>
  );
}
