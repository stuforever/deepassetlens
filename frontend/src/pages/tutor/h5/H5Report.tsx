/**
 * 家长学情报告（design §5.3 家长端）：学情周报 + 薄弱点提醒 + 复习建议 + 错因分析（§5.3）
 * ——原仓 app/h5/report/page.tsx 1:1 移植。
 *
 * 等价替换清单：
 * - "use client" 删除；next/link → react-router-dom Link；
 * - lucide → @ant-design/icons：Loader2→LoadingOutlined、ChevronLeft→LeftOutlined、
 *   ChevronDown→DownOutlined、AlertTriangle→WarningOutlined、CheckCircle2→CheckCircleOutlined、
 *   CalendarClock→ScheduleOutlined、Flame→FireOutlined、Award→TrophyOutlined、
 *   PieChart→PieChartOutlined、BrainCircuit→RobotOutlined、TrendingUp→RiseOutlined；
 * - Tailwind → 内联样式逐项对位（shadcn 语义色对位：muted=#f1f5f9、muted-foreground=#64748b、
 *   border=#e2e8f0；active:/hover: 伪类变体无法内联，随共享层先例省略）；
 * - fetchLearnerProfile/LearnerProfileDto ← h5shared/selfLearningApi（SA-D 共享数据层）；
 * - API 端点逐字：/api/v1/h5-links、/api/v1/mother-questions/analysis/{weak-points,error-patterns,retention}、
 *   /api/v1/learning/weekly-digest、/api/v1/learning/learner-profile（经 fetchLearnerProfile）。
 * - 路由前缀映射：原 /h5/* → /e/tutor/h5/*。
 */
import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  LoadingOutlined, LeftOutlined, DownOutlined, WarningOutlined, CheckCircleOutlined,
  ScheduleOutlined, FireOutlined, TrophyOutlined, PieChartOutlined, RobotOutlined, RiseOutlined,
} from "@ant-design/icons";
import { fetchLearnerProfile, type LearnerProfileDto } from "./h5shared/selfLearningApi";
import { withU } from "./h5shared/h5Utils";
import { H5Shell } from "./h5shared/H5Shell";

const STATUS_META: Record<string, { label: string; style: React.CSSProperties }> = {
  mastered: { label: "已掌握", style: { background: "#ecfdf5", color: "#059669", borderColor: "#a7f3d0" } },
  learning: { label: "学习中", style: { background: "#f0f9ff", color: "#0284c7", borderColor: "#bae6fd" } },
  weak: { label: "薄弱", style: { background: "#fff1f2", color: "#e11d48", borderColor: "#fecdd3" } },
  new: { label: "未学", style: { background: "rgba(241,245,249,0.4)", color: "#64748b", borderColor: "#e2e8f0" } },
};

const SUBJECT_LABEL: Record<string, string> = { math: "数学", chinese: "语文", english: "英语" };

/** 本周一（周一为起点）的 YYYY-MM-DD；offsetWeek 为负表示上周。 */
function mondayISO(offsetWeek: number): string {
  const now = new Date();
  const day = (now.getDay() + 6) % 7; // Mon=0
  const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - day);
  d.setDate(d.getDate() + offsetWeek * 7);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** ISO 日期串 -> "M/D"（供周卡标题显示）。 */
function fmtShortDate(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || "");
  if (!m) return "";
  return `${Number(m[2])}/${Number(m[3])}`;
}

/** W5（第八篇 M16-C）：错题来源标签 -> 中文名 */
function srcLabel(src: string): string {
  return (
    { photo: "拍照", chat: "对话", practice: "练习", manual: "手动" }[src] || src
  );
}

const cardStyle: React.CSSProperties = {
  background: "#fff", borderRadius: 16, boxShadow: "0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px -1px rgba(0,0,0,0.1)",
  border: "1px solid #e2e8f0", padding: 16,
};

/** 家长学情报告页组件（原仓默认导出 H5Report）。 */
export default function H5Report() {
  const [profile, setProfile] = useState<LearnerProfileDto | null>(null);
  const [loading, setLoading] = useState(true);
  const [openid, setOpenid] = useState("");
  const [u, setU] = useState("");
  // P2-C2 视角切换：viewU = 当前查看对象（默认自己，可切到关联孩子）
  const [viewU, setViewU] = useState("");
  const [children, setChildren] = useState<{ child: string; note: string }[]>([]);
  const [weakAnalysis, setWeakAnalysis] = useState<{ knowledge_point_id: string; mother_count: number }[]>([]);
  const [errorPatterns, setErrorPatterns] = useState<{ reason: string; count: number }[]>([]);
  const [retention, setRetention] = useState<{ avg_retention: number; reviewed_count: number; total_count: number } | null>(null);
  const [viewerOpen, setViewerOpen] = useState(false);
  // P2-A 本周成长卡
  const [weekly, setWeekly] = useState<any>(null);
  const [weeklyLoading, setWeeklyLoading] = useState(false);
  const [weekOffset, setWeekOffset] = useState(0);

  // 初始化：u 来自 URL；viewU 默认 = u；加载关联孩子
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const uid = params.get("u") || params.get("openid") || "";
    setOpenid(uid);
    setU(uid);
    setViewU(uid);
    if (uid) {
      void fetch(`/api/v1/h5-links?parent=${encodeURIComponent(uid)}`)
        .then((r) => (r.ok ? r.json() : { children: [] }))
        .then((d) =>
          setChildren(
            (d.children || []).map((c: any) => ({ child: c.child, note: c.note || "" })),
          ),
        )
        .catch(() => setChildren([]));
    }
  }, []);

  // 数据层统一用 viewU（切换视角即换 u 拉数据，天然只读）
  useEffect(() => {
    setLoading(true);
    setProfile(null);
    void fetchLearnerProfile(viewU || undefined)
      .then((p) => setProfile(p))
      .finally(() => setLoading(false));
    const qs = viewU ? `?u=${encodeURIComponent(viewU)}` : "";
    void fetch(`/api/v1/mother-questions/analysis/weak-points${qs}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setWeakAnalysis(d?.weak_points || []))
      .catch(() => {});
    void fetch(`/api/v1/mother-questions/analysis/error-patterns${qs}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setErrorPatterns(d?.patterns || []))
      .catch(() => {});
    void fetch(`/api/v1/mother-questions/analysis/retention${qs}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setRetention(d || null))
      .catch(() => {});
  }, [viewU]);

  // P2-A 本周成长卡：weekly-digest（周增量学情）
  useEffect(() => {
    setWeeklyLoading(true);
    const qs = viewU
      ? `?u=${encodeURIComponent(viewU)}&week_start=${mondayISO(weekOffset)}`
      : `?week_start=${mondayISO(weekOffset)}`;
    void fetch(`/api/v1/learning/weekly-digest${qs}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setWeekly(d))
      .catch(() => setWeekly(null))
      .finally(() => setWeeklyLoading(false));
  }, [viewU, weekOffset]);

  if (loading)
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", color: "#64748b" }}>
        <LoadingOutlined style={{ fontSize: 20 }} spin /> <span style={{ marginLeft: 8 }}>加载学情报告…</span>
      </div>
    );

  if (!profile || Object.keys(profile.kp_mastery || {}).length === 0) {
    return (
      <H5Shell active="home">
        <div style={{ padding: "24px 16px" }}>
          <Link to={withU("/e/tutor/h5", viewU)} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 14, color: "#4f46e5", marginBottom: 24, textDecoration: "none" }}>
            <LeftOutlined style={{ fontSize: 16 }} /> 返回
          </Link>
          <div style={{ textAlign: "center", padding: "64px 0", color: "#94a3b8" }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>📊</div>
            {viewU ? `${viewU} 还没有学习数据` : "还没有学习数据"}
            <div style={{ fontSize: 14, marginTop: 8 }}>从「拍错题」开始，系统会自动建立学情画像</div>
            <Link
              to={withU("/e/tutor/h5/wrong", viewU)}
              style={{ marginTop: 16, display: "inline-block", padding: "8px 16px", borderRadius: 12, background: "#f43f5e", color: "#fff", fontSize: 14, textDecoration: "none" }}
            >
              📷 去拍错题
            </Link>
          </div>
        </div>
      </H5Shell>
    );
  }

  const kps = Object.values(profile.kp_mastery);
  const weak = profile.weak_points || [];
  const due = profile.due_reviews || [];
  const bySubject = kps.reduce<Record<string, typeof kps>>((acc, kp) => {
    (acc[kp.subject] = acc[kp.subject] || []).push(kp);
    return acc;
  }, {});

  return (
    <H5Shell active="home">
      {/* 顶栏 */}
      <div style={{ background: "linear-gradient(to right, #059669, #0d9488)", color: "#fff", padding: "20px 16px", borderRadius: "0 0 24px 24px" }}>
        <Link to={withU("/e/tutor/h5", viewU)} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 14, color: "#d1fae5", marginBottom: 12, textDecoration: "none" }}>
          <LeftOutlined style={{ fontSize: 16 }} /> 返回首页
        </Link>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ fontSize: 20, fontWeight: 700 }}>{viewU ? `${viewU} 的` : "家长 · "}学情报告</div>
          {/* P2-C2 视角切换器（自己 + 关联孩子，纯 GET 只读） */}
          <div style={{ position: "relative" }}>
            <button
              onClick={() => setViewerOpen((v) => !v)}
              style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, background: "rgba(255,255,255,0.2)", borderRadius: 9999, padding: "6px 12px", color: "#fff", border: "none", cursor: "pointer" }}
            >
              {viewU ? viewU : "我"} 学情 <DownOutlined style={{ fontSize: 12 }} />
            </button>
            {viewerOpen && (
              <div style={{ position: "absolute", right: 0, top: "100%", marginTop: 4, background: "#fff", color: "#334155", borderRadius: 12, boxShadow: "0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1)", border: "1px solid #e2e8f0", padding: 4, minWidth: 144, zIndex: 30 }}>
                <button
                  onClick={() => {
                    setViewU(u);
                    setViewerOpen(false);
                  }}
                  style={{ width: "100%", textAlign: "left", padding: "8px 12px", fontSize: 14, borderRadius: 8, background: "none", border: "none", cursor: "pointer" }}
                >
                  我的学情 {viewU === u && "✓"}
                </button>
                {children.map((c) => (
                  <button
                    key={c.child}
                    onClick={() => {
                      setViewU(c.child);
                      setViewerOpen(false);
                    }}
                    style={{ width: "100%", textAlign: "left", padding: "8px 12px", fontSize: 14, borderRadius: 8, background: "none", border: "none", cursor: "pointer" }}
                  >
                    👧 {c.child}
                    {c.note ? `（${c.note}）` : ""} {viewU === c.child && "✓"}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
        <div style={{ color: "#d1fae5", fontSize: 14, marginTop: 4 }}>掌握度变化 · 薄弱点 · 进步反馈</div>
      </div>

      <div style={{ padding: "0 16px", marginTop: -16, display: "flex", flexDirection: "column", gap: 16 }}>
        {/* P2-A 本周成长卡 */}
        <div style={cardStyle}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <RiseOutlined style={{ fontSize: 16, color: "#6366f1" }} />
              <h3 style={{ fontWeight: 600, fontSize: 14, margin: 0 }}>本周成长</h3>
              {weekly?.week_start && (
                <span style={{ fontSize: 10, color: "#94a3b8" }}>
                  {fmtShortDate(weekly.week_start)} - {fmtShortDate(weekly.week_end)}
                </span>
              )}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <button
                onClick={() => setWeekOffset((o) => o - 1)}
                style={{ padding: "4px 8px", borderRadius: 8, background: "#f1f5f9", fontSize: 12, color: "#64748b", border: "none", cursor: "pointer" }}
              >
                ◀ 上周
              </button>
              <button
                onClick={() => setWeekOffset((o) => o + 1)}
                disabled={weekOffset >= 0}
                style={{ padding: "4px 8px", borderRadius: 8, background: "#f1f5f9", fontSize: 12, color: "#64748b", border: "none", cursor: "pointer", opacity: weekOffset >= 0 ? 0.4 : 1 }}
              >
                本周 ▶
              </button>
            </div>
          </div>
          {weeklyLoading ? (
            <div style={{ textAlign: "center", padding: "24px 0", color: "#94a3b8", fontSize: 14 }}>
              <LoadingOutlined style={{ fontSize: 16 }} spin /> <span style={{ marginInlineStart: 4 }}>加载中…</span>
            </div>
          ) : !weekly || weekly.attempts === 0 ? (
            <div style={{ textAlign: "center", padding: "24px 0" }}>
              <div style={{ fontSize: 30, marginBottom: 8 }}>🌱</div>
              <div style={{ fontSize: 14, color: "#64748b" }}>本周还没有学习记录，去做几道闯关题吧</div>
              <Link
                to={withU("/e/tutor/h5/learn", viewU)}
                style={{ marginTop: 12, display: "inline-block", padding: "8px 16px", borderRadius: 12, background: "#4f46e5", color: "#fff", fontSize: 14, textDecoration: "none" }}
              >
                去学习
              </Link>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, fontSize: 14 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ color: "#475569" }}>
                  答题 {weekly.attempts} · 正确率 {Math.round((weekly.accuracy || 0) * 100)}%
                </span>
                {weekly.accuracy != null && weekly.accuracy < 0.6 && (
                  <span style={{ fontSize: 10, color: "#b45309", background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 9999, padding: "2px 8px" }}>
                    建议先复习错题本
                  </span>
                )}
              </div>
              {(weekly.new_kps || []).length > 0 && (
                <div style={{ color: "#475569" }}>
                  新学知识点 {weekly.new_kps.length}：
                  {weekly.new_kps.map((k: any) => k.kp_name).join("、")}
                </div>
              )}
              {(weekly.top_improved || []).length > 0 && weekly.top_improved[0].delta != null && (
                <div style={{ color: "#475569" }}>
                  最大进步：{weekly.top_improved[0].kp_name}{" "}
                  {Math.round((weekly.top_improved[0].before || 0) * 100)}% →{" "}
                  {Math.round(weekly.top_improved[0].after * 100)}%
                  <span style={{ color: "#059669", fontWeight: 500 }}>
                    {" "}
                    ↑{Math.round(weekly.top_improved[0].delta * 100)}
                  </span>
                </div>
              )}
              {weekly.error_types && Object.keys(weekly.error_types).length > 0 && (
                <div style={{ color: "#475569" }}>
                  错因分布：
                  {Object.entries(weekly.error_types)
                    .map(([k, v]) => `${k} ${v}次`)
                    .join(" · ")}
                </div>
              )}
              <div style={{ color: "#64748b", fontSize: 12 }}>
                新增错题 {weekly.mothers_added || 0} · 完成复习 {weekly.reviews_done || 0}
              </div>
              {/* W5（第八篇 M16-C）：四源分布——错题从哪来（拍照/练习/对话/手动） */}
              {weekly.mother_sources && Object.keys(weekly.mother_sources).length > 0 && (
                <div style={{ color: "#64748b", fontSize: 12, marginTop: 4 }}>
                  来源：
                  {Object.entries(weekly.mother_sources)
                    .map(([k, v]) => `${srcLabel(k)} ${v}题`)
                    .join(" · ")}
                </div>
              )}
            </div>
          )}
        </div>

        {/* 关键指标 */}
        <div style={cardStyle}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12 }}>
            <div style={{ textAlign: "center" }}>
              <FireOutlined style={{ fontSize: 20, color: "#f97316", display: "block", margin: "0 auto" }} />
              <div style={{ fontSize: 20, fontWeight: 700, marginTop: 4 }}>{profile.streak_days}</div>
              <div style={{ fontSize: 11, color: "#64748b" }}>连续天数</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <CheckCircleOutlined style={{ fontSize: 20, color: "#10b981", display: "block", margin: "0 auto" }} />
              <div style={{ fontSize: 20, fontWeight: 700, marginTop: 4 }}>{profile.strong_points.length}</div>
              <div style={{ fontSize: 11, color: "#64748b" }}>已掌握</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <ScheduleOutlined style={{ fontSize: 20, color: "#f59e0b", display: "block", margin: "0 auto" }} />
              <div style={{ fontSize: 20, fontWeight: 700, marginTop: 4 }}>{due.length}</div>
              <div style={{ fontSize: 11, color: "#64748b" }}>待复习</div>
            </div>
          </div>
        </div>

        {/* 薄弱点提醒 */}
        {weak.length > 0 && (
          <div style={cardStyle}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <WarningOutlined style={{ fontSize: 16, color: "#f43f5e" }} />
              <h3 style={{ fontWeight: 600, fontSize: 14, margin: 0 }}>薄弱点提醒</h3>
              <span style={{ fontSize: 12, color: "#64748b" }}>{weak.length} 个需重点关注</span>
            </div>
            <ul style={{ display: "flex", flexDirection: "column", gap: 8, listStyle: "none", margin: 0, padding: 0 }}>
              {weak.slice(0, 6).map((w) => {
                const kp = profile.kp_mastery[w.kp_id];
                if (!kp) return null;
                return (
                  <li key={w.kp_id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <span style={{ fontSize: 14 }}>{kp.kp_name}</span>
                    <span style={{ fontSize: 12, padding: "2px 8px", borderRadius: 9999, border: "1px solid", background: "#fff1f2", color: "#e11d48", borderColor: "#fecdd3" }}>
                      掌握 {Math.round(kp.mastery * 100)}%
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {/* 错因分析（design §5.3） */}
        {(weakAnalysis.length > 0 || errorPatterns.length > 0 || retention) && (
          <div style={cardStyle}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <RobotOutlined style={{ fontSize: 16, color: "#8b5cf6" }} />
              <h3 style={{ fontWeight: 600, fontSize: 14, margin: 0 }}>错因分析</h3>
              <span style={{ fontSize: 12, color: "#64748b" }}>题目数据自动统计</span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {/* 薄弱知识点条形 */}
              {weakAnalysis.length > 0 && (
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 500, color: "#475569", marginBottom: 6 }}>
                    <WarningOutlined style={{ fontSize: 14, color: "#f43f5e" }} /> TOP 薄弱知识点
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {weakAnalysis.slice(0, 5).map((w, i) => {
                      const max = weakAnalysis[0].mother_count || 1;
                      const kp = profile?.kp_mastery[w.knowledge_point_id];
                      return (
                        <div key={w.knowledge_point_id} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <span style={{ width: 16, fontSize: 10, color: "#94a3b8", textAlign: "right", flexShrink: 0 }}>{i + 1}</span>
                          <div style={{ flex: 1 }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 2 }}>
                              <span style={{ fontSize: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{kp?.kp_name || w.knowledge_point_id}</span>
                              <span style={{ fontSize: 10, color: "#94a3b8", flexShrink: 0 }}>{w.mother_count} 题</span>
                            </div>
                            <div style={{ height: 6, borderRadius: 9999, background: "rgba(241,245,249,0.5)", overflow: "hidden" }}>
                              <div
                                style={{ height: "100%", borderRadius: 9999, background: "linear-gradient(to right, #fb7185, #f43f5e)", width: `${Math.max(6, (w.mother_count / max) * 100)}%` }}
                              />
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* 错因模式标签云 */}
              {errorPatterns.length > 0 && (
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, fontWeight: 500, color: "#475569", marginBottom: 6 }}>
                    <PieChartOutlined style={{ fontSize: 14, color: "#6366f1" }} /> 常见错因
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                    {errorPatterns.slice(0, 8).map((p) => {
                      const total = errorPatterns.reduce((n, x) => n + x.count, 0);
                      const pct = total ? Math.round((p.count / total) * 100) : 0;
                      const tip =
                        p.reason.includes("计算")
                          ? "建议每天 5 道口算"
                          : p.reason.includes("审题")
                            ? "建议读题两遍再动笔"
                            : p.reason.includes("概念")
                              ? "建议回归教材重看定义"
                              : "建议针对该错因专项练习";
                      return (
                        <span
                          key={p.reason}
                          title={`${p.reason}：占 ${pct}%，${tip}`}
                          style={{ padding: "4px 8px", borderRadius: 9999, border: "1px solid #e2e8f0", background: "#eef2ff", fontSize: 11, color: "#4338ca" }}
                        >
                          {p.reason} {pct}%
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* 记忆保持率 */}
              {retention && retention.reviewed_count > 0 && (
                <div style={{ display: "flex", alignItems: "center", gap: 12, background: "rgba(236,253,245,0.6)", border: "1px solid #d1fae5", borderRadius: 12, padding: 12 }}>
                  <RiseOutlined style={{ fontSize: 20, color: "#10b981", flexShrink: 0 }} />
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 500, color: "#334155" }}>
                      记忆保持率 {retention.avg_retention}%
                    </div>
                    <div style={{ fontSize: 11, color: "#64748b", marginTop: 2 }}>
                      已复习 {retention.reviewed_count}/{retention.total_count} 题
                      {retention.avg_retention >= 60
                        ? " · 保持节奏，遗忘曲线控制得很好"
                        : " · 保持率偏低，建议增加复习频次"}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 各科掌握度 */}
        <div style={cardStyle}>
          <h3 style={{ fontWeight: 600, fontSize: 14, margin: "0 0 12px" }}>各科掌握度</h3>
          {Object.entries(bySubject).map(([subject, list]) => (
            <div key={subject} style={{ marginBottom: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 }}>
                <span style={{ fontWeight: 500 }}>{SUBJECT_LABEL[subject] || subject}</span>
                <span style={{ color: "#94a3b8" }}>{list.length} 个知识点</span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {list
                  .sort((a, b) => a.mastery - b.mastery)
                  .slice(0, 8)
                  .map((kp) => {
                    const meta = STATUS_META[kp.status] || STATUS_META.new;
                    return (
                      <div key={kp.kp_id} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 2 }}>
                            <span style={{ fontSize: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{kp.kp_name}</span>
                            <span style={{ fontSize: 10, padding: "2px 6px", borderRadius: 9999, border: "1px solid", ...meta.style }}>
                              {meta.label}
                            </span>
                          </div>
                          <div style={{ height: 6, borderRadius: 9999, background: "rgba(241,245,249,0.5)", overflow: "hidden" }}>
                            <div
                              style={{
                                height: "100%", borderRadius: 9999,
                                background:
                                  kp.status === "mastered"
                                    ? "#10b981"
                                    : kp.status === "weak"
                                      ? "#f43f5e"
                                      : "#0ea5e9",
                                width: `${Math.max(4, kp.mastery * 100)}%`,
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          ))}
        </div>

        {/* 复习建议 */}
        <div style={cardStyle}>
          <h3 style={{ fontWeight: 600, fontSize: 14, margin: "0 0 12px" }}>📋 复习建议</h3>
          {due.length > 0 ? (
            <ul style={{ display: "flex", flexDirection: "column", gap: 6, listStyle: "none", margin: 0, padding: 0 }}>
              {due.slice(0, 6).map((r) => (
                <li key={r.kp_id} style={{ fontSize: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span>{r.kp_name}</span>
                  <span style={{ color: "#d97706" }}>{r.reason}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p style={{ fontSize: 12, color: "#94a3b8", margin: 0 }}>当前没有积压的到期复习，保持节奏即可。</p>
          )}
        </div>

        {/* 徽章 */}
        {profile.badges && profile.badges.length > 0 && (
          <div style={cardStyle}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <TrophyOutlined style={{ fontSize: 16, color: "#f59e0b" }} />
              <h3 style={{ fontWeight: 600, fontSize: 14, margin: 0 }}>成长徽章</h3>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {profile.badges.map((b) => (
                <div
                  key={b.id}
                  title={b.desc}
                  style={{ display: "flex", alignItems: "center", gap: 4, padding: "4px 8px", borderRadius: 9999, border: "1px solid #fde68a", background: "#fffbeb", fontSize: 12, color: "#b45309" }}
                >
                  <span>{b.icon}</span>
                  {b.name}
                </div>
              ))}
            </div>
          </div>
        )}

        <Link
          to={withU("/e/tutor/h5/learn", viewU)}
          style={{ display: "block", textAlign: "center", padding: "12px 0", borderRadius: 16, background: "#4f46e5", color: "#fff", fontWeight: 500, boxShadow: "0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px -1px rgba(0,0,0,0.1)", textDecoration: "none" }}
        >
          去学习 → 继续巩固
        </Link>
      </div>
    </H5Shell>
  );
}
