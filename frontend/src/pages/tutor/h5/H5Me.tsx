/**
 * H5 我的页（design §二）。原仓 app/h5/me/page.tsx 1:1 移植。
 *
 * 身份卡 + 最近身份切换（软登录）、统计卡、复习/朗读设置、分享设置、
 * 数据导出。u 由 ?u= 或最近身份决定。
 *
 * 等价替换清单：
 * - "use client" 删除；next/navigation（useSearchParams/useRouter）→ react-router-dom
 *   （useSearchParams/useNavigate，router.replace → navigate(replace:true)、router.push → navigate）；
 * - next/link → react-router-dom Link；
 * - lucide → @ant-design/icons：Loader2→LoadingOutlined、Flame→FireOutlined、Clock→ClockCircleOutlined、
 *   CheckCircle2→CheckCircleOutlined、Award→TrophyOutlined、UserRound→UserOutlined、Users→TeamOutlined、
 *   ChevronRight→RightOutlined、Share2→ShareAltOutlined、Mic→AudioOutlined、Download→DownloadOutlined、
 *   X→CloseOutlined、BookMarked→BookOutlined；
 * - useTtsCapability/ttsEngineLabel ← h5shared/useTtsCapability（本组私有移植件）；
 * - h5-outbox 动态 import → ./h5shared/h5Outbox；
 * - fetch(apiUrl(...)) → fetch('/api/v1/...') 逐字；window.confirm/window.alert 中文逐字保留；
 * - Tailwind → 内联样式逐项对位；`divide-y divide-slate-100` → .dsh-me-settings 子相邻边框规则；
 *   `pb-[max(1rem,env(safe-area-inset-bottom))]` → paddingBottom 同值；active:/hover: 变体随共享层先例省略；
 * - `process.env.NEXT_PUBLIC_BUILD_ID` → `process.env.REACT_APP_BUILD_ID`（CRA 注入口径，语义同源）；
 * - 路由前缀映射：原 /h5/* → /e/tutor-h5/*。
 */
import React, { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  LoadingOutlined, FireOutlined, ClockCircleOutlined, CheckCircleOutlined, TrophyOutlined,
  UserOutlined, TeamOutlined, RightOutlined, ShareAltOutlined, AudioOutlined, DownloadOutlined,
  CloseOutlined, BookOutlined,
} from "@ant-design/icons";
import { fetchLearnerProfile, type LearnerProfileDto } from "./h5shared/selfLearningApi";
import { withU } from "./h5shared/h5Utils";
import { H5Shell } from "./h5shared/H5Shell";
import { H5PageHeader } from "./h5shared/H5PageHeader";
import { H5Sheet } from "./h5shared/H5Sheet";
import { useTtsCapability, ttsEngineLabel } from "./h5shared/useTtsCapability";

const RECENT_KEY = "h5_recent_users";

function readRecentUsers(): string[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    const list = raw ? JSON.parse(raw) : [];
    return Array.isArray(list) ? list.filter((x) => typeof x === "string") : [];
  } catch {
    return [];
  }
}

function writeRecentUser(u: string) {
  if (!u) return;
  try {
    const list = [u, ...readRecentUsers().filter((x) => x !== u)].slice(0, 5);
    localStorage.setItem(RECENT_KEY, JSON.stringify(list));
  } catch {
    /* ignore */
  }
}

// D1（M22）：部署版本徽标——原 NEXT_PUBLIC_BUILD_ID（Next 构建烤入）→ CRA 的 REACT_APP_BUILD_ID
const BUILD_ID = (process.env as { REACT_APP_BUILD_ID?: string }).REACT_APP_BUILD_ID;

function MeContent() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const urlU = searchParams.get("u") || searchParams.get("openid") || "";
  const [u, setU] = useState("");
  const [profile, setProfile] = useState<LearnerProfileDto | null>(null);
  const [loading, setLoading] = useState(true);
  const [recent, setRecent] = useState<string[]>([]);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [newU, setNewU] = useState("");
  const [speechRate, setSpeechRate] = useState(1);
  // E4（M12）语音对话开关（localStorage：h5_tts_auto / h5_voice_loop）
  const [ttsAuto, setTtsAuto] = useState(false);
  const [voiceLoop, setVoiceLoop] = useState(false);
  const [publicBase, setPublicBase] = useState("");
  const [accessCode, setAccessCode] = useState("");
  const [exporting, setExporting] = useState(false);
  // P2-C2 家庭关联（家长-孩子只读视角）
  const [children, setChildren] = useState<{ child: string; note: string }[]>([]);
  const [newChild, setNewChild] = useState("");
  // P3-A PWA：是否已全屏运行（standalone），是则隐藏安装引导
  const [isStandalone, setIsStandalone] = useState(false);
  // E3（M12）：离线答题待同步条
  const [pendingSync, setPendingSync] = useState(0);
  // T1/T2（第十二篇）：朗读引擎设置 + 能力检测
  const tts = useTtsCapability();
  const [ttsEngine, setTtsEngine] = useState<"auto" | "browser" | "server">("auto");
  // N6-h（第十一篇）：管理员认领题库给孩子
  const [claimTarget, setClaimTarget] = useState("");
  const [claimMsg, setClaimMsg] = useState("");

  // E3（M12）：outbox 待同步数实时刷新
  useEffect(() => {
    let alive = true;
    const refresh = () => {
      void import("./h5shared/h5Outbox")
        .then((m) => m.count())
        .then((n) => {
          if (alive) setPendingSync(n);
        })
        .catch(() => {});
    };
    refresh();
    window.addEventListener("dsh-outbox-synced", refresh);
    window.addEventListener("online", refresh);
    return () => {
      alive = false;
      window.removeEventListener("dsh-outbox-synced", refresh);
      window.removeEventListener("online", refresh);
    };
  }, []);

  // 软登录：无 ?u= 时用最近身份
  useEffect(() => {
    const recents = readRecentUsers();
    setRecent(recents);
    const effective = urlU || recents[0] || "";
    setU(effective);
  }, [urlU]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem("h5_speech_rate");
      const n = raw ? parseFloat(raw) : NaN;
      if (Number.isFinite(n) && n >= 0.5 && n <= 2) setSpeechRate(n);
    } catch {
      /* ignore */
    }
    try {
      setPublicBase(localStorage.getItem("h5_public_base") || "");
    } catch {
      /* ignore */
    }
    // E4（M12）语音对话开关
    try {
      setTtsAuto(localStorage.getItem("h5_tts_auto") === "1");
      setVoiceLoop(localStorage.getItem("h5_voice_loop") === "1");
      const eng = localStorage.getItem("h5_tts_engine");
      if (eng === "browser" || eng === "server" || eng === "auto") setTtsEngine(eng);
    } catch {
      /* ignore */
    }
  }, []);

  // P3-A：检测已全屏运行（standalone）则隐藏安装引导
  useEffect(() => {
    if (
      typeof window !== "undefined" &&
      window.matchMedia("(display-mode: standalone)").matches
    ) {
      setIsStandalone(true);
    }
  }, []);

  // P3-B：加载公网设置（public_base + access_code，后端为准，localStorage 兜底）
  useEffect(() => {
    void fetch("/api/v1/h5-settings")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        if (d.public_base) setPublicBase(d.public_base);
        if (typeof d.access_code === "string") setAccessCode(d.access_code);
      })
      .catch(() => {
        /* 离线用 localStorage 兜底 */
      });
  }, []);

  useEffect(() => {
    if (!u) {
      setLoading(false);
      setProfile(null);
      return;
    }
    setLoading(true);
    writeRecentUser(u);
    setRecent(readRecentUsers());
    fetchLearnerProfile(u || undefined)
      .then((p) => setProfile(p))
      .catch(() => setProfile(null))
      .finally(() => setLoading(false));
  }, [u]);

  const switchTo = useCallback(
    (next: string) => {
      setU(next);
      setPickerOpen(false);
      navigate(withU("/e/tutor-h5/me", next), { replace: true });
    },
    [navigate],
  );

  // P2-C2 家庭关联（家长-孩子只读视角）
  const reloadChildren = useCallback(() => {
    if (!u) {
      setChildren([]);
      return;
    }
    fetch(`/api/v1/h5-links?parent=${encodeURIComponent(u)}`)
      .then((r) => (r.ok ? r.json() : { children: [] }))
      .then((d) =>
        setChildren(
          (d.children || []).map((c: any) => ({ child: c.child, note: c.note || "" })),
        ),
      )
      .catch(() => setChildren([]));
  }, [u]);

  useEffect(() => {
    reloadChildren();
  }, [reloadChildren]);

  const addChild = async () => {
    const name = newChild.trim();
    if (!name || !u) return;
    try {
      await fetch("/api/v1/h5-links", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ parent: u, child: name, note: "" }),
      });
      setNewChild("");
      reloadChildren();
    } catch {
      /* ignore */
    }
  };

  const removeChild = async (name: string) => {
    if (!u) return;
    try {
      await fetch(
        `/api/v1/h5-links?parent=${encodeURIComponent(u)}&child=${encodeURIComponent(name)}`,
        { method: "DELETE" },
      );
      reloadChildren();
    } catch {
      /* ignore */
    }
  };

  const setRate = (v: number) => {
    setSpeechRate(v);
    try {
      localStorage.setItem("h5_speech_rate", String(v));
    } catch {
      /* ignore */
    }
  };

  // P3-B 保存公网设置（public_base + access_code 到后端，localStorage 兜底）
  const saveSettings = async () => {
    const pb = publicBase.trim();
    const ac = accessCode.trim();
    try {
      const res = await fetch("/api/v1/h5-settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ public_base: pb, access_code: ac }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => null);
        window.alert((d && d.detail) || "保存失败");
        return;
      }
      try {
        localStorage.setItem("h5_public_base", pb);
      } catch {
        /* ignore */
      }
      window.alert("已保存：分享链接与访问码已生效");
    } catch {
      window.alert("保存失败（后端不可用）");
    }
  };

  const exportData = useCallback(async () => {
    if (!u) return;
    setExporting(true);
    try {
      const res = await fetch(`/api/v1/learner-profile?u=${encodeURIComponent(u)}`);
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `learner-profile-${u}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      /* ignore */
    } finally {
      setExporting(false);
    }
  }, [u]);

  const mastered = profile?.strong_points?.length ?? 0;
  const weak = profile?.weak_points?.length ?? 0;
  const total = profile ? Object.keys(profile.kp_mastery).length : 0;
  const due = profile?.due_reviews?.length ?? 0;

  // N6-h（第十一篇）：管理员把 admin 题库认领给孩子（复制到目标 H5 用户）
  const claimAll = async () => {
    const target = claimTarget.trim();
    if (!target) return;
    if (!window.confirm(`把管理员的全部错题认领给「${target}」？已存在的题目会自动跳过`)) return;
    setClaimMsg("认领中…");
    try {
      const res = await fetch("/api/v1/mother-questions/claim", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_u: target, all: true, include_variants: true }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        setClaimMsg(`✅ 已认领 ${data.claimed ?? 0} 道题给「${target}」${data.skipped_dup ? `（跳过重复 ${data.skipped_dup}）` : ""}`);
      } else {
        setClaimMsg(`❌ ${data.detail || "认领失败"}`);
      }
    } catch {
      setClaimMsg("❌ 网络错误，请重试");
    }
  };

  const shareUrl = useMemo(() => {
    const base = (publicBase || (typeof window !== "undefined" ? window.location.origin : "")).replace(/\/$/, "");
    return base + withU("/e/tutor-h5", u);
  }, [publicBase, u]);

  return (
    <H5Shell active="me">
      {/* 顶栏 */}
      <div style={{ background: "linear-gradient(to right, #475569, #1e293b)", color: "#fff", padding: "48px 16px 56px", borderRadius: "0 0 24px 24px" }}>
        <H5PageHeader title="👤 我的" />
      </div>

      <div style={{ padding: "0 16px", marginTop: -32, display: "flex", flexDirection: "column", gap: 16 }}>
        {/* 身份卡 */}
        <div style={{ background: "#fff", borderRadius: 16, boxShadow: "0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.1)", border: "1px solid #e2e8f0", padding: 16, display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 56, height: 56, borderRadius: 9999, background: "#e0e7ff", color: "#4f46e5", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, fontWeight: 700, flexShrink: 0 }}>
            {u ? u.slice(0, 1).toUpperCase() : "?"}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, color: "#1e293b" }}>{u || "未选择身份"}</div>
            <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 2 }}>
              {u ? "已接入专属学情" : "选择身份后开始记录学习"}
            </div>
          </div>
          <button
            onClick={() => setPickerOpen(true)}
            style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 14, color: "#4f46e5", padding: "6px 12px", borderRadius: 9999, border: "1px solid #c7d2fe", background: "#eef2ff", cursor: "pointer" }}
          >
            <UserOutlined style={{ fontSize: 16 }} /> 切换
          </button>
        </div>

        {/* 统计卡 */}
        <div style={{ background: "#fff", borderRadius: 16, boxShadow: "0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px -1px rgba(0,0,0,0.1)", border: "1px solid #e2e8f0", padding: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 600, color: "#1e293b", marginBottom: 12 }}>
            <CheckCircleOutlined style={{ fontSize: 16, color: "#10b981" }} /> 学习统计
          </div>
          {loading ? (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "24px 0", color: "#94a3b8" }}>
              <LoadingOutlined style={{ fontSize: 16 }} spin /> <span style={{ marginLeft: 8 }}>加载中…</span>
            </div>
          ) : !u || !profile ? (
            <div style={{ textAlign: "center", padding: "24px 0", fontSize: 14, color: "#94a3b8" }}>
              选择身份后查看统计
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 8 }}>
              <div style={{ textAlign: "center" }}>
                <FireOutlined style={{ fontSize: 20, color: "#f97316", display: "block", margin: "0 auto" }} />
                <div style={{ fontSize: 20, fontWeight: 700, marginTop: 4 }}>{profile.streak_days}</div>
                <div style={{ fontSize: 10, color: "#64748b" }}>连续天数</div>
              </div>
              <div style={{ textAlign: "center" }}>
                <ClockCircleOutlined style={{ fontSize: 20, color: "#3b82f6", display: "block", margin: "0 auto" }} />
                <div style={{ fontSize: 20, fontWeight: 700, marginTop: 4 }}>
                  {Math.round(profile.total_study_minutes || 0)}
                </div>
                <div style={{ fontSize: 10, color: "#64748b" }}>学习分钟</div>
              </div>
              <div style={{ textAlign: "center" }}>
                <CheckCircleOutlined style={{ fontSize: 20, color: "#10b981", display: "block", margin: "0 auto" }} />
                <div style={{ fontSize: 20, fontWeight: 700, marginTop: 4 }}>{mastered}</div>
                <div style={{ fontSize: 10, color: "#64748b" }}>已掌握</div>
              </div>
              <div style={{ textAlign: "center" }}>
                <TrophyOutlined style={{ fontSize: 20, color: "#f59e0b", display: "block", margin: "0 auto" }} />
                <div style={{ fontSize: 20, fontWeight: 700, marginTop: 4 }}>
                  {(profile.badges || []).length}
                </div>
                <div style={{ fontSize: 10, color: "#64748b" }}>徽章</div>
              </div>
            </div>
          )}

          {/* 徽章墙 */}
          {u && profile && (profile.badges || []).length > 0 && (
            <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid #f1f5f9", display: "flex", flexWrap: "wrap", gap: 8 }}>
              {profile.badges!.map((b: any) => (
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
          )}

          {u && due > 0 && (
            <Link
              to={withU("/e/tutor-h5/wrongbook", u)}
              style={{ marginTop: 12, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 12px", borderRadius: 12, background: "#fffbeb", border: "1px solid #fde68a", fontSize: 14, color: "#b45309", textDecoration: "none" }}
            >
              有 {due} 项到期复习
              <RightOutlined style={{ fontSize: 16 }} />
            </Link>
          )}
        </div>

        {/* 设置 */}
        {/* divide-y divide-slate-100 等价：.dsh-me-settings 相邻子块上边框（见页内 <style>） */}
        <div className="dsh-me-settings" style={{ background: "#fff", borderRadius: 16, boxShadow: "0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px -1px rgba(0,0,0,0.1)", border: "1px solid #e2e8f0" }}>
          {/* P3-A 安装到主屏引导（全屏运行时隐藏） */}
          {!isStandalone && (
            <div style={{ padding: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 600, color: "#1e293b", fontSize: 14, marginBottom: 4 }}>
                <DownloadOutlined style={{ fontSize: 16, color: "#6366f1" }} /> 📲 安装到主屏
              </div>
              <div style={{ fontSize: 12, color: "#64748b", display: "flex", flexDirection: "column", gap: 4 }}>
                <div>· iOS：浏览器分享 → 添加到主屏幕</div>
                <div>· Android：浏览器菜单 → 安装应用</div>
                <div>· 安装后可全屏使用，已访问的课件离线可读</div>
              </div>
            </div>
          )}
          {/* 复习设置 */}
          <div style={{ padding: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 600, color: "#1e293b", fontSize: 14, marginBottom: 8 }}>
              <CheckCircleOutlined style={{ fontSize: 16, color: "#6366f1" }} /> 复习设置
            </div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 14, color: "#475569" }}>
              <span>每日复习上限</span>
              <span style={{ color: "#1e293b", fontWeight: 500 }}>20 题</span>
            </div>
            <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>
              到期复习按遗忘曲线排序，超出上限的顺延到明天
            </div>
          </div>

          {/* 朗读语速 */}
          <div style={{ padding: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 600, color: "#1e293b", fontSize: 14, marginBottom: 8 }}>
              <AudioOutlined style={{ fontSize: 16, color: "#8b5cf6" }} /> 朗读语速
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 12, color: "#94a3b8" }}>0.5</span>
              <input
                type="range"
                min={0.5}
                max={2}
                step={0.1}
                value={speechRate}
                onChange={(e) => setRate(parseFloat(e.target.value))}
                style={{ flex: 1, accentColor: "#4f46e5" }}
              />
              <span style={{ fontSize: 12, color: "#94a3b8" }}>2.0</span>
              <span style={{ fontSize: 14, fontWeight: 500, color: "#334155", width: 40, textAlign: "right" }}>
                {speechRate.toFixed(1)}x
              </span>
            </div>
            <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>
              应用于对话 / 错题本的语音朗读（浏览器 TTS）
            </div>
          </div>

          {/* T1/T2（第十二篇）：朗读引擎——检测状态明说 + 服务端兜底 */}
          <div style={{ padding: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 600, color: "#1e293b", fontSize: 14, marginBottom: 8 }}>
              <AudioOutlined style={{ fontSize: 16, color: "#0ea5e9" }} /> 朗读引擎
            </div>
            <div style={{ fontSize: 12, marginBottom: 8 }} data-testid="tts-status">
              浏览器语音：
              {tts.status === "ok"
                ? `✅ 已检测到中文语音${tts.voiceName ? `（${tts.voiceName}）` : ""}`
                : tts.status === "no-voice"
                  ? "⚠️ 未检测到中文语音，将使用服务端朗读"
                  : tts.status === "unsupported"
                    ? "❌ 此浏览器不支持朗读"
                    : "检测中…"}
            </div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {(["auto", "browser", "server"] as const).map((eng) => (
                <button
                  key={eng}
                  onClick={() => {
                    setTtsEngine(eng);
                    try {
                      localStorage.setItem("h5_tts_engine", eng);
                    } catch {
                      /* ignore */
                    }
                  }}
                  style={{
                    padding: "6px 12px", borderRadius: 9999, fontSize: 12, cursor: "pointer",
                    background: ttsEngine === eng ? "#0ea5e9" : "#fff",
                    color: ttsEngine === eng ? "#fff" : "#64748b",
                    border: `1px solid ${ttsEngine === eng ? "#0ea5e9" : "#e2e8f0"}`,
                    fontWeight: ttsEngine === eng ? 500 : 400,
                  }}
                >
                  {ttsEngineLabel(eng)}
                </button>
              ))}
            </div>
            <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 6 }}>
              「智能」= 浏览器有中文语音用浏览器（零成本），没有自动落服务端合成；服务端朗读需在桌面「设置」配置 TTS。
            </div>
          </div>

          {/* E4 语音对话（M12）：自动播报 + 连续语音 */}
          <div style={{ padding: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 600, color: "#1e293b", fontSize: 14, marginBottom: 8 }}>
              <AudioOutlined style={{ fontSize: 16, color: "#10b981" }} /> 语音对话
            </div>
            <label style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 0", cursor: "pointer" }}>
              <span style={{ fontSize: 14, color: "#334155" }}>AI 回复自动播报</span>
              <input
                type="checkbox"
                checked={ttsAuto}
                onChange={(e) => {
                  setTtsAuto(e.target.checked);
                  try {
                    localStorage.setItem("h5_tts_auto", e.target.checked ? "1" : "0");
                  } catch {
                    /* ignore */
                  }
                }}
                style={{ accentColor: "#059669", width: 20, height: 20 }}
              />
            </label>
            <label style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 0", cursor: "pointer" }}>
              <span style={{ fontSize: 14, color: "#334155" }}>连续语音对话（零触屏）</span>
              <input
                type="checkbox"
                checked={voiceLoop}
                onChange={(e) => {
                  setVoiceLoop(e.target.checked);
                  try {
                    localStorage.setItem("h5_voice_loop", e.target.checked ? "1" : "0");
                  } catch {
                    /* ignore */
                  }
                }}
                style={{ accentColor: "#059669", width: 20, height: 20 }}
              />
            </label>
            <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>
              连续语音：自动听→AI 回答自动播报→再听，两轮对话零触屏；点击输入框或按住说话即退出。
            </div>
          </div>

          {/* 分享设置（P3-B：public_base + access_code 后端持久化） */}
          <div style={{ padding: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 600, color: "#1e293b", fontSize: 14, marginBottom: 8 }}>
              <ShareAltOutlined style={{ fontSize: 16, color: "#f59e0b" }} /> 分享给家人
            </div>
            <label style={{ fontSize: 12, color: "#64748b", marginBottom: 4, display: "block" }}>
              公网地址（内网穿透后的域名）
            </label>
            <input
              value={publicBase}
              onChange={(e) => setPublicBase(e.target.value)}
              placeholder="https://你的公网地址"
              style={{ width: "100%", padding: "8px 12px", borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 14, boxSizing: "border-box" }}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: "#94a3b8", wordBreak: "break-all" }}>{shareUrl}</div>
            <label style={{ fontSize: 12, color: "#64748b", marginTop: 12, marginBottom: 4, display: "block" }}>
              访问码（可选，设置后他人需输码才能打开）
            </label>
            <input
              value={accessCode}
              onChange={(e) => setAccessCode(e.target.value)}
              placeholder="留空则不设访问码"
              type="password"
              style={{ width: "100%", padding: "8px 12px", borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 14, boxSizing: "border-box" }}
            />
            <button
              onClick={() => void saveSettings()}
              style={{ marginTop: 12, width: "100%", padding: "10px 0", borderRadius: 12, background: "#f59e0b", color: "#fff", fontSize: 14, fontWeight: 500, border: "none", cursor: "pointer" }}
            >
              保存设置
            </button>
            <Link
              to={withU("/e/tutor-h5/share", u)}
              style={{ marginTop: 12, display: "flex", alignItems: "center", justifyContent: "center", gap: 4, width: "100%", padding: "10px 0", borderRadius: 12, border: "1px solid #fcd34d", color: "#d97706", fontSize: 14, fontWeight: 500, textDecoration: "none" }}
            >
              <ShareAltOutlined style={{ fontSize: 16 }} /> 生成分享二维码
            </Link>
          </div>

          {/* 数据导出 */}
          <div style={{ padding: 16 }}>
            <button
              onClick={() => void exportData()}
              disabled={exporting || !u}
              style={{ display: "flex", alignItems: "center", gap: 8, width: "100%", padding: "10px 0", borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 14, color: "#475569", justifyContent: "center", background: "none", cursor: "pointer", opacity: exporting || !u ? 0.5 : 1 }}
            >
              <DownloadOutlined style={{ fontSize: 16 }} />
              {exporting ? "导出中…" : "导出学情数据（JSON）"}
            </button>
          </div>

          {/* E3（M12）：离线答题待同步条 */}
          {pendingSync > 0 && (
            <div style={{ marginBottom: 12, padding: "10px 16px", borderRadius: 12, background: "#fffbeb", border: "1px solid #fde68a", color: "#b45309", fontSize: 14, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
              <span>📤 待同步 {pendingSync} 条学习记录</span>
              <button
                onClick={() => {
                  void import("./h5shared/h5Outbox")
                    .then((m) => m.replay())
                    .then(() => window.dispatchEvent(new Event("dsh-outbox-synced")))
                    .catch(() => {});
                }}
                style={{ fontSize: 12, fontWeight: 500, textDecoration: "underline", flexShrink: 0, background: "none", border: "none", cursor: "pointer", color: "inherit" }}
              >
                立即同步
              </button>
            </div>
          )}

          {/* 家庭关联（P2-C2：家长-孩子只读视角） */}
          <div style={{ padding: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 600, color: "#1e293b", fontSize: 14, marginBottom: 8 }}>
              <UserOutlined style={{ fontSize: 16, color: "#ec4899" }} /> 家庭关联
            </div>
            <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 8 }}>
              关联孩子后，可在学情报告中切换到孩子视角（只读）查看 TA 的学习情况。
            </div>
            {children.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 8 }}>
                {children.map((c) => (
                  <div
                    key={c.child}
                    style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 12px", borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 14 }}
                  >
                    <UserOutlined style={{ fontSize: 16, color: "#cbd5e1", flexShrink: 0 }} />
                    <span style={{ fontWeight: 500, color: "#334155" }}>{c.child}</span>
                    {c.note && <span style={{ fontSize: 12, color: "#94a3b8" }}>{c.note}</span>}
                    <button
                      onClick={() => void removeChild(c.child)}
                      style={{ marginLeft: "auto", color: "#cbd5e1", background: "none", border: "none", cursor: "pointer", padding: 0 }}
                      aria-label={`解除 ${c.child}`}
                    >
                      <CloseOutlined style={{ fontSize: 16 }} />
                    </button>
                  </div>
                ))}
              </div>
            )}
            {children.length === 0 && (
              <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 8 }}>
                还没有关联孩子，输入孩子的名字添加。
              </div>
            )}
            <div style={{ display: "flex", gap: 8 }}>
              <input
                value={newChild}
                onChange={(e) => setNewChild(e.target.value)}
                placeholder="孩子名字（如：小明）"
                style={{ flex: 1, padding: "8px 12px", borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 14, minWidth: 0, boxSizing: "border-box" }}
                maxLength={20}
              />
              <button
                onClick={() => void addChild()}
                disabled={!newChild.trim()}
                style={{ padding: "8px 16px", borderRadius: 12, background: "#ec4899", color: "#fff", fontSize: 14, fontWeight: 500, border: "none", cursor: "pointer", opacity: newChild.trim() ? 1 : 0.5 }}
              >
                关联
              </button>
            </div>
          </div>
          {/* N6-h（第十一篇）：管理员认领题库给孩子（仅无 ?u= 的管理视图显示） */}
          {!urlU && (
            <div style={{ padding: 16 }} data-testid="claim-card">
              <div style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 600, color: "#1e293b", fontSize: 14, marginBottom: 8 }}>
                <BookOutlined style={{ fontSize: 16, color: "#f59e0b" }} /> 认领题库给孩子
              </div>
              <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 8 }}>
                把管理员错题本的全部母题（含变式）复制到孩子的错题本，重复题目自动跳过。
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <input
                  value={claimTarget}
                  onChange={(e) => setClaimTarget(e.target.value)}
                  placeholder="孩子的名字（如：小明）"
                  style={{ flex: 1, padding: "8px 12px", borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 14, minWidth: 0, boxSizing: "border-box" }}
                  maxLength={20}
                />
                <button
                  onClick={() => void claimAll()}
                  disabled={!claimTarget.trim()}
                  style={{ padding: "8px 16px", borderRadius: 12, background: "#f59e0b", color: "#fff", fontSize: 14, fontWeight: 500, border: "none", cursor: "pointer", opacity: claimTarget.trim() ? 1 : 0.5 }}
                >
                  认领
                </button>
              </div>
              {claimMsg && <div style={{ fontSize: 12, marginTop: 8, color: "#475569" }}>{claimMsg}</div>}
            </div>
          )}

          {/* E2（M11）：班级视图入口 */}
          <button
            onClick={() => navigate(`/e/tutor-h5/classroom?u=${encodeURIComponent(u)}`)}
            style={{ width: "100%", marginTop: 12, padding: "10px 0", borderRadius: 12, border: "1px solid #c7d2fe", background: "#eef2ff", color: "#4f46e5", fontSize: 14, fontWeight: 500, cursor: "pointer" }}
          >
            <TeamOutlined style={{ fontSize: 16, marginRight: 4, verticalAlign: "-0.125em" }} /> 以班级视图查看
          </button>
        </div>

        <div style={{ fontSize: 12, color: "#94a3b8", padding: "0 8px 16px", textAlign: "center" }}>
          数据按用户隔离存储 · 私密安全
          {/* D1（M22）：部署版本徽标——构建时烤入，与 launcher 自检/SW 对比同源 */}
          {BUILD_ID && (
            <div style={{ marginTop: 4, fontSize: 10, color: "#cbd5e1", userSelect: "all" }} data-testid="dt-build-badge">
              版本 {BUILD_ID}
            </div>
          )}
        </div>
      </div>

      {/* 身份切换弹层（S1/M23：H5Sheet 统一基座 + S2 选择列表） */}
      <H5Sheet open={pickerOpen} onClose={() => setPickerOpen(false)} title="选择身份">
        <div style={{ padding: "0 20px", paddingBottom: "max(1rem, env(safe-area-inset-bottom))" }}>
          {/* 最近身份 */}
          {recent.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: "#94a3b8" }}>最近使用</div>
              {recent.map((name) => (
                <button
                  key={name}
                  onClick={() => switchTo(name)}
                  style={{
                    width: "100%", textAlign: "left", minHeight: 44, padding: "10px 12px", borderRadius: 12,
                    border: "1px solid", fontSize: 14, cursor: "pointer",
                    background: name === u ? "#eef2ff" : "#fff",
                    borderColor: name === u ? "#c7d2fe" : "#e2e8f0",
                    color: name === u ? "#4338ca" : "inherit",
                    fontWeight: name === u ? 500 : 400,
                  }}
                >
                  {name}
                  {name === u && <span style={{ marginLeft: 8, fontSize: 12 }}>当前</span>}
                </button>
              ))}
            </div>
          )}

          {/* 新增身份 */}
          <div style={{ display: "flex", gap: 8 }}>
            <input
              value={newU}
              onChange={(e) => setNewU(e.target.value)}
              placeholder="输入名字（如：小明 / 小红）"
              style={{ flex: 1, minHeight: 44, padding: "10px 12px", borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 14, minWidth: 0, boxSizing: "border-box" }}
              maxLength={20}
            />
            <button
              onClick={() => {
                const name = newU.trim();
                if (name) {
                  writeRecentUser(name);
                  setRecent(readRecentUsers());
                  switchTo(name);
                  setNewU("");
                }
              }}
              style={{ padding: "10px 16px", minHeight: 44, borderRadius: 12, background: "#4f46e5", color: "#fff", fontSize: 14, fontWeight: 500, border: "none", cursor: "pointer" }}
            >
              使用
            </button>
          </div>
          <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 8 }}>
            每个名字有独立的学习记录和学情画像
          </div>
        </div>
      </H5Sheet>

      {/* divide-y 等价规则：设置卡内相邻子块的上边框 */}
      <style>{`
        .dsh-me-settings > div + div { border-top: 1px solid #f1f5f9; }
      `}</style>
    </H5Shell>
  );
}

export default function H5Me() {
  return (
    <Suspense
      fallback={
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", color: "#94a3b8" }}>
          <LoadingOutlined style={{ fontSize: 20 }} spin /> <span style={{ marginLeft: 8 }}>加载中…</span>
        </div>
      }
    >
      <MeContent />
    </Suspense>
  );
}
