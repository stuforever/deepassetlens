/**
 * H5 复习中心（design §5.1）：双源合并视图。原仓 app/h5/review/page.tsx 1:1 移植。
 * 源1 母题 FSRS（题级）：/mother-questions/reviews/due_count + due
 * 源2 学习计划 kp 级：learner-profile.due_reviews + 各路径 map.due_reviews
 * 不合并存储，只合并视图。
 *
 * 等价替换清单：
 * - "use client" 删除；next/link → react-router-dom Link；next/navigation useSearchParams +
 *   Suspense 结构保留；
 * - lucide → @ant-design/icons：AlarmClock→ClockCircleOutlined、Loader2→LoadingOutlined、
 *   BookMarked→BookOutlined、Target→AimOutlined、ChevronRight→RightOutlined、
 *   PartyPopper→GiftOutlined、Flame→FireOutlined；
 * - fetchLearnerProfile ← h5shared/selfLearningApi；fetchAllProgress/ProgressSummary ←
 *   h5shared/learningApi（SA-D 共享数据层）；H5PageHeader ← h5shared；
 * - fetch(apiUrl(...)) → fetch('/api/v1/...') 逐字；
 * - Tailwind → 内联样式逐项对位（active:/hover: 伪类变体随共享层先例省略）；
 * - 路由前缀映射：原 /h5/* → /e/tutor/h5/*。
 */
import { useCallback, useEffect, useState, Suspense } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  ClockCircleOutlined, LoadingOutlined, BookOutlined, AimOutlined, RightOutlined,
  GiftOutlined, FireOutlined,
} from "@ant-design/icons";
import { fetchLearnerProfile } from "./h5shared/selfLearningApi";
import { fetchAllProgress, type ProgressSummary } from "./h5shared/learningApi";
import { withU } from "./h5shared/h5Utils";
import { H5Shell } from "./h5shared/H5Shell";
import { H5PageHeader } from "./h5shared/H5PageHeader";

interface DueItem {
  id: string;
  title: string;
  question_text?: string;
  difficulty?: number;
}

function fmtDue(ts?: number | null): string {
  if (!ts) return "已到期";
  const diff = ts - Date.now() / 1000;
  if (diff <= 0) return "已到期";
  const h = diff / 3600;
  if (h < 24) return `${Math.max(1, Math.round(h))} 小时后`;
  return `${Math.round(h / 24)} 天后`;
}

function H5ReviewContent() {
  const [searchParams] = useSearchParams();
  const u = searchParams.get("u") || searchParams.get("openid") || "";
  const qs = u ? `?u=${encodeURIComponent(u)}` : "";
  const [dueCount, setDueCount] = useState<number>(0);
  const [dueItems, setDueItems] = useState<DueItem[]>([]);
  const [kpDue, setKpDue] = useState<
    { kp_id: string; kp_name: string; due_at?: number; reason?: string }[]
  >([]);
  const [reviewPathId, setReviewPathId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [streak, setStreak] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [dueRes, dueCountRes, profile, progressRes] = await Promise.all([
        fetch(`/api/v1/mother-questions/reviews/due?max_items=50${qs}`).then((r) =>
          r.ok ? r.json() : { items: [] },
        ),
        fetch(`/api/v1/mother-questions/reviews/due_count${qs}`).then((r) =>
          r.ok ? r.json() : { due_count: 0 },
        ),
        fetchLearnerProfile(u || undefined),
        fetchAllProgress(u).catch(() => ({ summaries: [] as ProgressSummary[] })),
      ]);
      setDueItems(dueRes.items || []);
      setDueCount(typeof dueCountRes.due_count === "number" ? dueCountRes.due_count : 0);

      // kp 级：learner-profile.due_reviews（全部路径合并语义）
      const profDue = profile?.due_reviews || [];
      // 复习路径：取用户第一条精通之路（对话复习必须挂真实路径）
      const summaries = (progressRes as { summaries?: ProgressSummary[] }).summaries || [];
      const firstPath = summaries.find((s) => !s.book_id.startsWith("shadow_"))?.book_id || "";
      setReviewPathId(firstPath);
      // 路径级 due_reviews（从各路径 map 的 counts 无法逐个拿，用 profile 为准）
      setKpDue(profDue);
      setStreak(profile?.streak_days || 0);
    } catch {
      /* 单源失败不阻塞 */
    } finally {
      setLoading(false);
    }
  }, [qs, u]);

  useEffect(() => {
    void load();
  }, [load]);

  const hasItem = dueItems.length > 0;
  const hasKp = kpDue.length > 0;
  const allDone = !loading && !hasItem && !hasKp;

  return (
    <H5Shell active="home" onRefresh={load}>
      {/* 顶栏 */}
      <div style={{ background: "linear-gradient(to right, #0ea5e9, #0891b2)", color: "#fff", padding: "40px 20px 56px", borderRadius: "0 0 24px 24px" }}>
        <H5PageHeader title={<span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 6 }}><ClockCircleOutlined style={{ fontSize: 20 }} /> 复习中心</span>} />
        <div style={{ marginTop: 4, color: "#e0f2fe", fontSize: 12 }}>遗忘曲线到期 · 题级 + 知识点级双源合并</div>
      </div>

      <div style={{ padding: "0 16px", marginTop: -32, paddingBottom: 40 }}>
        {/* 今日到期大卡 */}
        <div style={{ background: "#fff", borderRadius: 16, boxShadow: "0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px -1px rgba(0,0,0,0.1)", border: "1px solid #e2e8f0", padding: 16 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div>
              <div style={{ fontSize: 12, color: "#94a3b8" }}>今日到期</div>
              <div style={{ fontSize: 30, fontWeight: 700, color: "#1e293b", marginTop: 2 }}>
                {loading ? "…" : dueCount + kpDue.length}
                <span style={{ fontSize: 14, color: "#94a3b8", fontWeight: 400, marginLeft: 4 }}>项</span>
              </div>
            </div>
            {streak > 0 && (
              <div style={{ display: "flex", alignItems: "center", gap: 4, color: "#d97706", fontSize: 14 }}>
                <FireOutlined style={{ fontSize: 16 }} /> 连续 {streak} 天
              </div>
            )}
          </div>

          {/* 开始复习：智能路由 */}
          {!loading && (hasItem || hasKp) && (
            <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 8 }}>
              {hasItem && (
                <Link
                  to={withU("/e/tutor/h5/wrongbook", u)}
                  style={{ padding: "12px 0", borderRadius: 16, background: "#f97316", color: "#fff", fontSize: 14, fontWeight: 500, textAlign: "center", textDecoration: "none" }}
                >
                  📖 复习错题（{dueItems.length}）
                </Link>
              )}
              {hasKp &&
                (reviewPathId ? (
                  <Link
                    to={withU(`/e/tutor/h5/chat?mode=mastery&path=${encodeURIComponent(reviewPathId)}`, u)}
                    style={{ padding: "12px 0", borderRadius: 16, background: "#4f46e5", color: "#fff", fontSize: 14, fontWeight: 500, textAlign: "center", textDecoration: "none" }}
                  >
                    💬 AI 带复习（{kpDue.length}）
                  </Link>
                ) : (
                  <Link
                    to={withU("/e/tutor/h5/paths", u)}
                    style={{ padding: "12px 0", borderRadius: 16, background: "#4f46e5", color: "#fff", fontSize: 14, fontWeight: 500, textAlign: "center", textDecoration: "none" }}
                  >
                    🏆 先建精通之路
                  </Link>
                ))}
            </div>
          )}
        </div>

        {loading ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "64px 0", color: "#94a3b8" }}>
            <LoadingOutlined style={{ fontSize: 20 }} spin /> <span style={{ marginLeft: 8 }}>加载复习计划…</span>
          </div>
        ) : allDone ? (
          <div style={{ textAlign: "center", padding: "64px 0", background: "#fff", borderRadius: 16, boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)", border: "1px solid #e2e8f0", marginTop: 16 }}>
            <GiftOutlined style={{ fontSize: 40, color: "#10b981", display: "block", margin: "0 auto" }} />
            <div style={{ fontWeight: 500, color: "#334155", marginTop: 12 }}>今天复习完了 🎉</div>
            <div style={{ fontSize: 14, color: "#94a3b8", marginTop: 4 }}>保持节奏，掌握度会稳步提升</div>
          </div>
        ) : (
          <>
            {/* 题级列表 */}
            {hasItem && (
              <div style={{ marginTop: 20 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, padding: "0 4px" }}>
                  <BookOutlined style={{ fontSize: 16, color: "#f97316" }} />
                  <h3 style={{ fontWeight: 600, fontSize: 14, margin: 0 }}>错题到期（母题 FSRS）</h3>
                  <span style={{ fontSize: 12, color: "#94a3b8" }}>{dueItems.length} 题</span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {dueItems.slice(0, 20).map((it) => (
                    <Link
                      key={it.id}
                      to={withU("/e/tutor/h5/wrongbook", u)}
                      style={{ display: "flex", background: "#fff", borderRadius: 16, border: "1px solid #e2e8f0", padding: 14, alignItems: "center", gap: 12, textDecoration: "none" }}
                    >
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 14, color: "#1e293b", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{it.title}</div>
                        <div style={{ fontSize: 11, color: "#d97706", marginTop: 2 }}>遗忘曲线到期</div>
                      </div>
                      <RightOutlined style={{ fontSize: 16, color: "#cbd5e1", flexShrink: 0 }} />
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {/* kp 级列表 */}
            {hasKp && (
              <div style={{ marginTop: 20 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, padding: "0 4px" }}>
                  <AimOutlined style={{ fontSize: 16, color: "#6366f1" }} />
                  <h3 style={{ fontWeight: 600, fontSize: 14, margin: 0 }}>知识点到期（学习计划）</h3>
                  <span style={{ fontSize: 12, color: "#94a3b8" }}>{kpDue.length} 项</span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {kpDue.slice(0, 20).map((kp) => (
                    <Link
                      key={kp.kp_id}
                      to={
                        reviewPathId
                          ? withU(`/e/tutor/h5/chat?mode=mastery&path=${encodeURIComponent(reviewPathId)}`, u)
                          : withU("/e/tutor/h5/paths", u)
                      }
                      style={{ display: "flex", background: "#fff", borderRadius: 16, border: "1px solid #e2e8f0", padding: 14, alignItems: "center", gap: 12, textDecoration: "none" }}
                    >
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 14, color: "#1e293b", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{kp.kp_name}</div>
                        <div style={{ fontSize: 11, color: "#4f46e5", marginTop: 2 }}>
                          {kp.reason || "遗忘曲线到期"} · {fmtDue(kp.due_at)}
                        </div>
                      </div>
                      <RightOutlined style={{ fontSize: 16, color: "#cbd5e1", flexShrink: 0 }} />
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </H5Shell>
  );
}

export default function H5Review() {
  return (
    <Suspense
      fallback={
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", color: "#94a3b8" }}>
          <LoadingOutlined style={{ fontSize: 20 }} spin /> <span style={{ marginLeft: 8 }}>加载中…</span>
        </div>
      }
    >
      <H5ReviewContent />
    </Suspense>
  );
}
