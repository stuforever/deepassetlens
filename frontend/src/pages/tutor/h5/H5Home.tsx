/**
 * H5 落地页（design §一/§二 + 第十一篇 N2 重排）——原仓 app/h5/page.tsx 1:1 移植。
 *
 * 四层结构，一层只说一件事：
 * ① 紧凑 hero 一行（问候 + streak——合并原 hero 与面板的重复问候）
 * ② 今日面板主卡（C3 保留；学情速览降级为面板内一行小字，独立白卡删除）
 * ③ 继续上次（智能续学条：localStorage h5_last_learn，learn 页进章节时写入）
 * ④ 功能入口（两组 2 列网格带副标题：学习 / 工具）
 *
 * 等价替换清单：
 * - "use client" 删除；next/link → react-router-dom Link；
 * - lucide（Loader2/ChevronRight/PlayCircle + 原文件未使用的 BookOpen/Camera/BarChart3/
 *   MessageCircle/BookMarked/Trophy/AlarmClock/Map/RotateCcw）→ @ant-design/icons 对应导出；
 * - Tailwind → 内联样式逐项对位（active:/hover: 伪类与 print: 变体无法内联，随共享层先例省略）；
 * - fetch(apiUrl('/api/v1/...')) → fetch('/api/v1/...') 逐字；
 * - fetchLearnerProfile/LearnerProfileDto ← h5shared/selfLearningApi（SA-D 共享数据层）；
 * - 路由前缀映射：原 /h5/* → /e/tutor-h5/*。
 */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ReadOutlined, CameraOutlined, BarChartOutlined, LoadingOutlined, RightOutlined,
  MessageOutlined, BookOutlined, TrophyOutlined, ClockCircleOutlined, EnvironmentOutlined,
  PlayCircleOutlined, UndoOutlined,
} from "@ant-design/icons";
import { fetchLearnerProfile, type LearnerProfileDto } from "./h5shared/selfLearningApi";
import { withU } from "./h5shared/h5Utils";
import { H5Shell } from "./h5shared/H5Shell";

interface LastLearn {
  name: string;
  chapter: string;
  href: string;
  ts: number;
}

function readLastLearn(uid: string): LastLearn | null {
  try {
    // S5（M23-E）：per-u 键优先；旧全局键兜底（learn 页写入已迁 per-u）
    const raw =
      localStorage.getItem(`h5_last_learn::${uid}`) || localStorage.getItem("h5_last_learn");
    if (!raw) return null;
    const v = JSON.parse(raw);
    if (v && typeof v.href === "string" && typeof v.chapter === "string") return v;
  } catch {
    /* ignore */
  }
  return null;
}

const ENTRIES = [
  {
    key: "learn",
    title: "自主学习",
    desc: "三档练习 + 闯关",
    href: "/e/tutor-h5/learn",
    emoji: "⚔️",
    color: "linear-gradient(to bottom right, #3b82f6, #4f46e5)",
  },
  {
    key: "wrongbook",
    title: "错题本",
    desc: "复习 / 变式 / 导出",
    href: "/e/tutor-h5/wrongbook",
    emoji: "📖",
    color: "linear-gradient(to bottom right, #f97316, #d97706)",
  },
  {
    key: "review",
    title: "复习中心",
    desc: "到期卡片",
    href: "/e/tutor-h5/review",
    emoji: "🔄",
    color: "linear-gradient(to bottom right, #0ea5e9, #0891b2)",
  },
  {
    key: "atlas",
    title: "知识地图",
    desc: "掌握度总览",
    href: "/e/tutor-h5/atlas",
    emoji: "🗺️",
    color: "linear-gradient(to bottom right, #14b8a6, #059669)",
  },
  {
    key: "paths",
    title: "精通之路",
    desc: "知识点达标进阶",
    href: "/e/tutor-h5/paths",
    emoji: "🏆",
    color: "linear-gradient(to bottom right, #8b5cf6, #9333ea)",
  },
];

const TOOL_ENTRIES = [
  {
    key: "wrong",
    title: "拍错题",
    desc: "拍照秒入库",
    href: "/e/tutor-h5/wrong",
    emoji: "📷",
    color: "linear-gradient(to bottom right, #f43f5e, #db2777)",
  },
  {
    key: "report",
    title: "学情报告",
    desc: "家长可看",
    href: "/e/tutor-h5/report",
    emoji: "📊",
    color: "linear-gradient(to bottom right, #10b981, #0d9488)",
  },
];

const iconStyle = { fontSize: 16 } as const;

export default function H5Home() {
  const [profile, setProfile] = useState<LearnerProfileDto | null>(null);
  const [loading, setLoading] = useState(true);
  const [u, setU] = useState("");
  // C3（M18-B）：今日面板聚合数据
  const [panel, setPanel] = useState<any>(null);
  // N2-③：继续上次
  const [lastLearn, setLastLearn] = useState<LastLearn | null>(null);

  const fetchData = useCallback(async (uid: string) => {
    fetchLearnerProfile(uid || undefined)
      .then((p) => setProfile(p))
      .finally(() => setLoading(false));
    fetch(`/api/v1/learning/today-panel${uid ? `?u=${encodeURIComponent(uid)}` : ""}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setPanel(d))
      .catch(() => setPanel(null));
  }, []);

  useEffect(() => {
    // 用户标识：?u=xxx（H5 分享链接）或 ?openid=（公众号遗留）；
    // 无 u 时软登录：自动带最近身份（design §二）
    const params = new URLSearchParams(window.location.search);
    let uid = params.get("u") || params.get("openid") || "";
    if (!uid) {
      try {
        const raw = localStorage.getItem("h5_recent_users");
        const recents = raw ? JSON.parse(raw) : [];
        if (Array.isArray(recents) && recents.length) uid = recents[0];
      } catch {
        /* ignore */
      }
    }
    setU(uid);
    setLastLearn(readLastLearn(uid));
    void fetchData(uid);
  }, [fetchData]);

  const mastered = profile?.strong_points?.length ?? 0;
  const weak = profile?.weak_points?.length ?? 0;
  const due = profile?.due_reviews?.length ?? 0;
  const total = profile ? Object.keys(profile.kp_mastery).length : 0;

  // N2-①：问候按小时分档（面板未到时兜底）
  const hour = new Date().getHours();
  const greeting =
    panel?.greeting ||
    (hour < 6 ? "夜深了" : hour < 12 ? "早上好" : hour < 14 ? "中午好" : hour < 18 ? "下午好" : "晚上好");

  return (
    <H5Shell active="home" onRefresh={() => fetchData(u)}>
      {/* ① 紧凑 hero：一行问候 + streak */}
      <div
        style={{
          background: "linear-gradient(to right, #4f46e5, #7c3aed, #9333ea)",
          color: "#fff", padding: "48px 20px 56px", borderRadius: "0 0 24px 24px",
        }}
      >
        <div style={{ fontSize: 24, fontWeight: 700, letterSpacing: "-0.025em" }}>
          {greeting
            ? `${greeting}，${u || "同学"}`
            : "AI 私教 · 学习助手"}
          {typeof panel?.streak_days === "number" && panel.streak_days > 0 && (
            <span
              style={{
                marginLeft: 8, fontSize: 12, verticalAlign: "middle", padding: "2px 8px",
                borderRadius: 9999, background: "rgba(255,255,255,0.2)", fontWeight: 500,
                whiteSpace: "nowrap",
              }}
            >
              🔥 连续 {panel.streak_days} 天
            </span>
          )}
        </div>
        <div style={{ marginTop: 4, color: "#e0e7ff", fontSize: 14 }}>
          {u ? "已接入专属学情 🎯 · 记忆驱动 · 一题一策" : "记忆驱动 · 主动触达 · 一题一策"}
        </div>
      </div>

      {/* ② 今日面板主卡（C3 保留 + 学情一行小字） */}
      <div style={{ padding: "0 16px", marginTop: -32 }}>
        <div
          style={{
            borderRadius: 16, border: "1px solid #fde68a",
            background: "linear-gradient(to bottom right, #fffbeb, #fff7ed)",
            boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)", padding: 16,
          }}
        >
          {loading ? (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "16px 0", color: "#94a3b8", fontSize: 14 }}>
              <LoadingOutlined style={iconStyle} spin /> <span style={{ marginLeft: 8 }}>正在为你安排今天…</span>
            </div>
          ) : panel ? (
            <>
              {panel.done_today && (!panel.due_count) ? (
                <div style={{ marginTop: 10, fontSize: 14, color: "#047857", fontWeight: 500 }}>
                  ✅ 今日任务已完成，明天见！
                </div>
              ) : (
                <div style={{ marginTop: 8, fontSize: 14, color: "#334155", lineHeight: 1.625 }}>
                  📅 今天：
                  {panel.due_count > 0 && (
                    <> <b style={{ color: "#b45309" }}>{panel.due_count} 张错题卡到期</b>{panel.due_names?.length ? `（${panel.due_names.join("、")}）` : ""}{panel.path ? " ·" : ""}
                    </>
                  )}
                  {panel.path ? (
                    <> 路径「{panel.path.name || panel.path.book_id}」还剩 {panel.path.remaining_kp} 个知识点</>
                  ) : !panel.due_count ? (
                    <>还没有到期任务，去学点新东西吧</>
                  ) : null}
                  {panel.est_minutes > 0 && <span style={{ color: "#64748b" }}> · 预计 {panel.est_minutes} 分钟</span>}
                </div>
              )}
              {!panel.done_today && (
                <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
                  <Link
                    to={withU("/e/tutor-h5/learn", u)}
                    style={{
                      flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                      padding: "10px 0", borderRadius: 12, background: "#4f46e5", color: "#fff",
                      fontSize: 14, fontWeight: 500, textDecoration: "none",
                    }}
                  >
                    <PlayCircleOutlined style={iconStyle} /> 继续学习
                  </Link>
                  {panel.due_count > 0 && (
                    <Link
                      to={withU("/e/tutor-h5/wrongbook", u)}
                      style={{
                        flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                        padding: "10px 0", borderRadius: 12, background: "#fff", border: "1px solid #fcd34d",
                        color: "#b45309", fontSize: 14, fontWeight: 500, textDecoration: "none",
                      }}
                    >
                      📖 先复习
                    </Link>
                  )}
                </div>
              )}
              {/* N2：学情速览降级为面板内一行 */}
              <div
                style={{
                  marginTop: 12, paddingTop: 8, borderTop: "1px solid rgba(253,230,138,0.6)",
                  display: "flex", alignItems: "center", fontSize: 12, color: "#64748b",
                }}
              >
                <span>
                  已学 {total} · 薄弱 {weak} · 待复习 {due}
                </span>
                <Link to={withU("/e/tutor-h5/report", u)} style={{ marginLeft: "auto", color: "#4f46e5", display: "flex", alignItems: "center", textDecoration: "none" }}>
                  学情报告 <RightOutlined style={{ fontSize: 12 }} />
                </Link>
              </div>
            </>
          ) : (
            <div style={{ fontSize: 14, color: "#64748b" }}>打开学习页开始今天的学习吧 📚</div>
          )}
        </div>
      </div>

      {/* ③ 继续上次（智能续学条；learn 页写入 h5_last_learn） */}
      {lastLearn && (
        <div style={{ padding: "0 16px", marginTop: 12 }} data-testid="continue-last">
          <Link
            to={withU(
              lastLearn.href.startsWith("/h5")
                ? lastLearn.href.replace(/^\/h5/, "/e/tutor-h5")
                : lastLearn.href.startsWith("/e/tutor-h5")
                  ? lastLearn.href
                  : lastLearn.href.startsWith("/e/tutor/h5")
                    ? lastLearn.href.replace(/^\/e\/tutor\/h5/, "/e/tutor-h5") // IA批1 迁移前存档旧前缀归一
                    : "/e/tutor-h5/learn",
              u,
            )}
            style={{
              display: "flex", alignItems: "center", gap: 12, background: "#fff",
              borderRadius: 16, border: "1px solid #e0e7ff",
              boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)", padding: "12px 16px", textDecoration: "none",
            }}
          >
            <span
              style={{
                width: 40, height: 40, borderRadius: 12, background: "#eef2ff",
                display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, flexShrink: 0,
              }}
            >
              📖
            </span>
            <span style={{ flex: 1, minWidth: 0 }}>
              <span style={{ display: "block", fontSize: 12, color: "#94a3b8" }}>上次学到</span>
              <span style={{ display: "block", fontSize: 14, fontWeight: 500, color: "#1e293b", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {lastLearn.chapter || lastLearn.name}
              </span>
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, color: "#4f46e5", fontWeight: 500, flexShrink: 0 }}>
              继续 <RightOutlined style={{ fontSize: 14 }} />
            </span>
          </Link>
        </div>
      )}

      {/* ④ 功能入口：两组网格 */}
      <div style={{ padding: "0 16px", marginTop: 16 }}>
        <div style={{ fontSize: 12, color: "#94a3b8", fontWeight: 500, marginBottom: 8, padding: "0 4px" }}>学习</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 8 }}>
          {ENTRIES.map((entry) => (
            <Link
              key={entry.key}
              to={withU(entry.href, u)}
              style={{
                display: "flex", alignItems: "center", gap: 12, background: "#fff",
                borderRadius: 16, boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)", border: "1px solid #e2e8f0",
                padding: 14, textDecoration: "none",
              }}
            >
              <div
                style={{
                  width: 40, height: 40, borderRadius: 12, background: entry.color,
                  display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, flexShrink: 0,
                }}
              >
                {entry.emoji}
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: "#1e293b" }}>{entry.title}</div>
                <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{entry.desc}</div>
              </div>
            </Link>
          ))}
        </div>
        <div style={{ fontSize: 12, color: "#94a3b8", fontWeight: 500, marginBottom: 8, marginTop: 16, padding: "0 4px" }}>工具</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 8 }}>
          {TOOL_ENTRIES.map((entry) => (
            <Link
              key={entry.key}
              to={withU(entry.href, u)}
              style={{
                display: "flex", alignItems: "center", gap: 12, background: "#fff",
                borderRadius: 16, boxShadow: "0 1px 2px 0 rgba(0,0,0,0.05)", border: "1px solid #e2e8f0",
                padding: 14, textDecoration: "none",
              }}
            >
              <div
                style={{
                  width: 40, height: 40, borderRadius: 12, background: entry.color,
                  display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18, flexShrink: 0,
                }}
              >
                {entry.emoji}
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: "#1e293b" }}>{entry.title}</div>
                <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{entry.desc}</div>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* 底部提示 */}
      <div style={{ textAlign: "center", fontSize: 12, color: "#94a3b8", padding: "20px 24px 16px" }}>
        由遗忘曲线（FSRS-5）驱动 · 在正确的时间推送正确的内容
      </div>
    </H5Shell>
  );
}
