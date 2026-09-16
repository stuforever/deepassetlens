/**
 * ── 复刻来源与替换点（tupu antd 复刻，批9 F2 / SA-D）────────────────────────
 * 源文件：DeepTutor web/app/h5/paths/page.tsx
 * 目标：frontend/src/pages/tutor/h5/H5Paths.tsx（1:1 复刻，逻辑逐字保留）
 * 路由：/h5/paths → /e/tutor/h5/paths
 * 替换点：
 * - "use client" 删除（tupu 为 CRA/SPA，无 RSC）；next/link → react-router Link；
 *   next/navigation useSearchParams → react-router useSearchParams；
 * - lucide（BookOpen/ChevronLeft/ChevronRight/ChevronDown/Loader2/Plus/CheckCircle2/
 *   Trophy/Target/Sparkles）→ @ant-design/icons（ReadOutlined/LeftOutlined/RightOutlined/
 *   LoadingOutlined/PlusOutlined/CheckCircleOutlined/TrophyOutlined/AimOutlined/StarOutlined）；
 *   ChevronDown 原仓 import 后未使用，不移植；
 * - "@/lib/learning-api" → "./h5shared/learningApi"；"@/lib/self-learning-api" →
 *   "./h5shared/selfLearningApi"；"@/lib/h5-utils" → "./h5shared/h5Utils"；
 *   fetch(apiUrl('/api/v1/...')) → fetch('/api/v1/...')（apiUrl pass-through 脱壳）；
 * - "@/components/h5/H5Sheet" 与 ../components/H5Shell → "./h5shared/H5Sheet" /
 *   "./h5shared/H5Shell"；站内链接前缀 /h5/* → /e/tutor/h5/*；
 * - Tailwind → 内联样式逐项对位（active:/focus: 伪类用注入 CSS 类等价实现）。
 * ─────────────────────────────────────────────────────────────────────
 */
import React, { useCallback, useEffect, useState, Suspense } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  ReadOutlined,
  LeftOutlined,
  RightOutlined,
  LoadingOutlined,
  PlusOutlined,
  CheckCircleOutlined,
  TrophyOutlined,
  AimOutlined,
  StarOutlined,
} from "@ant-design/icons";
import { fetchAllProgress, importFromBook } from "./h5shared/learningApi";
import {
  fetchTextbookTree,
  type TextbookNode,
  type ChapterNode,
} from "./h5shared/selfLearningApi";
import { withU } from "./h5shared/h5Utils";
import { H5Shell } from "./h5shared/H5Shell";
import { H5Sheet } from "./h5shared/H5Sheet";

/** active:/focus: 伪类等价注入（Tailwind 内联样式无法表达的按下/聚焦态）。 */
const PRESS_CSS = `
.dsh-h5-press-slate:active{background:#f8fafc;}
.dsh-h5-input:focus{border-color:#818cf8;}
`;

/** 顶部进度环（极简 SVG 圆环）。 */
function MasteryRing({ pct, size = 56 }: { pct: number; size?: number }) {
  const r = (size - 8) / 2;
  const c = 2 * Math.PI * r;
  const off = c * (1 - Math.min(100, Math.max(0, pct)) / 100);
  const color = pct >= 70 ? "#10b981" : pct >= 40 ? "#6366f1" : "#f59e0b";
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth={5} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={5}
          strokeDasharray={c}
          strokeDashoffset={off}
          strokeLinecap="round"
        />
      </svg>
      <div
        style={{
          position: "absolute", inset: 0, display: "flex", alignItems: "center",
          justifyContent: "center", fontSize: 14, fontWeight: 700, color,
        }}
      >
        {Math.round(pct)}%
      </div>
    </div>
  );
}

/** 创建向导：3 步（选教材 → 勾选章节 → 命名保存）。H5 简化版，复杂编辑回桌面。 */
function CreateWizard({
  u,
  onClose,
  onCreated,
}: {
  u: string;
  onClose: () => void;
  onCreated: (bookId: string) => void;
}) {
  const [step, setStep] = useState(1);
  const [textbooks, setTextbooks] = useState<TextbookNode[]>([]);
  const [tbLoading, setTbLoading] = useState(true);
  const [selectedTb, setSelectedTb] = useState<TextbookNode | null>(null);
  const [selectedChapters, setSelectedChapters] = useState<Set<string>>(new Set());
  const [kpNameMap, setKpNameMap] = useState<Record<string, string>>({});
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchTextbookTree()
      .then((data) => setTextbooks(data || []))
      .catch(() => setTextbooks([]))
      .finally(() => setTbLoading(false));
  }, []);

  // 加载全部知识点 id->name（组包用，内容管理端共享）
  useEffect(() => {
    fetch("/api/v1/curriculum/knowledge-points")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        const map: Record<string, string> = {};
        for (const k of d?.items || []) map[k.id] = k.name;
        setKpNameMap(map);
      })
      .catch(() => {});
  }, []);

  const flatChapters = (tb: TextbookNode): ChapterNode[] => {
    const out: ChapterNode[] = [];
    const walk = (chs: ChapterNode[]) => {
      for (const ch of chs) {
        if (ch.children && ch.children.length) walk(ch.children);
        else out.push(ch);
      }
    };
    walk(tb.chapters || []);
    return out;
  };

  const chapters = selectedTb ? flatChapters(selectedTb) : [];
  const selectedList = chapters.filter((c) => selectedChapters.has(c.id));
  const kpCount = selectedList.reduce(
    (n, c) => n + (c.kp_ids || []).filter((k) => kpNameMap[k]).length,
    0,
  );

  const toggle = (id: string) => {
    setSelectedChapters((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const save = async () => {
    const bookId = name.trim();
    if (!bookId || selectedList.length === 0) return;
    setSaving(true);
    setError("");
    try {
      const chaptersPayload = selectedList.map((c) => ({
        title: c.name,
        knowledge_points: (c.kp_ids || [])
          .map((k) => kpNameMap[k])
          .filter((n): n is string => Boolean(n)),
      }));
      const res = await importFromBook(bookId, chaptersPayload, u);
      if (res.status !== "ok") throw new Error(res.detail || "创建失败");
      onCreated(bookId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "创建失败");
    } finally {
      setSaving(false);
    }
  };

  const stepIndicator = (
    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 16 }}>
      {["选教材", "选章节", "命名"].map((label, i) => (
        <div key={label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <div
            style={{
              width: 24, height: 24, borderRadius: 999, fontSize: 12,
              display: "flex", alignItems: "center", justifyContent: "center",
              background:
                step === i + 1 ? "#4f46e5" : step > i + 1 ? "#10b981" : "#e2e8f0",
              color: step === i + 1 || step > i + 1 ? "#fff" : "#64748b",
            }}
          >
            {step > i + 1 ? <CheckCircleOutlined style={{ fontSize: 14 }} /> : i + 1}
          </div>
          <span
            style={{
              fontSize: 12,
              color: step === i + 1 ? "#1e293b" : "#94a3b8",
              fontWeight: step === i + 1 ? 500 : 400,
            }}
          >
            {label}
          </span>
          {i < 2 && <RightOutlined style={{ fontSize: 12, color: "#cbd5e1" }} />}
        </div>
      ))}
    </div>
  );

  return (
    // S1（M23）：H5Sheet 统一基座（多步向导底部弹层）
    <H5Sheet open onClose={onClose} title="🏆 新建精通之路">
      <div style={{ padding: "0 20px", paddingBottom: "max(1rem, env(safe-area-inset-bottom))" }}>
        {stepIndicator}

        {step === 1 && (
          <>
            {tbLoading ? (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "40px 0", color: "#94a3b8" }}>
                <LoadingOutlined spin style={{ fontSize: 20, marginRight: 8 }} /> 加载教材…
              </div>
            ) : textbooks.length === 0 ? (
              <div style={{ textAlign: "center", padding: "40px 0", color: "#94a3b8", fontSize: 14 }}>暂无可选教材</div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {textbooks.map((tb) => (
                  <button
                    key={tb.id}
                    onClick={() => {
                      setSelectedTb(tb);
                      setSelectedChapters(new Set());
                      setStep(2);
                    }}
                    className="dsh-h5-press-slate"
                    style={{
                      width: "100%", textAlign: "left", display: "flex", alignItems: "center",
                      gap: 12, padding: 12, borderRadius: 16, border: "1px solid #e2e8f0",
                      background: "none", cursor: "pointer", boxSizing: "border-box",
                    }}
                  >
                    <div style={{ width: 40, height: 40, borderRadius: 12, background: "#eff6ff", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                      <ReadOutlined style={{ fontSize: 20, color: "#2563eb" }} />
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 500, color: "#1e293b" }}>{tb.name}</div>
                      <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 2 }}>
                        {tb.subject} · {tb.grade || "通用"} · {(tb.chapters || []).length} 章
                      </div>
                    </div>
                    <RightOutlined style={{ fontSize: 16, color: "#cbd5e1" }} />
                  </button>
                ))}
              </div>
            )}
          </>
        )}

        {step === 2 && selectedTb && (
          <>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <button
                onClick={() => setStep(1)}
                style={{ fontSize: 12, color: "#64748b", display: "flex", alignItems: "center", background: "none", border: "none", cursor: "pointer", padding: 0 }}
              >
                <LeftOutlined style={{ fontSize: 14 }} /> 返回
              </button>
              <span style={{ fontSize: 14, fontWeight: 500, color: "#334155", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{selectedTb.name}</span>
            </div>
            <div style={{ fontSize: 12, color: "#64748b", marginBottom: 8 }}>
              已选 <b style={{ color: "#4f46e5" }}>{selectedList.length}</b> 章 · 约{" "}
              <b style={{ color: "#4f46e5" }}>{kpCount}</b> 个知识点
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: "52vh", overflowY: "auto" }}>
              {chapters.map((ch) => {
                const kpNames = (ch.kp_ids || [])
                  .map((k) => kpNameMap[k])
                  .filter(Boolean);
                const checked = selectedChapters.has(ch.id);
                return (
                  <button
                    key={ch.id}
                    onClick={() => toggle(ch.id)}
                    style={{
                      width: "100%", textAlign: "left", display: "flex", alignItems: "flex-start",
                      gap: 12, padding: 12, borderRadius: 12, cursor: "pointer", boxSizing: "border-box",
                      border: `1px solid ${checked ? "#818cf8" : "#e2e8f0"}`,
                      background: checked ? "rgba(238,242,255,0.6)" : "#fff",
                    }}
                  >
                    <div
                      style={{
                        marginTop: 2, width: 20, height: 20, borderRadius: 6,
                        display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                        background: checked ? "#4f46e5" : "transparent",
                        border: `1px solid ${checked ? "#4f46e5" : "#cbd5e1"}`,
                      }}
                    >
                      {checked && <CheckCircleOutlined style={{ fontSize: 16, color: "#fff" }} />}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 14, fontWeight: 500, color: "#1e293b" }}>{ch.name}</div>
                      <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>
                        {kpNames.length ? `${kpNames.length} 个知识点 · ${kpNames.slice(0, 3).join("、")}${kpNames.length > 3 ? "…" : ""}` : "暂无知识点"}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
            <button
              disabled={selectedList.length === 0}
              onClick={() => setStep(3)}
              style={{
                marginTop: 16, width: "100%", padding: "12px 0", borderRadius: 16,
                background: "#4f46e5", color: "#fff", fontWeight: 500, fontSize: 14,
                border: "none", cursor: "pointer", opacity: selectedList.length === 0 ? 0.4 : 1,
              }}
            >
              下一步（{selectedList.length} 章）
            </button>
          </>
        )}

        {step === 3 && (
          <>
            <div style={{ fontSize: 12, color: "#64748b", marginBottom: 12 }}>
              将创建 <b style={{ color: "#4f46e5" }}>{selectedList.length}</b> 章 ·{" "}
              <b style={{ color: "#4f46e5" }}>{kpCount}</b> 个知识点的精通之路
            </div>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="路径名称，如：有理数精讲"
              className="dsh-h5-input"
              style={{
                width: "100%", padding: "12px 16px", borderRadius: 12, border: "1px solid #e2e8f0",
                background: "#fff", fontSize: 14, outline: "none", boxSizing: "border-box",
              }}
            />
            <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 6, maxHeight: "40vh", overflowY: "auto" }}>
              {selectedList.map((c) => (
                <div key={c.id} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14, color: "#475569", padding: "0 4px" }}>
                  <AimOutlined style={{ fontSize: 14, color: "#818cf8", flexShrink: 0 }} />
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.name}</span>
                  <span style={{ fontSize: 11, color: "#94a3b8", marginLeft: "auto", flexShrink: 0 }}>
                    {(c.kp_ids || []).filter((k) => kpNameMap[k]).length} KP
                  </span>
                </div>
              ))}
            </div>
            {error && <div style={{ marginTop: 12, fontSize: 14, color: "#f43f5e" }}>{error}</div>}
            <div style={{ marginTop: 20, display: "flex", gap: 8 }}>
              <button
                onClick={() => setStep(2)}
                style={{ flex: 1, padding: "12px 0", borderRadius: 16, border: "1px solid #e2e8f0", color: "#475569", fontSize: 14, background: "none", cursor: "pointer" }}
              >
                上一步
              </button>
              <button
                disabled={!name.trim() || saving}
                onClick={save}
                style={{
                  flex: 1, padding: "12px 0", borderRadius: 16, background: "#4f46e5", color: "#fff",
                  fontSize: 14, fontWeight: 500, border: "none", cursor: "pointer",
                  opacity: !name.trim() || saving ? 0.4 : 1,
                  display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                }}
              >
                {saving ? <LoadingOutlined spin style={{ fontSize: 16 }} /> : <StarOutlined style={{ fontSize: 16 }} />}
                创建
              </button>
            </div>
          </>
        )}
      </div>
    </H5Sheet>
  );
}

function H5PathsContent() {
  const [searchParams] = useSearchParams();
  const u = searchParams.get("u") || searchParams.get("openid") || "";
  const [summaries, setSummaries] = useState<
    { book_id: string; name: string; modules_count: number; kp_count: number; avg_mastery_pct: number }[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [wizard, setWizard] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    fetchAllProgress(u)
      .then((d) => {
        setSummaries((d.summaries || []).filter((s) => s.book_id !== "auto" || true));
      })
      .catch(() => setSummaries([]))
      .finally(() => setLoading(false));
  }, [u]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <H5Shell active="home">
      <style>{PRESS_CSS}</style>
      {/* 顶栏 */}
      <div style={{ background: "linear-gradient(90deg, #f59e0b, #ea580c)", color: "#fff", padding: "40px 20px 56px", borderRadius: "0 0 24px 24px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ fontSize: 18, fontWeight: 700, display: "flex", alignItems: "center", gap: 6 }}>
            <TrophyOutlined style={{ fontSize: 20 }} /> 精通之路
          </div>
          <button
            onClick={() => setWizard(true)}
            style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 12, background: "rgba(255,255,255,0.2)", borderRadius: 999, padding: "6px 12px", border: "none", color: "#fff", cursor: "pointer" }}
          >
            <PlusOutlined style={{ fontSize: 14 }} /> 新建路径
          </button>
        </div>
        <div style={{ marginTop: 6, color: "#ffedd5", fontSize: 12 }}>
          引导式掌握学习 · 诊断 → 讲解 → 出题 → 复习
        </div>
      </div>

      <div style={{ padding: "0 16px 40px", marginTop: -32 }}>
        {loading ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "64px 0", color: "#94a3b8" }}>
            <LoadingOutlined spin style={{ fontSize: 20, marginRight: 8 }} /> 加载路径…
          </div>
        ) : summaries.length === 0 ? (
          <div style={{ textAlign: "center", padding: "64px 0", background: "#fff", borderRadius: 16, boxShadow: "0 1px 2px 0 rgba(0,0,0,.05)", border: "1px solid #e2e8f0" }}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>🏆</div>
            <div style={{ fontWeight: 500, color: "#334155" }}>还没有精通之路</div>
            <div style={{ fontSize: 14, color: "#94a3b8", marginTop: 8, padding: "0 32px" }}>
              从「新建路径」开始，或先在 <b>学习</b> 里做题——系统会自动为你生成影子学习路径
            </div>
            <Link
              to={withU("/e/tutor/h5/learn", u)}
              style={{ marginTop: 16, display: "inline-block", padding: "10px 20px", borderRadius: 12, background: "#4f46e5", color: "#fff", fontSize: 14, textDecoration: "none" }}
            >
              📚 去做题
            </Link>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {summaries.map((s) => {
              const isAuto = s.book_id.startsWith("h5_auto_") || s.book_id.startsWith("shadow_");
              return (
                <Link
                  key={s.book_id}
                  to={withU(`/e/tutor/h5/paths/${encodeURIComponent(s.book_id)}`, u)}
                  style={{ display: "block", background: "#fff", borderRadius: 16, boxShadow: "0 1px 2px 0 rgba(0,0,0,.05)", border: "1px solid #e2e8f0", padding: 16, textDecoration: "none" }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <MasteryRing pct={s.avg_mastery_pct} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontWeight: 600, color: "#1e293b", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.name}</span>
                        {isAuto && (
                          <span style={{ padding: "2px 6px", borderRadius: 4, background: "#fef3c7", color: "#b45309", fontSize: 10, fontWeight: 500, flexShrink: 0 }}>
                            自动生成
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>
                        {s.modules_count} 章 · {s.kp_count} 个知识点
                      </div>
                      <div style={{ fontSize: 12, color: "#4f46e5", marginTop: 6, display: "flex", alignItems: "center" }}>
                        继续学习 <RightOutlined style={{ fontSize: 14 }} />
                      </div>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>

      {wizard && (
        <CreateWizard
          u={u}
          onClose={() => setWizard(false)}
          onCreated={(bookId) => {
            setWizard(false);
            load();
          }}
        />
      )}
    </H5Shell>
  );
}

export default function H5PathsPage() {
  return (
    <Suspense
      fallback={
        <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", color: "#94a3b8" }}>
          <LoadingOutlined spin style={{ fontSize: 20, marginRight: 8 }} /> 加载中…
        </div>
      }
    >
      <H5PathsContent />
    </Suspense>
  );
}
