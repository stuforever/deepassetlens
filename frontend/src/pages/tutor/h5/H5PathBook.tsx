/**
 * ── 复刻来源与替换点（tupu antd 复刻，批9 F2 / SA-D）────────────────────────
 * 源文件：DeepTutor web/app/h5/paths/[bookId]/page.tsx
 * 目标：frontend/src/pages/tutor/h5/H5PathBook.tsx（1:1 复刻，逻辑逐字保留）
 * 路由：/h5/paths/[bookId] → /e/tutor-h5/paths/:bookId（useParams 取 bookId）
 * 替换点：
 * - "use client" 删除；next/link → react-router Link；next/navigation（useParams/
 *   useSearchParams）→ react-router 同名 hooks；
 * - lucide（ChevronLeft/Loader2/Play/RotateCcw/Trash2/ChevronDown/Target/Trophy）→
 *   @ant-design/icons（LeftOutlined/LoadingOutlined/CaretRightOutlined/UndoOutlined/
 *   DeleteOutlined/DownOutlined/AimOutlined/TrophyOutlined）；
 * - "@/lib/learning-api" → "./h5shared/learningApi"；"@/lib/h5-utils" → "./h5shared/h5Utils"；
 *   "../../components/H5Shell" → "./h5shared/H5Shell"；链接前缀 /h5/* → /e/tutor-h5/*；
 * - window.confirm 中文文案逐字保留；window.location.href 跳转原样（路径映射后）；
 * - Tailwind → 内联样式逐项对位（STATUS_META 的 dot/bar 类名改为色值常量，语义一致）。
 * ─────────────────────────────────────────────────────────────────────
 */
import React, { useCallback, useEffect, useState, Suspense } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import {
  LeftOutlined,
  LoadingOutlined,
  CaretRightOutlined,
  UndoOutlined,
  DeleteOutlined,
  DownOutlined,
  AimOutlined,
  TrophyOutlined,
} from "@ant-design/icons";
import {
  fetchMasteryMap,
  redoProgress,
  deleteProgress,
  type MasteryMapResult,
} from "./h5shared/learningApi";
import { withU } from "./h5shared/h5Utils";
import { H5Shell } from "./h5shared/H5Shell";

/** active: 伪类等价注入。 */
const PRESS_CSS = `
.dsh-h5-press-slate:active{background:#f8fafc;}
`;

const STATUS_META: Record<string, { label: string; dot: string; bar: string }> = {
  mastered: { label: "已掌握", dot: "#10b981", bar: "#10b981" },
  learning: { label: "学习中", dot: "#3b82f6", bar: "#3b82f6" },
  new: { label: "未开始", dot: "#cbd5e1", bar: "#cbd5e1" },
};

function statusColor(status: string) {
  return STATUS_META[status]?.bar || "#cbd5e1";
}

function H5PathDetailContent() {
  const params = useParams();
  const [searchParams] = useSearchParams();
  const u = searchParams.get("u") || searchParams.get("openid") || "";
  const bookId = decodeURIComponent(params?.bookId || "");
  const [map, setMap] = useState<MasteryMapResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    if (!bookId) return;
    setLoading(true);
    fetchMasteryMap(bookId, u)
      .then((m) => {
        setMap(m);
        // 默认展开当前目标所在模块
        const nextKp = m.next?.knowledge_point_name;
        if (nextKp) {
          const mod = m.map.modules.find((x) =>
            x.knowledge_points.some((kp) => kp.name === nextKp),
          );
          if (mod) setExpanded((prev) => prev ?? mod.id);
        }
      })
      .catch(() => setError("加载失败，请重试"))
      .finally(() => setLoading(false));
  }, [bookId, u]);

  useEffect(() => {
    load();
  }, [load]);

  const doRedo = async () => {
    if (!window.confirm("重置将清空本路径全部掌握度，确定？")) return;
    setBusy(true);
    try {
      await redoProgress(bookId, u);
      load();
    } catch {
      setError("重置失败");
    } finally {
      setBusy(false);
    }
  };

  const doDelete = async () => {
    if (!window.confirm("删除后不可恢复，确定删除该路径？")) return;
    setBusy(true);
    try {
      await deleteProgress(bookId, u);
      window.location.href = withU("/e/tutor-h5/paths", u);
    } catch {
      setError("删除失败");
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <H5Shell active="home" hideNav>
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", color: "#94a3b8" }}>
          <LoadingOutlined spin style={{ fontSize: 20, marginRight: 8 }} /> 加载进度…
        </div>
      </H5Shell>
    );
  }

  if (error || !map) {
    return (
      <H5Shell active="home" hideNav>
        <div style={{ textAlign: "center", padding: "80px 32px", color: "#64748b" }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>📭</div>
          <div style={{ fontSize: 14 }}>{error || "路径不存在"}</div>
          <Link
            to={withU("/e/tutor-h5/paths", u)}
            style={{ marginTop: 16, display: "inline-block", padding: "8px 16px", borderRadius: 12, background: "#4f46e5", color: "#fff", fontSize: 14, textDecoration: "none" }}
          >
            返回路径列表
          </Link>
        </div>
      </H5Shell>
    );
  }

  const { map: m, next } = map;
  const avg =
    m.counts.total > 0
      ? Math.round(
          (m.modules.reduce(
            (n, mod) =>
              n +
              mod.knowledge_points.reduce(
                (s, kp) => s + (kp.mastery || 0),
                0,
              ),
            0,
          ) /
            m.counts.total) *
            100,
        )
      : 0;

  return (
    <H5Shell active="home" hideNav>
      <style>{PRESS_CSS}</style>
      {/* 顶栏 */}
      <div style={{ background: "linear-gradient(90deg, #f59e0b, #ea580c)", color: "#fff", padding: "40px 20px 56px", borderRadius: "0 0 24px 24px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Link to={withU("/e/tutor-h5/paths", u)} aria-label="返回" style={{ display: "flex", alignItems: "center", gap: 4, color: "#fff", fontSize: 14, textDecoration: "none" }}>
            <LeftOutlined style={{ fontSize: 24 }} /> 返回
          </Link>
          <div style={{ fontSize: 18, fontWeight: 700, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", padding: "0 8px" }}>{map.book_id}</div>
          <button onClick={doDelete} aria-label="删除" disabled={busy} style={{ color: "rgba(255,255,255,0.8)", background: "none", border: "none", cursor: "pointer" }}>
            <DeleteOutlined style={{ fontSize: 20 }} />
          </button>
        </div>
        <div style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ fontSize: 30, fontWeight: 700 }}>{avg}%</div>
          <div style={{ fontSize: 12, color: "#ffedd5" }}>
            <div>平均掌握</div>
            <div style={{ marginTop: 2 }}>
              {m.counts.mastered}/{m.counts.total} 已掌握
            </div>
          </div>
          <div style={{ marginLeft: "auto", textAlign: "right", fontSize: 12, color: "#ffedd5" }}>
            <div>{m.due_reviews} 项待复习</div>
            <div style={{ marginTop: 2 }}>{m.complete ? "🎉 全部完成" : "继续加油"}</div>
          </div>
        </div>
      </div>

      <div style={{ padding: "0 16px 40px", marginTop: -24 }}>
        {/* 进入辅导 / 重置 */}
        <div style={{ background: "#fff", borderRadius: 16, boxShadow: "0 1px 2px 0 rgba(0,0,0,.05)", border: "1px solid #e2e8f0", padding: 16 }}>
          <Link
            to={withU(`/e/tutor-h5/chat?mode=mastery&path=${encodeURIComponent(bookId)}`, u)}
            style={{
              display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
              padding: "12px 0", borderRadius: 16,
              background: "linear-gradient(90deg, #f59e0b, #ea580c)",
              color: "#fff", fontWeight: 500, textDecoration: "none",
            }}
          >
            <CaretRightOutlined style={{ fontSize: 16 }} /> 继续学习（AI 辅导）
          </Link>
          <div style={{ marginTop: 12, display: "flex", alignItems: "flex-start", gap: 8, fontSize: 12, color: "#64748b", background: "#f8fafc", borderRadius: 12, padding: 12 }}>
            <AimOutlined style={{ fontSize: 16, color: "#6366f1", marginTop: 2, flexShrink: 0 }} />
            <div>
              <span style={{ fontWeight: 500, color: "#334155" }}>下一步：</span>
              {next?.reason || "进入 AI 辅导，由引擎判断下一步"}
            </div>
          </div>
          <button
            onClick={doRedo}
            disabled={busy}
            style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#94a3b8", background: "none", border: "none", cursor: "pointer", padding: 0 }}
          >
            <UndoOutlined style={{ fontSize: 14 }} /> 重置进度
          </button>
        </div>

        {/* 模块卡片流 */}
        <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 12 }}>
          {m.modules.map((mod) => {
            const pct =
              mod.total > 0 ? Math.round((mod.mastered / mod.total) * 100) : 0;
            const open = expanded === mod.id;
            const kps = mod.knowledge_points;
            return (
              <div key={mod.id} style={{ background: "#fff", borderRadius: 16, boxShadow: "0 1px 2px 0 rgba(0,0,0,.05)", border: "1px solid #e2e8f0", overflow: "hidden" }}>
                <button
                  onClick={() => setExpanded(open ? null : mod.id)}
                  style={{ width: "100%", display: "flex", alignItems: "center", gap: 12, padding: 14, background: "none", border: "none", cursor: "pointer", boxSizing: "border-box" }}
                >
                  <div style={{ flex: 1, textAlign: "left" }}>
                    <div style={{ fontWeight: 500, color: "#1e293b" }}>{mod.name}</div>
                    <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 2 }}>
                      {mod.mastered}/{mod.total} 已掌握
                    </div>
                  </div>
                  <div style={{ width: 64 }}>
                    <div style={{ height: 6, borderRadius: 999, background: "#f1f5f9", overflow: "hidden" }}>
                      <div style={{ height: "100%", background: pct === 100 ? "#10b981" : "#6366f1", width: `${pct}%` }} />
                    </div>
                    <div style={{ fontSize: 10, color: "#94a3b8", textAlign: "right", marginTop: 2 }}>{pct}%</div>
                  </div>
                  <DownOutlined style={{ fontSize: 16, color: "#cbd5e1", transition: "transform .15s", transform: open ? "rotate(180deg)" : "none" }} />
                </button>

                {open && (
                  <div style={{ padding: "0 12px 12px", display: "flex", flexDirection: "column", gap: 4 }}>
                    {kps.length === 0 && (
                      <div style={{ fontSize: 12, color: "#94a3b8", padding: "8px 8px" }}>暂无知识点</div>
                    )}
                    {kps.map((kp) => {
                      const meta = STATUS_META[kp.status] || STATUS_META.new;
                      const isNext = next?.knowledge_point_name === kp.name;
                      const barPct = Math.min(100, Math.round((kp.mastery || 0) * 100));
                      return (
                        <div
                          key={kp.id}
                          className={isNext ? undefined : "dsh-h5-press-slate"}
                          style={{
                            display: "flex", alignItems: "center", gap: 10, padding: "8px 10px",
                            borderRadius: 12, boxSizing: "border-box",
                            border: `1px solid ${isNext ? "#fcd34d" : "transparent"}`,
                            background: isNext ? "rgba(255,251,235,0.6)" : "transparent",
                          }}
                        >
                          <span style={{ width: 8, height: 8, borderRadius: 999, flexShrink: 0, background: meta.dot }} />
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: 14, color: "#334155", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "flex", alignItems: "center", gap: 6 }}>
                              {kp.name}
                              {isNext && (
                                <span style={{ padding: "2px 4px", borderRadius: 4, background: "#fef3c7", color: "#b45309", fontSize: 10, fontWeight: 500, flexShrink: 0 }}>
                                  当前目标
                                </span>
                              )}
                            </div>
                            <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>{meta.label}</div>
                          </div>
                          <div style={{ width: 80 }}>
                            <div style={{ height: 6, borderRadius: 999, background: "#f1f5f9", overflow: "hidden" }}>
                              <div style={{ height: "100%", background: statusColor(kp.status), width: `${barPct}%` }} />
                            </div>
                            <div style={{ fontSize: 10, color: "#94a3b8", textAlign: "right", marginTop: 2 }}>
                              {Math.round((kp.mastery || 0) * 100)}%
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {m.complete && (
          <div style={{ marginTop: 16, textAlign: "center", padding: "32px 0", background: "#ecfdf5", borderRadius: 16, border: "1px solid #a7f3d0" }}>
            <TrophyOutlined style={{ fontSize: 32, color: "#10b981", display: "block", margin: "0 auto" }} />
            <div style={{ fontWeight: 500, color: "#047857", marginTop: 8 }}>恭喜！本路径已全部掌握 🎉</div>
          </div>
        )}
      </div>
    </H5Shell>
  );
}

export default function H5PathDetailPage() {
  return (
    <Suspense
      fallback={
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", color: "#94a3b8" }}>
          <LoadingOutlined spin style={{ fontSize: 20, marginRight: 8 }} /> 加载中…
        </div>
      }
    >
      <H5PathDetailContent />
    </Suspense>
  );
}
