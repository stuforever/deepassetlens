/**
 * H5 App 壳层：固定底部 TabBar（design §一）——原仓 app/h5/components/H5Shell.tsx 1:1 移植。
 * 等价替换：next/link → react-router Link；useRouter → useNavigate；
 * lucide（Home/BookOpen/MessageCircle/BookMarked/User/Loader2）→ @ant-design/icons 对应；
 * Tailwind → 内联样式逐项对位；apiUrl(x) → fetch('/api/v1/...')。
 * 路由前缀映射：原 /h5/* → tupu /e/tutor-h5/*（TABS hrefs 同步映射）。
 *
 * 不做 layout（tab 高亮语义用 prop 更可控）。角标数据（错题 due_count）
 * 在此统一轮询（60s + window.focus 刷新），各页不再各自请求。
 * P3-B 访问码 fetch 补丁 / U2 首访身份引导 / N1 下拉刷新 / T4 TTS 解锁 /
 * E3 离线 outbox / P3-A PWA SW / D2 新版本黄条——全部保留。
 */
import React, { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  HomeOutlined, ReadOutlined, MessageOutlined, BookOutlined, UserOutlined, LoadingOutlined,
} from "@ant-design/icons";
import { withU, getH5User } from "./h5Utils";
import { isNewVersionMessage } from "./h5Version";
import { H5Sheet } from "./H5Sheet";

// P3-B：会话已解锁访问码时，给所有 fetch 附加 X-Access-Code header。
// 仅浏览器端执行；桌面端/未解锁时 sessionStorage 无码 => 零影响。
if (typeof window !== "undefined") {
  const _origFetch = window.fetch.bind(window);
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    let code = "";
    try {
      code = sessionStorage.getItem("dsh_h5_code") || "";
    } catch {
      /* ignore */
    }
    if (code) {
      const headers = new Headers(init?.headers);
      if (!headers.has("X-Access-Code")) headers.set("X-Access-Code", code);
      init = { ...init, headers };
    }
    return _origFetch(input, init);
  };
}

export type H5Tab = "home" | "learn" | "chat" | "wrongbook" | "me";

const TABS: { key: H5Tab; label: string; href: string; icon: typeof HomeOutlined }[] = [
  { key: "home", label: "首页", href: "/e/tutor-h5", icon: HomeOutlined },
  { key: "learn", label: "学习", href: "/e/tutor-h5/learn", icon: ReadOutlined },
  { key: "chat", label: "对话", href: "/e/tutor-h5/chat", icon: MessageOutlined },
  { key: "wrongbook", label: "错题本", href: "/e/tutor-h5/wrongbook", icon: BookOutlined },
  { key: "me", label: "我的", href: "/e/tutor-h5/me", icon: UserOutlined },
];

/**
 * P9 门禁①：当前 URL 的 u/openid + code query 串（供 TabBar 链接透传）。
 */
function currentTabQuery(): string {
  if (typeof window === "undefined") return "";
  const params = new URLSearchParams(window.location.search);
  const uid = params.get("u") || params.get("openid") || "";
  const code = params.get("code") || "";
  return [
    uid ? `u=${encodeURIComponent(uid)}` : "",
    code ? `code=${encodeURIComponent(code)}` : "",
  ]
    .filter(Boolean)
    .join("&");
}

export function H5Shell({
  active,
  hideNav,
  onRefresh,
  children,
}: {
  active: H5Tab | (string & {});
  hideNav?: boolean;
  /** 传入后启用下拉刷新（列表页数据重拉） */
  onRefresh?: () => Promise<void> | void;
  children: React.ReactNode;
}) {
  const u = getH5User();
  // P9 门禁①：TabBar 链接丢 u——挂载后按当前 URL 重算 u/code query，
  // 状态翻转驱动重渲把 query 补进链接；每次（重）渲染都重算。
  const [tabQueryMounted, setTabQueryMounted] = useState(false);
  useEffect(() => setTabQueryMounted(true), []);
  const tabQuery = tabQueryMounted ? currentTabQuery() : "";
  const withTabQuery = (href: string) =>
    tabQuery ? `${href}${href.includes("?") ? "&" : "?"}${tabQuery}` : href;
  const [dueCount, setDueCount] = useState<number | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // P3-B 访问码门禁：带 u 且设置了 access_code 时弹浮层输码
  const [codeNeeded, setCodeNeeded] = useState(false);
  const [codeInput, setCodeInput] = useState("");
  // U2（第六篇）：首访身份引导——无 u 且无最近用户时弹"你叫什么名字？"
  const [welcomeOpen, setWelcomeOpen] = useState(false);
  const [welcomeName, setWelcomeName] = useState("");
  const navigate = useNavigate();
  const location = useLocation();

  // N1：下拉刷新状态
  const scrollRef = useRef<HTMLDivElement>(null);
  const touchStartRef = useRef<number | null>(null);
  const [pullY, setPullY] = useState(0);
  const [refreshing, setRefreshing] = useState(false);

  const onTouchStart = (e: React.TouchEvent) => {
    if (!onRefresh || refreshing) return;
    if ((scrollRef.current?.scrollTop ?? 0) <= 0) {
      touchStartRef.current = e.touches[0]?.clientY ?? null;
    }
  };
  const onTouchMove = (e: React.TouchEvent) => {
    if (touchStartRef.current === null || refreshing) return;
    const dy = (e.touches[0]?.clientY ?? 0) - touchStartRef.current;
    if (dy > 0 && (scrollRef.current?.scrollTop ?? 0) <= 0) {
      setPullY(Math.min(Math.round(dy * 0.45), 90));
    } else if (pullY !== 0) {
      setPullY(0);
    }
  };
  const onTouchEnd = async () => {
    touchStartRef.current = null;
    if (pullY >= 60 && onRefresh && !refreshing) {
      setRefreshing(true);
      setPullY(48);
      try {
        await onRefresh();
      } catch {
        /* 刷新失败不打断 */
      }
      setRefreshing(false);
    }
    setPullY(0);
  };

  // T4（第十二篇）：首次交互全局解锁 TTS——空播一次 + AudioContext resume。
  useEffect(() => {
    if (typeof window === "undefined") return;
    const unlock = () => {
      try {
        if ("speechSynthesis" in window) {
          window.speechSynthesis.speak(new SpeechSynthesisUtterance(""));
        }
        const AC =
          window.AudioContext || (window as any).webkitAudioContext;
        if (AC) {
          const ctx = new AC();
          Promise.resolve(ctx.resume?.()).catch(() => {});
          setTimeout(() => {
            try {
              ctx.close?.();
            } catch {
              /* ignore */
            }
          }, 300);
        }
      } catch {
        /* ignore */
      }
    };
    window.addEventListener("pointerdown", unlock, { once: true });
    return () => window.removeEventListener("pointerdown", unlock);
  }, []);

  // U2：触发条件 = 无 URL u/openid + 未声明管理员 + 无最近用户
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("u") || params.get("openid")) return;
    try {
      if (localStorage.getItem("h5_is_admin") === "1") return;
      // 三轨M11(U6)：onboarding 一次性——跳过/确认后不再弹（localStorage 标记）
      if (localStorage.getItem("h5_onboarding_done") === "1") return;
      const raw = localStorage.getItem("h5_recent_users");
      const recents = raw ? JSON.parse(raw) : [];
      if (Array.isArray(recents) && recents.length) return;
    } catch {
      return;
    }
    setWelcomeOpen(true);
  }, []);

  const confirmWelcome = () => {
    const name = welcomeName.trim();
    if (!name) return;
    try {
      localStorage.setItem("h5_onboarding_done", "1"); // 三轨M11：确认后亦一次性
    } catch { /* ignore */ }
    try {
      const raw = localStorage.getItem("h5_recent_users");
      const recents = raw ? JSON.parse(raw) : [];
      const next = [name, ...recents.filter((x: string) => x !== name)].slice(0, 5);
      localStorage.setItem("h5_recent_users", JSON.stringify(next));
    } catch {
      /* ignore */
    }
    setWelcomeOpen(false);
    // 全站生效：带 u 跳当前页
    navigate(withU(location.pathname, name), { replace: true });
  };

  const chooseAdmin = () => {
    try {
      localStorage.setItem("h5_is_admin", "1");
    } catch {
      /* ignore */
    }
    setWelcomeOpen(false);
  };

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const hasU = !!params.get("u") || !!params.get("openid");
    if (!hasU) return;
    // R4：URL 直达带 code —— 补写 sessionStorage（与解锁同源锚点）。
    const urlCode = params.get("code");
    if (urlCode) {
      try {
        if (sessionStorage.getItem("dsh_h5_code") !== urlCode) {
          sessionStorage.setItem("dsh_h5_code", urlCode);
          window.dispatchEvent(new Event("dsh-h5-code"));
        }
      } catch {
        /* ignore */
      }
      return;
    }
    try {
      if (sessionStorage.getItem("dsh_h5_code")) return;
    } catch {
      /* ignore */
    }
    void fetch("/api/v1/h5-settings")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d && d.access_code) setCodeNeeded(true);
      })
      .catch(() => {
        /* 离线不弹 */
      });
  }, []);

  // E3（M12）：离线答题 outbox —— 联网后自动补报，启动时尝试遗留
  useEffect(() => {
    if (typeof window === "undefined") return;
    const onOnline = () => {
      void import("./h5Outbox")
        .then((m) => m.replay())
        .then((n) => {
          if (n > 0) window.dispatchEvent(new Event("dsh-outbox-synced"));
        })
        .catch(() => { /* ignore */ });
    };
    window.addEventListener("online", onOnline);
    onOnline();
    return () => window.removeEventListener("online", onOnline);
  }, []);

  useEffect(() => {
    const fetchDue = async () => {
      try {
        const qs = u ? `?u=${encodeURIComponent(u)}` : "";
        const res = await fetch(`/api/v1/mother-questions/reviews/due_count${qs}`);
        if (res.ok) {
          const data = await res.json();
          setDueCount(typeof data.due_count === "number" ? data.due_count : null);
        }
      } catch {
        /* 角标是增强，失败不打扰 */
      }
    };
    void fetchDue();
    timerRef.current = setInterval(fetchDue, 60_000);
    const onFocus = () => void fetchDue();
    window.addEventListener("focus", onFocus);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      window.removeEventListener("focus", onFocus);
    };
  }, [u]);

  // P3-A PWA：注册 Service Worker（https / localhost 安全上下文才可用）
  useEffect(() => {
    if (
      typeof window !== "undefined" &&
      "serviceWorker" in navigator &&
      (window.location.protocol === "https:" ||
        window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1")
    ) {
      navigator.serviceWorker.register("/dsh-sw.js").catch(() => {
        /* SW 是增强，失败不影响使用 */
      });
    }
  }, []);

  // D2（M22）：SW 检测到新部署（dt-build 变化）→ 顶部黄条提示手动刷新。
  const [newVersion, setNewVersion] = useState(false);
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;
    const onMessage = (e: MessageEvent) => {
      if (isNewVersionMessage(e.data)) setNewVersion(true);
    };
    navigator.serviceWorker.addEventListener("message", onMessage);
    return () => navigator.serviceWorker.removeEventListener("message", onMessage);
  }, []);

  // 三轨M11(U6) §7.1：桌面=深色设备展台（手机框 390×844 居中+说明条+新窗口打开）；
  // 移动端（≤768px）原样全屏 H5 壳。matchMedia 即时判定（不订阅 resize——刷新生效即可）。
  const isDesktopViewport =
    typeof window !== "undefined" && !!window.matchMedia?.("(min-width: 769px)").matches;

  return (
    <div
      data-testid="h5-shell-root"
      style={
        isDesktopViewport
          ? {
              minHeight: "100vh",
              background: "linear-gradient(160deg,#0f172a 0%,#1e293b 100%)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              padding: "32px 16px",
            }
          : { display: "flex", flexDirection: "column", minHeight: "100vh" }
      }
    >
      {isDesktopViewport && (
        <div
          data-testid="h5-expo-banner"
          style={{
            maxWidth: 430, width: "100%", color: "#94a3b8", fontSize: 12,
            marginBottom: 12, display: "flex", justifyContent: "space-between",
          }}
        >
          <span>📱 私塾先生 h5 · 手机视图</span>
          <button
            data-testid="h5-new-window"
            onClick={() => window.open(window.location.href, "_blank")}
            style={{ background: "none", border: "none", color: "#60a5fa", cursor: "pointer", fontSize: 12 }}
          >
            新窗口打开 ↗
          </button>
        </div>
      )}
      <div
        style={
          isDesktopViewport
            ? {
                width: 390, height: 844, borderRadius: 36, overflow: "hidden",
                border: "10px solid #0b1220", boxShadow: "0 24px 64px rgba(0,0,0,.5)",
                background: "#f8fafc", display: "flex", flexDirection: "column",
              }
            : { display: "flex", flexDirection: "column", flex: 1, width: "100%" }
        }
      >
    // 根容器固定视口高度，内滚容器才能正确产生滚动条（否则随内容长高被裁掉）。
    <div
      className="dsh-h5"
      style={{
        height: "100dvh", background: "#f8fafc", display: "flex", flexDirection: "column",
        maxWidth: 448, margin: "0 auto", width: "100%", overflow: "hidden",
      }}
    >
      {newVersion && (
        <button
          onClick={() => window.location.reload()}
          data-testid="new-version-bar"
          style={{
            width: "100%", padding: "6px 0", background: "#fbbf24", color: "#451a03",
            fontSize: 12, fontWeight: 500, border: "none", cursor: "pointer", flexShrink: 0,
          }}
        >
          🆕 新版本已就绪，点此刷新
        </button>
      )}
      <div
        ref={scrollRef}
        data-testid="h5-scroller"
        style={{ minHeight: 0, flex: 1, overflowY: "auto", paddingBottom: hideNav ? 16 : 96 }}
        onTouchStart={onRefresh ? onTouchStart : undefined}
        onTouchMove={onRefresh ? onTouchMove : undefined}
        onTouchEnd={onRefresh ? () => void onTouchEnd() : undefined}
        onTouchCancel={onRefresh ? () => { touchStartRef.current = null; setPullY(0); } : undefined}
      >
        {onRefresh && (
          <div aria-hidden style={{ height: 0, position: "relative", zIndex: 10, pointerEvents: "none" }}>
            <div
              data-testid="pull-indicator"
              style={{
                transform: `translateY(${pullY - 34}px)`,
                display: "flex", alignItems: "center", justifyContent: "center", gap: 4,
                fontSize: 11, color: "#94a3b8", transition: "transform .15s",
              }}
            >
              {refreshing ? (
                <>
                  <LoadingOutlined style={{ fontSize: 14 }} spin /> 正在刷新…
                </>
              ) : pullY >= 60 ? (
                <>↑ 松手刷新</>
              ) : pullY > 8 ? (
                <>↓ 下拉刷新</>
              ) : null}
            </div>
          </div>
        )}
        {children}
      </div>
      {!hideNav && (
        <nav
          style={{
            position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 40, height: 64,
            background: "rgba(255,255,255,0.9)", backdropFilter: "blur(8px)",
            borderTop: "1px solid #e2e8f0",
          }}
        >
          <div style={{ display: "flex", height: "100%", alignItems: "stretch", maxWidth: 448, margin: "0 auto" }}>
            {TABS.map((tab) => {
              const Icon = tab.icon;
              const activeTab = active === tab.key;
              return (
                <Link
                  key={tab.key}
                  to={withTabQuery(tab.href)}
                  aria-label={tab.label}
                  aria-current={activeTab ? "page" : undefined}
                  style={{
                    position: "relative", flex: 1, display: "flex", flexDirection: "column",
                    alignItems: "center", justifyContent: "center", gap: 2,
                    color: activeTab ? "#4f46e5" : "#94a3b8", textDecoration: "none",
                  }}
                >
                  <span style={{ position: "relative" }}>
                    <Icon style={{ fontSize: 20 }} />
                    {tab.key === "wrongbook" && dueCount !== null && dueCount > 0 && (
                      <span
                        style={{
                          position: "absolute", top: -6, right: -10, minWidth: 16, height: 16,
                          padding: "0 4px", borderRadius: 999, background: "#f43f5e", color: "#fff",
                          fontSize: 10, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center",
                        }}
                      >
                        {dueCount > 99 ? "99+" : dueCount}
                      </span>
                    )}
                  </span>
                  <span style={{ fontSize: 10, lineHeight: 1 }}>{tab.label}</span>
                </Link>
              );
            })}
          </div>
        </nav>
      )}

      {/* U2 首访身份引导（第六篇）：无 u 且无最近用户时弹，避免数据静默进 admin */}
      <H5Sheet open={welcomeOpen} onClose={() => setWelcomeOpen(false)} align="center">
        <div style={{ padding: "24px" }}>
          <div style={{ fontSize: 30, marginBottom: 8, textAlign: "center" }}>👋</div>
          <h3 style={{ fontWeight: 700, fontSize: 18, textAlign: "center", marginBottom: 4, margin: "0 0 4px" }}>欢迎使用</h3>
          <p style={{ textAlign: "center", fontSize: 14, color: "#64748b", marginBottom: 16 }}>
            输入你的名字，学习记录专属保存
          </p>
          <input
            value={welcomeName}
            onChange={(e) => setWelcomeName(e.target.value)}
            placeholder="我叫…（如：小明）"
            maxLength={20}
            style={{ width: "100%", padding: "12px", borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 16, marginBottom: 12, boxSizing: "border-box" }}
          />
          <button
            data-testid="h5-onboarding-skip"
            onClick={() => {
              try { localStorage.setItem("h5_onboarding_done", "1"); } catch { /* ignore */ }
              setWelcomeOpen(false);
            }}
            style={{ width: "100%", padding: "6px 0", textAlign: "center", fontSize: 13, color: "#94a3b8", background: "none", border: "none", cursor: "pointer", marginBottom: 4 }}
          >
            跳过，先逛逛
          </button>
          <button
            onClick={confirmWelcome}
            disabled={!welcomeName.trim()}
            style={{
              width: "100%", padding: "12px 0", borderRadius: 12, background: "#4f46e5", color: "#fff",
              fontSize: 16, fontWeight: 600, border: "none", cursor: "pointer", opacity: welcomeName.trim() ? 1 : 0.5, marginBottom: 8,
            }}
          >
            开始学习
          </button>
          <button
            onClick={chooseAdmin}
            style={{ width: "100%", padding: "8px 0", textAlign: "center", fontSize: 14, color: "#94a3b8", background: "none", border: "none", cursor: "pointer" }}
          >
            我是管理员（进管理视图）
          </button>
        </div>
      </H5Sheet>

      {/* P3-B 访问码浮层：带 u + 设置了 access_code 且未解锁时弹 */}
      <H5Sheet open={codeNeeded} onClose={() => setCodeNeeded(false)} align="center" lockBody={false}>
        <div style={{ padding: "0 20px 20px" }}>
          <h3 style={{ fontWeight: 600, fontSize: 14, marginBottom: 8, margin: "0 0 8px" }}>🔒 输入访问码</h3>
          <p style={{ fontSize: 12, color: "#64748b", marginBottom: 12 }}>
            该学习空间设置了访问码，输入后即可继续使用。
          </p>
          {/* Q2（第九篇）：儿童侧「向家长索取」引导——门禁不是障碍而是家长知情 */}
          <div
            style={{ fontSize: 12, color: "#4f46e5", background: "#eef2ff", borderRadius: 12, padding: "8px 12px", marginBottom: 12 }}
            data-testid="ask-parent-hint"
          >
            🙋 不知道访问码？<span style={{ fontWeight: 500 }}>向家长索取</span>——请爸爸妈妈在「我的 → 分享」里查看或生成。
          </div>
          <input
            value={codeInput}
            onChange={(e) => setCodeInput(e.target.value)}
            placeholder="访问码"
            type="password"
            style={{ width: "100%", padding: "8px 12px", borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 14, marginBottom: 12, boxSizing: "border-box" }}
          />
          <button
            onClick={() => {
              try {
                sessionStorage.setItem("dsh_h5_code", codeInput.trim());
                window.dispatchEvent(new Event("dsh-h5-code"));
              } catch {
                /* ignore */
              }
              window.location.reload();
            }}
            disabled={!codeInput.trim()}
            style={{
              width: "100%", padding: "10px 0", borderRadius: 12, background: "#4f46e5", color: "#fff",
              fontSize: 14, fontWeight: 500, border: "none", cursor: "pointer", opacity: codeInput.trim() ? 1 : 0.5,
            }}
          >
            解锁
          </button>
        </div>
      </H5Sheet>
    </div>
      </div>
    </div>
  );
}
