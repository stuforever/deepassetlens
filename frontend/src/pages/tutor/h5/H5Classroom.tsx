/**
 * E2 家庭/班级聚合视图（M11）—— 零后端改动。原仓 app/h5/classroom/page.tsx 1:1 移植。
 *
 * 数据：GET /h5-links?parent=老师 -> children；对每个 child 并行拉
 * weekly-digest / learner-profile / due_count（全部带 u 且过访问码门禁），
 * 客户端聚合。Promise.allSettled 容忍单个孩子数据缺失。
 *
 * 教育伦理：不排名——卡片按「最近活跃」排序，展示各自对比基线的进步，
 * 不做孩子间分数排行。
 *
 * Q3（第九篇）：全员码板——A4 网格打印每个孩子的专属入口二维码，
 * 打印后贴教室墙上，孩子扫码即进自己的空间。
 *
 * 等价替换清单：
 * - "use client" 删除；next/navigation（useRouter/useSearchParams/Suspense 包裹）→
 *   react-router-dom（useNavigate/useSearchParams，Suspense 结构保留）；
 * - lucide → @ant-design/icons：Users→TeamOutlined、ChevronRight→RightOutlined、
 *   RefreshCw→SyncOutlined、Plus→PlusOutlined、Baby→SmileOutlined、QrCode→QrcodeOutlined；
 * - qrcode.react QRCodeCanvas → h5shared/QrCode 的 QrCanvas（内联实现，不加包，见 QrCode.tsx 头注）；
 * - notify(...) → antd message.success / message.error（中文文案逐字）；
 * - Tailwind → 内联样式逐项对位（active:/hover:/print: 变体随共享层先例省略，
 *   print:hidden 以补充的 @media print 规则 .dsh-print-hidden 等价实现）；
 * - fetch(apiUrl(...)) → fetch('/api/v1/...') 逐字；
 * - 路由前缀映射：原 /h5/* → /e/tutor-h5/*。
 */
import { Suspense, useCallback, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  TeamOutlined, RightOutlined, SyncOutlined, PlusOutlined, SmileOutlined, QrcodeOutlined,
} from "@ant-design/icons";
import { message } from "antd";
import { H5Shell } from "./h5shared/H5Shell";
import { H5Sheet } from "./h5shared/H5Sheet";
import { QrCanvas } from "./h5shared/QrCode";

interface ChildCard {
  child: string;
  note?: string;
  attempts: number;
  accuracy: number | null;
  topGain: { kp_name: string; delta: number } | null;
  due: number;
  daysAgo: number | null;
}

function ClassroomContent() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const teacher = searchParams.get("u") || searchParams.get("openid") || "";
  const [children, setChildren] = useState<ChildCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [newChild, setNewChild] = useState("");
  // Q3：全员码板浮层
  const [boardOpen, setBoardOpen] = useState(false);
  const [originBase, setOriginBase] = useState("");

  useEffect(() => {
    // 码板基址：后端 public_base > 当前 origin（与 share 页同源逻辑）
    let local = "";
    try {
      local = localStorage.getItem("h5_public_base") || "";
    } catch {
      /* ignore */
    }
    setOriginBase(local || window.location.origin);
    void fetch("/api/v1/h5-settings")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d?.public_base) setOriginBase(String(d.public_base));
      })
      .catch(() => {});
  }, []);

  const load = useCallback(
    async (quiet = false) => {
      if (!teacher) {
        setChildren([]);
        setLoading(false);
        return;
      }
      if (!quiet) setLoading(true);
      setRefreshing(true);
      try {
        const res = await fetch(
          `/api/v1/h5-links?parent=${encodeURIComponent(teacher)}`,
        );
        if (!res.ok) {
          setChildren([]);
          return;
        }
        const data = await res.json();
        const kids: string[] = (data.children || []).map((c: { child: string }) => c.child);
        const results = await Promise.allSettled(
          kids.map(async (child: string) => {
            const [wk, due, pr] = await Promise.all([
              fetch(
                `/api/v1/learning/weekly-digest?u=${encodeURIComponent(child)}`,
              ).then((r) => (r.ok ? r.json() : null)),
              fetch(
                `/api/v1/mother-questions/reviews/due_count?u=${encodeURIComponent(child)}`,
              ).then((r) => (r.ok ? r.json() : null)),
              fetch(
                `/api/v1/learning/profile?u=${encodeURIComponent(child)}`,
              ).then((r) => (r.ok ? r.json() : null)),
            ]);
            let daysAgo: number | null = null;
            if (pr?.updated_at) {
              try {
                const d =
                  (Date.now() - new Date(pr.updated_at).getTime()) / 86_400_000;
                daysAgo = Math.max(0, Math.floor(d));
              } catch {
                /* ignore */
              }
            }
            const topGain =
              wk?.top_improved && wk.top_improved.length
                ? {
                    kp_name: String(wk.top_improved[0].kp_name || ""),
                    delta: Number(wk.top_improved[0].delta || 0),
                  }
                : null;
            return {
              child,
              attempts: Number(wk?.attempts || 0),
              accuracy:
                typeof wk?.accuracy === "number" ? Number(wk.accuracy) : null,
              topGain,
              due:
                typeof due?.due_count === "number" ? Number(due.due_count) : 0,
              daysAgo,
            };
          }),
        );
        const cards = results
          .filter((r): r is PromiseFulfilledResult<ChildCard> => r.status === "fulfilled")
          .map((r) => r.value);
        // 不排名：按最近活跃排序
        cards.sort((a, b) => (a.daysAgo ?? 999) - (b.daysAgo ?? 999));
        setChildren(cards);
      } catch {
        setChildren([]);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [teacher],
  );

  useEffect(() => {
    void load();
  }, [load]);

  const addChild = async () => {
    const name = newChild.trim();
    if (!name) return;
    try {
      const res = await fetch("/api/v1/h5-links", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ parent: teacher, child: name }),
      });
      if (res.ok) {
        message.success(`已关联 ${name}`);
        setNewChild("");
        setAddOpen(false);
        void load(true);
      } else {
        const d = await res.json().catch(() => null);
        message.error(d?.detail || "关联失败");
      }
    } catch {
      message.error("关联失败（网络错误）");
    }
  };

  return (
    <H5Shell active="classroom">
      <div style={{ padding: 16, maxWidth: 512, margin: "0 auto" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <h1 style={{ fontSize: 18, fontWeight: 700, display: "flex", alignItems: "center", gap: 8, margin: 0 }}>
            <TeamOutlined style={{ fontSize: 20, color: "#6366f1" }} /> 我的孩子
            <span style={{ fontSize: 14, color: "#94a3b8", fontWeight: 400 }}>
              {children.length} 人
            </span>
          </h1>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <button
              onClick={() => void load(true)}
              disabled={refreshing}
              style={{ padding: 8, borderRadius: 9999, border: "1px solid #e2e8f0", color: "#64748b", background: "none", cursor: "pointer", opacity: refreshing ? 0.4 : 1 }}
              aria-label="刷新"
            >
              <SyncOutlined style={{ fontSize: 16 }} spin={refreshing} />
            </button>
            {children.length > 0 && (
              <button
                onClick={() => setBoardOpen(true)}
                data-testid="board-open-btn"
                style={{ padding: "6px 12px", borderRadius: 12, border: "1px solid #c7d2fe", background: "#eef2ff", color: "#4f46e5", fontSize: 14, display: "flex", alignItems: "center", gap: 4, cursor: "pointer" }}
              >
                <QrcodeOutlined style={{ fontSize: 16 }} /> 全员码板
              </button>
            )}
            <button
              onClick={() => setAddOpen(true)}
              style={{ padding: "6px 12px", borderRadius: 12, background: "#4f46e5", color: "#fff", fontSize: 14, display: "flex", alignItems: "center", gap: 4, border: "none", cursor: "pointer" }}
            >
              <PlusOutlined style={{ fontSize: 16 }} /> 关联孩子
            </button>
          </div>
        </div>

        {loading && (
          <div style={{ textAlign: "center", color: "#94a3b8", fontSize: 14, padding: "40px 0" }}>加载中…</div>
        )}

        {!loading && children.length === 0 && (
          <div style={{ textAlign: "center", color: "#94a3b8", fontSize: 14, padding: "40px 0", display: "flex", flexDirection: "column", gap: 12 }}>
            <div>还没有关联孩子。</div>
            <div style={{ fontSize: 12 }}>
              让家长在「我的-家庭关联」里关联你，或在下方直接添加。
            </div>
            <button
              onClick={() => setAddOpen(true)}
              style={{ margin: "0 auto", padding: "8px 16px", borderRadius: 12, border: "1px solid #e2e8f0", color: "#4f46e5", fontSize: 14, display: "flex", alignItems: "center", gap: 4, background: "none", cursor: "pointer" }}
            >
              <PlusOutlined style={{ fontSize: 16 }} /> 直接添加孩子
            </button>
          </div>
        )}

        {!loading && children.length > 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {children.map((c) => (
              <button
                key={c.child}
                onClick={() =>
                  navigate(`/e/tutor-h5/report?u=${encodeURIComponent(teacher)}&child=${encodeURIComponent(c.child)}`)
                }
                style={{ width: "100%", background: "#fff", borderRadius: 16, boxShadow: "0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px -1px rgba(0,0,0,0.1)", border: "1px solid #e2e8f0", padding: 16, textAlign: "left", cursor: "pointer" }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <SmileOutlined style={{ fontSize: 20, color: "#0ea5e9" }} />
                  <span style={{ fontWeight: 600 }}>{c.child}</span>
                  <span style={{ marginLeft: "auto", fontSize: 14, color: "#64748b" }}>
                    本周 {c.attempts} 题
                    {c.accuracy != null && (
                      <span style={{ marginLeft: 4 }}>
                        · {Math.round(c.accuracy * 100)}%
                      </span>
                    )}
                  </span>
                </div>
                <div style={{ fontSize: 14, color: "#475569", display: "flex", flexDirection: "column", gap: 2 }}>
                  {c.topGain && c.topGain.kp_name ? (
                    <div>
                      最大进步：{c.topGain.kp_name}{" "}
                      <span style={{ color: "#16a34a" }}>
                        ↑{Math.round((c.topGain.delta || 0) * 100)}%
                      </span>
                    </div>
                  ) : (
                    <div style={{ color: "#94a3b8" }}>本周暂无掌握度提升</div>
                  )}
                  <div style={{ fontSize: 12, color: "#94a3b8" }}>
                    待复习 {c.due}
                    {c.daysAgo != null &&
                      ` · ${c.daysAgo === 0 ? "今天活跃" : `${c.daysAgo} 天前活跃`}`}
                  </div>
                </div>
                <div style={{ marginTop: 4, display: "flex", alignItems: "center", justifyContent: "flex-end", fontSize: 12, color: "#6366f1" }}>
                  查看详情 <RightOutlined style={{ fontSize: 14 }} />
                </div>
              </button>
            ))}
          </div>
        )}

        {/* Q3：全员码板（A4 网格；打印时仅显示码板） */}
        {boardOpen && (
          <div style={{ position: "fixed", inset: 0, zIndex: 60, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "flex-start", justifyContent: "center", overflowY: "auto", padding: 16 }}>
            <div style={{ background: "#fff", width: "100%", maxWidth: 768, borderRadius: 16, boxShadow: "0 20px 25px -5px rgba(0,0,0,.1), 0 8px 10px -6px rgba(0,0,0,.1)", padding: 20 }}>
              <div className="dsh-print-hidden" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>🧑‍🏫 全员码板（{children.length} 人）</h3>
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    onClick={() => window.print()}
                    data-testid="board-print-btn"
                    style={{ padding: "6px 12px", borderRadius: 12, background: "#4f46e5", color: "#fff", fontSize: 14, border: "none", cursor: "pointer" }}
                  >
                    🖨️ 打印
                  </button>
                  <button
                    onClick={() => setBoardOpen(false)}
                    style={{ padding: "6px 12px", borderRadius: 12, border: "1px solid #e2e8f0", color: "#64748b", fontSize: 14, background: "none", cursor: "pointer" }}
                  >
                    关闭
                  </button>
                </div>
              </div>
              <div className="qr-board" style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 16 }} data-testid="qr-board">
                {children.map((c) => {
                  const link = `${originBase.replace(/\/$/, "")}/e/tutor-h5?u=${encodeURIComponent(c.child)}`;
                  return (
                    <div
                      key={c.child}
                      style={{ border: "1px solid #e2e8f0", borderRadius: 16, padding: 12, display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center" }}
                    >
                      <QrCanvas value={link} size={132} level="M" />
                      <div style={{ marginTop: 8, fontSize: 14, fontWeight: 600 }}>{c.child}</div>
                      <div style={{ fontSize: 10, color: "#94a3b8", wordBreak: "break-all" }}>{link}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {addOpen && (
          <H5Sheet
            open
            onClose={() => setAddOpen(false)}
            title="关联孩子"
            align="center"
          >
            <div style={{ padding: "0 20px 20px" }}>
              <p style={{ fontSize: 12, color: "#64748b", marginBottom: 12 }}>
                输入孩子的 H5 用户名（与「我的-家庭关联」一致）。
              </p>
              <input
                value={newChild}
                onChange={(e) => setNewChild(e.target.value)}
                placeholder="如：小明"
                maxLength={20}
                style={{ width: "100%", padding: "10px 12px", minHeight: 44, borderRadius: 12, border: "1px solid #e2e8f0", fontSize: 14, marginBottom: 12, boxSizing: "border-box" }}
              />
              <button
                onClick={() => void addChild()}
                disabled={!newChild.trim()}
                style={{ width: "100%", padding: "10px 0", minHeight: 44, borderRadius: 12, background: "#4f46e5", color: "#fff", fontSize: 14, fontWeight: 500, border: "none", cursor: "pointer", opacity: newChild.trim() ? 1 : 0.5 }}
              >
                确认关联
              </button>
            </div>
          </H5Sheet>
        )}
      </div>
    </H5Shell>
  );
}

export default function H5Classroom() {
  return (
    <Suspense fallback={<div style={{ padding: 24, fontSize: 14, color: "#94a3b8" }}>加载中…</div>}>
      <ClassroomContent />
    </Suspense>
  );
}

/* Q3：打印全员码板时只显示码板网格（原样式表逐字移植；
   追加 .dsh-print-hidden 等价原 print:hidden 变体） */
if (typeof document !== "undefined") {
  const style = document.createElement("style");
  style.textContent = `@media print {
    body > * { visibility: hidden !important; }
    .qr-board, .qr-board * { visibility: visible !important; }
    .qr-board { position: absolute; inset: 0; background: #fff; padding: 12mm; }
    .dsh-print-hidden { display: none !important; }
  }`;
  document.head.appendChild(style);
}
